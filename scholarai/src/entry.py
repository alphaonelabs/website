import json
from urllib.parse import urlparse

from workers import Response, WorkerEntrypoint

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

AI_MODEL = "@cf/meta/llama-3.1-8b-instruct"

# ---------------------------------------------------------------------------
# HTTP helpers
# ---------------------------------------------------------------------------


def _json_response(data: dict, status: int = 200) -> Response:
    """Return a JSON Response with the correct Content-Type header."""
    return Response(
        json.dumps(data),
        status=status,
        headers={"Content-Type": "application/json"},
    )


def _error(message: str, status: int) -> Response:
    """Return a JSON error response."""
    return _json_response({"error": message}, status)


# ---------------------------------------------------------------------------
# Shared AI helper
# ---------------------------------------------------------------------------


def _try_parse_json(text: str):
    """Attempt to extract and parse a JSON object from a text response."""
    start = text.find("{")
    end = text.rfind("}") + 1
    if start >= 0 and end > start:
        try:
            return json.loads(text[start:end])
        except json.JSONDecodeError:
            pass
    return text


async def run_ai(env, system_prompt: str, user_prompt: str) -> str:
    """Run inference via the Cloudflare Workers AI binding."""
    result = await env.AI.run(
        AI_MODEL,
        {
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ]
        },
    )
    if isinstance(result, dict):
        return result.get("response", "")
    return getattr(result, "response", str(result))


# ---------------------------------------------------------------------------
# Business-logic handlers (pure async functions, easy to unit-test)
# ---------------------------------------------------------------------------


def handle_info() -> dict:
    """Return API metadata."""
    return {
        "name": "ScholarAI",
        "version": "1.0.0",
        "description": (
            "AI-powered research assistant for academic literature, "
            "powered by Cloudflare Workers AI."
        ),
        "endpoints": {
            "GET /": "API information",
            "POST /api/discover": "Discover relevant academic papers",
            "POST /api/summarize": "Summarize a research paper",
            "POST /api/citations": "Explore paper citations and related work",
            "POST /api/qa": "Question answering about research topics",
            "POST /api/organize": "Organize a collection of papers",
            "POST /api/trends": "Identify research trends in a field",
            "POST /api/review": "Generate a literature review",
        },
        "usage": {
            "discover": {
                "method": "POST",
                "body": {
                    "query": "string (required)",
                    "fields": "list[string] (optional)",
                    "limit": "int (optional, default: 10)",
                },
            },
            "summarize": {
                "method": "POST",
                "body": {
                    "title": "string (optional)",
                    "abstract": "string (optional)",
                    "content": "string (optional)",
                },
            },
            "citations": {
                "method": "POST",
                "body": {
                    "paper": "string (required)",
                    "type": "string (optional: forward | backward | related)",
                },
            },
            "qa": {
                "method": "POST",
                "body": {
                    "question": "string (required)",
                    "context": "string (optional)",
                    "papers": "list[dict] (optional)",
                },
            },
            "organize": {
                "method": "POST",
                "body": {
                    "papers": "list[dict] (required)",
                    "organize_by": "string (optional: topic | year | author | methodology)",
                },
            },
            "trends": {
                "method": "POST",
                "body": {
                    "field": "string (optional)",
                    "papers": "list[dict] (optional)",
                    "time_range": "string (optional)",
                },
            },
            "review": {
                "method": "POST",
                "body": {
                    "topic": "string (required)",
                    "papers": "list[dict] (optional)",
                    "style": "string (optional: comprehensive | brief | systematic)",
                    "audience": "string (optional)",
                },
            },
        },
    }


async def handle_discover(body: dict, env) -> tuple[dict, int]:
    """Discover relevant academic papers for a research query."""
    query = body.get("query", "").strip()
    if not query:
        return {"error": "query is required"}, 400

    fields = body.get("fields", [])
    limit = int(body.get("limit", 10))
    field_context = f" in the fields of {', '.join(fields)}" if fields else ""

    system_prompt = (
        "You are ScholarAI, an expert academic research assistant. "
        "You help researchers discover relevant academic papers and literature. "
        "When given a research query, provide structured information about relevant "
        "papers, key concepts, and research directions. "
        "Format your response as a valid JSON object."
    )
    user_prompt = (
        f"Discover academic papers for the following research query{field_context}:\n\n"
        f"Query: {query}\n"
        f"Requested limit: {limit} papers\n\n"
        "Return a JSON object with keys: papers (list with title, authors, year, venue, "
        "abstract_summary, relevance_score, key_topics), research_directions (list), "
        "key_concepts (list), related_queries (list)."
    )
    response_text = await run_ai(env, system_prompt, user_prompt)
    return {"query": query, "results": _try_parse_json(response_text)}, 200


async def handle_summarize(body: dict, env) -> tuple[dict, int]:
    """Generate a structured summary of a research paper."""
    title = body.get("title", "").strip()
    abstract = body.get("abstract", "").strip()
    content = body.get("content", "").strip()

    if not (title or abstract or content):
        return {"error": "At least one of title, abstract, or content is required"}, 400

    parts = []
    if title:
        parts.append(f"Title: {title}")
    if abstract:
        parts.append(f"Abstract: {abstract}")
    if content:
        parts.append(f"Content:\n{content[:4000]}")

    system_prompt = (
        "You are ScholarAI, an expert academic research assistant specialized in "
        "summarizing research papers. Provide clear, concise, and accurate summaries "
        "that capture the key contributions, methodology, results, and implications."
    )
    user_prompt = (
        f"Summarize the following research paper:\n\n{chr(10).join(parts)}\n\n"
        "Structure your summary with these sections:\n"
        "1. Main contribution\n"
        "2. Problem being solved\n"
        "3. Methodology\n"
        "4. Key findings / results\n"
        "5. Limitations\n"
        "6. Future work directions\n"
        "7. Impact and significance"
    )
    summary = await run_ai(env, system_prompt, user_prompt)
    return {"title": title, "summary": summary}, 200


async def handle_citations(body: dict, env) -> tuple[dict, int]:
    """Explore the citation network around a paper."""
    paper = body.get("paper", "").strip()
    if not paper:
        return {"error": "paper is required"}, 400

    citation_type = body.get("type", "related")

    system_prompt = (
        "You are ScholarAI, an expert academic research assistant specializing in "
        "citation analysis and research genealogy. Help researchers understand the "
        "citation network around papers, including foundational work, recent advances, "
        "and related research."
    )
    user_prompt = (
        f"Explore citations and related work for the following paper:\n\n"
        f"Paper: {paper}\n"
        f"Citation type requested: {citation_type}\n\n"
        "Please provide:\n"
        "1. Key foundational papers (seminal works this paper builds upon)\n"
        "2. Papers that cite this work (if applicable)\n"
        "3. Related papers in the same research area\n"
        "4. Research lineage and evolution of ideas\n"
        "5. Key authors and research groups in this area\n"
        "6. Connections to adjacent research fields"
    )
    result = await run_ai(env, system_prompt, user_prompt)
    return {"paper": paper, "citation_type": citation_type, "exploration": result}, 200


async def handle_qa(body: dict, env) -> tuple[dict, int]:
    """Answer a research question using the AI."""
    question = body.get("question", "").strip()
    if not question:
        return {"error": "question is required"}, 400

    context = body.get("context", "")
    papers = body.get("papers", [])

    context_parts = []
    if context:
        context_parts.append(f"Context:\n{context}")
    if papers:
        context_parts.append(f"Available papers:\n{json.dumps(papers[:5], indent=2)}")

    system_prompt = (
        "You are ScholarAI, an expert academic research assistant with deep knowledge "
        "across multiple scientific disciplines. Answer research questions accurately, "
        "citing relevant papers and providing evidence-based responses. "
        "Be precise, thorough, and acknowledge uncertainty when appropriate."
    )
    extra = ("\n\n" + "\n\n".join(context_parts)) if context_parts else ""
    user_prompt = (
        f"Please answer the following research question:\n\n"
        f"Question: {question}{extra}\n\n"
        "Provide:\n"
        "1. A comprehensive answer\n"
        "2. Key evidence and findings from the literature\n"
        "3. Relevant papers and references\n"
        "4. Important caveats or limitations\n"
        "5. Areas of ongoing debate or uncertainty"
    )
    answer = await run_ai(env, system_prompt, user_prompt)
    return {"question": question, "answer": answer}, 200


async def handle_organize(body: dict, env) -> tuple[dict, int]:
    """Organize a collection of papers into thematic clusters."""
    papers = body.get("papers")
    if not papers:
        return {"error": "papers is required"}, 400

    organize_by = body.get("organize_by", "topic")

    system_prompt = (
        "You are ScholarAI, an expert academic research assistant specialized in "
        "knowledge organization and taxonomy. Help researchers organize and structure "
        "their literature collection for better understanding and navigation."
    )
    papers_json = json.dumps(papers[:20], indent=2)
    user_prompt = (
        f"Organize the following research papers by {organize_by}:\n\n"
        f"Papers:\n{papers_json}\n\n"
        "Please provide:\n"
        "1. Organized groupings / clusters\n"
        "2. Key themes and relationships between papers\n"
        "3. A knowledge map showing connections\n"
        "4. Recommended reading order\n"
        "5. Research gaps identified from this collection\n"
        "6. Cross-cutting themes and methodologies"
    )
    result = await run_ai(env, system_prompt, user_prompt)
    return {"organize_by": organize_by, "organization": result}, 200


async def handle_trends(body: dict, env) -> tuple[dict, int]:
    """Identify research trends in a field or from a set of papers."""
    field = body.get("field", "").strip()
    papers = body.get("papers", [])

    if not field and not papers:
        return {"error": "At least one of field or papers is required"}, 400

    time_range = body.get("time_range", "")
    context_parts = []
    if field:
        context_parts.append(f"Research field: {field}")
    if time_range:
        context_parts.append(f"Time range: {time_range}")
    if papers:
        context_parts.append(f"Papers:\n{json.dumps(papers[:20], indent=2)}")

    system_prompt = (
        "You are ScholarAI, an expert academic research assistant specialized in "
        "research trend analysis and bibliometrics. Identify emerging trends, "
        "declining areas, hot topics, and research trajectories in academic literature."
    )
    user_prompt = (
        f"Identify research trends from the following information:\n\n"
        f"{chr(10).join(context_parts)}\n\n"
        "Please provide:\n"
        "1. Emerging research trends and hot topics\n"
        "2. Declining or saturated research areas\n"
        "3. Methodological trends and shifts\n"
        "4. Key breakthroughs and milestone papers\n"
        "5. Future research directions\n"
        "6. Cross-disciplinary connections and emerging intersections\n"
        "7. Technology / tool adoption trends"
    )
    result = await run_ai(env, system_prompt, user_prompt)
    return {"field": field, "trends": result}, 200


async def handle_review(body: dict, env) -> tuple[dict, int]:
    """Generate a structured literature review."""
    topic = body.get("topic", "").strip()
    if not topic:
        return {"error": "topic is required"}, 400

    papers = body.get("papers", [])
    style = body.get("style", "comprehensive")
    audience = body.get("audience", "researchers")

    context_parts = [
        f"Topic: {topic}",
        f"Review style: {style}",
        f"Target audience: {audience}",
    ]
    if papers:
        context_parts.append(f"Papers to include:\n{json.dumps(papers[:15], indent=2)}")

    system_prompt = (
        "You are ScholarAI, an expert academic research assistant specialized in "
        "writing high-quality literature reviews. Generate well-structured, "
        "comprehensive, and academically rigorous literature review sections that "
        "synthesize research findings."
    )
    user_prompt = (
        f"Generate a literature review for the following:\n\n"
        f"{chr(10).join(context_parts)}\n\n"
        f"Write a {style} literature review for {audience} that includes:\n"
        "1. Introduction to the research area\n"
        "2. Historical background and development\n"
        "3. Current state of the art\n"
        "4. Key methodologies and approaches\n"
        "5. Major findings and contributions\n"
        "6. Ongoing challenges and open problems\n"
        "7. Future research directions\n"
        "8. Conclusion"
    )
    review = await run_ai(env, system_prompt, user_prompt)
    return {"topic": topic, "style": style, "review": review}, 200


# ---------------------------------------------------------------------------
# Route table
# ---------------------------------------------------------------------------

_POST_ROUTES = {
    "/api/discover": handle_discover,
    "/api/summarize": handle_summarize,
    "/api/citations": handle_citations,
    "/api/qa": handle_qa,
    "/api/organize": handle_organize,
    "/api/trends": handle_trends,
    "/api/review": handle_review,
}

# ---------------------------------------------------------------------------
# Cloudflare Workers entrypoint
# ---------------------------------------------------------------------------


class Default(WorkerEntrypoint):
    async def fetch(self, request):
        path = urlparse(request.url).path.rstrip("/") or "/"
        method = request.method.upper()

        if method == "GET" and path == "/":
            return _json_response(handle_info())

        if method == "POST":
            handler = _POST_ROUTES.get(path)
            if handler is None:
                return _error("Not found", 404)

            try:
                body = await request.json()
            except Exception:
                return _error("Invalid JSON body", 400)

            data, status = await handler(body, self.env)
            return _json_response(data, status)

        return _error("Not found", 404)
