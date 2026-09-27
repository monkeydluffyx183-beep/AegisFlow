"""Atomic online feature update contract.

The Lua text is kept here as the source of truth for a Redis adapter. The local scorer uses
an equivalent in-memory implementation so unit tests and the browser demo have no infra
requirement.
"""

VELOCITY_UPDATE_LUA = r"""
local key = KEYS[1]
local event_key = KEYS[2]
local now = tonumber(ARGV[1])
local amount = tonumber(ARGV[2])
local tx_id = ARGV[3]
redis.call('HINCRBY', key, 'velocity_1h', 1)
redis.call('HINCRBY', key, 'velocity_24h', 1)
redis.call('HSET', key, 'last_amount', amount, 'last_tx_id', tx_id)
redis.call('ZADD', event_key, now, tx_id)
redis.call('EXPIRE', key, 604800)
redis.call('EXPIRE', event_key, 604800)
return 1
"""


def redis_keys(account_id: str) -> tuple[str, str]:
    safe = account_id.replace(":", "_")
    return f"feat:acct:{safe}", f"vel:acct:{safe}:7d"
