"""
All-in-One Enterprise AI Agent SaaS - FastAPI Backend
=======================================================
Run:  uvicorn main:app --reload --port 8000
Docs: http://localhost:8000/docs

Multi-Tenant: every protected request must send header  X-Tenant-ID: <tenant uuid>
(returned when you register a tenant via /api/v1/saas/register-tenant)
"""
from fastapi import FastAPI, Header, HTTPException, Depends, Request
from fastapi.middleware.cors import CORSMiddleware

import agents
import billing
import database
from models import (
    AgentResponse, CreateTenantRequest, TenantOut, UserQuery,
    CheckoutSessionRequest,
)

app = FastAPI(title="All-in-One Enterprise AI Agent SaaS", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def _startup():
    database.init_db()


# ---------------------------------------------------------
# Tenant dependency (Multi-Tenant Security Layer)
# ---------------------------------------------------------
async def get_current_tenant(x_tenant_id: str = Header(..., description="Company Tenant UUID")):
    tenant = database.get_tenant(x_tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail="Invalid Tenant ID — please register first")
    return tenant


def require_active_subscription(tenant: dict = Depends(get_current_tenant)):
    if tenant.get("subscription_status") not in ("ACTIVE",):
        raise HTTPException(status_code=402, detail="Active subscription required for this feature")
    return tenant


# ---------------------------------------------------------
# Health / Info
# ---------------------------------------------------------
@app.get("/")
def root():
    return {
        "status": "ok",
        "service": "All-in-One Enterprise AI Agent SaaS",
        "ai_mode": "GEMINI" if agents.USE_GEMINI else "OFFLINE_FALLBACK",
        "billing_enabled": billing.BILLING_ENABLED,
        "database": "SUPABASE" if database.USE_SUPABASE else "SQLITE (local)",
    }


# ---------------------------------------------------------
# Tenant Onboarding
# ---------------------------------------------------------
@app.post("/api/v1/saas/register-tenant", response_model=TenantOut)
def register_tenant(payload: CreateTenantRequest):
    try:
        tenant = database.create_tenant(payload.company_name, payload.admin_email, payload.plan_tier)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return TenantOut(**tenant)


@app.get("/api/v1/saas/me", response_model=TenantOut)
def get_me(tenant: dict = Depends(get_current_tenant)):
    return TenantOut(**tenant)


# ---------------------------------------------------------
# Main Multi-Agent Endpoint
# ---------------------------------------------------------
@app.post("/api/v1/agent/process", response_model=AgentResponse)
def process_user_request(request: UserQuery, tenant: dict = Depends(get_current_tenant)):
    try:
        route = agents.intent_router_agent(request.user_input)

        if route.target_agent == "FINANCE":
            result = agents.run_finance_agent(request.user_input)
            database.insert_finance_records(tenant["id"], [i.model_dump() for i in result.items])
            return AgentResponse(agent_used="FINANCE_AGENT", reasoning=route.reasoning, data=result.model_dump())

        if route.target_agent == "MARKETING":
            result = agents.run_marketing_agent(request.user_input)
            log_id = database.insert_marketing_log(tenant["id"], result.content_headline, result.facebook_post_caption)
            data = result.model_dump()
            data["log_id"] = log_id
            return AgentResponse(agent_used="MARKETING_AGENT", reasoning=route.reasoning, data=data)

        # GENERAL fallback
        reply = (
            "ဒီမေးခွန်းသည် Finance/Marketing နှင့် တိုက်ရိုက် မသက်ဆိုင်ပါ။ "
            "ငွေစာရင်း (သို့) Facebook Post ဆိုင်ရာ တောင်းဆိုချက်များကို ထည့်သွင်းမေးမြန်းကြည့်ပါ။"
        )
        if agents.USE_GEMINI:
            gen = agents._client.models.generate_content(model=agents.MODEL_NAME, contents=request.user_input)
            reply = gen.text
        return AgentResponse(agent_used="GENERAL_AGENT", reasoning=route.reasoning, data={"reply": reply})

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ---------------------------------------------------------
# Finance Records
# ---------------------------------------------------------
@app.get("/api/v1/finance/my-records")
def my_finance_records(tenant: dict = Depends(get_current_tenant)):
    records = database.get_finance_records(tenant["id"])
    total_income = sum(r["amount"] for r in records if r["type"] == "INCOME")
    total_expense = sum(r["amount"] for r in records if r["type"] == "EXPENSE")
    return {
        "tenant_name": tenant["company_name"],
        "plan_tier": tenant["plan_tier"],
        "records_count": len(records),
        "total_income": total_income,
        "total_expense": total_expense,
        "net_profit": total_income - total_expense,
        "data": records,
    }


# ---------------------------------------------------------
# Marketing Approval (Human-in-the-Loop)
# ---------------------------------------------------------
@app.post("/api/v1/marketing/{log_id}/approve")
def approve_marketing_post(log_id: str, tenant: dict = Depends(get_current_tenant)):
    ok = database.approve_marketing_log(tenant["id"], log_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Marketing log not found")
    return {"status": "APPROVED", "message": "Post ကို Publish လုပ်ရန် အတည်ပြုပြီးပါပြီ (Meta API ချိတ်ဆက်ပြီးမှ တကယ်တင်ပါ)"}


# ---------------------------------------------------------
# Billing (Optional - requires Stripe keys in .env)
# ---------------------------------------------------------
@app.post("/api/v1/billing/create-checkout-session")
def create_checkout(payload: CheckoutSessionRequest, tenant: dict = Depends(get_current_tenant)):
    try:
        url = billing.create_checkout_session(tenant, payload.plan_tier)
        return {"checkout_url": url}
    except (RuntimeError, ValueError) as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/v1/billing/customer-portal")
def customer_portal(tenant: dict = Depends(get_current_tenant)):
    try:
        url = billing.create_customer_portal(tenant)
        return {"portal_url": url}
    except (RuntimeError, ValueError) as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/v1/billing/webhook")
async def stripe_webhook(request: Request):
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature", "")
    try:
        event_type = billing.handle_webhook_event(payload, sig_header)
        return {"status": "success", "event": event_type}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# ---------------------------------------------------------
# Example Premium-only Feature (subscription gate demo)
# ---------------------------------------------------------
@app.get("/api/v1/ai-agent/premium-feature")
def premium_feature(tenant: dict = Depends(require_active_subscription)):
    return {
        "status": "SUCCESS",
        "message": f"Welcome {tenant['company_name']}! Premium AI Agent features unlocked.",
        "current_plan": tenant["plan_tier"],
    }
