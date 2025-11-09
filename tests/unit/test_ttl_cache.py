import time

from application.ttl_cache import TTLCache, get_cache_metrics


def test_ttl_cache_set_get_and_expire():
    cache = TTLCache("ttl_test")

    # Initial miss
    assert cache.get("alpha") is None

    # Store value and ensure deep copy semantics
    payload = {"value": 42}
    cache.set("alpha", payload, ttl=0.1)

    cached = cache.get("alpha")
    assert cached == {"value": 42}

    # Mutating returned object must not affect cache
    cached["value"] = 0
    assert cache.get("alpha") == {"value": 42}

    # Expire entry
    time.sleep(0.12)
    cache.purge_expired()
    assert cache.get("alpha") is None


def test_ttl_cache_metrics_tracking():
    cache = TTLCache("metrics_test")

    cache.set("key", {"foo": "bar"}, ttl=0.05)
    assert cache.get("key") is not None
    time.sleep(0.06)
    cache.get("key")  # Expired miss

    metrics = get_cache_metrics()
    assert metrics["hits"]["metrics_test"] >= 1
    assert metrics["misses"]["metrics_test"] >= 1
    assert metrics["items"]["metrics_test"] >= 0

