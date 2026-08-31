"""FastAPI application entrypoint for RecoverAI."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

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
