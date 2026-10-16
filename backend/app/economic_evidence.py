"""User-supplied quote assumptions, stored with evidence; no prescribed prices."""
from pydantic import BaseModel,ConfigDict,Field


class CostItem(BaseModel):
    model_config=ConfigDict(extra='forbid',allow_inf_nan=False)
    name:str=Field(min_length=1,max_length=180)
    amount:float|None=Field(default=None,ge=0,le=1e12)


class EconomicAssumptions(BaseModel):
    model_config=ConfigDict(extra='forbid',allow_inf_nan=False)
    costs:list[CostItem]=Field(max_length=30)
    contingency_pct:float|None=Field(default=None,ge=0,le=100)
    markup_pct:float|None=Field(default=None,ge=0,le=500)
    vat_pct:float|None=Field(default=None,ge=0,le=100)
    self_use_pct:float|None=Field(default=None,ge=0,le=100)
    buy_price:float|None=Field(default=None,ge=0,le=1e9)
    sell_price:float|None=Field(default=None,ge=0,le=1e9)
    maintenance_year:float|None=Field(default=None,ge=0,le=1e12)
    degradation_pct:float|None=Field(default=None,ge=0,le=100)
    price_growth_pct:float|None=Field(default=None,ge=0,le=100)
    discount_pct:float|None=Field(default=None,ge=0,le=100)
    years:int=Field(default=25,ge=1,le=40)
    replacement_year:int=Field(default=12,ge=1,le=40)
    replacement_cost:float|None=Field(default=None,ge=0,le=1e12)
    loan_amount:float|None=Field(default=None,ge=0,le=1e12)
    loan_rate_pct:float|None=Field(default=None,ge=0,le=100)
    loan_years:int=Field(default=5,ge=1,le=40)
    source:str=Field(default='',max_length=4000)


class LayoutDatum(BaseModel):
    model_config=ConfigDict(extra='forbid')
    vertex_index:int=Field(default=0,ge=0,le=200)
    description:str=Field(default='',max_length=500)
