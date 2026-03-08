import json
from typing import Optional

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from workers import WorkerEntrypoint

# ---------------------------------------------------------------------------
# App setup
# ---------------------------------------------------------------------------

app = FastAPI(
    title="ScholarAI",
    description=(
        "AI-powered research assistant for students and scientists. "
        "Supports paper discovery, summarization, citation exploration, "
        "question answering, knowledge organization, trend identification, "
        "and literature review generation."
    ),
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

AI_MODEL = "@cf/meta/llama-3.1-8b-instruct"

# ---------------------------------------------------------------------------
# Dependency: AI environment
# ---------------------------------------------------------------------------


def get_env(request: Request):
    """Return the Cloudflare env object injected by the Workers runtime."""
    return request.scope.get("env")


# ---------------------------------------------------------------------------
# Request models
# ---------------------------------------------------------------------------


class DiscoverRequest(BaseModel):
    query: str
    fields: list[str] = []
    limit: int = 10


class SummarizeRequest(BaseModel):
    title: str = ""
    abstract: str = ""
    content: str = ""


class CitationsRequest(BaseModel):
    paper: str
    type: str = "related"


class QARequest(BaseModel):
    question: str
    context: str = ""
    papers: list[dict] = []


class OrganizeRequest(BaseModel):
    papers: list[dict]
    organize_by: str = "topic"


class TrendsRequest(BaseModel):
    field: str = ""
    papers: list[dict] = []
    time_range: str = ""


class ReviewRequest(BaseModel):
    topic: str
    papers: list[dict] = []
    style: str = "comprehensive"
    audience: str = "researchers"


# ---------------------------------------------------------------------------
# Shared AI helper
# ---------------------------------------------------------------------------


def _try_parse_json(text: str) -> dict | str:
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
    # The llama-3.1 model returns a dict with a "response" key
    if isinstance(result, dict):
        return result.get("response", "")
    # Newer model objects may expose an attribute
    return getattr(result, "response", str(result))


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@app.get("/", summary="API information and usage guide")
async def api_info():
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


@app.post("/api/discover", summary="Discover relevant academic papers")
async def discover_papers(body: DiscoverRequest, env=Depends(get_env)):
    """
    Discover relevant academic papers for a research query.
    Returns suggested papers, research directions, key concepts, and related queries.
    """
    if env is None:
        raise HTTPException(status_code=503, detail="AI binding not available")

    field_context = (
        f" in the fields of {', '.join(body.fields)}" if body.fields else ""
    )
    system_prompt = (
        "You are ScholarAI, an expert academic research assistant. "
        "You help researchers discover relevant academic papers and literature. "
        "When given a research query, provide structured information about relevant "
        "papers, key concepts, and research directions. "
        "Format your response as a valid JSON object."
    )
    user_prompt = (
        f"Discover academic papers for the following research query{field_context}:\n\n"
        f"Query: {body.query}\n"
        f"Requested limit: {body.limit} papers\n\n"
        "Return a JSON object with keys: papers (list with title, authors, year, venue, "
        "abstract_summary, relevance_score, key_topics), research_directions (list), "
        "key_concepts (list), related_queries (list)."
    )
    response_text = await run_ai(env, system_prompt, user_prompt)
    return {"query": body.query, "results": _try_parse_json(response_text)}


@app.post("/api/summarize", summary="Summarize a research paper")
async def summarize_paper(body: SummarizeRequest, env=Depends(get_env)):
    """
    Generate a structured summary of a research paper from its title, abstract, or full content.
    """
    if env is None:
        raise HTTPException(status_code=503, detail="AI binding not available")

    if not (body.title or body.abstract or body.content):
        raise HTTPException(
            status_code=400,
            detail="At least one of title, abstract, or content is required",
        )

    parts = []
    if body.title:
        parts.append(f"Title: {body.title}")
    if body.abstract:
        parts.append(f"Abstract: {body.abstract}")
    if body.content:
        # Limit content to avoid exceeding context window
        parts.append(f"Content:\n{body.content[:4000]}")

    system_prompt = (
        "You are ScholarAI, an expert academic research assistant specialized in "
        "summarizing research papers. Provide clear, concise, and accurate summaries "
        "that capture the key contributions, methodology, results, and implications."
    )
    user_prompt = (
        f"Summarise the following research paper:\n\n{chr(10).join(parts)}\n\n"
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
    return {"title": body.title, "summary": summary}


@app.post("/api/citations", summary="Explore paper citations and related work")
async def explore_citations(body: CitationsRequest, env=Depends(get_env)):
    """
    Analyse the citation network around a paper: foundational works, citing papers,
    and related research.
    """
    if env is None:
        raise HTTPException(status_code=503, detail="AI binding not available")

    system_prompt = (
        "You are ScholarAI, an expert academic research assistant specializing in "
        "citation analysis and research genealogy. Help researchers understand the "
        "citation network around papers, including foundational work, recent advances, "
        "and related research."
    )
    user_prompt = (
        f"Explore citations and related work for the following paper:\n\n"
        f"Paper: {body.paper}\n"
        f"Citation type requested: {body.type}\n\n"
        "Please provide:\n"
        "1. Key foundational papers (seminal works this paper builds upon)\n"
        "2. Papers that cite this work (if applicable)\n"
        "3. Related papers in the same research area\n"
        "4. Research lineage and evolution of ideas\n"
        "5. Key authors and research groups in this area\n"
        "6. Connections to adjacent research fields"
    )
    result = await run_ai(env, system_prompt, user_prompt)
    return {"paper": body.paper, "citation_type": body.type, "exploration": result}


@app.post("/api/qa", summary="Question answering about research topics")
async def question_answering(body: QARequest, env=Depends(get_env)):
    """
    Answer a research question, drawing on provided context or papers and the
    model's knowledge of the scientific literature.
    """
    if env is None:
        raise HTTPException(status_code=503, detail="AI binding not available")

    context_parts = []
    if body.context:
        context_parts.append(f"Context:\n{body.context}")
    if body.papers:
        context_parts.append(
            f"Available papers:\n{json.dumps(body.papers[:5], indent=2)}"
        )

    system_prompt = (
        "You are ScholarAI, an expert academic research assistant with deep knowledge "
        "across multiple scientific disciplines. Answer research questions accurately, "
        "citing relevant papers and providing evidence-based responses. "
        "Be precise, thorough, and acknowledge uncertainty when appropriate."
    )
    extra = ("\n\n" + "\n\n".join(context_parts)) if context_parts else ""
    user_prompt = (
        f"Please answer the following research question:\n\n"
        f"Question: {body.question}{extra}\n\n"
        "Provide:\n"
        "1. A comprehensive answer\n"
        "2. Key evidence and findings from the literature\n"
        "3. Relevant papers and references\n"
        "4. Important caveats or limitations\n"
        "5. Areas of ongoing debate or uncertainty"
    )
    answer = await run_ai(env, system_prompt, user_prompt)
    return {"question": body.question, "answer": answer}


@app.post("/api/organize", summary="Organise a collection of papers")
async def organize_knowledge(body: OrganizeRequest, env=Depends(get_env)):
    """
    Organise a list of papers into thematic clusters, a knowledge map, and a
    recommended reading order.
    """
    if env is None:
        raise HTTPException(status_code=503, detail="AI binding not available")

    system_prompt = (
        "You are ScholarAI, an expert academic research assistant specialized in "
        "knowledge organization and taxonomy. Help researchers organize and structure "
        "their literature collection for better understanding and navigation."
    )
    papers_json = json.dumps(body.papers[:20], indent=2)
    user_prompt = (
        f"Organise the following research papers by {body.organize_by}:\n\n"
        f"Papers:\n{papers_json}\n\n"
        "Please provide:\n"
        "1. Organised groupings / clusters\n"
        "2. Key themes and relationships between papers\n"
        "3. A knowledge map showing connections\n"
        "4. Recommended reading order\n"
        "5. Research gaps identified from this collection\n"
        "6. Cross-cutting themes and methodologies"
    )
    result = await run_ai(env, system_prompt, user_prompt)
    return {"organize_by": body.organize_by, "organization": result}


@app.post("/api/trends", summary="Identify research trends in a field")
async def identify_trends(body: TrendsRequest, env=Depends(get_env)):
    """
    Identify emerging trends, hot topics, declining areas, and future directions
    in a research field or from a set of papers.
    """
    if env is None:
        raise HTTPException(status_code=503, detail="AI binding not available")

    if not (body.field or body.papers):
        raise HTTPException(
            status_code=400, detail="At least one of field or papers is required"
        )

    context_parts = []
    if body.field:
        context_parts.append(f"Research field: {body.field}")
    if body.time_range:
        context_parts.append(f"Time range: {body.time_range}")
    if body.papers:
        context_parts.append(
            f"Papers:\n{json.dumps(body.papers[:20], indent=2)}"
        )

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
    return {"field": body.field, "trends": result}


@app.post("/api/review", summary="Generate a literature review")
async def generate_review(body: ReviewRequest, env=Depends(get_env)):
    """
    Generate a structured, academically rigorous literature review section on
    a given topic, incorporating provided papers if supplied.
    """
    if env is None:
        raise HTTPException(status_code=503, detail="AI binding not available")

    context_parts = [
        f"Topic: {body.topic}",
        f"Review style: {body.style}",
        f"Target audience: {body.audience}",
    ]
    if body.papers:
        context_parts.append(
            f"Papers to include:\n{json.dumps(body.papers[:15], indent=2)}"
        )

    system_prompt = (
        "You are ScholarAI, an expert academic research assistant specialized in "
        "writing high-quality literature reviews. Generate well-structured, "
        "comprehensive, and academically rigorous literature review sections that "
        "synthesize research findings."
    )
    user_prompt = (
        f"Generate a literature review for the following:\n\n"
        f"{chr(10).join(context_parts)}\n\n"
        f"Write a {body.style} literature review for {body.audience} that includes:\n"
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
    return {"topic": body.topic, "style": body.style, "review": review}


# ---------------------------------------------------------------------------
# Cloudflare Workers entrypoint
# ---------------------------------------------------------------------------


class Default(WorkerEntrypoint):
    async def fetch(self, request):
        import asgi

        return await asgi.fetch(app, request.js_object, self.env)
