"""TRACE. workbench wired to the Person 2 fraud-investigation backend."""

from __future__ import annotations

import html
import json
import sys
from pathlib import Path

import streamlit as st

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from Backend.agent import FraudInvestigationAgent  # noqa: E402


st.set_page_config(page_title="TRACE. — Fraud Investigation Workbench", page_icon=".", layout="wide")

st.markdown(
    """<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Mono&family=Space+Grotesk:wght@400;500;600;700&display=swap');
.stApp{background:#090909;color:#f1eee7}.block-container{max-width:1500px;padding:1.3rem 2.6rem 3rem}section[data-testid=stSidebar]{background:#0c0c0c;border-right:1px solid #292929}
body,[class*="css"]{font-family:"Space Grotesk",sans-serif}.mono{font-family:"DM Mono",monospace}
.k{font-family:"DM Mono",monospace;font-size:.58rem;letter-spacing:.22em;color:#666;text-transform:uppercase}.title{font-size:clamp(4rem,8vw,7rem);line-height:.83;font-weight:700;letter-spacing:-.08em;margin:.6rem 0}.soft{color:#aaa59e}
.meta{border-top:1px solid #303030;padding-top:9px;margin-bottom:14px}.meta small{display:block;color:#666;font-family:"DM Mono",monospace;font-size:.55rem;letter-spacing:.15em;text-transform:uppercase}.meta b{display:block;font-size:.82rem;margin-top:5px}
.panel{border-top:1px solid #292929;padding-top:8px;margin-top:18px;font-family:"DM Mono",monospace;font-size:.62rem;letter-spacing:.13em;text-transform:uppercase;color:#ccc}.entity,.box,.action{border:1px solid #292929;background:#101010;padding:12px}.entity small{color:#666;font-family:"DM Mono",monospace;font-size:.5rem;text-transform:uppercase}.entity b{display:block;font-size:.78rem;margin:6px 0 4px}.muted{color:#777;font-size:.62rem}.event{border-left:1px solid #3b3b3b;padding:0 0 17px 15px;margin-left:7px}.event.add{border-color:#ef4b36}.event small{font-family:"DM Mono",monospace;color:#666;font-size:.5rem}.event b{font-size:.72rem}.event p{color:#999;font-size:.64rem;line-height:1.5;margin:4px 0 0}.action{margin-bottom:8px}.action.after{border-color:#4a3530;background:#141110}.action b{font-size:.72rem}.reason{color:#999;font-size:.64rem;line-height:1.6}.sar{border:1px solid #3a2724;background:#120e0e;padding:12px}
div[data-testid="stProgressBar"] > div > div{background:#ef4b36}
</style>""",
    unsafe_allow_html=True,
)


def esc(value: object) -> str:
    return html.escape(str(value))


def status_label(status: str) -> str:
    return {"needs_evidence": "Evidence requested", "escalated": "Escalated", "open": "Open", "resolved": "Resolved", "closed": "Closed"}.get(status, status.replace("_", " ").title())


def pattern_label(case: dict) -> str:
    findings = case.get("findings", [])
    return findings[0].get("pattern", "Unclassified").replace("_", " ").title() if findings else "Unclassified"


def confidence_label(value: float) -> str:
    return "High" if value >= .8 else "Medium" if value >= .5 else "Low"


def run_investigation(agent: FraudInvestigationAgent, trigger: dict) -> dict:
    try:
        return agent.investigate(trigger)
    except ValueError as exc:
        st.error(str(exc))
        return {}


if "agent" not in st.session_state:
    st.session_state.agent = FraudInvestigationAgent(evidence_wait_seconds=.02)
if "cases" not in st.session_state:
    initial = run_investigation(
        st.session_state.agent,
        {"type": "fraud_signal", "risk_score": .87, "reason": "velocity and device anomaly", "customer_id": "cust-1001", "transaction_id": "tx-1001-01"},
    )
    st.session_state.cases = {initial["case_id"]: initial} if initial else {}

agent = st.session_state.agent
cases = st.session_state.cases

with st.sidebar:
    st.markdown('<div style="font-size:22px;font-weight:800;letter-spacing:-.07em">TRACE<span style="color:#ef4b36">.</span></div><div class="k">Fraud intelligence • live agent</div>', unsafe_allow_html=True)
    st.divider()
    st.markdown('<div class="k">Run investigation</div>', unsafe_allow_html=True)
    trigger_type = st.selectbox("TRIGGER", ["fraud_signal", "customer_report", "analyst_request"], format_func=lambda value: value.replace("_", " ").title(), key="trigger_type")
    customer_id = st.text_input("CUSTOMER ID", value="cust-1001")
    if trigger_type == "fraud_signal":
        risk_score = st.slider("RISK SCORE", 0.0, 1.0, .87, .01)
        transaction_id = st.text_input("TRANSACTION ID", value="tx-1001-01")
        reason = st.text_input("SIGNAL REASON", value="velocity and device anomaly")
        trigger = {"type": trigger_type, "risk_score": risk_score, "reason": reason, "customer_id": customer_id, "transaction_id": transaction_id}
    elif trigger_type == "customer_report":
        description = st.text_area("CUSTOMER DESCRIPTION", value="I do not recognize this activity.")
        trigger = {"type": trigger_type, "customer_id": customer_id, "description": description, "reported_date": "2026-09-24"}
    else:
        analyst_id = st.text_input("ANALYST ID", value="analyst-001")
        description = st.text_area("REQUEST", value="Review linked accounts and recent activity.")
        trigger = {"type": trigger_type, "analyst_id": analyst_id, "customer_id": customer_id, "description": description}
    if st.button("INVESTIGATE", type="primary", use_container_width=True):
        result = run_investigation(agent, trigger)
        if result:
            cases[result["case_id"]] = result
            st.session_state.cases = cases
            st.rerun()
    st.divider()
    case_options = list(cases.values())
    selected_id = st.selectbox("CASES", [case["case_id"] for case in case_options], index=max(0, len(case_options) - 1), key="case_selector") if case_options else None

case = cases[selected_id] if selected_id else {}
if not case:
    st.warning("Run an investigation to create a case.")
    st.stop()

findings = case.get("findings", [])
pattern = pattern_label(case)
status = status_label(case.get("status", "open"))
confidence = float(case.get("uncertainty", {}).get("confidence", 0))
risk_score = float(case.get("uncertainty", {}).get("risk_score", 0))
entities = case.get("graph_refs", {}).get("entity_ids", {})
all_entity_count = sum(len(values) for values in entities.values())

st.markdown(f'<div class="k" style="border-bottom:1px solid #292929;padding-bottom:14px">WORKBENCH &nbsp;&nbsp; EVIDENCE &nbsp;&nbsp; CASE MEMORY &nbsp;&nbsp; REPORTS <span style="float:right">LIVE AGENT • {len(cases)} CASES</span></div>', unsafe_allow_html=True)
left, right = st.columns([1.3, .7], gap="large")
with left:
    st.markdown(f'<div class="k" style="margin-top:35px">Case <b>{esc(case["case_id"])}</b></div>', unsafe_allow_html=True)
    st.markdown('<div class="title">FRAUD<br><span class="soft">INVESTIGATION.</span></div>', unsafe_allow_html=True)
    st.markdown('<div style="color:#9b9892;font-size:.76rem;line-height:1.7;max-width:650px">Evidence-first investigation workspace powered by the live agent: graph evidence, policy grounding, uncertainty reduction and human-approved action.</div>', unsafe_allow_html=True)
with right:
    for label, value in [("Status", status), ("Trigger", case.get("trigger", {}).get("type", "-")), ("Pattern", pattern), ("Updated", case.get("updated_at", "-")[:19].replace("T", " "))]:
        st.markdown(f'<div class="meta"><small>{esc(label)}</small><b>{esc(value)}</b></div>', unsafe_allow_html=True)

metrics = st.columns(5)
for col, label, value in zip(metrics, ["Bank risk", "Agent assessment", "Confidence", "Connected entities", "Evidence items"], [f"{risk_score:.0%}", f"{confidence:.0%}", confidence_label(confidence), str(all_entity_count), str(len(case.get("evidence", [])))]):
    with col:
        st.markdown(f'<div class="meta"><small>{esc(label)}</small><b>{esc(value)}</b></div>', unsafe_allow_html=True)

st.divider()
left, right = st.columns([1.25, .75], gap="large")
with left:
    st.markdown('<div class="panel">01 / Entities involved</div>', unsafe_allow_html=True)
    entity_cards = []
    for entity_type, ids in entities.items():
        for entity_id in ids:
            entity_cards.append((entity_type.rstrip("s").title(), entity_id))
    entity_columns = [column for _ in range(4) for column in st.columns(3)]
    for slot, column in enumerate(entity_columns):
        with column:
            if slot < len(entity_cards):
                entity_type, entity_id = entity_cards[slot]
                st.markdown(f'<div class="entity"><small>{esc(entity_type)}</small><b>{esc(entity_id)}</b><span class="muted">Graph-linked investigation entity</span></div>', unsafe_allow_html=True)
            else:
                st.markdown('<div class="entity" style="visibility:hidden">&nbsp;</div>', unsafe_allow_html=True)

    st.markdown('<div class="panel">02 / Evidence timeline</div>', unsafe_allow_html=True)
    evidence_items = case.get("evidence", [])
    for slot in range(12):
        if slot < len(evidence_items):
            item = evidence_items[slot]
            extra = item.get("type") in {"customer_validation", "pattern_grounding", "policy_grounding"}
            st.markdown(f'<div class="event {"add" if extra else ""}"><small>{esc(item.get("observed_at", ""))} • {esc(item.get("source", ""))}</small><br><b>{esc(item.get("type", "").replace("_", " ").title())}</b><p>{esc(item.get("summary", ""))}</p></div>', unsafe_allow_html=True)
        else:
            st.markdown('<div class="event" style="visibility:hidden">&nbsp;</div>', unsafe_allow_html=True)

    st.markdown('<div class="panel">03 / Fraud pattern & assessment</div>', unsafe_allow_html=True)
    pattern_col, assessment_col = st.columns(2)
    with pattern_col:
        st.markdown(f'<div style="font-size:3rem;font-weight:700;letter-spacing:-.08em">{confidence:.0%}</div>', unsafe_allow_html=True)
        st.progress(confidence)
        st.markdown(f'<div class="reason">The graph and policy-grounded evidence currently supports <b>{esc(pattern.lower())}</b>.</div>', unsafe_allow_html=True)
    with assessment_col:
        st.markdown(f'<div class="meta"><small>Uncertainty</small><b>{esc(confidence_label(confidence))}</b></div>', unsafe_allow_html=True)
        st.markdown(f'<div class="meta"><small>Pattern class</small><b>{esc(pattern)}</b></div>', unsafe_allow_html=True)
        st.markdown(f'<div class="meta"><small>Evidence to act</small><b>{"Yes" if case.get("uncertainty", {}).get("enough_evidence_to_act") else "No"}</b></div>', unsafe_allow_html=True)

    st.markdown('<div class="panel">04 / Case progression</div>', unsafe_allow_html=True)
    progression = case.get("uncertainty", {}).get("assessment_history", [])
    progression_columns = st.columns(4)
    steps = [("Signal detected", "Initial trigger received."), ("Evidence requested", "Controlled evidence gathered."), ("Assessment updated", "Confidence recalculated."), ("Human decision", "Consequential action remains gated.")]
    for column, (title, description) in zip(progression_columns, steps):
        with column:
            st.markdown(f'<div class="meta"><small>{len(progression)} assessment stage(s)</small><b>{esc(title)}</b><div class="muted">{esc(description)}</div></div>', unsafe_allow_html=True)

with right:
    st.markdown('<div class="panel">05 / Case memory</div>', unsafe_allow_html=True)
    similar = case.get("memory", {}).get("similar_cases", [])
    for slot in range(5):
        if slot < len(similar):
            case_id = similar[slot]
            st.markdown(f'<div class="box" style="margin-bottom:8px"><b style="font-size:.7rem">{esc(case_id)}</b><div class="muted">Retrieved as a related prior case</div><div class="reason">Used to inform pattern confidence and next-best action.</div></div>', unsafe_allow_html=True)
        else:
            st.markdown('<div class="box" style="visibility:hidden;margin-bottom:8px">&nbsp;</div>', unsafe_allow_html=True)

    st.markdown('<div class="panel">06 / Next best action</div>', unsafe_allow_html=True)
    actions = case.get("actions", [])
    for slot in range(5):
        if slot < len(actions):
            action = actions[slot]
            st.markdown(f'<div class="action {"after" if action.get("mode") == "recommend" else ""}"><b>{esc(action.get("action", "").replace("_", " ").title())}</b><div class="muted">{esc(action.get("status", "").replace("_", " ").title())} • {esc(action.get("approval_route", ""))}</div><div class="reason">{esc(action.get("reason", ""))}</div></div>', unsafe_allow_html=True)
        else:
            st.markdown('<div class="action" style="visibility:hidden">&nbsp;</div>', unsafe_allow_html=True)

    st.markdown('<div class="panel">07 / Explainability</div>', unsafe_allow_html=True)
    with st.expander("What evidence was used?"):
        st.write("; ".join(item.get("type", "").replace("_", " ") for item in case.get("evidence", [])))
    with st.expander("How did confidence change?"):
        st.json(case.get("uncertainty", {}).get("assessment_history", []))
    with st.expander("Agent explanation"):
        st.write(case.get("explanation", ""))

    st.markdown('<div class="panel">08 / Case record</div>', unsafe_allow_html=True)
    st.download_button("DOWNLOAD CASE JSON", data=json.dumps(case, indent=2, default=str), file_name=f"{case['case_id']}.json", mime="application/json", use_container_width=True)
    with st.expander("View raw case record"):
        st.json(case)

st.divider()
st.markdown('<div class="k">TRACE. / LIVE MOCK GRAPH + AGENT • Consequential controls require human approval</div>', unsafe_allow_html=True)
