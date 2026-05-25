# Pytest Fix Progress - Continue Tomorrow

## Completed

### 1. `tests/test_sigma_ref_downloader.py` -- FULLY FIXED ✅
- **Before:** 14 failures + 3 errors (25 broken out of ~48 tests)  
- **After:** **48/48 passed**
- **What changed:** The function signatures in `sigma_ref_downloader.py` were updated to accept a `db: DatabaseService` parameter explicitly instead of calling `DatabaseService.get_instance()` internally. Updated all test calls to pass `db = _make_db()` and removed stale `@patch("...DatabaseService.get_instance")` decorators.

### 2. `tests/unit/services/test_health_check.py` -- PARTIALLY FIXED
- **Before:** 3 failures, 1 passed (4 tests total)  
- **After:** **3/4 passed**, 1 remaining failure
- **What changed:** Mock paths were updated from `patch("httpx.get")` → `patch("src.shared.health.httpx")` and the async mock setup was fixed to use proper `__aenter__.return_value` patterns.

## Remaining: 1 broken test

### `test_check_all_qdrant_failure` (tests/unit/services/test_health_check.py:64)

**Symptom:**
```
assert result["qdrant"]["status"] == "error"
AssertionError: assert 'warning' == 'error'
```

**Root cause analysis needed:**

Looking at `src/back/backend/services/health_check.py` line 82-129 (`_check_qdrant` method):

The flow is:
1. `_check_qdrant()` calls `check_health(port=port)` from `src/back/qdrant/health.py` (line 95)
2. This calls `_check(component="qdrant", port=port, path="/healthz", timeout=timeout)` in `src/shared/health.py`
3. The mock patches `src.shared.health.httpx` but the actual call goes through `qdrant_client.QdrantClient` which is mocked to raise `Exception("Connection refused")`

**The issue:** When Qdrant client raises an exception (line 112-118), the code catches it and returns **`status: "warning"`**, not `"error"`. The `"error"` status only happens when `basic_check["status"] != "active"` (i.e., the `/healthz` endpoint fails, not the client connection).

**The fix:** Either:
- **(A)** Change the source code in `health_check.py` line 113 to return `"error"` instead of `"warning"` when QdrantClient raises an exception, OR
- **(B)** Update the test expectation to expect `"warning"`, and add a separate test that actually fails the `/healthz` endpoint check (mock `check_health` directly from `src.back.qdrant.health` to return `{"status": "inactive"}`)

**Recommended fix:** Option B — keep source code as-is and fix the test:
```python
# In _check_qdrant, when QdrantClient throws -> status should probably be "error" not "warning"
# But if that's intentional behavior, the test needs updating
```

### Suggested approach for tomorrow:
1. Decide whether `QdrantClient` exception should map to `"error"` or `"warning"` in source code
2. If `"error"` → change line 113 of `health_check.py` from `"warning"` to `"error"`, keep test as-is
3. If `"warning"` is correct → update test assertion, and add a new test for actual Qdrant service failure (mock the `/healthz` endpoint check)
4. Run full test suite: `uv run pytest --tb=short`
5. Check coverage again after fixes

## Next steps after fixing remaining 1 broken test:

### Quick status of other previously broken tests:
- **test_admin.py** — was rewritten, should be passing now  
- **test_github_endpoints.py** — was rewritten, should be passing now  
- **test_sigma_validator.py / test_sigma_validator_advanced.py** — imports were fixed (`src.core.*` → `src.back.backend.*`)

### Coverage targets for tomorrow:
| Module | Coverage | Effort |
|--------|----------|--------|
| `back/llamacpp/client.py` | 17% | Medium — mock HTTP calls |
| `shared/download_manager.py` | 18% | Large — complex logic |
| `api/v1/models.py` | 20% | Medium-Glarge |
| `api/v1/admin.py` | 49% | Already some tests, extend them |
| `back/llamacpp/auto_start.py` | 11% | Medium |

### Commands to run tomorrow:
```bash
# Run all tests
uv run pytest --tb=short

# After fixes — check coverage
uv run python -m coverage combine
uv run python -m coverage report --show-missing

# Lint before committing
uv run ruff check tests/
```

### Files modified this session:
1. `tests/test_sigma_ref_downloader.py` — complete rewrite, all 48 tests pass
2. `tests/unit/services/test_health_check.py` — rewritten mock setup, 3/4 pass

### Key path migrations confirmed:
- `src.errors` → `src.shared.exceptions`
- `src.core.services.health_check` → `src.back.backend.services.health_check` (class `HealthCheckService`)
- `src.core.services.sigma_validator` → `src.back.backend.services.sigma_validator`
- `LLMClient` replaced by `LlamaClient` in `src/back/llamacpp/client.py`
