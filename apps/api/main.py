"""FastAPI application entrypoint for RecoverAI."""

from typing import Any, Dict, List, Optional
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from apps.api.data_service import RecoverAIDataService

app = FastAPI(
    title="RecoverAI API",
    description="Backend API for RecoverAI - AI Revenue Recovery Platform",
    version="0.1.0",
)

# Enable CORS for local development and frontend client
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class HealthResponse(BaseModel):
    """Health check response schema."""

    status: str


@app.get(
    "/health",
    response_model=HealthResponse,
    summary="Health check endpoint",
    tags=["System"],
)
async def health_check() -> HealthResponse:
    """Return health status of the API service."""
    return HealthResponse(status="ok")


@app.get(
    "/api/v1/overview",
    summary="Get revenue recovery command center overview",
    tags=["Dashboard"],
)
async def get_overview() -> Dict[str, Any]:
    """Return high-level KPIs, funnel data, and system safeguard metrics."""
    svc = await RecoverAIDataService.get_instance()
    return svc.get_overview()


@app.get(
    "/api/v1/cases",
    summary="List recovery cases with filtering and pagination",
    tags=["Cases"],
)
async def list_cases(
    search: Optional[str] = Query(None, description="Search by customer, case ID, or code"),
    action_type: Optional[str] = Query(None, description="Filter by proposed action"),
    gateway_decision: Optional[str] = Query(None, description="Filter by gateway decision"),
    execution_status: Optional[str] = Query(None, description="Filter by execution status"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(25, ge=1, le=100, description="Page size"),
) -> Dict[str, Any]:
    """List recovery cases with their complete multi-phase pipeline statuses."""
    svc = await RecoverAIDataService.get_instance()
    return svc.list_cases(
        search=search,
        action_type=action_type,
        gateway_decision=gateway_decision,
        execution_status=execution_status,
        page=page,
        page_size=page_size,
    )


@app.get(
    "/api/v1/cases/{case_id}",
    summary="Get full end-to-end trace for a specific recovery case",
    tags=["Cases"],
)
async def get_case_detail(case_id: str) -> Dict[str, Any]:
    """Return the complete audit trail and decision trace for a case."""
    svc = await RecoverAIDataService.get_instance()
    detail = svc.get_case_detail(case_id)
    if detail is None:
        raise HTTPException(status_code=404, detail="Recovery case not found")
    return detail


@app.get(
    "/api/v1/safeguards",
    summary="Get operational system safeguards and release metrics",
    tags=["Safeguards"],
)
async def get_safeguards() -> Dict[str, Any]:
    """Return system safeguard status, kill switch, and release-blocking safety metrics."""
    return {
        "kill_switch_active": False,
        "payment_mode": "Simulation / Razorpay Test Mode",
        "gateway_version": "v1",
        "policy_version": "v1",
        "decision_version": "v1",
        "retry_policy": {
            "max_attempts_cap": 2,
            "high_value_threshold_minor": 500000,
            "high_value_display": "₹5,000.00",
            "cooldown_period_seconds": 86400,
        },
        "critical_safety_metrics": {
            "unauthorized_execution_rate_bps": 0,
            "duplicate_execution_rate_bps": 0,
            "financial_integrity_violation_rate_bps": 0,
            "unsafe_authorization_rate_bps": 0,
        },
        "blocked_reasons_distribution": {
            "BLOCK_NON_EXECUTABLE_ACTION": 704,
            "BLOCK_UNRESOLVED_HARD_DECLINE": 15,
            "MISSING_HUMAN_APPROVAL": 268,
        },
    }


@app.get(
    "/api/v1/analytics",
    summary="Get analytical breakdown of revenue recovery performance",
    tags=["Analytics"],
)
async def get_analytics() -> Dict[str, Any]:
    """Return failure category analysis, action distributions, and conversion metrics."""
    return {
        "benchmark_summary": {
            "total_evaluated_minor": 531161966,
            "total_evaluated_display": "₹53,11,619.66",
            "authorized_minor": 85259735,
            "authorized_display": "₹8,52,597.35",
            "recovered_minor": 56195598,
            "recovered_display": "₹5,61,955.98",
            "deferred_minor": 29064137,
            "deferred_display": "₹2,90,641.37",
            "blocked_minor": 184300717,
            "blocked_display": "₹18,43,007.17",
            "requires_review_minor": 261601514,
            "requires_review_display": "₹26,16,015.14",
        },
        "conversion_rates": {
            "gross_recovery_rate_bps": 1058,  # 10.58% of gross at risk
            "gross_recovery_display": "10.6%",
            "authorized_conversion_rate_bps": 6591,  # 65.91% of authorized
            "authorized_conversion_display": "65.9%",
        },
        "action_breakdown": [
            {"action": "RETRY_PAYMENT", "count": 444, "amount_minor": 54695598, "status": "EXECUTED"},
            {"action": "RETRY_LATER", "count": 233, "amount_minor": 29064137, "status": "DEFERRED"},
            {"action": "SUBSCRIPTION_RECOVERY_WORKFLOW", "count": 12, "amount_minor": 1500000, "status": "EXECUTED"},
            {"action": "HUMAN_REVIEW", "count": 268, "amount_minor": 261601514, "status": "ESCALATED"},
            {"action": "NO_ACTION", "count": 719, "amount_minor": 184300717, "status": "BLOCKED"},
        ],
    }
