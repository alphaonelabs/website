"""
Unit tests for ScholarAI.

Handler functions from src.entry are called directly with a mocked Cloudflare
env so that tests run without a live Workers runtime.
"""
import json
import pytest

# ---------------------------------------------------------------------------
# Mock Cloudflare AI binding
# ---------------------------------------------------------------------------


class MockAI:
    """Minimal stand-in for the Cloudflare Workers AI binding."""

    DEFAULT_RESPONSE = "This is a mocked AI response for testing purposes."

    async def run(self, model: str, params: dict) -> dict:  # noqa: ARG002
        return {"response": self.DEFAULT_RESPONSE}


class MockEnv:
    """Minimal stand-in for the Cloudflare Workers env object."""

    AI = MockAI()


ENV = MockEnv()

# ---------------------------------------------------------------------------
# Tests: handle_info
# ---------------------------------------------------------------------------


def test_handle_info_name():
    from src.entry import handle_info

    data = handle_info()
    assert data["name"] == "ScholarAI"
    assert data["version"] == "1.0.0"


def test_handle_info_endpoints_listed():
    from src.entry import handle_info

    data = handle_info()
    expected = {
        "GET /",
        "POST /api/discover",
        "POST /api/summarize",
        "POST /api/citations",
        "POST /api/qa",
        "POST /api/organize",
        "POST /api/trends",
        "POST /api/review",
    }
    assert expected == set(data["endpoints"].keys())


# ---------------------------------------------------------------------------
# Tests: handle_discover
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_discover_success():
    from src.entry import handle_discover

    data, status = await handle_discover({"query": "transformer models"}, ENV)
    assert status == 200
    assert data["query"] == "transformer models"
    assert "results" in data


@pytest.mark.asyncio
async def test_discover_with_fields_and_limit():
    from src.entry import handle_discover

    data, status = await handle_discover(
        {"query": "protein folding", "fields": ["biology", "ML"], "limit": 5}, ENV
    )
    assert status == 200
    assert data["query"] == "protein folding"


@pytest.mark.asyncio
async def test_discover_missing_query():
    from src.entry import handle_discover

    data, status = await handle_discover({}, ENV)
    assert status == 400
    assert "error" in data


# ---------------------------------------------------------------------------
# Tests: handle_summarize
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_summarize_with_abstract():
    from src.entry import handle_summarize

    data, status = await handle_summarize(
        {"title": "Test Paper", "abstract": "This paper proposes a new method."}, ENV
    )
    assert status == 200
    assert data["title"] == "Test Paper"
    assert "summary" in data
    assert len(data["summary"]) > 0


@pytest.mark.asyncio
async def test_summarize_with_content_only():
    from src.entry import handle_summarize

    data, status = await handle_summarize(
        {"content": "Full paper content goes here..."}, ENV
    )
    assert status == 200


@pytest.mark.asyncio
async def test_summarize_no_input():
    from src.entry import handle_summarize

    data, status = await handle_summarize({}, ENV)
    assert status == 400
    assert "error" in data


# ---------------------------------------------------------------------------
# Tests: handle_citations
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_citations_success():
    from src.entry import handle_citations

    data, status = await handle_citations(
        {"paper": "Attention Is All You Need", "type": "related"}, ENV
    )
    assert status == 200
    assert data["paper"] == "Attention Is All You Need"
    assert data["citation_type"] == "related"
    assert "exploration" in data


@pytest.mark.asyncio
async def test_citations_missing_paper():
    from src.entry import handle_citations

    data, status = await handle_citations({}, ENV)
    assert status == 400
    assert "error" in data


@pytest.mark.asyncio
async def test_citations_forward_type():
    from src.entry import handle_citations

    data, status = await handle_citations(
        {"paper": "BERT: Pre-training of Deep Bidirectional Transformers", "type": "forward"},
        ENV,
    )
    assert status == 200
    assert data["citation_type"] == "forward"


# ---------------------------------------------------------------------------
# Tests: handle_qa
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_qa_success():
    from src.entry import handle_qa

    data, status = await handle_qa({"question": "What is transfer learning?"}, ENV)
    assert status == 200
    assert data["question"] == "What is transfer learning?"
    assert "answer" in data
    assert len(data["answer"]) > 0


@pytest.mark.asyncio
async def test_qa_with_context_and_papers():
    from src.entry import handle_qa

    data, status = await handle_qa(
        {
            "question": "How does BERT work?",
            "context": "BERT is a language model.",
            "papers": [{"title": "BERT", "year": 2018}],
        },
        ENV,
    )
    assert status == 200


@pytest.mark.asyncio
async def test_qa_missing_question():
    from src.entry import handle_qa

    data, status = await handle_qa({}, ENV)
    assert status == 400
    assert "error" in data


# ---------------------------------------------------------------------------
# Tests: handle_organize
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_organize_success():
    from src.entry import handle_organize

    papers = [{"title": "Paper A", "year": 2020}, {"title": "Paper B", "year": 2021}]
    data, status = await handle_organize({"papers": papers, "organize_by": "topic"}, ENV)
    assert status == 200
    assert data["organize_by"] == "topic"
    assert "organization" in data


@pytest.mark.asyncio
async def test_organize_missing_papers():
    from src.entry import handle_organize

    data, status = await handle_organize({}, ENV)
    assert status == 400
    assert "error" in data


@pytest.mark.asyncio
async def test_organize_by_year():
    from src.entry import handle_organize

    data, status = await handle_organize(
        {"papers": [{"title": "Paper A", "year": 2019}], "organize_by": "year"}, ENV
    )
    assert status == 200
    assert data["organize_by"] == "year"


# ---------------------------------------------------------------------------
# Tests: handle_trends
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_trends_with_field():
    from src.entry import handle_trends

    data, status = await handle_trends({"field": "machine learning"}, ENV)
    assert status == 200
    assert data["field"] == "machine learning"
    assert "trends" in data


@pytest.mark.asyncio
async def test_trends_with_papers():
    from src.entry import handle_trends

    data, status = await handle_trends(
        {"papers": [{"title": "Paper A", "year": 2023}]}, ENV
    )
    assert status == 200


@pytest.mark.asyncio
async def test_trends_no_field_or_papers():
    from src.entry import handle_trends

    data, status = await handle_trends({}, ENV)
    assert status == 400
    assert "error" in data


@pytest.mark.asyncio
async def test_trends_with_time_range():
    from src.entry import handle_trends

    data, status = await handle_trends({"field": "NLP", "time_range": "2018-2024"}, ENV)
    assert status == 200


# ---------------------------------------------------------------------------
# Tests: handle_review
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_review_success():
    from src.entry import handle_review

    data, status = await handle_review({"topic": "deep learning for NLP"}, ENV)
    assert status == 200
    assert data["topic"] == "deep learning for NLP"
    assert data["style"] == "comprehensive"
    assert "review" in data
    assert len(data["review"]) > 0


@pytest.mark.asyncio
async def test_review_with_papers_and_style():
    from src.entry import handle_review

    data, status = await handle_review(
        {
            "topic": "graph neural networks",
            "papers": [{"title": "GNN Survey", "year": 2022}],
            "style": "brief",
            "audience": "graduate students",
        },
        ENV,
    )
    assert status == 200
    assert data["style"] == "brief"


@pytest.mark.asyncio
async def test_review_missing_topic():
    from src.entry import handle_review

    data, status = await handle_review({}, ENV)
    assert status == 400
    assert "error" in data


# ---------------------------------------------------------------------------
# Tests: _json_response and _error helpers
# ---------------------------------------------------------------------------


def test_json_response_content_type():
    from src.entry import _json_response

    resp = _json_response({"key": "value"})
    assert resp.headers.get("Content-Type") == "application/json"
    assert resp.status == 200
    assert json.loads(resp.body) == {"key": "value"}


def test_json_response_custom_status():
    from src.entry import _json_response

    resp = _json_response({"error": "bad"}, status=400)
    assert resp.status == 400


def test_error_helper():
    from src.entry import _error

    resp = _error("Not found", 404)
    assert resp.status == 404
    assert json.loads(resp.body) == {"error": "Not found"}

