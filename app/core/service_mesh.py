"""
Service Mesh for En Garde Microservices.

Provides service discovery and inter-service communication for:
- Onside (SEO Intelligence)
- Sankore (Paid Ads Intelligence)
- Madan Sara (Audience Conversion Intelligence)
"""

import os
import httpx
from typing import Dict, List, Optional, Any
from enum import Enum
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class ServiceName(Enum):
    """En Garde microservices."""
    ENGARDE_CORE = "engarde-core"
    ONSIDE = "onside"
    SANKORE = "sankore"
    MADAN_SARA = "madan-sara"


class ServiceMesh:
    """
    Service discovery and communication layer.

    Manages inter-service communication between En Garde microservices
    with automatic service discovery, retries, and circuit breaking.
    """

    def __init__(self):
        """Initialize service mesh with Railway service URLs."""
        # Get service URLs from environment (Railway provides these)
        self.services = {
            ServiceName.ENGARDE_CORE: os.getenv(
                "ENGARDE_CORE_URL",
                "http://localhost:8000"
            ),
            ServiceName.ONSIDE: os.getenv(
                "ONSIDE_URL",
                "http://localhost:8001"
            ),
            ServiceName.SANKORE: os.getenv(
                "SANKORE_URL",
                "http://localhost:8003"
            ),
            ServiceName.MADAN_SARA: os.getenv(
                "MADAN_SARA_URL",
                "http://localhost:8002"
            ),
        }

        # Service health status
        self.health_status: Dict[ServiceName, bool] = {}

        # Circuit breaker settings
        self.failure_threshold = int(os.getenv("CIRCUIT_BREAKER_THRESHOLD", "5"))
        self.failure_counts: Dict[ServiceName, int] = {}

        # Request timeout
        self.timeout = int(os.getenv("SERVICE_MESH_TIMEOUT", "30"))

        # Service authentication (shared secret)
        self.service_secret = os.getenv("SERVICE_MESH_SECRET", "")

    def get_service_url(self, service: ServiceName) -> str:
        """Get URL for a service."""
        return self.services.get(service, "")

    async def call_service(
        self,
        service: ServiceName,
        path: str,
        method: str = "GET",
        data: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        retry: int = 3,
    ) -> Dict[str, Any]:
        """
        Call another microservice.

        Args:
            service: Target service
            path: API path (e.g., "/api/v1/analyze")
            method: HTTP method
            data: Request data
            headers: Additional headers
            retry: Number of retries

        Returns:
            Response data

        Example:
            result = await mesh.call_service(
                ServiceName.ONSIDE,
                "/api/v1/seo/analyze",
                method="POST",
                data={"url": "https://example.com"}
            )
        """
        # Check circuit breaker
        if self.failure_counts.get(service, 0) >= self.failure_threshold:
            logger.error(f"Circuit breaker open for {service.value}")
            return {
                "success": False,
                "error": "Service unavailable (circuit breaker open)",
                "service": service.value,
            }

        url = f"{self.services[service]}{path}"

        # Add service authentication
        request_headers = headers or {}
        if self.service_secret:
            request_headers["X-Service-Secret"] = self.service_secret
        request_headers["X-Service-Source"] = "madan-sara"  # Identify caller

        attempts = 0
        last_error = None

        while attempts < retry:
            try:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    if method.upper() == "GET":
                        response = await client.get(url, headers=request_headers)
                    elif method.upper() == "POST":
                        response = await client.post(
                            url,
                            json=data,
                            headers=request_headers
                        )
                    elif method.upper() == "PUT":
                        response = await client.put(
                            url,
                            json=data,
                            headers=request_headers
                        )
                    elif method.upper() == "DELETE":
                        response = await client.delete(url, headers=request_headers)
                    else:
                        return {
                            "success": False,
                            "error": f"Unsupported method: {method}"
                        }

                    # Success - reset failure count
                    self.failure_counts[service] = 0
                    self.health_status[service] = True

                    if response.status_code in [200, 201]:
                        return {
                            "success": True,
                            "data": response.json(),
                            "status_code": response.status_code,
                        }
                    else:
                        return {
                            "success": False,
                            "error": response.text,
                            "status_code": response.status_code,
                        }

            except Exception as e:
                last_error = str(e)
                attempts += 1
                logger.warning(
                    f"Service call failed (attempt {attempts}/{retry}): {e}"
                )

                # Increment failure count
                self.failure_counts[service] = self.failure_counts.get(service, 0) + 1
                self.health_status[service] = False

                if attempts < retry:
                    # Exponential backoff
                    import asyncio
                    await asyncio.sleep(2 ** attempts)

        # All retries failed
        return {
            "success": False,
            "error": f"Service call failed after {retry} attempts: {last_error}",
            "service": service.value,
        }

    async def get_seo_analysis(
        self,
        url: str,
        tenant_uuid: str,
    ) -> Dict[str, Any]:
        """
        Get SEO analysis from Onside service.

        Args:
            url: URL to analyze
            tenant_uuid: Tenant UUID

        Returns:
            SEO analysis results
        """
        return await self.call_service(
            ServiceName.ONSIDE,
            "/api/v1/seo/analyze",
            method="POST",
            data={
                "url": url,
                "tenant_uuid": tenant_uuid,
            }
        )

    async def get_ad_intelligence(
        self,
        campaign_id: str,
        tenant_uuid: str,
    ) -> Dict[str, Any]:
        """
        Get paid ads intelligence from Sankore service.

        Args:
            campaign_id: Campaign ID
            tenant_uuid: Tenant UUID

        Returns:
            Ad campaign intelligence
        """
        return await self.call_service(
            ServiceName.SANKORE,
            f"/api/v1/campaigns/{campaign_id}/intelligence",
            method="GET",
        )

    async def get_conversion_insights(
        self,
        customer_id: str,
        tenant_uuid: str,
    ) -> Dict[str, Any]:
        """
        Get conversion insights (useful for Onside and Sankore to call Madan Sara).

        Args:
            customer_id: Customer ID
            tenant_uuid: Tenant UUID

        Returns:
            Conversion insights
        """
        return await self.call_service(
            ServiceName.MADAN_SARA,
            f"/api/v1/conversion/customers/{customer_id}/insights",
            method="GET",
        )

    async def sync_to_engarde_core(
        self,
        data_type: str,
        data: Dict[str, Any],
        tenant_uuid: str,
    ) -> Dict[str, Any]:
        """
        Sync data to En Garde core application.

        Args:
            data_type: Type of data (conversion, campaign, etc.)
            data: Data to sync
            tenant_uuid: Tenant UUID

        Returns:
            Sync result
        """
        return await self.call_service(
            ServiceName.ENGARDE_CORE,
            f"/api/v1/sync/{data_type}",
            method="POST",
            data={
                "tenant_uuid": tenant_uuid,
                "source": "madan-sara",
                "data": data,
                "timestamp": datetime.utcnow().isoformat(),
            }
        )

    async def check_service_health(self, service: ServiceName) -> bool:
        """
        Check if a service is healthy.

        Args:
            service: Service to check

        Returns:
            True if healthy, False otherwise
        """
        try:
            result = await self.call_service(
                service,
                "/health",
                method="GET",
                retry=1,
            )
            return result.get("success", False)
        except Exception as e:
            logger.error(f"Health check failed for {service.value}: {e}")
            return False

    async def check_all_services_health(self) -> Dict[str, bool]:
        """
        Check health of all services.

        Returns:
            Dict mapping service names to health status
        """
        health = {}
        for service in ServiceName:
            health[service.value] = await self.check_service_health(service)
        return health

    def reset_circuit_breaker(self, service: ServiceName) -> None:
        """Reset circuit breaker for a service."""
        self.failure_counts[service] = 0
        logger.info(f"Circuit breaker reset for {service.value}")

    def get_service_status(self) -> Dict[str, Any]:
        """
        Get status of all services.

        Returns:
            Service status information
        """
        return {
            "services": {
                service.value: {
                    "url": self.services[service],
                    "healthy": self.health_status.get(service, False),
                    "failure_count": self.failure_counts.get(service, 0),
                    "circuit_breaker_open": self.failure_counts.get(service, 0) >= self.failure_threshold,
                }
                for service in ServiceName
            },
            "circuit_breaker_threshold": self.failure_threshold,
        }


# Global service mesh instance
_service_mesh: Optional[ServiceMesh] = None


def get_service_mesh() -> ServiceMesh:
    """
    Get global service mesh instance.

    Returns:
        ServiceMesh: Global service mesh

    Example:
        mesh = get_service_mesh()
        result = await mesh.get_seo_analysis(url, tenant_uuid)
    """
    global _service_mesh
    if _service_mesh is None:
        _service_mesh = ServiceMesh()
    return _service_mesh


# Export main classes
__all__ = [
    "ServiceMesh",
    "ServiceName",
    "get_service_mesh",
]
