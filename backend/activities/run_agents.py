"""
Activity: run_agents — Research Agent + Document Agent via Azure OpenAI + AI Search (T-024)

Lightweight placeholder that formats a structured prompt and calls gpt-4o
with retrieved context (RAG). Full agent wiring with AI Foundry SDK done in T-025/T-026.

Returns dict:
  - analysis: str          — root-cause analysis from Research Agent
  - recommendations: list  — CAPA recommendations list
  - references: list       — relevant SOP / policy references (from Document Agent)
  - confidence: float      — 0..1
"""

import json
import logging
import os

from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient
from openai import AzureOpenAI

logger = logging.getLogger(__name__)

OPENAI_ENDPOINT = os.environ["AZURE_OPENAI_ENDPOINT"]
OPENAI_KEY = os.environ["AZURE_OPENAI_API_KEY"]
GPT4O_DEPLOYMENT = os.getenv("AZURE_OPENAI_GPT4O_DEPLOYMENT", "gpt-4o")

SEARCH_ENDPOINT = os.environ["AZURE_SEARCH_ENDPOINT"]
SEARCH_KEY = os.environ["AZURE_SEARCH_ADMIN_KEY"]

# Indexes to query
SOP_INDEX = "idx-sop"
GMP_INDEX = "idx-gmp-policies"


def run_agents(input_data: dict) -> dict:
    incident_id: str = input_data["incident_id"]
    context: dict = input_data.get("context", {})
    loop_count: int = input_data.get("loop_count", 0)
    extra_info: str = context.get("extra_info_request", "")

    logger.info("run_agents for incident %s (loop %d)", incident_id, loop_count)

    # ── 1. Document Agent: search relevant SOPs / GMP policies ─────────────
    equipment = context.get("equipment", {})
    alert_type = context.get("equipment", {}).get("alertType", "deviation")
    search_query = f"GMP deviation {alert_type} {equipment.get('type', '')} CAPA procedure"

    references = _search_knowledge_base(search_query)

    # ── 2. Research Agent: LLM analysis ────────────────────────────────────
    system_prompt = (
        "You are an expert GMP compliance specialist in pharmaceutical manufacturing. "
        "Analyse the given deviation incident and provide: "
        "(1) root-cause analysis, "
        "(2) immediate corrective actions, "
        "(3) preventive CAPA recommendations. "
        "Be concise and cite regulatory references where relevant."
    )

    user_prompt_parts = [
        f"## Incident ID: {incident_id}",
        f"## Equipment: {json.dumps(equipment, indent=2)}",
        f"## Alert: {json.dumps(context.get('activeBatch', {}), indent=2)}",
        f"## Recent incidents on this equipment: {json.dumps(context.get('recentIncidents', []), indent=2)}",
    ]
    if extra_info:
        user_prompt_parts.append(f"## Additional context requested by operator: {extra_info}")
    if references:
        ref_text = "\n".join(f"- {r['title']}: {r['snippet']}" for r in references[:5])
        user_prompt_parts.append(f"## Relevant SOPs / Policies:\n{ref_text}")
    if loop_count > 0:
        user_prompt_parts.append(
            f"(This is loop {loop_count + 1} — operator requested more information.)"
        )

    user_prompt = "\n\n".join(user_prompt_parts)

    ai_response = _call_llm(system_prompt, user_prompt)

    return {
        "analysis": ai_response.get("analysis", ""),
        "recommendations": ai_response.get("recommendations", []),
        "references": references,
        "confidence": ai_response.get("confidence", 0.8),
        "loop_count": loop_count,
    }


def _search_knowledge_base(query: str) -> list[dict]:
    """Retrieve top-5 chunks from SOP + GMP policy indexes."""
    results = []
    for index_name in (SOP_INDEX, GMP_INDEX):
        try:
            client = SearchClient(
                endpoint=SEARCH_ENDPOINT,
                index_name=index_name,
                credential=AzureKeyCredential(SEARCH_KEY),
            )
            hits = client.search(search_text=query, top=3, select=["title", "content", "source"])
            for h in hits:
                results.append(
                    {
                        "index": index_name,
                        "title": h.get("title", ""),
                        "snippet": (h.get("content", "") or "")[:300],
                        "source": h.get("source", ""),
                    }
                )
        except Exception as exc:
            logger.warning("Search failed on index %s: %s", index_name, exc)
    return results


def _call_llm(system_prompt: str, user_prompt: str) -> dict:
    """Call gpt-4o and parse structured JSON response."""
    client = AzureOpenAI(api_key=OPENAI_KEY, azure_endpoint=OPENAI_ENDPOINT, api_version="2024-02-01")

    structured_system = (
        system_prompt
        + "\n\nRespond with a JSON object with keys: "
        '"analysis" (string), "recommendations" (array of strings), "confidence" (float 0-1).'
    )

    try:
        response = client.chat.completions.create(
            model=GPT4O_DEPLOYMENT,
            messages=[
                {"role": "system", "content": structured_system},
                {"role": "user", "content": user_prompt},
            ],
            response_format={"type": "json_object"},
            temperature=0.2,
            max_tokens=1500,
        )
        content = response.choices[0].message.content or "{}"
        return json.loads(content)
    except Exception as exc:
        logger.error("LLM call failed: %s", exc)
        return {
            "analysis": f"AI analysis unavailable: {exc}",
            "recommendations": [],
            "confidence": 0.0,
        }
