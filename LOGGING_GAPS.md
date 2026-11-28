# Logging gaps

Known gaps in the API's logging, roughly in the order they're worth fixing. A logging review found these alongside four more serious problems, which have since been fixed: secrets leaking into logs, error logs that didn't say where a failure happened, raw database errors logged twice, and authentication failures that weren't logged properly.

## Conventions to keep

The fixes so far established a few rules. New logging should follow them:

* **No user identifiers in logs.** That means Clerk IDs, email addresses, list names, and anything else a user typed or that identifies them. Exception messages can contain these values (MySQL errors echo row values, for example), so worker failures log only the error type, MySQL error codes, and a code-location stack.
  * **Exception: search queries and search options may be logged,** since they're the main thing needed to debug search. This covers only what's sent to the search endpoint, not other user-typed text such as list names, and never anything tied to who the user is. Log them with `!r` so a query containing a newline can't forge a log line.
* **Use `_error_log_fields(e)` for worker failures.** It's defined in `BaseWorker` and produces `error_type=… errno=… sqlstate=… stack=ItemWorker.py:add_item:66`. Outside the workers, `exception_stack(e)` in [Utilities/ExceptionStack.py](Utilities/ExceptionStack.py) gives the same stack on its own.
* **Pass anything that might contain a request URL through `redact_secrets()`** ([Utilities/RedactSecrets.py](Utilities/RedactSecrets.py)) before logging it. TMDB and Discogs take their API keys as query parameters, and `requests` puts the full URL into its exception messages.
* **Log each failure once,** in the method that handles it.

## 1. No request-level logging or request IDs

**Priority: medium**

Nothing logs a summary line for each request, with method, path, status code and duration. [api.py](api.py) has no `before_request` or `after_request` hooks and no error handlers.

The workers deliberately leave user identifiers out of their log lines. That means there's also nothing to connect the lines written while handling a single request. When several requests run at once, you can't tell which worker log lines belong together, or which request produced a given error.

**Suggested fix:** generate a request ID at the start of each request (or reuse Lambda's `aws_request_id` when deployed there). Attach it to every log record, for example with a `logging.Filter` that reads it from `flask.g`. Log one summary line when each request finishes. A request ID identifies no one, so it fits the rule above.

## 2. External API failures are mostly invisible

**Priority: medium**

`SearchWorker` calls seven external APIs, and their failures are hard to see:

* **No HTTP status checks.** No call checks the status code. An error page or a rate-limit response fails later, during parsing, with an unrelated-looking exception.
* **Results dropped silently.** `board_game_detail_lookup` and `rpg_detail_lookup` return `{}` for any item they can't parse, and `lookup_board_game` and `lookup_rpg` drop those without logging (`if lookup:`). If BoardGameGeek rate-limits the detail requests, the search can log `Search succeeded … item_count=0` with no sign that anything went wrong.
* **No detail on failed detail lookups.** When one detail lookup raises, the whole search fails as `step=fetch_details`, without saying which item failed or what status code came back.
* **No per-API timing.** Only the total search duration is logged. With several requests per search, you can't see which API was slow.
* **No timeouts.** No outbound request has one, so an API that can't be reached hangs the request instead of failing it.

**Suggested fix:**
* Check the status code on each response and log the status and the API name when it isn't a success.
* Log a warning with a count when detail lookups are dropped.
* Add a timeout to every outbound request. Jikan accepts a custom `requests.Session`. The Discogs client has no timeout option, so it needs a small custom fetcher.

## 3. A failed media type load is never retried

**Priority: medium (also a bug)**

`BaseWorker._initialize_pool` sets `_pool_initialized = True` *before* calling `_load_media_type_mappings()`. If loading the mappings fails, the error is logged once and the pool is never initialized again. Every later `add_item` then fails as an unknown media type. These failures now log `stack=ItemWorker.py:add_item:…`, which points at the media type check. But the root cause, the failed load, only appears once, possibly much earlier.

The test suite tracks this as bug B3, in the xfailed test `test_failed_mapping_load_is_retried` in [tests/unit/test_base_worker.py](tests/unit/test_base_worker.py).

Two related gaps:

* `_initialize_pool` only catches MySQL's `Error`. A missing key in `secrets` or a malformed `local_db_config.json` raises something else, which surfaces later in a worker's log as a confusing `KeyError`.
* An empty `media_types` table logs `Loaded media type mappings: {}` at INFO with no warning.

**Suggested fix:**
* Only mark the pool initialized after the mappings load, so a failed load is retried on the next request.
* Catch configuration errors in `_initialize_pool` and log which setting is missing, without its value.
* Warn when no media types are loaded.

## 4. Client errors (400s) are logged inconsistently

**Priority: low**

Most 400 responses in [api.py](api.py) aren't logged at all: missing required fields, a non-integer `page`, a request body of the wrong shape. The search route is the exception. It logs its 400s (no `media_type`, or an unrecognized one) at ERROR, which puts client mistakes alongside real server failures.

There are also two INFO lines that run before the request has been validated, in `lookup_data` and `get_collection`.

**Suggested fix:** log every 400 at INFO or WARNING with the route and the reason, never at ERROR. Once item 1 is done, the request summary line covers most of this.

## 5. Smaller consistency issues

**Priority: low**

* **Root logger instead of module loggers.** `SearchWorker` and `api.py` log through the root `logging` module instead of a module logger, unlike the other workers, so their lines don't say which module wrote them.
* **"Search crashed" has no exception information.** `_log_search_result` logs it from a `finally` block, which has no access to the exception. Every lookup catches its own exceptions, so this line is rarely reached.
* **The production config source isn't logged.** `_initialize_pool` logs when it uses `local_db_config.json`, but logs nothing when it reads the database settings from `secrets`.
* **Dead code.** [Utilities/ValidateRequestInput.py](Utilities/ValidateRequestInput.py) isn't imported anywhere, so its logging never runs.
