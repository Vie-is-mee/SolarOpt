"""Compare SolarOpt layouts with rooftop PV arrays that were actually installed and mapped in OpenStreetMap.

Reference: array outlines drawn by OSM contributors over aerial imagery (ODbL, © OpenStreetMap contributors).
They show where an installer put panels, not an engineering optimum, and OSM has no roof obstacles, so
low overlap can mean SolarOpt used roof area the installer left free for plant, access or structure.

Two runs per roof:
  same_area : SolarOpt may place only as much panel area as the real arrays cover -> where would it put them?
  max       : unlimited budget -> how much of the roof SolarOpt considers usable.
A roof-fill baseline (real arrays vs the whole usable roof) gives the IoU a naive "cover everything" answer gets.

  python scripts/benchmark_real_installs.py                 # run from the committed snapshot
  python scripts/benchmark_real_installs.py --from-overpass raw.json --ids 1 2 3   # rebuild snapshot
"""
from pathlib import Path
import argparse
import html
import json
import math
import random
import sys

from shapely.geometry import Polygon, box
from shapely.ops import unary_union

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.schemas import DesignRequest, PanelSpec, Point, ProjectConfig
from app.services.geometry import build_context, panel_shape
from app.services.optimizer import generate_design

ROOT = Path(__file__).resolve().parents[2]
SNAPSHOT = ROOT / 'sample_data/benchmark/osm_rooftop_pv_exeter.json'
OUT = ROOT / 'output/validation/real_installs'
# Typical UK residential/commercial module of the 2015-2020 installs mapped in this area.
PANEL = PanelSpec(manufacturer='Generic', model='60-cell 300 W', width_m=0.99, height_m=1.65, power_w=300, price_vnd=1_000_000)
CONFIG = dict(setback_m=0.5, panel_gap_m=0.02, obstacle_clearance_m=0.25, annual_irradiance_kwh_m2=1100, performance_ratio=0.8)


def build_snapshot(raw_path, ids, retrieved):
    raw = json.loads(Path(raw_path).read_text(encoding='utf-8'))
    ring = lambda e: [[p['lon'], p['lat']] for p in e['geometry']]
    solar = [e for e in raw['elements'] if e.get('tags', {}).get('generator:source') == 'solar']
    by_id = {e['id']: e for e in raw['elements']}
    cases = []
    for building_id in ids:
        b = by_id[building_id]
        outline = Polygon(ring(b))
        arrays = [e for e in solar if outline.contains(Polygon(ring(e)).representative_point())]
        cases.append({'osm_building_way': building_id, 'building_tags': {k: v for k, v in b['tags'].items() if k in ('building', 'roof:shape', 'building:levels')},
                      'building_lonlat': ring(b), 'arrays': [{'osm_way': e['id'], 'lonlat': ring(e), 'tags': e['tags']} for e in arrays]})
    return {'source': 'OpenStreetMap via Overpass API', 'license': 'ODbL 1.0, © OpenStreetMap contributors', 'retrieved': retrieved,
            'note': 'Array outlines are contributor-mapped from aerial imagery; no rooftop obstacles are mapped.', 'cases': cases}


def to_local(lonlat, lat0, lon0):
    k = 111_320 * math.cos(math.radians(lat0))
    return [((lon - lon0) * k, (lat - lat0) * 110_540) for lon, lat in lonlat]


def run_case(case):
    lon0 = min(p[0] for p in case['building_lonlat']); lat0 = min(p[1] for p in case['building_lonlat'])
    roof = Polygon(to_local(case['building_lonlat'], lat0, lon0)).buffer(0)
    real = unary_union([Polygon(to_local(a['lonlat'], lat0, lon0)).buffer(0) for a in case['arrays']]).intersection(roof)
    minx, miny, maxx, maxy = roof.bounds
    if maxx - minx > 100 or maxy - miny > 100:
        raise ValueError('Roof frame exceeds the 100 m limit of the MVP')
    pts = [Point(x=round(x - minx, 3), y=round(y - miny, 3)) for x, y in list(roof.exterior.coords)[:-1]]
    shift = lambda g: __import__('shapely.affinity', fromlist=['translate']).translate(g, -minx, -miny)
    roof, real = shift(roof), shift(real)
    base = dict(CONFIG, project_name=f"OSM {case['osm_building_way']}", latitude=lat0, longitude=lon0, roof_width_m=math.ceil(maxx - minx + .01),
                roof_height_m=math.ceil(maxy - miny + .01), roof_polygon=pts, geometry_confirmed=True)
    usable = build_context(ProjectConfig(**base), [], None).usable_roof
    panel_area = PANEL.width_m * PANEL.height_m
    same_n = max(1, round(real.area / panel_area))
    result = {'osm_building_way': case['osm_building_way'], 'tags': case['building_tags'], 'roof_m2': round(roof.area, 1),
              'real_array_m2': round(real.area, 1), 'real_array_count': len(case['arrays']), 'equivalent_panels': same_n,
              'baseline_roof_fill_iou': round(real.intersection(usable).area / real.union(usable).area, 3), 'runs': {}}
    for mode, budget in (('same_area', same_n * PANEL.price_vnd), ('max', 1e12)):
        design = generate_design(DesignRequest(config=ProjectConfig(**base, budget_vnd=budget), panel=PANEL, obstacles=[], objective='max_energy'))
        ours = unary_union([panel_shape(p.x, p.y, p.width_m, p.height_m, p.rotation_deg) for p in design.panels]) if design.panels else Polygon()
        inter = real.intersection(ours).area
        result['runs'][mode] = {'panels': design.metrics.panel_count, 'panel_m2': round(ours.area, 1),
                                'iou': round(inter / real.union(ours).area, 3) if not ours.is_empty else 0.0,
                                'covers_real_pct': round(100 * inter / real.area, 1), 'inside_real_pct': round(100 * inter / ours.area, 1) if ours.area else 0.0,
                                'kwp': design.metrics.peak_power_kwp, 'solver': design.solver_status}
        result['runs'][mode]['_panels'] = [list(panel_shape(p.x, p.y, p.width_m, p.height_m, p.rotation_deg).exterior.coords) for p in design.panels]
    # Fair reference for same_area: the same number of panels drawn at random from SolarOpt's own
    # feasible positions (the max run), averaged over fixed seeds.
    feasible = [Polygon(c) for c in result['runs']['max']['_panels']]
    n = min(result['runs']['same_area']['panels'], len(feasible))
    draws = []
    for seed in range(30):
        pick = unary_union(random.Random(seed).sample(feasible, n)) if n else Polygon()
        draws.append(real.intersection(pick).area / real.union(pick).area if not pick.is_empty else 0.0)
    result['baseline_random_same_area_iou'] = round(sum(draws) / len(draws), 3)
    result['_roof'] = list(roof.exterior.coords)
    result['_real'] = [list(g.exterior.coords) for g in getattr(real, 'geoms', [real]) if not g.is_empty]
    return result


def svg(r, mode):
    minx, miny, maxx, maxy = Polygon(r['_roof']).bounds
    s = 300 / max(maxx - minx, maxy - miny)
    path = lambda c: ' '.join(f'{(x - minx) * s + 10:.1f},{(maxy - y) * s + 10:.1f}' for x, y in c)
    parts = [f'<polygon points="{path(r["_roof"])}" fill="#eef1ea" stroke="#7a8a74"/>']
    parts += [f'<polygon points="{path(c)}" fill="#3f8f5f" fill-opacity=".45"/>' for c in r['_real']]
    parts += [f'<polygon points="{path(c)}" fill="none" stroke="#2d6080" stroke-width="1"/>' for c in r['runs'][mode]['_panels']]
    return f'<svg viewBox="0 0 {(maxx - minx) * s + 20:.0f} {(maxy - miny) * s + 20:.0f}" width="320">{"".join(parts)}</svg>'


def report(results, snapshot):
    cards = []
    for r in results:
        a, m = r['runs']['same_area'], r['runs']['max']
        cards.append(f"""<article><h2>OSM way {r['osm_building_way']} · {html.escape(str(r['tags']))}</h2>
<p>Mái {r['roof_m2']} m² · dãy pin thật {r['real_array_m2']} m² ({r['real_array_count']} vùng ≈ {r['equivalent_panels']} tấm)</p>
<div class="pair"><figure>{svg(r, 'same_area')}<figcaption>Cùng diện tích: IoU {a['iou']} · phủ {a['covers_real_pct']}% vùng thật</figcaption></figure>
<figure>{svg(r, 'max')}<figcaption>Tối đa: {m['panels']} tấm · phủ {m['covers_real_pct']}% vùng thật · IoU {m['iou']}</figcaption></figure></div>
<p>Mốc so sánh: đặt ngẫu nhiên cùng số tấm IoU {r['baseline_random_same_area_iou']} · phủ kín mái IoU {r['baseline_roof_fill_iou']}</p></article>""")
    return f"""<!doctype html><meta charset="utf-8"><title>SolarOpt · So với mái đã lắp thật</title>
<style>body{{font-family:system-ui,sans-serif;max-width:900px;margin:24px auto;padding:0 16px;color:#2f4935}}article{{border-top:1px solid #dde5d6;padding:12px 0}}.pair{{display:flex;flex-wrap:wrap;gap:16px}}figure{{margin:0}}figcaption{{font-size:13px}}</style>
<h1>SolarOpt so với dãy pin đã lắp thật (OpenStreetMap, Exeter)</h1>
<p>Xanh lá: vùng pin thật do người đóng góp OSM vẽ từ ảnh hàng không. Viền xanh dương: tấm pin SolarOpt đặt. Nguồn: {html.escape(snapshot['license'])}, truy xuất {html.escape(snapshot['retrieved'])}. OSM không có vật cản trên mái, nên chênh lệch không đồng nghĩa SolarOpt sai.</p>
{''.join(cards)}"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--from-overpass'); ap.add_argument('--ids', nargs='*', type=int); ap.add_argument('--retrieved', default='')
    args = ap.parse_args()
    if args.from_overpass:
        SNAPSHOT.parent.mkdir(parents=True, exist_ok=True)
        SNAPSHOT.write_text(json.dumps(build_snapshot(args.from_overpass, args.ids, args.retrieved), ensure_ascii=False, indent=1), encoding='utf-8')
    snapshot = json.loads(SNAPSHOT.read_text(encoding='utf-8'))
    results = [run_case(c) for c in snapshot['cases']]
    OUT.mkdir(parents=True, exist_ok=True)
    clean = [{k: v for k, v in r.items() if not k.startswith('_')} | {'runs': {m: {k: v for k, v in run.items() if not k.startswith('_')} for m, run in r['runs'].items()}} for r in results]
    summary = {'cases': len(clean), 'mean_iou_same_area': round(sum(r['runs']['same_area']['iou'] for r in clean) / len(clean), 3),
               'mean_baseline_iou': round(sum(r['baseline_roof_fill_iou'] for r in clean) / len(clean), 3),
               'mean_random_same_area_iou': round(sum(r['baseline_random_same_area_iou'] for r in clean) / len(clean), 3),
               'mean_covers_real_pct_max': round(sum(r['runs']['max']['covers_real_pct'] for r in clean) / len(clean), 1)}
    (OUT / 'report.json').write_text(json.dumps({'snapshot': {k: v for k, v in snapshot.items() if k != 'cases'}, 'panel': PANEL.model_dump(), 'config': CONFIG,
                                                  'summary': summary, 'cases': clean}, ensure_ascii=False, indent=1), encoding='utf-8')
    (OUT / 'report.html').write_text(report(results, snapshot), encoding='utf-8')
    print(json.dumps(summary, ensure_ascii=False))
    for r in clean:
        print(r['osm_building_way'], r['real_array_m2'], r['runs'], r['baseline_roof_fill_iou'])


if __name__ == '__main__':
    main()
