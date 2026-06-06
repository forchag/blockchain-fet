from policy_cache import PolicyCache


def test_policy_cache_expiry():
    now = [100.0]
    cache = PolicyCache(ttl_seconds=5, clock=lambda: now[0])
    cache.set("k", "GRANT")
    assert cache.get("k") == "GRANT"
    now[0] = 106.0
    assert cache.get("k") is None


def test_policy_cache_invalidation():
    cache = PolicyCache(ttl_seconds=300)
    cache.set("a", "GRANT")
    cache.set("b", "DENY")
    cache.invalidate("a")
    assert cache.get("a") is None
    assert cache.get("b") == "DENY"
    cache.invalidate_all()
    assert cache.get("b") is None
