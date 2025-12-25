#!/usr/bin/env python3
"""
Initialize ZeroDB Collections for Walker Agents.

This script creates the required Qdrant collections for Walker agent memory.
Run this once before deploying the microservices.
"""

import os
import sys
import httpx
import asyncio
from typing import Dict, List

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.zerodb_integration import MemoryType


# Qdrant connection settings
ZERODB_URL = os.getenv("ZERODB_URL", "http://localhost:6333")
ZERODB_API_KEY = os.getenv("ZERODB_API_KEY", "")

# Collection configuration
VECTOR_SIZE = 384  # Sentence transformer dimension
COLLECTIONS = {
    "walker_short_term_memory": {
        "description": "Short-term memory for Walker agents (24-48 hours)",
        "vector_size": VECTOR_SIZE,
    },
    "walker_long_term_memory": {
        "description": "Long-term persistent knowledge",
        "vector_size": VECTOR_SIZE,
    },
    "walker_episodic_memory": {
        "description": "Specific events and interactions",
        "vector_size": VECTOR_SIZE,
    },
    "walker_semantic_memory": {
        "description": "Facts and concepts",
        "vector_size": VECTOR_SIZE,
    },
    "walker_procedural_memory": {
        "description": "How-to knowledge and procedures",
        "vector_size": VECTOR_SIZE,
    },
    "walker_working_memory": {
        "description": "Active task context",
        "vector_size": VECTOR_SIZE,
    },
}


async def create_collection(
    client: httpx.AsyncClient,
    name: str,
    config: Dict,
) -> bool:
    """Create a Qdrant collection."""
    headers = {"Content-Type": "application/json"}
    if ZERODB_API_KEY:
        headers["api-key"] = ZERODB_API_KEY

    try:
        # Check if collection exists
        response = await client.get(
            f"{ZERODB_URL}/collections/{name}",
            headers=headers,
        )

        if response.status_code == 200:
            print(f"  ✓ Collection '{name}' already exists")
            return True

        # Create collection
        payload = {
            "vectors": {
                "size": config["vector_size"],
                "distance": "Cosine",  # Cosine similarity for semantic search
            },
            "optimizers_config": {
                "memmap_threshold": 20000,  # Optimize for memory
            },
            "hnsw_config": {
                "m": 16,  # Number of edges per node
                "ef_construct": 100,  # Construction time/accuracy tradeoff
            },
        }

        response = await client.put(
            f"{ZERODB_URL}/collections/{name}",
            json=payload,
            headers=headers,
        )

        if response.status_code in [200, 201]:
            print(f"  ✓ Created collection '{name}'")
            return True
        else:
            print(f"  ✗ Failed to create '{name}': {response.text}")
            return False

    except Exception as e:
        print(f"  ✗ Error creating '{name}': {e}")
        return False


async def create_indexes(client: httpx.AsyncClient, name: str) -> bool:
    """Create payload indexes for efficient filtering."""
    headers = {"Content-Type": "application/json"}
    if ZERODB_API_KEY:
        headers["api-key"] = ZERODB_API_KEY

    try:
        # Create index for agent_id (most common filter)
        await client.put(
            f"{ZERODB_URL}/collections/{name}/index",
            json={
                "field_name": "agent_id",
                "field_schema": "keyword",
            },
            headers=headers,
        )

        # Create index for timestamp
        await client.put(
            f"{ZERODB_URL}/collections/{name}/index",
            json={
                "field_name": "timestamp",
                "field_schema": "datetime",
            },
            headers=headers,
        )

        # Create index for memory_type
        await client.put(
            f"{ZERODB_URL}/collections/{name}/index",
            json={
                "field_name": "memory_type",
                "field_schema": "keyword",
            },
            headers=headers,
        )

        print(f"  ✓ Created indexes for '{name}'")
        return True

    except Exception as e:
        print(f"  ⚠ Warning: Could not create indexes for '{name}': {e}")
        return False


async def verify_collection(client: httpx.AsyncClient, name: str) -> Dict:
    """Verify collection was created successfully."""
    headers = {}
    if ZERODB_API_KEY:
        headers["api-key"] = ZERODB_API_KEY

    try:
        response = await client.get(
            f"{ZERODB_URL}/collections/{name}",
            headers=headers,
        )

        if response.status_code == 200:
            info = response.json()["result"]
            return {
                "exists": True,
                "vectors_count": info.get("vectors_count", 0),
                "points_count": info.get("points_count", 0),
                "status": info.get("status", "unknown"),
            }
        else:
            return {"exists": False}

    except Exception as e:
        print(f"  ⚠ Warning: Could not verify '{name}': {e}")
        return {"exists": False}


async def main():
    """Main initialization function."""
    print("╔══════════════════════════════════════════════════════════╗")
    print("║  ZeroDB Collection Initialization                        ║")
    print("╚══════════════════════════════════════════════════════════╝")
    print()

    print(f"Connecting to ZeroDB at: {ZERODB_URL}")
    print()

    async with httpx.AsyncClient(timeout=30.0) as client:
        # Test connection
        try:
            headers = {}
            if ZERODB_API_KEY:
                headers["api-key"] = ZERODB_API_KEY

            response = await client.get(f"{ZERODB_URL}/collections", headers=headers)
            if response.status_code != 200:
                print("✗ Failed to connect to ZeroDB")
                print(f"  Error: {response.text}")
                sys.exit(1)
            print("✓ Connected to ZeroDB")
            print()
        except Exception as e:
            print(f"✗ Failed to connect to ZeroDB: {e}")
            sys.exit(1)

        # Create collections
        print("Creating collections...")
        print()

        success_count = 0
        for name, config in COLLECTIONS.items():
            print(f"Collection: {name}")
            print(f"  Description: {config['description']}")

            if await create_collection(client, name, config):
                success_count += 1
                await create_indexes(client, name)

                # Verify
                info = await verify_collection(client, name)
                if info["exists"]:
                    print(f"  Status: {info.get('status', 'ready')}")

            print()

        # Summary
        print("╔══════════════════════════════════════════════════════════╗")
        print("║  Initialization Complete                                 ║")
        print("╚══════════════════════════════════════════════════════════╝")
        print()
        print(f"Collections created: {success_count}/{len(COLLECTIONS)}")
        print()

        if success_count == len(COLLECTIONS):
            print("✓ All collections ready for Walker agents")
            print()
            print("Next steps:")
            print("  1. Deploy microservices to Railway")
            print("  2. Set ZERODB_URL in environment variables")
            print("  3. Test with: python scripts/test-zerodb.py")
        else:
            print("⚠ Some collections failed to create")
            print("  Check logs and retry")
            sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
