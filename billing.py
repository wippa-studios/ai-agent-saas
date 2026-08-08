"""
Stripe Billing (Optional)
--------------------------
.env တွင် STRIPE_SECRET_KEY မထည့်ထားလျှင် Billing endpoint များက
"Billing not configured" ဟု ရှင်းလင်းစွာ ပြန်ပေးမည် (Server မကျိုးစေရန်).
"""
import os
from dotenv import load_dotenv

load_dotenv()

STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY", "").strip()
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET", "").strip()
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5500").strip()

PRICING_PLANS = {
    "STARTER": os.getenv("STRIPE_PRICE_STARTER", "").strip(),
    "PRO": os.getenv("STRIPE_PRICE_PRO", "").strip(),
}

BILLING_ENABLED = bool(STRIPE_SECRET_KEY)

if BILLING_ENABLED:
    import stripe
    stripe.api_key = STRIPE_SECRET_KEY


def create_checkout_session(tenant: dict, plan_tier: str) -> str:
    if not BILLING_ENABLED:
        raise RuntimeError("Stripe is not configured. Add STRIPE_SECRET_KEY to .env")

    import stripe
    price_id = PRICING_PLANS.get(plan_tier)
    if not price_id:
        raise ValueError(f"No Stripe price configured for plan '{plan_tier}'")

    customer_id = tenant.get("stripe_customer_id")
    if not customer_id:
        customer = stripe.Customer.create(
            email=tenant["admin_email"],
            metadata={"tenant_id": tenant["id"]},
            description=tenant["company_name"],
        )
        customer_id = customer.id
        import database
        database.update_tenant_subscription(tenant_id=tenant["id"], stripe_customer_id=customer_id)

    session = stripe.checkout.Session.create(
        customer=customer_id,
        payment_method_types=["card"],
        line_items=[{"price": price_id, "quantity": 1}],
        mode="subscription",
        success_url=f"{FRONTEND_URL}/?checkout=success",
        cancel_url=f"{FRONTEND_URL}/?checkout=cancel",
        metadata={"tenant_id": tenant["id"], "plan_tier": plan_tier},
    )
    return session.url


def create_customer_portal(tenant: dict) -> str:
    if not BILLING_ENABLED:
        raise RuntimeError("Stripe is not configured. Add STRIPE_SECRET_KEY to .env")
    import stripe
    customer_id = tenant.get("stripe_customer_id")
    if not customer_id:
        raise ValueError("No billing history found for this tenant")
    portal = stripe.billing_portal.Session.create(customer=customer_id, return_url=f"{FRONTEND_URL}/")
    return portal.url


def handle_webhook_event(payload: bytes, sig_header: str):
    if not BILLING_ENABLED:
        raise RuntimeError("Stripe is not configured.")
    import stripe
    import database

    event = stripe.Webhook.construct_event(payload, sig_header, STRIPE_WEBHOOK_SECRET)
    event_type = event["type"]
    obj = event["data"]["object"]

    if event_type == "checkout.session.completed":
        tenant_id = obj["metadata"].get("tenant_id")
        plan_tier = obj["metadata"].get("plan_tier")
        if tenant_id:
            database.update_tenant_subscription(
                tenant_id=tenant_id,
                subscription_status="ACTIVE",
                plan_tier=plan_tier,
                stripe_subscription_id=obj.get("subscription"),
            )
    elif event_type == "invoice.payment_succeeded":
        database.update_tenant_subscription(customer_id=obj.get("customer"), subscription_status="ACTIVE")
    elif event_type == "invoice.payment_failed":
        database.update_tenant_subscription(customer_id=obj.get("customer"), subscription_status="PAST_DUE")
    elif event_type == "customer.subscription.deleted":
        database.update_tenant_subscription(customer_id=obj.get("customer"), subscription_status="CANCELED", plan_tier="FREE")

    return event_type
