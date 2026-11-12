import os
from typing import TypedDict

from langchain_openai import ChatOpenAI
from langgraph.graph import END, START, StateGraph

from .models import Finding, InvestigationPlan
from .sources import inspect_repository, read_log_excerpt, terms_from_incident


class TriageState(TypedDict, total=False):
    incident: str
    log_path: str | None
    repo_path: str | None
    terms: list[str]
    log_evidence: str
    code_evidence: str
    rounds: int
    plan: InvestigationPlan
    finding: Finding


def build_graph():
    model = ChatOpenAI(model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"), temperature=0)
    plan_model = model.with_structured_output(InvestigationPlan)
    finding_model = model.with_structured_output(Finding)
    max_rounds = max(1, int(os.getenv("MAX_INVESTIGATION_ROUNDS", "2")))
    max_files = int(os.getenv("MAX_REPO_FILES", "250"))
    max_file_bytes = int(os.getenv("MAX_FILE_BYTES", "200000"))

    def gather(state: TriageState):
        terms = state.get("terms") or terms_from_incident(state["incident"])
        logs = read_log_excerpt(state.get("log_path"), terms)
        code = inspect_repository(state.get("repo_path"), terms, max_files, max_file_bytes)
        return {
            "terms": terms,
            "log_evidence": (state.get("log_evidence", "") + "\n\n" + logs)[-22000:],
            "code_evidence": (state.get("code_evidence", "") + "\n\n" + code)[-30000:],
            "rounds": state.get("rounds", 0) + 1,
        }

    def plan(state: TriageState):
        prompt = f"""Incident: {state['incident']}
Current search terms: {state.get('terms', [])}
Evidence gathered so far:
LOGS: {state.get('log_evidence', '')[-8000:]}
SOURCE: {state.get('code_evidence', '')[-12000:]}

Choose a few specific additional search terms that could uncover missing evidence. Continue only when another read-only search is likely to help. Do not suggest executing repository code."""
        result = plan_model.invoke(prompt)
        return {"plan": result, "terms": result.search_terms[:8]}

    def route(state: TriageState):
        if state.get("rounds", 0) < max_rounds and state.get("plan") and state["plan"].continue_investigation:
            return "gather"
        return "assess"

    def assess(state: TriageState):
        prompt = f"""Triage this incident based only on the supplied incident and evidence. Clearly label uncertainty; do not invent facts. Keep the summary concise, cite concrete log paths/lines or source paths/lines where present, and recommend one actionable next step. Map critical/high/medium/low to ClickUp priorities 1/2/3/4.

Incident: {state['incident']}
Logs:
{state.get('log_evidence', '')}
Read-only repository excerpts:
{state.get('code_evidence', '')}"""
        return {"finding": finding_model.invoke(prompt)}

    graph = StateGraph(TriageState)
    graph.add_node("gather", gather)
    graph.add_node("plan", plan)
    graph.add_node("assess", assess)
    graph.add_edge(START, "gather")
    graph.add_edge("gather", "plan")
    graph.add_conditional_edges("plan", route, {"gather": "gather", "assess": "assess"})
    graph.add_edge("assess", END)
    return graph.compile()
