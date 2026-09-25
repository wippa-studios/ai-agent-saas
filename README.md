# 🏢 All-in-One Enterprise AI Agent SaaS

Multi-Agent (Finance + Marketing + Router) SaaS System — FastAPI Backend + HTML Dashboard။
**API Key မရှိသေးလည်း ချက်ချင်း Run လို့ရအောင် Offline Fallback Mode ပါဝင်ပါသည်။**

---

## 📁 Project Structure

```
ai-agent-saas/
├── main.py              # FastAPI app (all routes)
├── agents.py            # Router / Finance / Marketing agent logic (Gemini + offline fallback)
├── database.py          # SQLite (default) or Supabase (optional) multi-tenant storage
├── billing.py           # Stripe subscription billing (optional)
├── models.py            # Pydantic schemas
├── requirements.txt
├── .env.example         # Copy to .env and fill in the keys you need (all optional)
├── .gitignore
├── index.html           # Onboarding wizard + Chat-first AI dashboard
└── app/
    └── globals.css      # Shared styles for future frontend pages
```

> အထက်က Main file များ repository root တွင် ပါဝင်ပါသည်။ `backend/` (သို့) `frontend/` subfolder
> သီးခြားမရှိပါ — `uvicorn main:app` ကို repo root မှာသာ run လုပ်ရပါမည်။
>
> ⚠️ `backend` နှင့် `Frontend` ဟူသော ၂ ခုကို root တွင် တွေ့ရှိရပါမည်ဖြစ်သည် — သို့သော် တို့က **folder မဟုတ်**ပါ။
> Empty placeholder file ၂ ခု သာ ဖြစ်ပြီး code အတွက် လုံးဝမလိုအပ်ပါ။ `ls` လုပ်တုန်း မြင်ရပါမည်ကို
> သတိထားပါ။ n8n demo files (`messenger*.json`, `n8n_*.json`) များလည်း root တွင် ရှိပါသေးသည်။

---

## 🚀 Quick Start (API Key မလိုအပ်ဘဲ ၅ မိနစ်ဖြင့် စမ်းသပ်ရန်)

### 1. Backend ကို Setup လုပ်ပါ

```bash
cd ai-agent-saas               # repo root — main.py နှင့် requirements.txt တို့ ဒီနေရာမှာပါ
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

pip install -r requirements.txt
cp .env.example .env            # Optional — API key မထည့်ဘဲထားလည်း အလုပ်လုပ်ပါမည်
                               # Windows: copy .env.example .env
```

### 2. Server ကို Run ပါ

```bash
uvicorn main:app --reload --port 8000
```

Browser တွင် http://localhost:8000/ ကို ဖွင့်ကြည့်လျှင် status အောက်ပါအတိုင်း မြင်ရမည်-

```json
{
  "status": "ok",
  "service": "All-in-One Enterprise AI Agent SaaS",
  "ai_mode": "OFFLINE_FALLBACK",
  "billing_enabled": false,
  "database": "SQLITE (local)"
}
```

API Docs အပြည့်အစုံကို http://localhost:8000/docs တွင် ကြည့်နိုင်ပါသည်။

### 3. Frontend Dashboard ကို ဖွင့်ပါ

`index.html` ဖိုင်ကို Browser တွင် **double-click** ၍ ဖွင့်ရုံပါပဲ (Server မလို)။
- ကုမ္ပဏီအမည် + Email ဖြင့် Onboard လုပ်ပါ
- "📊 Finance Sample" / "📢 Marketing Sample" ခလုတ်များနှိပ်ပြီး AI Agent ကို စမ်းသပ်ပါ

---

## 🤖 Real AI (Google Gemini) ကို ချိတ်ဆက်ချင်ပါက

1. https://aistudio.google.com တွင် API Key ရယူပါ (အခမဲ့)
2. `.env` ဖိုင်ထဲတွင်:
   ```
   GEMINI_API_KEY=AIzaSy...your-key...
   ```
3. Server ကို ပြန်စတင်ပါ (`uvicorn main:app --reload`) — `ai_mode` သည် `GEMINI` သို့ အလိုအလျောက် ပြောင်းသွားပါမည်။

---

## 💾 Production Database (Supabase) ကို ချိတ်ဆက်ချင်ပါက

1. https://supabase.com တွင် Project အသစ် ဖန်တီးပါ
2. SQL Editor တွင် အောက်ပါ script ကို Run ပါ:

```sql
CREATE TABLE tenants (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_name VARCHAR(255) NOT NULL,
    admin_email VARCHAR(255) UNIQUE NOT NULL,
    plan_tier VARCHAR(50) DEFAULT 'FREE',
    subscription_status VARCHAR(50) DEFAULT 'INACTIVE',
    stripe_customer_id VARCHAR(255),
    stripe_subscription_id VARCHAR(255),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE finance_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID REFERENCES tenants(id) ON DELETE CASCADE,
    type VARCHAR(20) NOT NULL,
    amount NUMERIC(12,2) NOT NULL,
    category VARCHAR(100),
    description TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE marketing_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID REFERENCES tenants(id) ON DELETE CASCADE,
    headline TEXT,
    caption TEXT,
    approved BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

ALTER TABLE finance_logs ENABLE ROW LEVEL SECURITY;
ALTER TABLE marketing_logs ENABLE ROW LEVEL SECURITY;
```

3. `.env` တွင်:
   ```
   SUPABASE_URL=https://xxxx.supabase.co
   SUPABASE_SERVICE_ROLE_KEY=eyJxxxx...
   ```
4. Server ပြန်စတင်ပါ — `database` status သည် `SUPABASE` သို့ ပြောင်းသွားပါမည်။

---

## 💳 Stripe Billing ချိတ်ဆက်ချင်ပါက

1. https://dashboard.stripe.com/products တွင် Product ၂ ခု ဖန်တီးပါ (Starter / Pro) — Price ID များ ကူးထားပါ
2. `.env` တွင်:
   ```
   STRIPE_SECRET_KEY=sk_test_...
   STRIPE_PRICE_STARTER=price_...
   STRIPE_PRICE_PRO=price_...
   FRONTEND_URL=http://localhost:5500
   ```
   > `FRONTEND_URL` သည် Customer ကို Checkout / Billing Portal မှ ပြန်ခေါ်ယူမည့် URL ဖြစ်ပါသည်။
   > Default က `http://localhost:5500` ဖြစ်လို့ `index.html` ကို **ထို port ပေါ်တွင်** ဝန်ဆောင်မည်ဆိုပါက
   > (ဥပမာ — Live Server extension) အလိုက်ပါသည်။ `file://` ဖြင့် ဖွင့်ထားပါက (double-click) ဒီငွေက **ပြောင်းပါ** —
   > deploy လုပ်ပြီးဆိုရင် production frontend URL ကိုသာ သုံးပါ။
3. Local testing အတွက် Stripe CLI ကို သုံးပါ:
   ```bash
   stripe login
   stripe listen --forward-to localhost:8000/api/v1/billing/webhook
   ```
   ထွက်လာသော `whsec_...` ကို `.env` ရှိ `STRIPE_WEBHOOK_SECRET` တွင် ထည့်ပါ
4. Trigger events ဖြင့် စမ်းသပ်ပါ:
   ```bash
   stripe trigger checkout.session.completed
   ```

---

## 🔑 Multi-Tenant Security Model

- Request တိုင်းတွင် `X-Tenant-ID: <tenant uuid>` header ပါရမည်
- Local (SQLite) mode: application-level filtering (`WHERE tenant_id = ?`)
- Supabase mode: application filter + database-level Row Level Security (RLS) နှစ်ထပ်ကာကွယ်မှု

## ⚠️ Human-in-the-Loop (HITL)

Marketing Agent ထုတ်ပေးသော Facebook Post များကို **"Approve & Publish"** ခလုတ်ဖြင့် လူကိုယ်တိုင် အတည်ပြုမှသာ
Publish ဖြစ်စေရန် ဒီဇိုင်းလုပ်ထားပါသည် (AI က မှားယွင်းစွာ Auto-post လုပ်မှု မဖြစ်စေရန်)။
Meta Graph API ကို တကယ်ချိတ်ဆက်ရန် `main.py` ရှိ `approve_marketing_post()` endpoint ထဲတွင် Facebook API call ကို ထပ်ဖြည့်ရပါမည်။

## 📌 Endpoint List (အကျဉ်းချုပ်)

| Method | Path | Auth |
|---|---|---|
| POST | `/api/v1/saas/register-tenant` | - |
| GET | `/api/v1/saas/me` | X-Tenant-ID |
| POST | `/api/v1/agent/process` | X-Tenant-ID |
| GET | `/api/v1/finance/my-records` | X-Tenant-ID |
| POST | `/api/v1/marketing/{log_id}/approve` | X-Tenant-ID |
| POST | `/api/v1/billing/create-checkout-session` | X-Tenant-ID |
| POST | `/api/v1/billing/customer-portal` | X-Tenant-ID |
| POST | `/api/v1/billing/webhook` | Stripe signature |
| GET | `/api/v1/ai-agent/premium-feature` | X-Tenant-ID + ACTIVE subscription |

## 🌐 Cloud Deploy (Production)

- **Backend**: Render.com / Railway.app (Git repo ချိတ်ပြီး `uvicorn main:app --host 0.0.0.0 --port $PORT`)
- **Frontend**: Vercel / Netlify (static `index.html` ကို upload ပြီး `API_BASE` ကို production URL သို့ ပြောင်းပါ)
- **Database**: Supabase Cloud (အပေါ်ပါအတိုင်း)
