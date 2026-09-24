"""
FinVisor 2.0 — Redis Client
============================
Manages the Redis connection and stream reading utilities.
Stream key: transactions:live
"""

from __future__ import annotations

import os
from typing import Any, Dict, List, Optional, Tuple

import redis.asyncio as aioredis

from simulator.schemas import Transaction

STREAM_KEY = "transactions:live"

# ---------------------------------------------------------------------------
# Singleton async Redis pool
# ---------------------------------------------------------------------------

_redis_pool: Optional[aioredis.Redis] = None


async def get_redis(redis_url: Optional[str] = None) -> aioredis.Redis:
    """Return (or create) the global async Redis connection pool."""
    global _redis_pool
    if _redis_pool is None:
        url = redis_url or os.getenv("REDIS_URL", "redis://localhost:6379")
        _redis_pool = aioredis.from_url(url, decode_responses=True)
    return _redis_pool


async def close_redis() -> None:
    global _redis_pool
    if _redis_pool is not None:
        await _redis_pool.aclose()
        _redis_pool = None


# ---------------------------------------------------------------------------
# Stream helpers
# ---------------------------------------------------------------------------

async def ping_redis() -> bool:
    """Return True if Redis is reachable."""
    try:
        r = await get_redis()
        return await r.ping()
    except Exception:
        return False


async def get_latest_from_stream(
    count: int = 20,
    stream_key: str = STREAM_KEY,
) -> List[Transaction]:
    """
    Read the last `count` entries from the Redis stream.
    Returns a list of Transaction objects (newest first).
    """
    r = await get_redis()
    try:
        # XREVRANGE reads newest → oldest
        entries: List[Tuple[str, Dict[str, str]]] = await r.xrevrange(
            stream_key, count=count
        )
    except Exception:
        return []

    result: List[Transaction] = []
    for _stream_id, fields in entries:
        try:
            result.append(Transaction.from_redis_dict(fields))
        except Exception:
            continue
    return result


async def read_stream_from(
    last_id: str = "0",
    count: int = 50,
    stream_key: str = STREAM_KEY,
    block_ms: Optional[int] = None,
) -> Tuple[str, List[Transaction]]:
    """
    Read entries from the stream after `last_id`.

    Args:
        last_id  : Stream ID to read after (use "0" for all, "$" for only new).
        count    : Maximum entries to return.
        block_ms : If set, block for this many ms waiting for new entries.

    Returns:
        (new_last_id, [Transaction, ...])
    """
    r = await get_redis()
    try:
        if block_ms is not None:
            results = await r.xread(
                {stream_key: last_id}, count=count, block=block_ms
            )
        else:
            results = await r.xread({stream_key: last_id}, count=count)
    except Exception:
        return last_id, []

    if not results:
        return last_id, []

    txs: List[Transaction] = []
    new_last_id = last_id
    for _key, entries in results:
        for stream_id, fields in entries:
            new_last_id = stream_id
            try:
                txs.append(Transaction.from_redis_dict(fields))
            except Exception:
                continue

    return new_last_id, txs


async def stream_length(stream_key: str = STREAM_KEY) -> int:
    """Return the number of entries currently in the stream."""
    r = await get_redis()
    try:
        return await r.xlen(stream_key)
    except Exception:
        return 0


async def publish_transaction(tx: Transaction, stream_key: str = STREAM_KEY) -> None:
    """Publish a single transaction to the Redis stream."""
    r = await get_redis()
    await r.xadd(stream_key, tx.to_redis_dict(), maxlen=5000)
