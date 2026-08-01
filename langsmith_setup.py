"""Applies LangSmith tracing config from our typed settings to the environment
variables LangChain/LangGraph auto-detect (LANGSMITH_TRACING, LANGSMITH_API_KEY,
LANGSMITH_PROJECT, LANGSMITH_ENDPOINT) -- those libraries read os.environ directly,
not our Pydantic Settings object, so this bridges the two. Call once at process
start, before constructing any ChatOllama/graph (see bootstrap.start_stack).

A no-op if langsmith_tracing_enabled is False or no API key is configured -- this
repo has no LangSmith account available, so tracing/evals are wired but inert
unless the user supplies their own key in .env.
"""
from __future__ import annotations

import os

from config.settings import settings


def apply_langsmith_env() -> bool:
    """Returns True if tracing was actually enabled."""
    if not (settings.langsmith_tracing_enabled and settings.langsmith_api_key):
        return False
    os.environ["LANGSMITH_TRACING"] = "true"
    os.environ["LANGSMITH_API_KEY"] = settings.langsmith_api_key
    os.environ["LANGSMITH_PROJECT"] = settings.langsmith_project
    os.environ["LANGSMITH_ENDPOINT"] = settings.langsmith_endpoint
    return True
