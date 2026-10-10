from __future__ import annotations

from datetime import datetime, timedelta

import requests

from app.schemas import IrradianceResult, SunPosition, SunRequest


def sun_position(req: SunRequest) -> SunPosition:
    try:
        import pandas as pd
        import pvlib

        hour = int(req.hour_local)
        minute = int(round((req.hour_local - hour) * 60))
        ts = pd.DatetimeIndex([
            datetime(req.date.year, req.date.month, req.date.day, hour, minute)
        ]).tz_localize(req.timezone)
        pos = pvlib.solarposition.get_solarposition(ts, req.latitude, req.longitude).iloc[0]
        return SunPosition(
            altitude_deg=float(pos["apparent_elevation"]),
            azimuth_deg=float(pos["azimuth"]),
            zenith_deg=float(pos["apparent_zenith"]),
        )
    except Exception:
        # Fallback nhẹ: đủ cho demo nếu pvlib chưa cài.
        import math
        day_of_year = req.date.timetuple().tm_yday
        decl = 23.45 * math.sin(math.radians(360 * (284 + day_of_year) / 365))
        lat = math.radians(req.latitude)
        dec = math.radians(decl)
        hour_angle = math.radians(15 * (req.hour_local - 12))
        sin_alt = math.sin(lat) * math.sin(dec) + math.cos(lat) * math.cos(dec) * math.cos(hour_angle)
        alt = math.degrees(math.asin(max(-1, min(1, sin_alt))))
        cos_az = (math.sin(dec) - math.sin(math.radians(alt)) * math.sin(lat)) / max(1e-6, math.cos(math.radians(alt)) * math.cos(lat))
        az = math.degrees(math.acos(max(-1, min(1, cos_az))))
        if req.hour_local > 12:
            az = 360 - az
        return SunPosition(altitude_deg=alt, azimuth_deg=az, zenith_deg=90-alt)


def fetch_pvgis(lat: float, lon: float, tilt: float = 10.0, azimuth: float = 180.0) -> IrradianceResult:
    # PVGIS aspect: 0 = South, -90 = East, +90 = West.
    aspect = ((azimuth - 180 + 180) % 360) - 180
    params = {
        "lat": lat,
        "lon": lon,
        "peakpower": 1,
        "loss": 14,
        "angle": tilt,
        "aspect": aspect,
        "outputformat": "json",
    }
    try:
        r = requests.get("https://re.jrc.ec.europa.eu/api/v5_3/PVcalc", params=params, timeout=15)
        r.raise_for_status()
        data = r.json()
        totals = data.get("outputs", {}).get("totals", {}).get("fixed", {})
        annual_irrad = float(totals.get("H(i)_y", 0) or 0)
        specific = float(totals.get("E_y", 0) or 0)
        if annual_irrad <= 0:
            annual_irrad = max(1200.0, specific / 0.82 if specific > 0 else 1581.0)
        if specific <= 0:
            specific = annual_irrad * 0.82
        return IrradianceResult(
            source="PVGIS",
            annual_irradiance_kwh_m2=round(annual_irrad, 1),
            specific_yield_kwh_kwp=round(specific, 1),
            detail="PVGIS PVcalc, hệ 1 kWp với tổn thất mặc định 14%.",
        )
    except Exception as exc:
        return IrradianceResult(
            source="fallback",
            annual_irradiance_kwh_m2=1581.0,
            specific_yield_kwh_kwp=1296.4,
            detail=f"Không lấy được PVGIS, dùng giá trị demo TP.HCM. Lỗi: {type(exc).__name__}",
        )
