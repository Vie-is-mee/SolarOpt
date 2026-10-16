"""Bounded, embedded project evidence. Never fetch remote image URLs."""
import base64
import io
from datetime import datetime
from typing import Literal
from PIL import Image
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from app.economic_evidence import EconomicAssumptions, LayoutDatum


class EvidencePoint(BaseModel):
    model_config=ConfigDict(allow_inf_nan=False,extra='forbid')
    x:float=Field(ge=0,le=100)
    y:float=Field(ge=0,le=100)


class CalibrationRecord(BaseModel):
    model_config=ConfigDict(allow_inf_nan=False,extra='forbid')
    captured_at:datetime
    method:str=Field(max_length=80)
    image_width_px:int=Field(gt=0,le=16000)
    image_height_px:int=Field(gt=0,le=16000)
    reference_points:list[EvidencePoint]=Field(default_factory=list,max_length=2)
    reference_m:float|None=Field(default=None,gt=0,le=100)
    check_points:list[EvidencePoint]=Field(default_factory=list,max_length=2)
    check_m:float|None=Field(default=None,gt=0,le=100)
    measured_width_m:float|None=Field(default=None,gt=0,le=100)
    measured_length_m:float|None=Field(default=None,gt=0,le=100)
    result_width_m:float=Field(gt=0,le=100)
    result_height_m:float=Field(gt=0,le=100)
    frame_error_pct:float=Field(ge=0,le=10000)
    check_error_pct:float|None=Field(default=None,ge=0,le=10000)

    @model_validator(mode='after')
    def paired_measurements(self):
        for points,length in [(self.reference_points,self.reference_m),(self.check_points,self.check_m)]:
            if (len(points),length is not None) not in [(0,False),(2,True)]:
                raise ValueError('Đoạn đo cần hai điểm và chiều dài tương ứng.')
            if len(points)==2 and points[0]==points[1]:raise ValueError('Hai đầu đoạn đo phải khác nhau.')
        return self


class ProjectEvidence(BaseModel):
    model_config=ConfigDict(extra='forbid')
    source_name:str=Field(default='',max_length=180)
    input_kind:Literal['drone','plan','partial']='drone'
    source_image:str|None=Field(default=None,max_length=4_000_000)
    reference_image:str|None=Field(default=None,max_length=4_000_000)
    calibration:CalibrationRecord|None=None
    economic_assumptions:EconomicAssumptions|None=None
    layout_datum:LayoutDatum|None=None

    @field_validator('source_image','reference_image')
    @classmethod
    def embedded_raster(cls,value):
        if value is None:return value
        try:
            header,payload=value.split(',',1)
            formats={'data:image/png;base64':'PNG','data:image/jpeg;base64':'JPEG','data:image/webp;base64':'WEBP'}
            if header not in formats:raise ValueError()
            raw=base64.b64decode(payload,validate=True)
            with Image.open(io.BytesIO(raw)) as image:
                if image.format!=formats[header] or image.width*image.height>4_000_000:raise ValueError()
                image.verify()
        except Exception as exc:raise ValueError('Ảnh bằng chứng phải là PNG/JPEG/WEBP nhúng hợp lệ, tối đa 4 triệu điểm ảnh.') from exc
        return value

    @model_validator(mode='after')
    def calibration_image_matches(self):
        if self.calibration:
            if not self.source_image:raise ValueError('Hồ sơ đo cần ảnh đã dùng để hiệu chuẩn.')
            raw=base64.b64decode(self.source_image.split(',',1)[1],validate=True)
            with Image.open(io.BytesIO(raw)) as image:
                if image.size!=(self.calibration.image_width_px,self.calibration.image_height_px):
                    raise ValueError('Kích thước ảnh không khớp hồ sơ đo.')
        return self
