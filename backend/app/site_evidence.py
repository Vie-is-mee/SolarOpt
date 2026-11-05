"""Site survey answers stored with the project evidence (services/site.py screens them)."""
import re
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

Zone = Literal["I", "II", "III", "IV", "V"]


class SiteSurvey(BaseModel):
    """What the engineer saw or asked on site. Unknown answers stay unknown and are flagged, never guessed."""
    model_config = ConfigDict(allow_inf_nan=False, extra="forbid")
    roof_material: Literal["metal", "concrete", "tile", "combustible", "unknown"] = "unknown"
    roof_age_years: float | None = Field(default=None, ge=0, le=100)
    purlin: Literal["steel", "wood", "concrete", "unknown"] = "unknown"
    roof_defects: bool = Field(default=False, description="Rust, leaks, sagging or cracks seen on the roof")
    wind_zone: Zone | None = None
    terrain: Literal["A", "B", "C"] = Field(default="B", description="A open/sea shore, B suburbs and towns, C dense city")
    coast_km: float | None = Field(default=None, ge=0, le=2000)
    industrial_air: bool = Field(default=False, description="Next to industry, chemical works or heavy traffic")
    foot_capacity_kn: float | None = Field(default=None, gt=0, le=20, description="Design pull-out of one attachment")
    grid_connected: bool = True
    pccc_listed: bool = Field(default=False, description="Building on the list that needs fire-design approval (industrial parks, universities, airports…)")
    public_property: bool = False
    image_source: Literal["satellite", "drone", "drawing", "site"] | None = None
    image_date: str | None = Field(default=None, max_length=7, description="YYYY-MM the photo was taken")
    tilt_measured: bool = False
    site_visit: bool = False

    @field_validator("image_date")
    @classmethod
    def month(cls, v):
        if v in (None, ""):
            return None
        if not re.fullmatch(r"(19|20)\d\d-(0[1-9]|1[0-2])", v):
            raise ValueError("Ngày chụp ảnh ghi theo dạng năm-tháng, ví dụ 2026-03.")
        return v
