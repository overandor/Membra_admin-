"""MEMBRA Admin — operator console for proof, fraud, campaign, and payout decisions.

This app records review decisions, fraud holds, campaign approvals, payout eligibility
decisions, canonical MEMBRA OS events, and audit logs. It does not settle funds;
it gates eligibility for external payment rails.
"""
from __future__ import annotations

import csv
import datetime as dt
import hashlib
import hmac
import json
import os
import sqlite3
import uuid
from pathlib import Path
from typing import Any

import gradio as gr
import uvicorn
from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel, Field

APP_NAME = "MEMBRA Admin"
APP_VERSION = "1.1.0"
DB_PATH = Path(os.getenv("APP_DB_PATH", "/tmp/membra_admin.sqlite3"))
ADMIN_TOKEN = os.getenv("ADMIN_TOKEN", "")
MEMBRA_EVENT_SECRET = os.getenv("MEMBRA_EVENT_SECRET", "")
api = FastAPI(title=APP_NAME, version=APP_VERSION)


class DecisionIn(BaseModel):
    subject_type: str = Field(description="proof|campaign|payout|relay|wear_kit|asset|listing")
    subject_id: str
    decision: str = "approved"
    operator: str = "operator"
    risk_level: str = "low"
    notes: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)


class MembraEventIn(BaseModel):
    event_id: str
    event_type: str
    source_module: str
    subject_type: str
    subject_id: str
    owner_id: str | None = None
    correlation_id: str | None = None
    causation_id: str | None = None
    created_at: str
    consent_scope: str | None = None
    risk_level: str = "normal"
    payload: dict[str, Any] = Field(default_factory=dict)
    proof_hash: str | None = None
    signature: str | None = None


def now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


def canonical(payload: dict[str, Any]) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str)


def verify_event_signature(event: dict[str, Any]) -> bool:
    if not MEMBRA_EVENT_SECRET:
        return True
    supplied = event.get("signature") or ""
    unsigned = dict(event)
    unsigned["signature"] = None
    expected = "hmac_sha256:" + hmac.new(MEMBRA_EVENT_SECRET.encode("utf-8"), canonical(unsigned).encode("utf-8"), hashlib.sha256).hexdigest()
    return hmac.compare_digest(supplied, expected)


def db() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH, timeout=30, isolation_level=None)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with db() as conn:
        conn.executescript("""
        CREATE TABLE IF NOT EXISTS review_queue(
          queue_id TEXT PRIMARY KEY,
          subject_type TEXT,
          subject_id TEXT,
          status TEXT,
          priority TEXT,
          created_at TEXT
        );
        CREATE TABLE IF NOT EXISTS decisions(
          decision_id TEXT PRIMARY KEY,
          subject_type TEXT,
          subject_id TEXT,
          decision TEXT,
          operator TEXT,
          risk_level TEXT,
          notes TEXT,
          metadata_json TEXT,
          created_at TEXT
        );
        CREATE TABLE IF NOT EXISTS audit_events(
          audit_id TEXT PRIMARY KEY,
          actor TEXT,
          action TEXT,
          subject_type TEXT,
          subject_id TEXT,
          metadata_json TEXT,
          created_at TEXT
        );
        CREATE TABLE IF NOT EXISTS events(
          event_id TEXT PRIMARY KEY,
          event_type TEXT,
          source_module TEXT,
          subject_type TEXT,
          subject_id TEXT,
          owner_id TEXT,
          risk_level TEXT,
          proof_hash TEXT,
          signature TEXT,
          payload_json TEXT,
          status TEXT,
          created_at TEXT,
          ingested_at TEXT
        );
        CREATE INDEX IF NOT EXISTS idx_admin_events_type ON events(event_type);
        CREATE INDEX IF NOT EXISTS idx_admin_events_subject ON events(subject_type, subject_id);
        """)


init_db()


def require_admin(authorization: str | None) -> None:
    if ADMIN_TOKEN and authorization != f"Bearer {ADMIN_TOKEN}":
        raise HTTPException(401, "Unauthorized")


def add_audit(actor: str, action: str, subject_type: str, subject_id: str, metadata: dict[str, Any]) -> dict[str, Any]:
    row = {"audit_id": new_id("audit"), "actor": actor, "action": action, "subject_type": subject_type, "subject_id": subject_id, "metadata_json": json.dumps(metadata, default=str), "created_at": now()}
    with db() as conn:
        conn.execute("INSERT INTO audit_events VALUES(?,?,?,?,?,?,?)", tuple(row.values()))
    return row


def add_to_queue(subject_type: str, subject_id: str, priority: str = "normal") -> dict[str, Any]:
    row = {"queue_id": new_id("queue"), "subject_type": subject_type, "subject_id": subject_id, "status": "pending_review", "priority": priority, "created_at": now()}
    with db() as conn:
        conn.execute("INSERT INTO review_queue VALUES(?,?,?,?,?,?)", tuple(row.values()))
    add_audit("system", "queued_for_review", subject_type, subject_id, {"priority": priority})
    return row


def record_decision(data: DecisionIn) -> dict[str, Any]:
    allowed = {"approved", "rejected", "needs_more_evidence", "fraud_hold", "payout_hold", "payout_eligible", "archived"}
    if data.decision not in allowed:
        raise ValueError(f"decision must be one of {sorted(allowed)}")
    row = {"decision_id": new_id("dec"), "subject_type": data.subject_type, "subject_id": data.subject_id, "decision": data.decision, "operator": data.operator, "risk_level": data.risk_level, "notes": data.notes, "metadata_json": json.dumps(data.metadata, default=str), "created_at": now()}
    with db() as conn:
        conn.execute("INSERT INTO decisions VALUES(?,?,?,?,?,?,?,?,?)", tuple(row.values()))
        conn.execute("UPDATE review_queue SET status=? WHERE subject_type=? AND subject_id=?", (data.decision, data.subject_type, data.subject_id))
    add_audit(data.operator, f"decision:{data.decision}", data.subject_type, data.subject_id, {"risk_level": data.risk_level, "notes": data.notes, **data.metadata})
    return row


def table(name: str) -> list[dict[str, Any]]:
    allowed = {"review_queue", "decisions", "audit_events", "events"}
    if name not in allowed:
        return []
    order_col = "ingested_at" if name == "events" else "created_at"
    with db() as conn:
        rows = conn.execute(f"SELECT * FROM {name} ORDER BY {order_col} DESC LIMIT 300").fetchall()
    return [dict(r) for r in rows]


def export_decisions() -> str:
    decision_rows = table("decisions")
    path = "/tmp/membra_admin_decisions.csv"
    if decision_rows:
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=list(decision_rows[0].keys()))
            writer.writeheader(); writer.writerows(decision_rows)
    else:
        Path(path).write_text("decision_id,subject_type,subject_id,decision\n", encoding="utf-8")
    return path


def priority_for_event(data: MembraEventIn) -> str:
    if data.risk_level in {"high", "blocked"}:
        return "urgent"
    if data.event_type in {"visibility_requested", "payout_eligibility_created", "admin_decision_recorded"}:
        return "high"
    return "normal"


@api.get("/api/health")
def health():
    return {"ok": True, "app": APP_NAME, "version": APP_VERSION, "admin_token_configured": bool(ADMIN_TOKEN)}


@api.get("/api/ready")
def ready():
    warnings = [] if MEMBRA_EVENT_SECRET else ["MEMBRA_EVENT_SECRET not configured; signed event verification is permissive"]
    return {"ok": True, "warnings": warnings, "queue_count": len(table("review_queue")), "event_count": len(table("events"))}


@api.post("/api/events/ingest")
def ingest_event(data: MembraEventIn):
    event = data.model_dump()
    if not verify_event_signature(event):
        raise HTTPException(401, "invalid event signature")
    with db() as conn:
        conn.execute(
            "INSERT OR IGNORE INTO events VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (data.event_id, data.event_type, data.source_module, data.subject_type, data.subject_id, data.owner_id, data.risk_level, data.proof_hash, data.signature, json.dumps(event, default=str), "ingested", data.created_at, now()),
        )
    queued = None
    if data.event_type in {"visibility_requested", "visibility_confirmed", "payout_eligibility_created", "photo_analyzed", "listing_drafts_created"}:
        queued = add_to_queue(data.subject_type, data.subject_id, priority_for_event(data))
        add_audit("event_ingest", f"event:{data.event_type}", data.subject_type, data.subject_id, event)
    return {"ok": True, "event_id": data.event_id, "queued": queued}


@api.get("/api/events")
def list_events():
    return {"events": table("events")}


@api.post("/api/queue")
def api_queue(subject_type: str, subject_id: str, priority: str = "normal", authorization: str | None = Header(default=None)):
    require_admin(authorization)
    return add_to_queue(subject_type, subject_id, priority)


@api.post("/api/decisions")
def api_decision(data: DecisionIn, authorization: str | None = Header(default=None)):
    require_admin(authorization)
    try:
        return record_decision(data)
    except ValueError as exc:
        raise HTTPException(400, str(exc))


@api.get("/api/{name}")
def api_table(name: str):
    return {name: table(name)}


def ui_queue(subject_type, subject_id, priority):
    return add_to_queue(subject_type, subject_id, priority), table("review_queue"), table("audit_events")


def ui_decide(subject_type, subject_id, decision, operator, risk, notes, metadata_json):
    try:
        metadata = json.loads(metadata_json or "{}")
        out = record_decision(DecisionIn(subject_type=subject_type, subject_id=subject_id, decision=decision, operator=operator, risk_level=risk, notes=notes, metadata=metadata))
        return out, table("decisions"), table("review_queue"), table("audit_events"), export_decisions()
    except Exception as exc:
        return {"error": str(exc)}, table("decisions"), table("review_queue"), table("audit_events"), None


with gr.Blocks(title=APP_NAME) as demo:
    gr.Markdown("# MEMBRA Admin\nOperator console and canonical event review queue for proof review, campaign approval, fraud holds, and payout eligibility.")
    with gr.Tab("Queue"):
        q_type = gr.Dropdown(["proof", "campaign", "payout", "relay", "wear_kit", "asset", "listing"], label="Subject type", value="proof")
        q_id = gr.Textbox(label="Subject ID")
        q_priority = gr.Dropdown(["low", "normal", "high", "urgent"], value="normal", label="Priority")
        q_btn = gr.Button("Queue for review", variant="primary")
        q_out = gr.JSON(label="Queued item")
    with gr.Tab("Decision"):
        d_type = gr.Dropdown(["proof", "campaign", "payout", "relay", "wear_kit", "asset", "listing"], label="Subject type", value="proof")
        d_id = gr.Textbox(label="Subject ID")
        d_decision = gr.Dropdown(["approved", "rejected", "needs_more_evidence", "fraud_hold", "payout_hold", "payout_eligible", "archived"], value="approved", label="Decision")
        d_operator = gr.Textbox(label="Operator", value="operator")
        d_risk = gr.Dropdown(["low", "medium", "high", "critical"], value="low", label="Risk level")
        d_notes = gr.Textbox(label="Notes", lines=3)
        d_meta = gr.Code(label="Metadata JSON", language="json", value="{}")
        d_btn = gr.Button("Record decision", variant="primary")
        d_out = gr.JSON(label="Decision")
    with gr.Tab("Events"):
        gr.Markdown("Canonical MEMBRA events arrive through `/api/events/ingest` and may create review queue items.")
        gr.Dataframe(label="Events", value=lambda: table("events"), interactive=False)
    queue_table = gr.Dataframe(label="Review queue", value=lambda: table("review_queue"), interactive=False)
    decisions_table = gr.Dataframe(label="Decisions", value=lambda: table("decisions"), interactive=False)
    audit_table = gr.Dataframe(label="Audit events", value=lambda: table("audit_events"), interactive=False)
    export_file = gr.File(label="Decision CSV export")
    q_btn.click(ui_queue, [q_type, q_id, q_priority], [q_out, queue_table, audit_table])
    d_btn.click(ui_decide, [d_type, d_id, d_decision, d_operator, d_risk, d_notes, d_meta], [d_out, decisions_table, queue_table, audit_table, export_file])

app = gr.mount_gradio_app(api, demo, path="/")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", "7860")))
