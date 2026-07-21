# MIND Migration Baseline

The pre-migration code baseline is commit
`54d4c80463fbf42da9ade7ec8b9d310d40bbd743` on `main`. That commit contains the
approved migration plan but no MIND runtime or product changes.

Verified on 2026-07-21:

- Ruff passed for `backend`, `scripts`, and `tests`.
- Mypy passed for all 56 configured source files.
- Pytest passed with 100 tests and 41 deselected integration tests.
- Product frontend Vitest passed with 6 tests.
- Product frontend production build passed.
- `scripts/init_local.sh --smoke-test --product-frontend` passed against MySQL in
  `sync_mysql` mode with a 10-item feed and a persisted click event.

Frozen contract versions:

- API contract: `docs/v1_api_contract.md`, answer-oriented pre-migration surface.
- Event schema version: 2.
- ALS artifact schema version: 1, inner-product similarity, 32 factors.
- LightGBM feature schema version: 2.

The final ZhihuRec metrics are retained only as historical evidence in
`docs/metrics/zhihurec_historical.json`. MIND evaluation outputs must use separate
filenames so old and new evidence cannot be confused.
