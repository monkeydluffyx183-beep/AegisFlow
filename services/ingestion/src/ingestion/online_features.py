"""Atomic Redis feature updates compiled from the M2 feature definitions.

One transaction executes one Lua script. The script uses transaction event time, integer
minor units, ``SET seen:txn:{id} NX`` idempotency, and Welford profile-before-update
semantics. Every number crosses Redis as a string so Redis/Lua numeric conversion does not
silently truncate floats.
"""

from __future__ import annotations

from typing import Any

from aegis_ml.features import definitions as D

SCRIPT = r"""
local function fmt(x) return string.format('%.17g', x) end
local ts  = tonumber(ARGV[2])
local amt = tonumber(ARGV[3])
local ttl = tonumber(ARGV[9])
if not redis.call('SET', KEYS[1], '1', 'NX', 'EX', ttl) then
  return {'dup'}
end
local out = {}
local member = ARGV[1] .. '|' .. ARGV[3]

-- Velocity windows are (ts - w, ts], current transaction included.
for i = 1, 4 do
  local k = KEYS[2 + i]
  local cut = ts - tonumber(ARGV[9 + i])
  local field = 'sum' .. i
  local s = tonumber(redis.call('HGET', KEYS[2], field)) or 0
  local expired = redis.call('ZRANGEBYSCORE', k, '-inf', fmt(cut))
  for _, m in ipairs(expired) do
    s = s - tonumber(string.match(m, '|(%-?%d+)$'))
  end
  if #expired > 0 then redis.call('ZREMRANGEBYSCORE', k, '-inf', fmt(cut)) end
  redis.call('ZADD', k, fmt(ts), member)
  s = s + amt
  redis.call('HSET', KEYS[2], field, fmt(s))
  redis.call('EXPIRE', k, ttl)
  out[#out + 1] = fmt(redis.call('ZCARD', k))
  out[#out + 1] = fmt(s)
end

local function distinct(k, w, m, has)
  redis.call('ZREMRANGEBYSCORE', k, '-inf', fmt(ts - w))
  if has == '1' then redis.call('ZADD', k, fmt(ts), m) end
  redis.call('EXPIRE', k, ttl)
  return redis.call('ZCARD', k)
end
local dw, sw = tonumber(ARGV[14]), tonumber(ARGV[15])
out[#out + 1] = fmt(distinct(KEYS[7], dw, ARGV[7], ARGV[4]))
out[#out + 1] = fmt(distinct(KEYS[8], dw, ARGV[8], ARGV[5]))
if ARGV[4] == '1' then out[#out + 1] = fmt(distinct(KEYS[9], sw, ARGV[6], '1'))
else out[#out + 1] = '0' end
if ARGV[5] == '1' then out[#out + 1] = fmt(distinct(KEYS[10], sw, ARGV[6], '1'))
else out[#out + 1] = '0' end

-- Amount z-score from profile BEFORE this amount, then Welford update.
local h = redis.call('HMGET', KEYS[2], 'n', 'mean', 'm2', 'last_ts')
local n = tonumber(h[1]) or 0
local mean = tonumber(h[2]) or 0
local m2 = tonumber(h[3]) or 0
local x = amt / 100
local z = 0
if n >= 2 then
  local sd = math.sqrt(m2 / (n - 1))
  if sd > 0 then z = (x - mean) / sd end
end
local since = -1
if h[4] then since = ts - tonumber(h[4]) end
n = n + 1
local delta = x - mean
mean = mean + delta / n
m2 = m2 + delta * (x - mean)
redis.call('HSET', KEYS[2], 'n', fmt(n), 'mean', fmt(mean), 'm2', fmt(m2), 'last_ts', fmt(ts))
redis.call('EXPIRE', KEYS[2], ttl)
out[#out + 1] = fmt(z)
out[#out + 1] = fmt(since)
return out
"""
# Backwards-compatible name used by early M1 examples.
VELOCITY_UPDATE_LUA = SCRIPT


def keys_for(transaction: dict[str, Any]) -> list[str]:
    account = str(transaction["account_id"])
    return (
        [f"seen:txn:{transaction['id']}", f"feat:acct:{account}"]
        + [f"vel:acct:{account}:{label}" for label in D.WINDOWS]
        + [f"dist:acct:{account}:dev", f"dist:acct:{account}:ip", f"share:dev:{transaction.get('device_id') or '-'}", f"share:ip:{transaction.get('ip_id') or '-'}"]
    )


def args_for(transaction: dict[str, Any]) -> list[str]:
    timestamp = transaction["ts"]
    return (
        [
            str(transaction["id"]),
            repr(D.epoch_seconds(timestamp)),
            str(int(transaction["amount_minor"])),
            "1" if transaction.get("device_id") else "0",
            "1" if transaction.get("ip_id") else "0",
            str(transaction["account_id"]),
            str(transaction.get("device_id") or ""),
            str(transaction.get("ip_id") or ""),
            str(D.KEY_TTL_S),
        ]
        + [str(window) for window in D.WINDOWS.values()]
        + [str(D.DISTINCT_WINDOW_S), str(D.SHARE_WINDOW_S)]
    )


def redis_keys(account_id: str) -> tuple[str, str]:
    """M1 compatibility helper; M2 exposes all feature keys through ``keys_for``."""
    account = str(account_id).replace(":", "_")
    return f"feat:acct:{account}", f"vel:acct:{account}:7d"


def read_graph(redis_client: Any, account_id: str) -> dict[str, float]:
    values = redis_client.hmget(f"gfeat:acct:{account_id}", *D.GRAPH_FIELDS.values())
    return {name: (float(value) if value is not None else D.BY_NAME[name].default) for name, value in zip(D.GRAPH_FIELDS, values)}


def update(redis_client: Any, transaction: dict[str, Any]) -> dict[str, float] | None:
    """Run the one atomic script and return the full 19-feature row; ``None`` means duplicate."""
    result = redis_client.register_script(SCRIPT)(keys=keys_for(transaction), args=args_for(transaction))
    result = [item.decode() if isinstance(item, bytes) else item for item in result]
    if result == ["dup"]:
        return None
    row = dict(zip(D.LUA_OUTPUTS, (float(value) for value in result)))
    row.update(D.calendar(transaction["ts"]))
    row.update(read_graph(redis_client, transaction["account_id"]))
    return {name: row[name] for name in D.FEATURE_LIST}
