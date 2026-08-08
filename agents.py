"""
Multi-Agent Logic
------------------
GEMINI_API_KEY ရှိလျှင်  -> Google Gemini (google-genai SDK) ကို JSON Structured Output ဖြင့် သုံးမည်
GEMINI_API_KEY မရှိလျှင် -> Offline Fallback (Regex/Keyword based) Logic ဖြင့် Demo အလုပ်လုပ်မည်
  (API Key ကုန်ကျစရိတ် မရှိဘဲ UI/Backend/Database ကို အပြည့်အစုံ စမ်းသပ်နိုင်ရန်)
"""
import json
import os
import re
from typing import Tuple

from dotenv import load_dotenv

from models import RouteDecision, FinanceAnalysis, MarketingCampaign, TransactionItem

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
USE_GEMINI = bool(GEMINI_API_KEY)

_client = None
if USE_GEMINI:
    try:
        from google import genai
        from google.genai import types
        _client = genai.Client(api_key=GEMINI_API_KEY)
    except Exception as e:
        print(f"[WARN] Gemini client init failed, using offline fallback: {e}")
        USE_GEMINI = False


MODEL_NAME = "gemini-2.5-flash"


# ---------------------------------------------------------
# 1. Intent Router Agent
# ---------------------------------------------------------
FINANCE_KEYWORDS = ["ကျပ်", "ဝင်ငွေ", "ထွက်ငွေ", "ရောင်းရငွေ", "ကုန်တယ်", "ဒေါ်လာ", "$", "invoice", "ဖိုး", "ငွေ"]
MARKETING_KEYWORDS = ["post", "ပို့စ်", "caption", "marketing", "ကြော်ငြာ", "promotion", "ဒစ်စကောင့်", "facebook", "hashtag"]


def intent_router_agent(user_input: str) -> RouteDecision:
    if USE_GEMINI:
        system_prompt = (
            "သင်သည် Enterprise AI System ၏ Main Router Agent ဖြစ်သည်။ "
            "User Input ကိုကြည့်ပြီး FINANCE / MARKETING / GENERAL အနက်တစ်ခုကို ရွေးချယ်ပါ။\n"
            "- FINANCE: ငွေစာရင်း၊ ဝင်ငွေ၊ ထွက်ငွေ၊ အမြတ်အစွန်း\n"
            "- MARKETING: Facebook Post၊ Caption၊ Marketing Strategy\n"
            "- GENERAL: အထက်ပါ နှစ်ခုနှင့် မဆိုင်သော မေးခွန်းများ"
        )
        response = _client.models.generate_content(
            model=MODEL_NAME,
            contents=user_input,
            config=_types_config(system_prompt, RouteDecision),
        )
        return RouteDecision.model_validate_json(response.text)

    # ---- Offline fallback: keyword scoring ----
    text = user_input.lower()
    finance_score = sum(1 for k in FINANCE_KEYWORDS if k in text)
    marketing_score = sum(1 for k in MARKETING_KEYWORDS if k in text)
    if finance_score == 0 and marketing_score == 0:
        return RouteDecision(target_agent="GENERAL", reasoning="(Offline mode) သီးခြား keyword မတွေ့ပါ")
    if finance_score >= marketing_score:
        return RouteDecision(target_agent="FINANCE", reasoning="(Offline mode) ငွေကြေးဆိုင်ရာ စကားလုံးများ တွေ့ရှိသည်")
    return RouteDecision(target_agent="MARKETING", reasoning="(Offline mode) မားကတ်တင်းဆိုင်ရာ စကားလုံးများ တွေ့ရှိသည်")


# ---------------------------------------------------------
# 2. Finance Agent
# ---------------------------------------------------------
_NUMBER_RE = re.compile(r"([\d,]+(?:\.\d+)?)\s*(ကျပ်|ks|kyat|\$|dollars?)?", re.IGNORECASE)
_INCOME_HINTS = ["ရောင်းရငွေ", "ဝင်ငွေ", "income", "ရငွေ", "ရလာ"]


def run_finance_agent(user_input: str) -> FinanceAnalysis:
    if USE_GEMINI:
        system_prompt = (
            "သင်သည် ကုမ္ပဏီ၏ CFO / Senior Accountant Agent ဖြစ်သည်။ "
            "User ပေးထားသော စာသားပါ ငွေစာရင်းများကို စိစစ်ပြီး JSON schema အတိုင်း တိကျစွာ ထုတ်ပေးပါ။ "
            "financial_advice ကို Burmese ဖြင့် ရေးပါ။"
        )
        response = _client.models.generate_content(
            model=MODEL_NAME,
            contents=user_input,
            config=_types_config(system_prompt, FinanceAnalysis),
        )
        return FinanceAnalysis.model_validate_json(response.text)

    # ---- Offline fallback: naive sentence splitting + number extraction ----
    clauses = re.split(r"[၊,、、\n]|(?<=တယ်)|(?<=သည်)", user_input)
    items = []
    for clause in clauses:
        clause = clause.strip()
        if not clause:
            continue
        m = _NUMBER_RE.search(clause.replace(",", ""))
        if not m:
            continue
        amount = float(m.group(1).replace(",", ""))
        if amount <= 0:
            continue
        is_income = any(h in clause for h in _INCOME_HINTS)
        items.append(TransactionItem(
            type="INCOME" if is_income else "EXPENSE",
            category="Sales" if is_income else "General",
            amount=amount,
            description=clause[:80],
        ))

    total_income = sum(i.amount for i in items if i.type == "INCOME")
    total_expense = sum(i.amount for i in items if i.type == "EXPENSE")
    net_profit = total_income - total_expense
    advice = (
        f"(Offline mode) စုစုပေါင်း အသားတင်အမြတ် {net_profit:,.0f} ကျပ် ဖြစ်ပါသည်။ "
        "တိကျသော AI Insight ရယူလိုပါက .env တွင် GEMINI_API_KEY ထည့်သွင်းပါ။"
    )
    return FinanceAnalysis(
        items=items, total_income=total_income, total_expense=total_expense,
        net_profit=net_profit, financial_advice=advice,
    )


# ---------------------------------------------------------
# 3. Marketing Agent
# ---------------------------------------------------------
def run_marketing_agent(user_input: str) -> MarketingCampaign:
    if USE_GEMINI:
        system_prompt = (
            "သင်သည် Myanmar Facebook Sales Page များအတွက် Senior Social Media Marketing Expert ဖြစ်သည်။ "
            "Burmese ဘာသာဖြင့်၊ Emoji များ၊ Urgency CTA (Inbox/Comment) ပါဝင်သော Facebook Post Caption "
            "တစ်ခုကို ရေးသားပေးပါ။ requires_human_approval ကို အမြဲ true သတ်မှတ်ပါ။"
        )
        response = _client.models.generate_content(
            model=MODEL_NAME,
            contents=user_input,
            config=_types_config(system_prompt, MarketingCampaign),
        )
        return MarketingCampaign.model_validate_json(response.text)

    # ---- Offline fallback: simple Burmese sales-post template ----
    caption = (
        f"🔥 {user_input.strip()} 🔥\n\n"
        "✅ အရည်အသွေး အာမခံ\n"
        "✅ Yangon အနှံ့ Delivery လုပ်ပေးပါတယ်\n"
        "📩 Inbox / Comment ချန်ထားခဲ့ပါ\n"
        "⏰ အကန့်အသတ်ဖြင့်သာ ရရှိနိုင်ပါသည်!"
    )
    return MarketingCampaign(
        target_audience="Yangon local Facebook customers (Offline mode default)",
        content_headline=user_input.strip()[:60] or "Special Promotion",
        facebook_post_caption=caption,
        suggested_hashtags=["#YangonDelivery", "#FreshDaily", "#SpecialOffer"],
        requires_human_approval=True,
    )


# ---------------------------------------------------------
# Helper for Gemini structured-output config
# ---------------------------------------------------------
def _types_config(system_prompt: str, schema):
    from google.genai import types
    return types.GenerateContentConfig(
        system_instruction=system_prompt,
        response_mime_type="application/json",
        response_schema=schema,
        temperature=0.2,
    )
