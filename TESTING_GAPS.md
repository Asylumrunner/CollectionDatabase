# Testing gaps

Known gaps and problems in the test suite, roughly in the order they're worth fixing. They come from a review of the suite in November 2026. At the time, every test passed: 570 passed and 46 xfailed across both tiers, in about 100 seconds. The unit tier gives 99% line and branch coverage of the app code, and running the unit files in reverse order changes nothing. So the problems below are about what the suite doesn't enforce, not about tests that fail.

## Conventions to keep

The suite already follows these rules. New tests should too:

* **Known bugs are strict xfails.** Mark them `@pytest.mark.xfail(reason="B#: …")`, describing the *correct* behaviour. `xfail_strict = true` in [pytest.ini](pytest.ini) turns a fix into an `XPASS(strict)` failure, which is the reminder to remove the marker.
* **A fixture error on an xfail test counts as a failure.** The hook in [tests/conftest.py](tests/conftest.py) does this, so tests that never ran (say, because Docker is down) can't pass as expected failures.
* **The unit tier is fully offline.** `pytest_socket` blocks the network, `responses` stubs HTTP, and `FakeDB` stands in for MySQL.
* **The functional tier only touches `collection_test`.** It only connects to localhost (or `TEST_DB_HOST`), and `assert_test_database` runs before any truncate.
* **Real secrets are never loaded.** A fake `Workers.secrets` module is installed before any app code is imported.
* **Auth runs for real in functional tests.** Only Clerk's signing-key (JWKS) download is stubbed. Tokens are real RS256 JWTs, and webhooks carry real Svix signatures.

## 1. Passing tests assert buggy behaviour

**Priority: high**

Several passing tests rely on behaviour that known bugs cause. When those bugs are fixed, these tests go red, so a fix breaks tests that aren't marked for it. That undoes the point of strict xfails.

* [tests/functional/test_resilience.py:40](tests/functional/test_resilience.py#L40) (`test_failing_requests_dont_leak_connections`) requires `GET /collection` to return **500** for a user with no `users` row. But `test_user_without_a_row_gets_a_404` in [tests/functional/test_collection.py](tests/functional/test_collection.py) is the B18 xfail, which says that case should be **404**. These two contradict each other.
* The same test, at [lines 38-39](tests/functional/test_resilience.py#L38-L39), requires 500 for `release_year="not a year"` and for an unknown `media_type`. With input validation in place, both should be 400s.
* `test_db_failure_doesnt_leak_a_traceback` in [tests/functional/test_collection.py](tests/functional/test_collection.py) also uses `release_year="not a year"` to force a 500.
* `test_failure_partway_leaves_no_rows_and_retry_succeeds` (in the same file) uses a 65-character genre to force a failure partway through a write. That only works while lengths aren't validated (the B17 family). Once they are, the request is rejected before anything is written, and the rollback path goes untested without anyone noticing.

**Suggested fix:** trigger 500s with failures the app should always treat as server errors, not with invalid input. For example, have the database drop partway through the request, or monkeypatch a worker method so it raises. Keep separate tests for what invalid input *should* return, marked xfail against the bug they depend on.

## 2. No CI

**Priority: high**

Nothing runs the tests automatically. There's no `.github/` directory and no other CI config. The 85% coverage minimum and the strict xfails only take effect when someone remembers to run `pytest`.

**Suggested fix:** add a GitHub Actions workflow. Run the unit tier on every push and the functional tier on pull requests. GitHub's Ubuntu runners have Docker, so the testcontainers path works there as is. Run it on the Python version picked in gap 4.

## 3. Open bugs tracked only as xfails, with no registry

**Priority: high (these are app bugs, not test gaps)**

Twenty-two known bugs are tracked as 46 xfailed tests. Tests cite bug IDs (`B19e`) and test IDs (`U-ITEM-3`, `F-RES-4`), and one comment mentions "the plan's first draft", but nothing in the repo defines these IDs. Today the xfail reason strings are the only list (`python -m pytest -rx`). B1, B4, B6, B8, B9, B15 and B21 don't appear anywhere, so it's unclear whether they were fixed or dropped.

The open bugs, from the xfail reasons:

| Bug | Problem | Where it's tested |
|---|---|---|
| **B5** | **Any non-empty `SKIP_AUTH`, including `false` or `0`, disables authentication. This is a security bug.** | unit `test_auth.py`, functional `test_auth.py` |
| **B20** | An IGDB token failure at import takes down the whole API, not just video game search | functional `test_resilience.py` |
| **B16** | Adding to a list that doesn't exist creates the catalog item before list ownership is checked | functional `test_lists.py` |
| B2 | On a cold pool, `check_item` reads the media-type mappings before they're loaded, so an existing item looks new | unit `test_item_worker.py`, functional `test_resilience.py` |
| B3 | The pool is marked initialized before the mappings load, so a failed load is never retried (also gap 2 in [LOGGING_GAPS.md](LOGGING_GAPS.md)) | unit `test_base_worker.py` |
| B14 | Pool state is assigned to `cls`, so each worker subclass builds its own pool instead of sharing one | unit `test_base_worker.py` |
| B7 | `created_by` isn't validated, so a string is iterated one character at a time | unit `test_routes.py` |
| (none) | Non-dict elements in a bulk request aren't validated, so the `TypeError` becomes a 500 | unit `test_routes.py` |
| B10 | A page number below 1 isn't rejected, becomes a negative `OFFSET` and fails as a SQL error | unit `test_routes.py`, functional `test_lists.py` |
| B11 | A bulk add where every item fails still reports `passed=True`, and the same item twice in one request violates the primary key | unit `test_item_worker.py`, functional `test_collection.py` |
| B12 | Null first and last names produce the username `'None None'` | unit `test_routes.py`, functional `test_webhooks.py` |
| B17 | Summaries over 1024 characters fail with a 500 (BoardGameGeek descriptions can be longer). List names aren't validated: too long is a 500 and blank is accepted | functional `test_collection.py`, `test_lists.py`, `test_search.py` |
| B18 | A valid token with no `users` row is a 500 instead of a 404 | functional `test_collection.py` |
| B19b | A null TMDB `poster_path` is formatted into the image URL | unit `test_search_lookups.py` |
| B19c | An empty TMDB `release_date` becomes an empty-string year, which the SMALLINT column rejects | unit `test_search_lookups.py`, functional `test_search.py` |
| B19d | Anime with no English title get a null title | unit `test_search_lookups.py` |
| B19e | RPG results are plain dicts rather than `Item`s (no xfail; the tests read either shape) | unit `test_search_lookups.py` |
| B19f | An IGDB game with no release date is reported as 1970 (1969 in US time zones) | unit `test_search_lookups.py` |
| B19g | `next_page` keeps incrementing when a search returns no results, for all seven media types | unit `test_search_lookups.py` |
| B19h | BoardGameGeek lookups ignore the page, so every page is identical | unit `test_search_lookups.py` |
| B19i | One malformed BoardGameGeek or RPGGeek record fails the whole search | unit `test_search_lookups.py` |
| B22 | The installed Discogs client's `Master` model has no year or notes, so albums lose both | functional `test_search.py` |

B13 (raw database messages, which can contain user values, being logged) seems to be fixed: `test_raw_database_messages_are_not_logged` in [tests/unit/test_base_worker.py](tests/unit/test_base_worker.py) passes.

**Suggested fix:** fix B5 first, then B20 and B16. Either commit the original test plan or keep this table up to date as the bug registry, and record what happened to the missing IDs.

## 4. Tests run on a different Python version from deployment

**Priority: medium**

The tests were run on Python 3.10 (the local venv). The [Dockerfile](Dockerfile) uses `python:3.9-slim-bullseye`, and [zappa_settings.json](zappa_settings.json) targets 3.12. Zappa is being retired, so Docker is presumably the deployment going forward, but Python 3.9 reached end-of-life in October 2025. pytest 9 also appears to have dropped 3.9 support, so `requirements-dev.txt` probably won't install in that image.

**Suggested fix:** pick one supported Python version, update the Dockerfile to it, and make CI and the local venv use it too.

## 5. No checks against the real third-party APIs

**Priority: medium**

All seven search sources are stubbed with fixture files in [tests/fixtures/](tests/fixtures/), recorded at some point in the past. If an API changes its response format, nothing notices until users do. B22 shows this kind of drift has already happened.

**Suggested fix:** add one small live smoke test per source, behind an opt-in marker (for example `@pytest.mark.live`, left out of default runs). Run them by hand or nightly with real credentials from CI secrets. They should only check the shape of the response, not specific values.

## 6. The list of authenticated routes is maintained by hand

**Priority: medium**

`test_no_token_is_rejected_on_every_route` in [tests/functional/test_auth.py](tests/functional/test_auth.py) checks the hard-coded `AUTHENTICATED_ROUTES` list. It currently matches all 15 authenticated routes in [api.py](api.py), but a new route added without `@authenticate_request` would never be checked.

**Suggested fix:** build the list from `app.url_map`, minus an explicit list of public routes (`/` and `/webhooks/clerk`), filling in path parameters with dummy values.

## 7. `FakeDB` silently accepts queries it wasn't set up for

**Priority: medium**

In [tests/helpers.py](tests/helpers.py), SQL that matches no scripted fragment returns no rows, with no error. A typo in a fragment, or a query that was renamed, can turn a test into one that passes without checking anything.

**Suggested fix:** add an optional strict mode, or make it the default, that raises on unmatched SQL. Tests that expect an empty result then register it explicitly, for example `db.on("SELECT id FROM items", rows=[])`.

## 8. Coverage configuration

**Priority: low**

* **Stale and dead entries.** [.coveragerc](.coveragerc) excludes `Collections/*`, which doesn't exist. It also excludes [Utilities/ValidateRequestInput.py](Utilities/ValidateRequestInput.py) and [Workers/CollectionWorker.py](Workers/CollectionWorker.py), which nothing imports. Delete the dead code rather than excluding it. `ValidateRequestInput` sets a 512-character summary limit, which contradicts the 1024 behind B17, and could mislead whoever adds validation.
* **Test files are measured too.** With a plain `--cov=.`, the test files count toward the total. The README's narrower command is right, but nothing makes it the default.
* **No branch coverage by default.** Branch coverage is also 99% today, but nothing keeps it there.
* **The functional tier is never measured.** You can't see code that's covered only through mocks.

**Suggested fix:** in `.coveragerc`, set `source = api, Workers, Utilities, DataClasses` and `branch = True` under `[run]`, and remove the stale `omit` entries. Optionally, collect functional coverage too and combine the two reports.

## 9. Smaller gaps

**Priority: low**

* **Uncovered code paths.** The webhook decorator's unexpected-error branch ([Utilities/VerifyClerkWebhook.py:60-62](Utilities/VerifyClerkWebhook.py#L60-L62)) and two branches in `BaseWorker` startup ([Workers/BaseWorker.py](Workers/BaseWorker.py) lines 31 and 45) have no tests.
* **The end-to-end test is thin.** [tests/functional/test_journey.py](tests/functional/test_journey.py) covers a single book. A second run with a source that makes follow-up detail requests (movie or board game), plus a bulk add, would be cheap to add.
