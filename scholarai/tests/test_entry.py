"""
Unit tests for ScholarAI FastAPI endpoints.

The Cloudflare Workers AI binding (`env.AI`) is mocked so that tests run
without a live Workers runtime.  FastAPI dependency overrides inject the mock
into every endpoint that calls `Depends(get_env)`.
"""
import json
import pytest
from fastapi.testclient import TestClient

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


# ---------------------------------------------------------------------------
# App fixture with dependency override
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def client():
    """Return a TestClient with the AI env dependency overridden."""
    from src.entry import app, get_env

    mock_env = MockEnv()
    app.dependency_overrides[get_env] = lambda: mock_env
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Tests: GET /
# ---------------------------------------------------------------------------


def test_api_info_status(client):
    response = client.get("/")
    assert response.status_code == 200


def test_api_info_name(client):
    data = client.get("/").json()
    assert data["name"] == "ScholarAI"
    assert data["version"] == "1.0.0"


def test_api_info_endpoints_listed(client):
    data = client.get("/").json()
    expected_keys = {
        "GET /",
        "POST /api/discover",
        "POST /api/summarize",
        "POST /api/citations",
        "POST /api/qa",
        "POST /api/organize",
        "POST /api/trends",
        "POST /api/review",
    }
    assert expected_keys == set(data["endpoints"].keys())


# ---------------------------------------------------------------------------
# Tests: POST /api/discover
# ---------------------------------------------------------------------------


def test_discover_success(client):
    response = client.post("/api/discover", json={"query": "transformer models"})
    assert response.status_code == 200
    data = response.json()
    assert data["query"] == "transformer models"
    assert "results" in data


def test_discover_with_fields_and_limit(client):
    response = client.post(
        "/api/discover",
        json={"query": "protein folding", "fields": ["biology", "ML"], "limit": 5},
    )
    assert response.status_code == 200
    assert response.json()["query"] == "protein folding"


def test_discover_missing_query(client):
    response = client.post("/api/discover", json={})
    assert response.status_code == 422  # FastAPI validation error


# ---------------------------------------------------------------------------
# Tests: POST /api/summarize
# ---------------------------------------------------------------------------


def test_summarize_with_abstract(client):
    response = client.post(
        "/api/summarize",
        json={"title": "Test Paper", "abstract": "This paper proposes a new method."},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "Test Paper"
    assert "summary" in data
    assert len(data["summary"]) > 0


def test_summarize_with_content_only(client):
    response = client.post(
        "/api/summarize",
        json={"content": "Full paper content goes here..."},
    )
    assert response.status_code == 200


def test_summarize_no_input(client):
    """All fields empty — endpoint should return 400."""
    response = client.post("/api/summarize", json={})
    assert response.status_code == 400


# ---------------------------------------------------------------------------
# Tests: POST /api/citations
# ---------------------------------------------------------------------------


def test_citations_success(client):
    response = client.post(
        "/api/citations",
        json={"paper": "Attention Is All You Need", "type": "related"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["paper"] == "Attention Is All You Need"
    assert data["citation_type"] == "related"
    assert "exploration" in data


def test_citations_missing_paper(client):
    response = client.post("/api/citations", json={})
    assert response.status_code == 422


def test_citations_forward_type(client):
    response = client.post(
        "/api/citations",
        json={"paper": "BERT: Pre-training of Deep Bidirectional Transformers", "type": "forward"},
    )
    assert response.status_code == 200
    assert response.json()["citation_type"] == "forward"


# ---------------------------------------------------------------------------
# Tests: POST /api/qa
# ---------------------------------------------------------------------------


def test_qa_success(client):
    response = client.post(
        "/api/qa",
        json={"question": "What is transfer learning?"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["question"] == "What is transfer learning?"
    assert "answer" in data
    assert len(data["answer"]) > 0


def test_qa_with_context_and_papers(client):
    response = client.post(
        "/api/qa",
        json={
            "question": "How does BERT work?",
            "context": "BERT is a language model.",
            "papers": [{"title": "BERT", "year": 2018}],
        },
    )
    assert response.status_code == 200


def test_qa_missing_question(client):
    response = client.post("/api/qa", json={})
    assert response.status_code == 422


# ---------------------------------------------------------------------------
# Tests: POST /api/organize
# ---------------------------------------------------------------------------


def test_organize_success(client):
    papers = [
        {"title": "Paper A", "year": 2020},
        {"title": "Paper B", "year": 2021},
    ]
    response = client.post(
        "/api/organize",
        json={"papers": papers, "organize_by": "topic"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["organize_by"] == "topic"
    assert "organization" in data


def test_organize_missing_papers(client):
    response = client.post("/api/organize", json={})
    assert response.status_code == 422


def test_organize_by_year(client):
    papers = [{"title": "Paper A", "year": 2019}]
    response = client.post(
        "/api/organize", json={"papers": papers, "organize_by": "year"}
    )
    assert response.status_code == 200
    assert response.json()["organize_by"] == "year"


# ---------------------------------------------------------------------------
# Tests: POST /api/trends
# ---------------------------------------------------------------------------


def test_trends_with_field(client):
    response = client.post("/api/trends", json={"field": "machine learning"})
    assert response.status_code == 200
    data = response.json()
    assert data["field"] == "machine learning"
    assert "trends" in data


def test_trends_with_papers(client):
    response = client.post(
        "/api/trends",
        json={"papers": [{"title": "Paper A", "year": 2023}]},
    )
    assert response.status_code == 200


def test_trends_no_field_or_papers(client):
    """Neither field nor papers provided — endpoint should return 400."""
    response = client.post("/api/trends", json={})
    assert response.status_code == 400


def test_trends_with_time_range(client):
    response = client.post(
        "/api/trends",
        json={"field": "NLP", "time_range": "2018-2024"},
    )
    assert response.status_code == 200


# ---------------------------------------------------------------------------
# Tests: POST /api/review
# ---------------------------------------------------------------------------


def test_review_success(client):
    response = client.post(
        "/api/review",
        json={"topic": "deep learning for NLP"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["topic"] == "deep learning for NLP"
    assert data["style"] == "comprehensive"
    assert "review" in data
    assert len(data["review"]) > 0


def test_review_with_papers_and_style(client):
    response = client.post(
        "/api/review",
        json={
            "topic": "graph neural networks",
            "papers": [{"title": "GNN Survey", "year": 2022}],
            "style": "brief",
            "audience": "graduate students",
        },
    )
    assert response.status_code == 200
    assert response.json()["style"] == "brief"


def test_review_missing_topic(client):
    response = client.post("/api/review", json={})
    assert response.status_code == 422


# ---------------------------------------------------------------------------
# Tests: missing env binding (simulate misconfigured deployment)
# ---------------------------------------------------------------------------


@pytest.fixture
def client_no_env():
    """Return a TestClient where get_env returns None (no AI binding)."""
    from src.entry import app, get_env

    app.dependency_overrides[get_env] = lambda: None
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c
    app.dependency_overrides.clear()


def test_discover_no_env(client_no_env):
    response = client_no_env.post("/api/discover", json={"query": "test"})
    assert response.status_code == 503


def test_summarize_no_env(client_no_env):
    response = client_no_env.post(
        "/api/summarize", json={"abstract": "some text"}
    )
    assert response.status_code == 503


def test_qa_no_env(client_no_env):
    response = client_no_env.post("/api/qa", json={"question": "what is AI?"})
    assert response.status_code == 503
