"""Automated tests for RecoverAI FastAPI read-only endpoints."""

import pytest
from httpx import ASGITransport, AsyncClient

from apps.api.main import app


@pytest.mark.asyncio
async def test_api_health():
    """Verify health endpoint."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


@pytest.mark.asyncio
async def test_api_overview():
    """Verify command center overview endpoint."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/api/v1/overview")
    assert response.status_code == 200
    data = response.json()
    assert "kpis" in data
    assert "funnel" in data
    assert data["kpis"]["amount_at_risk_minor"] == 531161966
    assert data["kpis"]["recovered_amount_minor"] == 56195598
    assert data["kpis"]["total_cases_count"] == 1676
    assert len(data["funnel"]) == 6


@pytest.mark.asyncio
async def test_api_cases_list_and_filter():
    """Verify cases listing, pagination, and action filtering."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # Default listing
        res = await ac.get("/api/v1/cases?page=1&page_size=10")
        assert res.status_code == 200
        data = res.json()
        assert data["total"] == 1676
        assert len(data["items"]) == 10

        # Filter by action RETRY_PAYMENT
        res_filtered = await ac.get("/api/v1/cases?action_type=RETRY_PAYMENT")
        assert res_filtered.status_code == 200
        f_data = res_filtered.json()
        assert f_data["total"] > 0
        assert all(i["decision_proposal"]["action_type"] == "RETRY_PAYMENT" for i in f_data["items"])


@pytest.mark.asyncio
async def test_api_case_detail():
    """Verify case detail trace endpoint."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        list_res = await ac.get("/api/v1/cases?page=1&page_size=1")
        case_id = list_res.json()["items"][0]["case_id"]

        detail_res = await ac.get(f"/api/v1/cases/{case_id}")
        assert detail_res.status_code == 200
        detail = detail_res.json()
        assert detail["case_id"] == case_id
        assert "ai_diagnosis" in detail
        assert "decision_proposal" in detail
        assert "gateway_result" in detail
        assert "timeline" in detail
        assert len(detail["timeline"]) >= 5


@pytest.mark.asyncio
async def test_api_case_not_found():
    """Verify 404 for non-existent case."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        res = await ac.get("/api/v1/cases/00000000-0000-0000-0000-000000000000")
        assert res.status_code == 404


@pytest.mark.asyncio
async def test_api_safeguards():
    """Verify safeguards endpoint."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        res = await ac.get("/api/v1/safeguards")
        assert res.status_code == 200
        data = res.json()
        assert data["kill_switch_active"] is False
        assert data["critical_safety_metrics"]["unauthorized_execution_rate_bps"] == 0
        assert data["critical_safety_metrics"]["duplicate_execution_rate_bps"] == 0


@pytest.mark.asyncio
async def test_api_analytics():
    """Verify analytics endpoint."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        res = await ac.get("/api/v1/analytics")
        assert res.status_code == 200
        data = res.json()
        assert "benchmark_summary" in data
        assert "action_breakdown" in data
