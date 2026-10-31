"""Observable multi-plane sunlight and shadow simulation with surveyed geometry."""
from __future__ import annotations
import math
from datetime import datetime, timedelta
from shapely.geometry import box
from app.schemas import SceneRequest, SunRequest
from app.services.solar import sun_position
from app.services.geometry import build_context, overlap_ratio, direct_sun_reaches, obstacle_elevations, surface_z, _parts


def polygons(shape):
    if shape is None or shape.is_empty:
        return []
    if shape.geom_type == "Polygon":
        return [[[round(x, 4), round(y, 4)] for x, y in shape.exterior.coords]]
    return [p for g in getattr(shape, "geoms", []) for p in polygons(g)]


def regions(shape):
    if shape is None or shape.is_empty:return []
    if shape.geom_type=='Polygon':
        ring=lambda coords:[[round(x,6),round(y,6)] for x,y in coords]
        return [{'boundary':ring(shape.exterior.coords),'openings':[ring(h.coords) for h in shape.interiors]}]
    return [part for g in getattr(shape,'geoms',[]) for part in regions(g)]


def simulate_scene(req: SceneRequest) -> dict:
    cfg = req.config
    sun = sun_position(SunRequest(latitude=cfg.latitude, longitude=cfg.longitude, date=req.date, hour_local=req.hour_local))
    ctx = build_context(cfg, req.obstacles, sun)
    irradiance = 0.0
    irradiance_source = "clear_sky_approximation"
    if sun.altitude_deg > 0:
        try:
            import pandas as pd
            import pvlib
            when = (datetime.combine(req.date, datetime.min.time()) + timedelta(hours=req.hour_local))
            times = pd.DatetimeIndex([when]).tz_localize("Asia/Ho_Chi_Minh")
            sky = pvlib.location.Location(cfg.latitude, cfg.longitude, tz="Asia/Ho_Chi_Minh").get_clearsky(times)
            row = sky.iloc[0]
            poa = pvlib.irradiance.get_total_irradiance(cfg.roof_tilt_deg, cfg.roof_azimuth_deg, sun.zenith_deg, sun.azimuth_deg, row.dni, row.ghi, row.dhi)
            irradiance = float(poa["poa_global"])
            irradiance_source = "pvlib_ineichen_clear_sky"
        except ImportError:
            irradiance = 1000*max(0, math.sin(math.radians(sun.altitude_deg)))
    shadow_area = ctx.roof.intersection(ctx.shadow_union).area if ctx.shadow_union is not None else 0.0
    if sun.altitude_deg <= 0:
        shadow_area = ctx.roof.area
    shadows = [{"id":r['id'],"label":r['label'],"polygons":polygons(r['shape']),'regions':regions(r['shape']),'area_m2':round(r['shape'].area,3) if r['shape'] is not None else 0} for r in ctx.shadows]
    face_results=[]
    for surface in ctx.surfaces:
        face_irradiance=irradiance
        if sun.altitude_deg>0 and irradiance_source=='pvlib_ineichen_clear_sky':
            value=pvlib.irradiance.get_total_irradiance(surface.tilt,surface.azimuth,sun.zenith_deg,sun.azimuth_deg,row.dni,row.ghi,row.dhi)
            face_irradiance=float(value['poa_global'])
        face_results.append({'id':surface.id,'label':surface.label,'polygons':polygons(surface.polygon),'elevation_m':surface.elevation,'tilt_deg':surface.tilt,'azimuth_deg':surface.azimuth,'origin':[surface.origin_x,surface.origin_y],'group':surface.group,'regions':regions(surface.polygon),'mount':surface.mount,'mount_tilt':surface.mount_tilt,'mount_azimuth':surface.mount_azimuth,'irradiance_w_m2':round(face_irradiance,1),'area_m2':surface.polygon.area,'installable':surface.installable,'direct_sunlight':direct_sun_reaches(surface,sun,cfg)})
    irradiance=sum(f['irradiance_w_m2']*f['area_m2'] for f in face_results)/max(ctx.roof.area,.001)
    cells = []
    if req.heatmap:
        step = max(cfg.roof_width_m, cfg.roof_height_m)/22
        y = 0.0
        while y < cfg.roof_height_m:
            x = 0.0
            while x < cfg.roof_width_m:
                shape = box(x, y, min(x+step,cfg.roof_width_m), min(y+step,cfg.roof_height_m)).intersection(ctx.roof)
                if not shape.is_empty and shape.area > 0:
                    cover = overlap_ratio(shape, ctx.shadow_union) if sun.altitude_deg>0 else 1.0
                    local_irradiance=sum(f['irradiance_w_m2']*shape.intersection(s.polygon).area for f,s in zip(face_results,ctx.surfaces))/shape.area
                    cells.append({"x":x,"y":y,"width_m":step,"height_m":step,"irradiance_w_m2":round(local_irradiance*(1-cover),1),"shade_fraction":round(cover,3)})
                x += step
            y += step
    diagnostics=obstacle_elevations(cfg,req.obstacles,ctx.surfaces)
    notes=["Bức xạ trời quang mô phỏng, không phải số đo hay dự báo thời tiết.","Các phần mái là mặt phẳng riêng, vật cản là khối đứng theo mặt bằng. Cao độ phải đo/nhập; chưa dựng 3D từ ảnh hoặc mô phỏng mái cong."]
    if sun.altitude_deg<=0:notes.append('Mặt trời dưới chân trời: toàn mái không có nắng trực tiếp; đây không phải bóng do một vật cản riêng.')
    elif any(not f['direct_sunlight'] for f in face_results):notes.append('Có phần mái quay lưng với nắng trực tiếp. Bức xạ trời quang vẫn có thể gồm ánh sáng tán xạ; không quy toàn phần mái thành bóng của một vật cản.')
    notes.extend(f"{r['label']}: {warning}" for r in diagnostics for warning in r['warnings'])
    for surface in ctx.surfaces:
        if any(surface_z(surface,x,y,cfg)<-1e-6 for part in _parts(surface.polygon) for x,y in part.exterior.coords):
            notes.append(f'{surface.label}: có điểm thấp hơn mặt đất. Kiểm tra cao độ tại gốc/tâm mặt mái, độ dốc và hướng dốc.')
    return {"sun":sun.model_dump(),"faces":face_results,"shadows":shadows,"obstacle_elevations":diagnostics,"cells":cells,"roof_polygons":polygons(ctx.roof),"usable_polygons":polygons(ctx.usable_roof),"shaded_area_m2":round(shadow_area,2),"shaded_pct":round(100*shadow_area/max(ctx.roof.area,0.001),1),"plane_irradiance_w_m2":round(irradiance,1),"irradiance_source":irradiance_source,"notes":notes}
