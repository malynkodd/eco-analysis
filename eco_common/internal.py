"""High-level wrappers for the internal calls between services.

Service URLs come from the standard docker-compose service names; they
can be overridden with environment variables for non-docker deployments.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from typing import List, Optional

from eco_common.http_client import HttpRetryClient, get_internal_client


def _env(name: str, default: str) -> str:
    return os.getenv(name, default)


@dataclass
class InternalAPI:
    """Typed entry points for cross-service reads."""

    project_url: str = _env(
        "PROJECT_SERVICE_URL", "http://project-service:8000"
    )
    financial_url: str = _env(
        "FINANCIAL_SERVICE_URL", "http://financial-service:8000"
    )
    eco_url: str = _env("ECO_IMPACT_SERVICE_URL", "http://eco-impact-service:8000")
    multi_url: str = _env(
        "MULTI_CRITERIA_SERVICE_URL", "http://multi-criteria-service:8000"
    )
    scenario_url: str = _env(
        "SCENARIO_SERVICE_URL", "http://scenario-service:8000"
    )
    comparison_url: str = _env(
        "COMPARISON_SERVICE_URL", "http://comparison-service:8000"
    )
    client: Optional[HttpRetryClient] = None

    def _client(self) -> HttpRetryClient:
        return self.client or get_internal_client()

    @staticmethod
    def _auth_headers(token: str) -> dict:
        return {"Authorization": f"Bearer {token}"}

    async def get_project(self, project_id: int, token: str) -> dict:
        resp = await self._client().request(
            "GET",
            f"{self.project_url}/{project_id}",
            service="project-service",
            headers=self._auth_headers(token),
        )
        return resp.json()

    async def get_financial_results(
        self, project_id: int, token: str
    ) -> List[dict]:
        resp = await self._client().request(
            "GET",
            f"{self.financial_url}/projects/{project_id}/results",
            service="financial-service",
            headers=self._auth_headers(token),
        )
        return resp.json()

    async def get_eco_results(
        self, project_id: int, token: str
    ) -> List[dict]:
        resp = await self._client().request(
            "GET",
            f"{self.eco_url}/projects/{project_id}/results",
            service="eco-impact-service",
            headers=self._auth_headers(token),
        )
        return resp.json()

    async def get_ahp_results(self, project_id: int, token: str) -> List[dict]:
        resp = await self._client().request(
            "GET",
            f"{self.multi_url}/projects/{project_id}/ahp/results",
            service="multi-criteria-service",
            headers=self._auth_headers(token),
        )
        return resp.json()

    async def get_topsis_results(
        self, project_id: int, token: str
    ) -> List[dict]:
        resp = await self._client().request(
            "GET",
            f"{self.multi_url}/projects/{project_id}/topsis/results",
            service="multi-criteria-service",
            headers=self._auth_headers(token),
        )
        return resp.json()

    async def get_scenario_results(
        self, project_id: int, token: str
    ) -> List[dict]:
        resp = await self._client().request(
            "GET",
            f"{self.scenario_url}/projects/{project_id}/results",
            service="scenario-service",
            headers=self._auth_headers(token),
        )
        return resp.json()

    async def get_comparison_results(
        self, project_id: int, token: str
    ) -> List[dict]:
        resp = await self._client().request(
            "GET",
            f"{self.comparison_url}/projects/{project_id}/results",
            service="comparison-service",
            headers=self._auth_headers(token),
        )
        return resp.json()
