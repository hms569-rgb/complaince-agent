from pydantic import BaseModel
from typing import Optional

class BusinessProfile(BaseModel):
    business_name: str
    business_type: str
    state: str
    employee_count: int
    annual_turnover_lakhs: float
    industry_sector: str
    has_gst: bool
    additional_info: Optional[str] = None

class ComplianceReport(BaseModel):
    business_name: str
    applicable_regulations: list[str]
    compliance_gaps: list[str]
    action_items: list[str]
    deadlines: list[str]
    risk_level: str
    summary: str