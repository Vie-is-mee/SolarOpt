from __future__ import annotations

from datetime import datetime, timedelta
from functools import lru_cache
from zoneinfo import ZoneInfo
import math

import requests

from app.schemas import IrradianceResult, SunPosition, SunRequest


def sun_position(req: SunRequest) -> SunPosition:
    return _sun_position(req.latitude, req.longitude, req.date.isoformat(), req.hour_local, req.timezone).model_copy()


@lru_cache(maxsize=4096)
def _sun_position(latitude: float, longitude: float, date_string: str, hour_local: float, timezone: str) -> SunPosition:
    instant = datetime.fromisoformat(date_string) + timedelta(hours=hour_local)
    instant = instant.replace(tzinfo=ZoneInfo(timezone))
    try:
        import pandas as pd
        import pvlib
        ts = pd.DatetimeIndex([instant])
        pos = pvlib.solarposition.get_solarposition(ts, latitude, longitude).iloc[0]
        return SunPosition(
            altitude_deg=float(pos["apparent_elevation"]),
            azimuth_deg=float(pos["azimuth"]),
            zenith_deg=float(pos["apparent_zenith"]),
        )
    except ImportError:
        # Approximation with longitude, equation of time and actual UTC offset.
        day_of_year = instant.timetuple().tm_yday
        gamma = 2*math.pi/365*(day_of_year-1+(hour_local-12)/24)
        equation = 229.18*(0.000075+0.001868*math.cos(gamma)-0.032077*math.sin(gamma)-0.014615*math.cos(2*gamma)-0.040849*math.sin(2*gamma))
        decl = 0.006918-0.399912*math.cos(gamma)+0.070257*math.sin(gamma)-0.006758*math.cos(2*gamma)+0.000907*math.sin(2*gamma)-0.002697*math.cos(3*gamma)+0.00148*math.sin(3*gamma)
        lat = math.radians(latitude)
        dec = decl
        offset = instant.utcoffset().total_seconds()/3600
        hour_angle = math.radians((hour_local*60 + equation + 4*longitude - 60*offset)/4 - 180)
        sin_alt = math.sin(lat) * math.sin(dec) + math.cos(lat) * math.cos(dec) * math.cos(hour_angle)
        alt = math.degrees(math.asin(max(-1, min(1, sin_alt))))
        az = (math.degrees(math.atan2(math.sin(hour_angle), math.cos(hour_angle)*math.sin(lat)-math.tan(dec)*math.cos(lat))) + 180) % 360
        return SunPosition(altitude_deg=alt, azimuth_deg=az, zenith_deg=90-alt, source="approximation")


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
        if not math.isfinite(annual_irrad) or annual_irrad <= 0:
            raise ValueError("PVGIS thiếu bức xạ năm hợp lệ; không thay bằng giá trị giả định dưới nhãn PVGIS.")
        if specific <= 0:
            specific = annual_irrad * 0.82
        return IrradianceResult(
            source="PVGIS",
            annual_irradiance_kwh_m2=round(annual_irrad, 1),
            specific_yield_kwh_kwp=round(specific, 1),
            detail="PVGIS PVcalc, hệ 1 kWp với tổn thất mặc định 14%.",
            reference_tilt_deg=tilt, reference_azimuth_deg=azimuth,
        )
    except Exception as exc:
        return IrradianceResult(
            source="fallback",
            annual_irradiance_kwh_m2=1581.0,
            specific_yield_kwh_kwp=1296.4,
            detail=f"Không lấy được PVGIS, dùng giá trị demo TP.HCM. Lỗi: {type(exc).__name__}",
        )
