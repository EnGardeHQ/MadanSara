"""
ZeroDB Memory Layer Integration for Walker Agents.

This module provides integration with En Garde's ZeroDB memory system,
enabling Walker agents to store and retrieve context, knowledge, and
conversation history across all microservices.
"""

import os
import json
import httpx
from typing import Dict, List, Optional, Any, Union
from datetime import datetime, timedelta
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class MemoryType(Enum):
    """Types of memory stored in ZeroDB."""
    SHORT_TERM = "short_term"  # Recent conversation context
    LONG_TERM = "long_term"  # Persistent knowledge
    EPISODIC = "episodic"  # Specific events/interactions
    SEMANTIC = "semantic"  # Facts and concepts
    PROCEDURAL = "procedural"  # How-to knowledge
    WORKING = "working"  # Active task context


class ZeroDBClient:
    """
    Client for interacting with En Garde's ZeroDB memory layer.

    ZeroDB provides vector-based memory storage for Walker agents,
    enabling context retention across sessions and microservices.
    """

    def __init__(
        self,
        base_url: Optional[str] = None,
        api_key: Optional[str] = None,
        timeout: int = 30,
    ):
        """
        Initialize ZeroDB client.

        Args:
            base_url: ZeroDB API base URL
            api_key: Authentication API key
            timeout: Request timeout in seconds
        """
        self.base_url = base_url or os.getenv(
            "ZERODB_URL",
            "http://localhost:6333"  # Default Qdrant port
        )
        self.api_key = api_key or os.getenv("ZERODB_API_KEY", "")
        self.timeout = timeout

        self.headers = {
            "Content-Type": "application/json",
        }
        if self.api_key:
            self.headers["Authorization"] = f"Bearer {self.api_key}"

        # Collection names for different memory types
        self.collections = {
            MemoryType.SHORT_TERM: "walker_short_term_memory",
            MemoryType.LONG_TERM: "walker_long_term_memory",
            MemoryType.EPISODIC: "walker_episodic_memory",
            MemoryType.SEMANTIC: "walker_semantic_memory",
            MemoryType.PROCEDURAL: "walker_procedural_memory",
            MemoryType.WORKING: "walker_working_memory",
        }

    async def store_memory(
        self,
        agent_id: str,
        memory_type: MemoryType,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
        embedding: Optional[List[float]] = None,
        ttl: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Store a memory in ZeroDB.

        Args:
            agent_id: Unique identifier for the Walker agent
            memory_type: Type of memory to store
            content: Memory content (text)
            metadata: Additional metadata
            embedding: Pre-computed embedding vector
            ttl: Time-to-live in seconds (for short-term memory)

        Returns:
            Storage result with memory ID

        Example:
            result = await zerodb.store_memory(
                agent_id="walker_001",
                memory_type=MemoryType.SHORT_TERM,
                content="Customer prefers email communication",
                metadata={"customer_id": "cust_123", "confidence": 0.9}
            )
        """
        try:
            collection = self.collections[memory_type]

            # If no embedding provided, generate one
            if embedding is None:
                embedding = await self._generate_embedding(content)

            payload = {
                "agent_id": agent_id,
                "content": content,
                "memory_type": memory_type.value,
                "timestamp": datetime.utcnow().isoformat(),
                "metadata": metadata or {},
            }

            # Add TTL for short-term memory
            if ttl:
                payload["expires_at"] = (datetime.utcnow() + timedelta(seconds=ttl)).isoformat()

            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/collections/{collection}/points",
                    headers=self.headers,
                    json={
                        "points": [
                            {
                                "vector": embedding,
                                "payload": payload,
                            }
                        ]
                    },
                )

                if response.status_code in [200, 201]:
                    result = response.json()
                    logger.info(f"Memory stored for agent {agent_id}")
                    return {
                        "success": True,
                        "memory_id": result.get("result", {}).get("operation_id"),
                        "collection": collection,
                    }
                else:
                    logger.error(f"Failed to store memory: {response.text}")
                    return {
                        "success": False,
                        "error": response.text,
                    }

        except Exception as e:
            logger.error(f"Error storing memory: {str(e)}")
            return {
                "success": False,
                "error": str(e),
            }

    async def retrieve_memories(
        self,
        agent_id: str,
        query: str,
        memory_type: Optional[MemoryType] = None,
        limit: int = 10,
        score_threshold: float = 0.7,
    ) -> List[Dict[str, Any]]:
        """
        Retrieve relevant memories for an agent.

        Args:
            agent_id: Walker agent identifier
            query: Query text for semantic search
            memory_type: Filter by memory type (optional)
            limit: Maximum number of memories to return
            score_threshold: Minimum similarity score (0-1)

        Returns:
            List of relevant memories with scores

        Example:
            memories = await zerodb.retrieve_memories(
                agent_id="walker_001",
                query="customer communication preferences",
                memory_type=MemoryType.LONG_TERM,
                limit=5
            )
        """
        try:
            # Generate query embedding
            query_embedding = await self._generate_embedding(query)

            # Determine which collection(s) to search
            collections = []
            if memory_type:
                collections = [self.collections[memory_type]]
            else:
                # Search all collections
                collections = list(self.collections.values())

            all_memories = []

            async with httpx.AsyncClient(timeout=self.timeout) as client:
                for collection in collections:
                    response = await client.post(
                        f"{self.base_url}/collections/{collection}/points/search",
                        headers=self.headers,
                        json={
                            "vector": query_embedding,
                            "limit": limit,
                            "score_threshold": score_threshold,
                            "with_payload": True,
                            "filter": {
                                "must": [
                                    {
                                        "key": "agent_id",
                                        "match": {"value": agent_id}
                                    }
                                ]
                            }
                        },
                    )

                    if response.status_code == 200:
                        results = response.json().get("result", [])
                        for result in results:
                            memory = {
                                "content": result["payload"]["content"],
                                "memory_type": result["payload"]["memory_type"],
                                "timestamp": result["payload"]["timestamp"],
                                "metadata": result["payload"].get("metadata", {}),
                                "score": result["score"],
                                "collection": collection,
                            }
                            all_memories.append(memory)

            # Sort by score and limit
            all_memories.sort(key=lambda x: x["score"], reverse=True)
            return all_memories[:limit]

        except Exception as e:
            logger.error(f"Error retrieving memories: {str(e)}")
            return []

    async def get_agent_context(
        self,
        agent_id: str,
        max_age_hours: int = 24,
    ) -> Dict[str, Any]:
        """
        Get full context for an agent (recent memories + working memory).

        Args:
            agent_id: Walker agent identifier
            max_age_hours: Maximum age of memories to include

        Returns:
            Agent context with categorized memories

        Example:
            context = await zerodb.get_agent_context("walker_001")
            print(context["short_term_memories"])
            print(context["working_context"])
        """
        cutoff_time = datetime.utcnow() - timedelta(hours=max_age_hours)

        context = {
            "agent_id": agent_id,
            "short_term_memories": [],
            "working_context": [],
            "relevant_facts": [],
            "active_tasks": [],
            "timestamp": datetime.utcnow().isoformat(),
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                # Get short-term memories
                short_term = await self._get_recent_memories(
                    client,
                    agent_id,
                    MemoryType.SHORT_TERM,
                    cutoff_time,
                )
                context["short_term_memories"] = short_term

                # Get working memory
                working = await self._get_recent_memories(
                    client,
                    agent_id,
                    MemoryType.WORKING,
                    cutoff_time,
                )
                context["working_context"] = working

                # Get semantic facts
                semantic = await self._get_recent_memories(
                    client,
                    agent_id,
                    MemoryType.SEMANTIC,
                    cutoff_time,
                    limit=20,
                )
                context["relevant_facts"] = semantic

            return context

        except Exception as e:
            logger.error(f"Error getting agent context: {str(e)}")
            return context

    async def clear_expired_memories(self, agent_id: str) -> Dict[str, Any]:
        """
        Clear expired memories for an agent.

        Args:
            agent_id: Walker agent identifier

        Returns:
            Cleanup result
        """
        try:
            now = datetime.utcnow().isoformat()
            deleted_count = 0

            async with httpx.AsyncClient(timeout=self.timeout) as client:
                for collection in self.collections.values():
                    response = await client.post(
                        f"{self.base_url}/collections/{collection}/points/delete",
                        headers=self.headers,
                        json={
                            "filter": {
                                "must": [
                                    {
                                        "key": "agent_id",
                                        "match": {"value": agent_id}
                                    },
                                    {
                                        "key": "expires_at",
                                        "range": {"lt": now}
                                    }
                                ]
                            }
                        },
                    )

                    if response.status_code == 200:
                        result = response.json()
                        deleted_count += result.get("result", {}).get("points_deleted", 0)

            logger.info(f"Cleared {deleted_count} expired memories for agent {agent_id}")
            return {
                "success": True,
                "deleted_count": deleted_count,
            }

        except Exception as e:
            logger.error(f"Error clearing expired memories: {str(e)}")
            return {
                "success": False,
                "error": str(e),
            }

    async def _generate_embedding(self, text: str) -> List[float]:
        """
        Generate embedding vector for text.

        Uses En Garde's embedding service or fallback to simple hashing.

        Args:
            text: Text to embed

        Returns:
            Embedding vector
        """
        # TODO: Integrate with En Garde's embedding service
        # For now, return a simple placeholder
        # In production, this should call an embedding API (OpenAI, Cohere, etc.)

        embedding_url = os.getenv("EMBEDDING_SERVICE_URL")
        if embedding_url:
            try:
                async with httpx.AsyncClient(timeout=10) as client:
                    response = await client.post(
                        embedding_url,
                        json={"text": text},
                        headers=self.headers,
                    )
                    if response.status_code == 200:
                        return response.json()["embedding"]
            except Exception as e:
                logger.warning(f"Embedding service failed: {e}, using fallback")

        # Fallback: simple hash-based embedding (for development only)
        import hashlib
        hash_obj = hashlib.sha256(text.encode())
        hash_bytes = hash_obj.digest()
        # Convert to 384-dimensional vector (typical for sentence transformers)
        embedding = [float(b) / 255.0 for b in hash_bytes[:384]]
        # Pad to 384 dimensions
        while len(embedding) < 384:
            embedding.append(0.0)
        return embedding[:384]

    async def _get_recent_memories(
        self,
        client: httpx.AsyncClient,
        agent_id: str,
        memory_type: MemoryType,
        cutoff_time: datetime,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """Get recent memories of a specific type."""
        collection = self.collections[memory_type]

        try:
            response = await client.post(
                f"{self.base_url}/collections/{collection}/points/scroll",
                headers=self.headers,
                json={
                    "filter": {
                        "must": [
                            {
                                "key": "agent_id",
                                "match": {"value": agent_id}
                            },
                            {
                                "key": "timestamp",
                                "range": {"gte": cutoff_time.isoformat()}
                            }
                        ]
                    },
                    "limit": limit,
                    "with_payload": True,
                },
            )

            if response.status_code == 200:
                results = response.json().get("result", {}).get("points", [])
                return [
                    {
                        "content": point["payload"]["content"],
                        "timestamp": point["payload"]["timestamp"],
                        "metadata": point["payload"].get("metadata", {}),
                    }
                    for point in results
                ]

        except Exception as e:
            logger.error(f"Error getting recent memories: {e}")

        return []


# Global ZeroDB client instance
_zerodb_client: Optional[ZeroDBClient] = None


def get_zerodb() -> ZeroDBClient:
    """
    Get global ZeroDB client instance.

    Returns:
        ZeroDBClient: Global client instance

    Example:
        zerodb = get_zerodb()
        await zerodb.store_memory(...)
    """
    global _zerodb_client
    if _zerodb_client is None:
        _zerodb_client = ZeroDBClient()
    return _zerodb_client


# Export main classes
__all__ = [
    "ZeroDBClient",
    "MemoryType",
    "get_zerodb",
]
