"""Typical-year weather from PVGIS, reduced to the 12 × 24 grid the energy model already uses.

PVGIS publishes a typical meteorological year (TMY, 8 760 hours, ERA5 2005–2023 for Việt Nam) per location.
Each hour is averaged into its month and local hour (Việt Nam, UTC+7, no daylight saving), giving one
typical day per month at HH:30 — the same instants as energy._sky. Beam is kept as horizontal energy and
turned into normal irradiance with the sun at that instant, so the month-hour GHI equals the TMY exactly;
beam that falls in an hour whose mid-point sun is below 5° is counted as diffuse instead of being lost.

From the same weather a temperature loss is computed for the roof's main plane (PVsyst cell model):
roofs run hotter than open racks, which is a large part of why measured output in the south of Việt Nam
sits well below nameplate. The result is stored in the project, so later calculations need no network.
"""
from __future__ import annotations

from datetime import datetime, timedelta
from functools import lru_cache

import requests

from app.schemas import WeatherYear, YieldLosses

PVGIS_TMY = "https://re.jrc.ec.europa.eu/api/v5_3/tmy"
UTC_OFFSET = 7
MIN_COS_ZENITH = 0.087        # sun below 5°: an hour's beam is treated as diffuse


@lru_cache(maxsize=32)
def _download(lat: float, lon: float):
    r = requests.get(PVGIS_TMY, params={"lat": lat, "lon": lon, "outputformat": "json"}, timeout=40)
    r.raise_for_status()
    return r.json()


def month_hour_grid(hours: list[dict]):
    """TMY records → month-hour means (12 × 24, flattened month*24 + local hour) of beam-horizontal,
    diffuse, air temperature and wind. Records are hourly means centred half an hour after their UTC stamp."""
    sums = {k: [0.0] * 288 for k in ("beam_h", "dhi", "temp", "wind")}
    counts = [0] * 288
    for row in hours:
        stamp = datetime.strptime(row["time(UTC)"], "%Y%m%d:%H%M") + timedelta(hours=UTC_OFFSET)
        i = (stamp.month - 1) * 24 + stamp.hour
        ghi, dhi = max(0.0, float(row["G(h)"])), max(0.0, float(row["Gd(h)"]))
        sums["beam_h"][i] += max(0.0, ghi - dhi)
        sums["dhi"][i] += min(dhi, ghi) if ghi > 0 else 0.0
        sums["temp"][i] += float(row["T2m"])
        sums["wind"][i] += max(0.0, float(row["WS10m"]))
        counts[i] += 1
    if min(counts) == 0:
        raise ValueError("Dữ liệu thời tiết PVGIS thiếu giờ; chưa dùng được.")
    return {k: [v / c for v, c in zip(values, counts)] for k, values in sums.items()}


def build_weather(lat: float, lon: float, data: dict) -> WeatherYear:
    import numpy as np
    from app.services.energy import _sky
    grid = month_hour_grid(data["outputs"]["tmy_hourly"])
    position, _, weights = _sky(lat, lon)
    cosz = np.cos(np.radians(position.apparent_zenith.to_numpy()))
    beam_h, dhi = np.asarray(grid["beam_h"]), np.asarray(grid["dhi"])
    usable = cosz >= MIN_COS_ZENITH
    dni = np.where(usable, beam_h / np.where(usable, cosz, 1), 0.0)
    dhi = np.where(usable, dhi, dhi + beam_h)
    ghi = np.where(usable, beam_h, 0.0) + dhi
    meta = data.get("inputs", {}).get("meteo_data", {})
    period = f"{meta.get('radiation_db', 'PVGIS')} {meta.get('year_min', '')}–{meta.get('year_max', '')}".strip()
    annual = float((ghi * np.asarray(weights)).sum()) / 1000
    return WeatherYear(source=f"PVGIS TMY · {period}", latitude=round(lat, 4), longitude=round(lon, 4),
                       ghi=[round(float(v), 2) for v in ghi], dni=[round(float(v), 2) for v in dni],
                       dhi=[round(float(v), 2) for v in dhi], temp_air=[round(float(v), 2) for v in grid["temp"]],
                       wind=[round(float(v), 2) for v in grid["wind"]], annual_ghi_kwh_m2=round(annual, 1))


def temperature_loss_pct(weather: WeatherYear, tilt: float, azimuth: float, mounting: str, temp_coeff_pct: float) -> float:
    """Share of output lost to cell temperature over the year, for one plane (PVsyst model).
    Flush roof mounting (little air behind the module): U = 20 W/m²K; open racks and trackers: 29."""
    import numpy as np
    import pandas as pd
    import pvlib
    from app.services.energy import _sky
    position, _, weights = _sky(weather.latitude, weather.longitude)
    poa = pvlib.irradiance.get_total_irradiance(tilt, azimuth, position.apparent_zenith, position.azimuth,
                                                pd.Series(weather.dni, index=position.index), pd.Series(weather.ghi, index=position.index),
                                                pd.Series(weather.dhi, index=position.index))["poa_global"].fillna(0).clip(lower=0).to_numpy()
    cell = pvlib.temperature.pvsyst_cell(poa, np.asarray(weather.temp_air), np.asarray(weather.wind),
                                         u_c=20.0 if mounting == "flush" else 29.0, u_v=0.0, module_efficiency=0.21, alpha_absorption=0.9)
    w = poa * np.asarray(weights)
    if w.sum() <= 0:
        return 0.0
    factor = float((w * (1 + temp_coeff_pct / 100 * (cell - 25))).sum() / w.sum())
    return round(max(0.0, (1 - factor) * 100), 2)


def fetch_weather(lat: float, lon: float, tilt: float, azimuth: float, mounting: str, temp_coeff_pct: float):
    """Typical-year weather for the site plus a loss breakdown with its temperature loss filled in."""
    try:
        data = _download(round(lat, 3), round(lon, 3))
    except Exception as exc:
        raise ValueError(f"Chưa tải được dữ liệu thời tiết PVGIS ({type(exc).__name__}). Kiểm tra mạng rồi thử lại; dự án vẫn dùng mô hình trời quang.") from exc
    weather = build_weather(lat, lon, data)
    losses = YieldLosses(temp_coeff_pct=temp_coeff_pct,
                         temperature_pct=temperature_loss_pct(weather, tilt, azimuth, mounting, temp_coeff_pct))
    return weather, losses
