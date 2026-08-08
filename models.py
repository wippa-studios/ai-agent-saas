"""
Pydantic Schemas - AI Agent SaaS System
စနစ်တစ်ခုလုံးတွင် သုံးမည့် Data Structure များ
"""
from typing import List, Literal, Optional
from pydantic import BaseModel, Field


# ---------------------------------------------------------
# Tenant / Onboarding
# ---------------------------------------------------------
class CreateTenantRequest(BaseModel):
    company_name: str
    admin_email: str
    plan_tier: Literal["FREE", "STARTER", "PRO", "ENTERPRISE"] = "FREE"


class TenantOut(BaseModel):
    id: str
    company_name: str
    admin_email: str
    plan_tier: str
    subscription_status: str
    created_at: str


# ---------------------------------------------------------
# Agent Router
# ---------------------------------------------------------
class UserQuery(BaseModel):
    user_input: str


class RouteDecision(BaseModel):
    target_agent: Literal["FINANCE", "MARKETING", "GENERAL"] = Field(
        description="ခိုင်းစေချက်နှင့် ကိုက်ညီသော Sub-Agent"
    )
    reasoning: str = Field(description="ရွေးချယ်ရသည့် အကြောင်းပြချက်")


# ---------------------------------------------------------
# Finance Agent
# ---------------------------------------------------------
class TransactionItem(BaseModel):
    type: Literal["INCOME", "EXPENSE"]
    category: str
    amount: float
    description: str


class FinanceAnalysis(BaseModel):
    items: List[TransactionItem]
    total_income: float
    total_expense: float
    net_profit: float
    financial_advice: str


# ---------------------------------------------------------
# Marketing Agent
# ---------------------------------------------------------
class MarketingCampaign(BaseModel):
    target_audience: str
    content_headline: str
    facebook_post_caption: str
    suggested_hashtags: List[str]
    requires_human_approval: bool = True


# ---------------------------------------------------------
# Generic Agent Response Wrapper
# ---------------------------------------------------------
class AgentResponse(BaseModel):
    agent_used: str
    reasoning: str
    data: dict


# ---------------------------------------------------------
# Billing
# ---------------------------------------------------------
class CheckoutSessionRequest(BaseModel):
    plan_tier: Literal["STARTER", "PRO"]
