"""RG Analyst Console - Databricks App.

* Case queue, case actions -> Lakebase Postgres (app service principal, OLTP)
* Player trend, entitlements, Genie -> Unity Catalog as the signed-in user (on-behalf-of), so row filters and masks apply
"""
from __future__ import annotations

import os
import threading
import time
from contextlib import contextmanager
from pathlib import Path

import psycopg
from databricks.sdk import WorkspaceClient
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from psycopg.rows import dict_row
from pydantic import BaseModel

CATALOG = os.environ["CATALOG"]
SCHEMA = os.getenv("SCHEMA", "sportsbook_rg")
FQ = f"{CATALOG}.{SCHEMA}"
WAREHOUSE_ID = os.environ["WAREHOUSE_ID"]
GENIE_SPACE_ID = os.environ["GENIE_SPACE_ID"]
LAKEBASE_ENDPOINT = os.environ["LAKEBASE_ENDPOINT"]
LAKEBASE_DB = os.getenv("LAKEBASE_DB", "databricks_postgres")

ACTIONS = ["SAFER_GAMBLING_MESSAGE", "OUTBOUND_WELLBEING_CALL", "MANDATORY_COOL_OFF_24H",
           "DEPOSIT_LIMIT_REDUCTION", "AFFORDABILITY_REVIEW", "ESCALATE_TO_COMPLIANCE", "NO_ACTION_REQUIRED"]
STATUSES = ["OPEN", "IN_REVIEW", "ACTIONED", "CLOSED_NO_ACTION"]

app_ws = WorkspaceClient()  # app service principal (or local profile)
app = FastAPI(title="RG Analyst Console")


# ----------------------------------------------------------------------------- Lakebase (app SP)
class _Lakebase:
    """Postgres connection with an OAuth token refreshed before its 1h expiry."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._token, self._exp = None, 0.0
        ep = app_ws.api_client.do("GET", f"/api/2.0/postgres/{LAKEBASE_ENDPOINT}")
        self.host = ep["status"]["hosts"]["host"]
        self.user = os.getenv("DATABRICKS_CLIENT_ID") or app_ws.current_user.me().user_name

    def _password(self) -> str:
        with self._lock:
            if time.time() > self._exp:
                cred = app_ws.api_client.do("POST", "/api/2.0/postgres/credentials", body={"endpoint": LAKEBASE_ENDPOINT})
                self._token, self._exp = cred["token"], time.time() + 45 * 60
            return self._token

    @contextmanager
    def conn(self):
        with psycopg.connect(host=self.host, dbname=LAKEBASE_DB, user=self.user, password=self._password(),
                             sslmode="require", row_factory=dict_row, connect_timeout=15) as c:
            yield c


_lb: _Lakebase | None = None


def lakebase() -> _Lakebase:
    global _lb
    if _lb is None:
        _lb = _Lakebase()
    return _lb


# ----------------------------------------------------------------------------- Unity Catalog (on-behalf-of user)
def user_ws(request: Request) -> WorkspaceClient:
    token = request.headers.get("x-forwarded-access-token")
    if not token:  # local development: fall back to the developer's own profile
        return app_ws
    return WorkspaceClient(host=app_ws.config.host, token=token, auth_type="pat")


def user_email(request: Request) -> str:
    return request.headers.get("x-forwarded-email") or app_ws.current_user.me().user_name


def sql(request: Request, statement: str, params: dict | None = None) -> list[dict]:
    body = {"warehouse_id": WAREHOUSE_ID, "statement": statement, "wait_timeout": "30s", "disposition": "INLINE",
            "format": "JSON_ARRAY",
            "parameters": [{"name": k, "value": str(v)} for k, v in (params or {}).items()]}
    r = user_ws(request).api_client.do("POST", "/api/2.0/sql/statements", body=body)
    while r["status"]["state"] in ("PENDING", "RUNNING"):
        time.sleep(1)
        r = user_ws(request).api_client.do("GET", f"/api/2.0/sql/statements/{r['statement_id']}")
    if r["status"]["state"] != "SUCCEEDED":
        raise HTTPException(502, r["status"].get("error", {}).get("message", "query failed"))
    cols = [c["name"] for c in r["manifest"]["schema"]["columns"]]
    return [dict(zip(cols, row)) for row in r.get("result", {}).get("data_array", [])]


_markets_cache: dict[str, tuple[float, list[str]]] = {}


def allowed_markets(request: Request) -> list[str]:
    """Markets the user may see, decided by the Unity Catalog row filter (not by the app)."""
    email = user_email(request)
    hit = _markets_cache.get(email)
    if hit and time.time() - hit[0] < 300:
        return hit[1]
    rows = sql(request, f"SELECT DISTINCT market FROM {FQ}.player_risk_scores ORDER BY market")
    markets = [r["market"] for r in rows]
    _markets_cache[email] = (time.time(), markets)
    return markets


# ----------------------------------------------------------------------------- API
@app.get("/api/me")
def me(request: Request):
    return {"email": user_email(request), "markets": allowed_markets(request), "actions": ACTIONS, "statuses": STATUSES}


@app.get("/api/summary")
def summary(request: Request):
    markets = allowed_markets(request)
    with lakebase().conn() as c:
        rows = c.execute("""
          SELECT market,
                 count(*) FILTER (WHERE status IN ('OPEN','IN_REVIEW')) AS open_cases,
                 count(*) FILTER (WHERE status IN ('OPEN','IN_REVIEW') AND risk_tier = 'HIGH') AS open_high,
                 count(*) FILTER (WHERE status IN ('OPEN','IN_REVIEW') AND sla_due_at < now() + interval '24 hours') AS due_24h,
                 count(*) FILTER (WHERE status IN ('ACTIONED','CLOSED_NO_ACTION')) AS resolved
          FROM rg_ops.risk_cases WHERE market = ANY(%s) GROUP BY market ORDER BY market""", (markets,)).fetchall()
        recent = c.execute("""
          SELECT i.player_id, i.action, i.new_status, i.analyst, i.created_at
          FROM rg_ops.interventions i JOIN rg_ops.risk_cases r USING (player_id)
          WHERE r.market = ANY(%s) ORDER BY i.created_at DESC LIMIT 8""", (markets,)).fetchall()
    return {"by_market": rows, "recent_interventions": recent}


@app.get("/api/cases")
def cases(request: Request, status: str = "OPEN", market: str = "", tier: str = "", limit: int = 100):
    markets = allowed_markets(request)
    if market:
        markets = [m for m in markets if m == market]
    q = """SELECT player_id, market, risk_score, risk_tier, reason_codes, recommended_action, urgency, status,
                  assigned_to, sla_due_at, updated_at
           FROM rg_ops.risk_cases WHERE market = ANY(%s) AND (%s = '' OR status = %s) AND (%s = '' OR risk_tier = %s)
           ORDER BY (risk_tier = 'HIGH') DESC, sla_due_at, risk_score DESC LIMIT %s"""
    with lakebase().conn() as c:
        return c.execute(q, (markets, status, status, tier, tier, min(limit, 500))).fetchall()


@app.get("/api/cases/{player_id}")
def case_detail(player_id: str, request: Request):
    with lakebase().conn() as c:
        case = c.execute("SELECT * FROM rg_ops.risk_cases WHERE player_id = %s", (player_id,)).fetchone()
        if not case or case["market"] not in allowed_markets(request):
            raise HTTPException(404, "case not found or not in your licensed markets")
        history = c.execute("SELECT * FROM rg_ops.interventions WHERE player_id = %s ORDER BY created_at DESC",
                            (player_id,)).fetchall()
    trend = sql(request, f"""
        SELECT activity_date, bets, stake_eur, net_loss_eur, night_bets, deposits, reversed_withdrawals
        FROM {FQ}.gold_player_daily
        WHERE player_id = :pid AND activity_date > date_sub((SELECT max(activity_date) FROM {FQ}.gold_player_daily), 56)
        ORDER BY activity_date""", {"pid": player_id})
    profile = sql(request, f"""SELECT player_id, first_name, last_name, email, date_of_birth, age, market, tenure_days, kyc_status
                               FROM {FQ}.silver_players WHERE player_id = :pid""", {"pid": player_id})
    return {"case": case, "history": history, "trend": trend, "profile": profile[0] if profile else None}


class ActionIn(BaseModel):
    action: str
    note: str = ""
    new_status: str = "ACTIONED"


@app.post("/api/cases/{player_id}/actions")
def take_action(player_id: str, body: ActionIn, request: Request):
    if body.action not in ACTIONS or body.new_status not in STATUSES:
        raise HTTPException(400, "unknown action or status")
    analyst = user_email(request)
    with lakebase().conn() as c:
        case = c.execute("SELECT market FROM rg_ops.risk_cases WHERE player_id = %s", (player_id,)).fetchone()
        if not case or case["market"] not in allowed_markets(request):
            raise HTTPException(404, "case not found or not in your licensed markets")
        with c.transaction():
            row = c.execute("""INSERT INTO rg_ops.interventions (player_id, action, note, analyst, new_status)
                               VALUES (%s,%s,%s,%s,%s) RETURNING *""",
                            (player_id, body.action, body.note[:2000], analyst, body.new_status)).fetchone()
            c.execute("UPDATE rg_ops.risk_cases SET status = %s, assigned_to = %s, updated_at = now() WHERE player_id = %s",
                      (body.new_status, analyst, player_id))
    return row


# ----------------------------------------------------------------------------- Genie (on-behalf-of user)
class AskIn(BaseModel):
    question: str
    conversation_id: str | None = None


@app.post("/api/genie/ask")
def genie_ask(body: AskIn, request: Request):
    w = user_ws(request)
    base = f"/api/2.0/genie/spaces/{GENIE_SPACE_ID}"
    if body.conversation_id:
        r = w.api_client.do("POST", f"{base}/conversations/{body.conversation_id}/messages", body={"content": body.question})
        return {"conversation_id": body.conversation_id, "message_id": r.get("message_id") or r.get("id")}
    r = w.api_client.do("POST", f"{base}/start-conversation", body={"content": body.question})
    return {"conversation_id": r["conversation_id"], "message_id": r["message_id"]}


@app.get("/api/genie/{conversation_id}/{message_id}")
def genie_poll(conversation_id: str, message_id: str, request: Request):
    w = user_ws(request)
    base = f"/api/2.0/genie/spaces/{GENIE_SPACE_ID}/conversations/{conversation_id}/messages/{message_id}"
    m = w.api_client.do("GET", base)
    out = {"status": m.get("status"), "text": None, "sql": None, "columns": [], "rows": [], "error": m.get("error")}
    for att in m.get("attachments") or []:
        if att.get("text"):
            out["text"] = att["text"].get("content")
        if att.get("query"):
            out["sql"] = att["query"].get("query")
            out["text"] = out["text"] or att["query"].get("description")
            if m.get("status") == "COMPLETED":
                res = w.api_client.do("GET", f"{base}/attachments/{att['attachment_id']}/query-result")
                sr = res.get("statement_response", {})
                out["columns"] = [c["name"] for c in sr.get("manifest", {}).get("schema", {}).get("columns", [])]
                out["rows"] = sr.get("result", {}).get("data_array", [])[:50]
    return out


@app.get("/api/health")
def health():
    with lakebase().conn() as c:
        n = c.execute("SELECT count(*) AS n FROM rg_ops.risk_cases").fetchone()["n"]
    return {"ok": True, "lakebase_cases": n}


STATIC = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=STATIC), name="static")


@app.get("/")
def index():
    return FileResponse(STATIC / "index.html")
