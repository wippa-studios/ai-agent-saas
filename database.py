"""
Database Layer - Multi-Tenant Storage
--------------------------------------
Default: Local SQLite file (agent_saas.db) -> ချက်ချင်း Run လို့ရ၊ Setup မလို။
Optional: SUPABASE_URL + SUPABASE_SERVICE_ROLE_KEY ကို .env တွင် ထည့်လိုက်ပါက
          Supabase (PostgreSQL) ကို အလိုအလျောက် သုံးမည်။ (Production အတွက် အကြံပြု)

Multi-Tenant Isolation: query တိုင်းတွင် tenant_id ဖြင့် filter လုပ်ထားသည်.
"""
import os
import sqlite3
import uuid
from datetime import datetime, timezone
from typing import Optional

from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL", "").strip()
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "").strip()
USE_SUPABASE = bool(SUPABASE_URL and SUPABASE_KEY)

DB_PATH = os.path.join(os.path.dirname(__file__), "agent_saas.db")

_supabase_client = None
if USE_SUPABASE:
    try:
        from supabase import create_client
        _supabase_client = create_client(SUPABASE_URL, SUPABASE_KEY)
    except Exception as e:
        print(f"[WARN] Supabase client init failed, falling back to SQLite: {e}")
        USE_SUPABASE = False


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


# ---------------------------------------------------------
# SQLite (Default / Local Dev / Demo)
# ---------------------------------------------------------
def _get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Local SQLite အသုံးပြုနေလျှင် Table များကို Setup ပြုလုပ်သည်။"""
    if USE_SUPABASE:
        return  # Supabase side လုပ်ငန်းစဉ်ကို README ရှိ SQL script ဖြင့် ကိုယ်တိုင် run ရန်
    conn = _get_conn()
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS tenants (
            id TEXT PRIMARY KEY,
            company_name TEXT NOT NULL,
            admin_email TEXT UNIQUE NOT NULL,
            plan_tier TEXT DEFAULT 'FREE',
            subscription_status TEXT DEFAULT 'INACTIVE',
            stripe_customer_id TEXT,
            stripe_subscription_id TEXT,
            created_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS finance_logs (
            id TEXT PRIMARY KEY,
            tenant_id TEXT NOT NULL,
            type TEXT NOT NULL,
            amount REAL NOT NULL,
            category TEXT,
            description TEXT,
            created_at TEXT NOT NULL,
            FOREIGN KEY (tenant_id) REFERENCES tenants (id)
        );

        CREATE TABLE IF NOT EXISTS marketing_logs (
            id TEXT PRIMARY KEY,
            tenant_id TEXT NOT NULL,
            headline TEXT,
            caption TEXT,
            approved INTEGER DEFAULT 0,
            created_at TEXT NOT NULL,
            FOREIGN KEY (tenant_id) REFERENCES tenants (id)
        );
        """
    )
    conn.commit()
    conn.close()


# ---------------------------------------------------------
# Public API (used by main.py) - routes to SQLite or Supabase
# ---------------------------------------------------------

def create_tenant(company_name: str, admin_email: str, plan_tier: str = "FREE") -> dict:
    tenant_id = str(uuid.uuid4())
    payload = {
        "id": tenant_id,
        "company_name": company_name,
        "admin_email": admin_email,
        "plan_tier": plan_tier,
        "subscription_status": "ACTIVE" if plan_tier == "FREE" else "INACTIVE",
        "created_at": _now(),
    }
    if USE_SUPABASE:
        _supabase_client.table("tenants").insert(payload).execute()
        return payload

    conn = _get_conn()
    try:
        conn.execute(
            "INSERT INTO tenants (id, company_name, admin_email, plan_tier, subscription_status, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (tenant_id, company_name, admin_email, plan_tier, payload["subscription_status"], payload["created_at"]),
        )
        conn.commit()
    except sqlite3.IntegrityError:
        conn.close()
        raise ValueError("ဒီ Email ဖြင့် Tenant အကောင့် ရှိပြီးသားဖြစ်ပါသည်")
    conn.close()
    return payload


def get_tenant(tenant_id: str) -> Optional[dict]:
    if USE_SUPABASE:
        res = _supabase_client.table("tenants").select("*").eq("id", tenant_id).execute()
        return res.data[0] if res.data else None

    conn = _get_conn()
    row = conn.execute("SELECT * FROM tenants WHERE id = ?", (tenant_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def update_tenant_subscription(customer_id: str = None, tenant_id: str = None, **fields):
    """subscription_status / plan_tier / stripe_customer_id / stripe_subscription_id ကို update"""
    if not fields:
        return
    if USE_SUPABASE:
        q = _supabase_client.table("tenants").update(fields)
        if tenant_id:
            q = q.eq("id", tenant_id)
        elif customer_id:
            q = q.eq("stripe_customer_id", customer_id)
        q.execute()
        return

    conn = _get_conn()
    set_clause = ", ".join(f"{k} = ?" for k in fields.keys())
    values = list(fields.values())
    if tenant_id:
        conn.execute(f"UPDATE tenants SET {set_clause} WHERE id = ?", (*values, tenant_id))
    elif customer_id:
        conn.execute(f"UPDATE tenants SET {set_clause} WHERE stripe_customer_id = ?", (*values, customer_id))
    conn.commit()
    conn.close()


def insert_finance_records(tenant_id: str, items: list) -> None:
    if USE_SUPABASE:
        rows = [
            {"id": str(uuid.uuid4()), "tenant_id": tenant_id, "type": i["type"], "amount": i["amount"],
             "category": i["category"], "description": i["description"], "created_at": _now()}
            for i in items
        ]
        if rows:
            _supabase_client.table("finance_logs").insert(rows).execute()
        return

    conn = _get_conn()
    for i in items:
        conn.execute(
            "INSERT INTO finance_logs (id, tenant_id, type, amount, category, description, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (str(uuid.uuid4()), tenant_id, i["type"], i["amount"], i["category"], i["description"], _now()),
        )
    conn.commit()
    conn.close()


def get_finance_records(tenant_id: str) -> list:
    if USE_SUPABASE:
        res = _supabase_client.table("finance_logs").select("*").eq("tenant_id", tenant_id) \
            .order("created_at", desc=True).execute()
        return res.data

    conn = _get_conn()
    rows = conn.execute(
        "SELECT * FROM finance_logs WHERE tenant_id = ? ORDER BY created_at DESC", (tenant_id,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def insert_marketing_log(tenant_id: str, headline: str, caption: str) -> str:
    log_id = str(uuid.uuid4())
    if USE_SUPABASE:
        _supabase_client.table("marketing_logs").insert(
            {"id": log_id, "tenant_id": tenant_id, "headline": headline, "caption": caption,
             "approved": 0, "created_at": _now()}
        ).execute()
        return log_id

    conn = _get_conn()
    conn.execute(
        "INSERT INTO marketing_logs (id, tenant_id, headline, caption, approved, created_at) "
        "VALUES (?, ?, ?, ?, 0, ?)",
        (log_id, tenant_id, headline, caption, _now()),
    )
    conn.commit()
    conn.close()
    return log_id


def approve_marketing_log(tenant_id: str, log_id: str) -> bool:
    if USE_SUPABASE:
        res = _supabase_client.table("marketing_logs").update({"approved": 1}) \
            .eq("id", log_id).eq("tenant_id", tenant_id).execute()
        return bool(res.data)

    conn = _get_conn()
    cur = conn.execute(
        "UPDATE marketing_logs SET approved = 1 WHERE id = ? AND tenant_id = ?", (log_id, tenant_id)
    )
    conn.commit()
    changed = cur.rowcount > 0
    conn.close()
    return changed
