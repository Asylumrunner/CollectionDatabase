# CollectionDatabase
A database application for cataloging my collection of physical media, powered by Python, Flask, MySQL, Clerk, AWS Lambda, Zappa, and a collection of APIs

## Table of Contents
1. [Background](https://www.github.com/Asylumrunner/CollectionDatabase#background)
2. [Tech Stack](https://www.github.com/Asylumrunner/CollectionDatabase#tech-stack)
3. [APIs In Use](https://www.github.com/Asylumrunner/CollectionDatabase#apis-in-use)
4. [Architecture](https://www.github.com/Asylumrunner/CollectionDatabase#architecture)
5. [Local Development](https://www.github.com/Asylumrunner/CollectionDatabase#local-development)
6. [Running Tests](https://www.github.com/Asylumrunner/CollectionDatabase#running-tests)
7. [Endpoint Documentation](https://www.github.com/Asylumrunner/CollectionDatabase#endpoint-documentation)

## Background
Like a lot of people with nerdy sensibilities, I own a lot of physical media, from video games to movies to books to tabletop RPGs to board and card games. I've found that having a large digital record of this collection is fairly useful for a variety of reasons, including but not limited to:

* Keeping track of all of this stuff when I take it all on a cross-country move
* Knowing what stuff I have while I'm out and about shopping so I don't buy a book I already own again like a humongous doofus
* Being able to hand a list of games/movies/books to a friend and ask "what do you recommend I play/watch/read next?" instead of having to try to hastily remember all the stuff you own
* Having programmatic access to this collection could help another project in which I build a recommendation engine, using my own preferences as a data set
* I dunno I like writing APIs

So, for all of these reasons, I built this API, designed to be able to look up collection items (the clumsy catch-all term I'm going to use, as a more official-sounding synonym for "my crap"), and offer CRUD operations with a MySQL database to maintain a digital signature of this collection. Each user signs in through Clerk and gets their own collection, plus as many named lists (wishlists, "lend to Dave", whatever) as they want.

### Why Don't You Just Buy Digital Copies?
Because I'm a psychopath who likes having a big physical pile of stuff.

## Tech Stack
This project is written in Python 3 (the Lambda deployment runs Python 3.12), with the RESTful API scaffolding provided by Flask 3. Data lives in a MySQL 8 database, whose schema is in `SQL/database.sql`, accessed through a shared `mysql-connector-python` connection pool.

User accounts are handled by [Clerk](https://clerk.com/). The API verifies a Clerk session token on every request, and Clerk tells the API about new and deleted users through webhooks, which are signed with [Svix](https://www.svix.com/) and verified before they're processed.

This project was designed to run in the cloud, using AWS API Gateway to connect to the API, deployed as an AWS Lambda function via Zappa (see `zappa_settings.json`). However, it runs perfectly fine on local as well, either directly with `python api.py` or in Docker with the provided `Dockerfile`. Retrieval of data for all of the various collection items is handled by a bundle of miscellaneous public APIs, described below.

### Configuration
Credentials are read from `Workers/secrets.py`, which is gitignored and has to be created by hand. It defines a single dictionary called `secrets`:

| Key | Used for |
|---|---|
| `IGDB_Client_ID`, `IGDB_Client_Secret` | Twitch app credentials for IGDB (video games) |
| `BGG_API_Key` | BoardGameGeek and RPGGeek (board games, RPGs) |
| `MovieDB_Key` | The Movie Database (movies) |
| `Discogs_Token` | Discogs user token (albums) |
| `CLERK_SECRET_KEY` | Verifying Clerk session tokens |
| `CLERK_WEBHOOK_SECRET` | Verifying Clerk webhook signatures |
| `database_endpoint`, `collection_database_name`, `database_username`, `database_password` | The MySQL database, when `local_db_config.json` is absent |

OpenLibrary and Jikan don't need credentials.

For local development, create `local_db_config.json` in the repo root (also gitignored). When it exists, it takes priority over the database keys in `secrets.py`:
```json
{
  "host": "localhost",
  "port": 3306,
  "database": "collectionDB",
  "username": "root",
  "password": "yourpassword"
}
```

Two environment variables help with local development:

* `SKIP_AUTH` - when set to any non-empty value, Clerk verification is skipped and every request is treated as coming from the user in `DEV_USER_ID`
* `DEV_USER_ID` - the Clerk user ID to act as when `SKIP_AUTH` is set. Defaults to `test_user_dev`. A row with this `clerk_user_id` must exist in the `users` table, or every endpoint that touches user data will fail

## APIs In Use
Every search goes to exactly one of these APIs, picked by the `media_type` of the request:

| `media_type` | Source |
|---|---|
| `book` | OpenLibrary |
| `movie` | The Movie Database |
| `video_game` | IGDB |
| `board_game` | BoardGameGeek |
| `rpg` | RPGGeek |
| `anime` | Jikan (MyAnimeList) |
| `album` | Discogs |

  * [IGDB](https://api-docs.igdb.com/) - The Internet Game Database, run by Twitch, is now the source for video game data (this project originally used Giant Bomb). Queries are written in IGDB's own query language and POSTed to the API, which makes filtering by platform and release date straightforward. Authentication goes through a Twitch app: the client ID and secret are exchanged for an access token when the API starts up.
  * [BoardGameGeek](https://boardgamegeek.com/wiki/page/BGG_XML_API2) - BGG is a monolithic database for information on tabletop games, completely incomparable across the board. While their API is XML-based (I'd prefer JSON for consistency's sake), there's just no competing with their data. The API now requires a bearer token.
  * [RPGGeek](https://rpggeek.com/wiki/page/BGG_XML_API2) - BGG's sister site for tabletop RPGs, which runs the same XML API (and accepts the same API key). Tabletop RPGs are looked up here instead of on BGG proper.
  * [OpenLibrary](https://openlibrary.org/developers/api) - This project originally utilized GoodReads' API, but on top of them depracating said (not very good, frankly) API, GoodReads as a platform is totally stagnant and obviously not interested in being a good steward of data. OpenLibrary, meanwhile, totally is invested in just that, and also it returns its data in JSON because it's the 21st century and not 1642, *Amazon*.
  * [The Movie Database](https://developers.themoviedb.org/3/getting-started/introduction) - The Movie Database, as its pleasantly on-the-nose name suggests, is a massive repository of data about movies, which I'm using to store my collection of physical movies. It also returns JSON, which is delightful.
  * [Discogs](https://www.discogs.com/developers/) - A massive repository of information for released music, and my source of truth for tracking CDs as well as vinyls. Discogs' information is generally limited towards things that have gotten a physical release (excluding things such as Soundcloud or digital-only Bandcamp releases), but since this project is built to handle my physical collection, this constraint is a non-issue for me. Searches are run against Discogs "masters" (the album as a whole, rather than one specific pressing).
  * [Jikan](https://jikan.moe/) - A FOSS Restful API built on top of the massive collection of anime data hosted at MyAnimeList. This will allow me to cultivate a distinct category from movies for my small but non-zero collection of physical anime releases.

## Architecture
The Flask app in `api.py` creates one instance of each worker at startup and keeps them in a dictionary keyed by name (`SEARCH`, `ITEM`, `USER` and `LIST`). Routes check the request, hand the actual work to the right worker, and wrap whatever comes back in the standard response envelope described in [Endpoint Documentation](https://www.github.com/Asylumrunner/CollectionDatabase#endpoint-documentation).

Worker methods don't raise errors to the routes. Every one returns a dictionary with a `passed` flag, and on failure that dictionary also carries `step_failed` (the stage of the method that broke, such as `resolve_user_id` or `insert_item`) and an `exception` object with the error type, message, traceback and the arguments the method was called with. The workers log failures without the user-identifying details. The routes only send the client the name of the step that failed (`worker_failure` in `api.py`).

### Workers
* **BaseWorker** (`Workers/BaseWorker.py`) - The parent class for all the other workers. On first use it creates a single MySQL connection pool of 5 connections that every worker shares, and loads the `media_types` table so media type names can be mapped to their database IDs. It provides context managers that check out a connection or cursor and always return it to the pool, logging a warning when a connection takes more than 100ms to acquire or is held for more than a second. It also holds the shared helpers for turning a database row into an `Item` and for building failure responses.
* **SearchWorker** (`Workers/SearchWorker.py`) - The only worker that talks to the outside world, and the only one that doesn't touch the database. `search_item` dispatches to one lookup function per media type, each of which translates its source API's response into `Item` objects. Movies, board games and RPGs need a second request per result to get full details, so those requests run in parallel on a thread pool. The IGDB access token is fetched when this worker is created, so the app won't start if IGDB credentials are wrong. Before each video game search, the token is refreshed if it's within 5 minutes of expiring.
* **ItemWorker** (`Workers/ItemWorker.py`) - Manages the shared catalog of items and each user's collection. Items are shared between users, so adding an item first checks whether one with the same `media_type` and `original_api_id` already exists and reuses it if so. Otherwise it writes the item, its creators, genres, type-specific details, platforms and tracklist in a single transaction. A user's collection is a set of links between that user and catalog items, so removing something from a collection only removes the link.
* **ListWorker** (`Workers/ListWorker.py`) - Creates, renames, reads and deletes a user's named lists, and adds and removes items in them. Every list operation first checks that the list belongs to the user making the request, and reports a list that doesn't exist or belongs to someone else as not found.
* **UserWorker** (`Workers/UserWorker.py`) - Creates and deletes users in response to Clerk webhooks. Creating a user who already exists succeeds without doing anything, so Clerk's webhook retries are harmless. Deleting a user removes their lists, list entries, collection and user row in one transaction. Catalog items are left in place, since other users may have them.
* **CollectionWorker** (`Workers/CollectionWorker.py`) - An empty placeholder. Nothing uses it yet.

### Supporting Modules
* `DataClasses/item.py` - The `Item` dataclass that every worker passes around and every endpoint returns
* `DataClasses/igdb_platforms.py` - Maps common platform names and abbreviations ("ps5", "switch") to IGDB platform IDs, for the video game `platform` search filter
* `Utilities/AuthenticateRequest.py` - The `@authenticated_endpoint` decorator, which verifies the Clerk session token and passes the Clerk user ID to the route
* `Utilities/VerifyClerkWebhook.py` - The `@verify_clerk_webhook` decorator, which checks the Svix signature on incoming Clerk webhooks
* `Utilities/ResolveUserId.py` - Converts a Clerk user ID (`user_xxxxxxx`) into the internal integer `user_id` used throughout the database
* `Utilities/ValidateRequestInput.py` - Pydantic models for each media type. These aren't wired into any endpoint yet

### Database
`SQL/database.sql` creates the schema. Every item gets a row in `items` with the fields all media types share, plus a row in a per-type table (`books`, `movies`, `video_games`, `board_games`, `rpgs`, `anime` or `albums`) for its type-specific fields. Creators, genres, video game platforms and album tracks have their own tables. The `items_complete_view` view joins all of this back into one row per item, which is what the read endpoints query.

Users are identified by their Clerk user ID at the API boundary and by an internal integer `user_id` inside the database. `collection_items` links users to the items they own, and `user_lists` and `list_items` hold their lists.

## Local Development

A `Dockerfile.mysql` is provided to spin up a local MySQL instance for development. It creates a database named `collectionDB` with the root password `yourpassword`, matching the defaults in `local_db_config.json`.

**Build the image:**
```bash
docker build -f Dockerfile.mysql -t collectiondb-mysql .
```

**Run the container:**
```bash
docker run -p 3306:3306 collectiondb-mysql
```

The database will be available at `localhost:3306`. From there, connect with your preferred MySQL client and run `SQL/database.sql` to initialize the schema.

To override the default credentials at runtime:
```bash
docker run -p 3306:3306 \
  -e MYSQL_ROOT_PASSWORD=yourpassword \
  -e MYSQL_DATABASE=collectionDB \
  collectiondb-mysql
```

## Running Tests

The tests come in two tiers:

* **Unit tests** (`tests/unit`) fake the database, Clerk and every third-party API, so they run offline with no credentials.
* **Functional tests** (`tests/functional`) run the real app against a real MySQL 8.0 database, with real Clerk token verification and Svix webhook signatures. Only the third-party APIs are stubbed.

Neither tier reads `Workers/secrets.py` or `local_db_config.json`, so the tests never touch your real keys or your dev database.

**Install the test dependencies** (run everything here from the repo root, with your virtualenv active):
```bash
pip install -r requirements-dev.txt
```

### Unit tests
```bash
python -m pytest tests/unit
```

### Functional tests
These need a MySQL server. There are two ways to provide one.

**Option 1: Docker (recommended).** The tests start their own throwaway `mysql:8.0` container, load `SQL/database.sql` into it and remove it when they finish. Your user needs access to Docker:
```bash
sudo usermod -aG docker $USER
```
Log out and back in for the group change to take effect. If you run tests from an editor's terminal, restart the editor too. The first run downloads the MySQL image.

```bash
python -m pytest tests/functional
```

**Option 2: an existing MySQL server.** Point the tests at it with environment variables. The user must be able to create and drop databases. The tests drop and recreate a database called `collection_test` and leave every other database alone, but use a disposable server anyway:
```bash
TEST_DB_HOST=127.0.0.1 TEST_DB_PORT=3306 TEST_DB_USER=root TEST_DB_PASSWORD=yourpassword \
  python -m pytest tests/functional
```

Without either option, the functional tests that need a database fail with an error explaining why. The rest still run.

### Useful commands

| To do this | Run |
|---|---|
| Run everything | `python -m pytest` |
| Run one file | `python -m pytest tests/unit/test_auth.py` |
| Run tests matching a name | `python -m pytest -k skip_auth` |
| Stop at the first failure, with print output | `python -m pytest -x -s` |
| List known bugs and their reasons | `python -m pytest -rx` |
| See how the known bugs actually fail | `python -m pytest --runxfail` |
| Check coverage (fails under 85%) | `python -m pytest tests/unit --cov=api --cov=Workers --cov=Utilities --cov-report=term-missing` |

### Known bugs and `xfail`
Some tests describe the correct behaviour for bugs that haven't been fixed yet. They're marked `@pytest.mark.xfail(reason="B#")` and show up as `xfailed`, which is expected and doesn't fail the run.

When you fix one of those bugs, its test starts passing, and pytest reports that as a failure (`XPASS(strict)`). This is deliberate: it reminds you to remove the test's `xfail` marker so it becomes a normal test.

## Endpoint Documentation

### Responses
Every endpoint returns the same envelope:
```
{
  'status': 'SUCCESS' | 'FAILURE',
  'data': any,
  'err_msg': string | object,
  'next_page': int | null
}
```
The Example Response sections below show only the contents of `data`. `next_page` is only used by paginated endpoints: pass it back as the `page` query parameter to get the next page. `null` means there are no more pages.

On a 400, 401 or 404, `err_msg` is a string explaining what went wrong. On a 500, it only names the step that failed, such as `Internal server error at step 'insert_item'`. The full failure object, with its traceback, stays in the server logs (see [Architecture](https://www.github.com/Asylumrunner/CollectionDatabase#architecture)).

### Authentication
Every endpoint except `GET /` and `POST /webhooks/clerk` requires a Clerk session token in the `Authorization` header:
```
Authorization: Bearer <token>
```
The token's authorized party must be `http://localhost:8080`. A missing or invalid token returns 401. See [Configuration](https://www.github.com/Asylumrunner/CollectionDatabase#configuration) for skipping authentication during local development.

### The Item Object
Most endpoints accept or return items in this shape. Fields that don't apply to an item's media type are `null`.
```
{
  'id': string,
  'title': string,
  'media_type': string,
  'release_year': int,
  'img_link': string,
  'original_api_id': string,
  'created_by': [string],
  'isbn': string (books, rpgs only),
  'printing_year': int (books only),
  'lang': string (movies only),
  'summary': string,
  'duration': int (movies, board games only),
  'min_players': int (board games only),
  'max_players': int (board games only),
  'episodes': int (anime only),
  'platforms': [string] (video games only),
  'platform_igdb_ids': {string: int} (video games only),
  'tracklist': [string] (albums only),
  'genres': [string]
}
```
`media_type` is one of `book`, `movie`, `video_game`, `board_game`, `rpg`, `anime` or `album`. `original_api_id` is the item's ID in its source API. `created_by` holds authors, directors, developers, designers, studios or artists, depending on the media type.

What `id` means depends on where the item came from. In search results it's the same as `original_api_id`. In items read from the database (a collection or a list) it's the item's database ID, and that's the ID the remove endpoints expect.

#### GET /
Health check. Doesn't require authentication.

##### Example Response
```
["Health Check Passed!"]
```

#### GET /search/\<title>
Searches for a collection item via the appropriate public API (see [APIs In Use](https://www.github.com/Asylumrunner/CollectionDatabase#apis-in-use)) and returns the results as items. Nothing is saved to the database.

##### Request Parameters
```
title - The title of the collection item to be looked up
```

##### Query Parameters
```
media_type - REQUIRED. The kind of collection item to search for. Must be one of ['book', 'movie', 'video_game', 'board_game', 'rpg', 'anime', 'album'], or the request is a 400
page - The page of results to fetch. Default 1
```
Any other query parameters are passed to the source API as search filters. Each media type recognizes a different set, and unrecognized filters are ignored:

| `media_type` | Recognized filters |
|---|---|
| `book` | `author`, `subject`, `place`, `person`, `language`, `publisher`, `edition_count`, `author_key`, `earliest_publish_year`, `latest_publish_year`, `earliest_first_publish_year`, `latest_first_publish_year`, `min_number_of_pages`, `max_number_of_pages` |
| `movie` | `include_adult`, `language`, `primary_release_year`, `region`, `year` |
| `video_game` | `platform` (a name such as `ps5` or `switch`, see `DataClasses/igdb_platforms.py`), `release_date_before`, `release_date_after` (both `MM/DD/YYYY`) |
| `board_game` | None |
| `rpg` | None |
| `anime` | `type`, `status`, `rating`, `genre`, `score`, `sfw`, `order_by`, `sort`, `min_score`, `max_score`, `start_date`, `end_date`, `genres`, `genres_exclude`, `producers` |
| `album` | `artist`, `genre`, `year`, `format`, `label`, `country`, `style` |

`next_page` is always the current page plus one, because the source APIs don't say when results run out. An empty page means you've reached the end. BoardGameGeek and RPGGeek return every result in one go, so board game and RPG searches ignore `page`.

Some quirks of particular sources:
* Video game `img_link` is an IGDB image ID, not a full URL
* Board game and RPG fields such as `release_year` and the player counts come back as strings, as BGG returns them

##### Example Response
```
[
  {
    'id': string,
    'title': string,
    'media_type': string,
    'release_year': int,
    'img_link': string,
    'original_api_id': string,
    'created_by': [string],
    ...
  },
  {},
  ...
]
```

#### GET /collection
Returns the requesting user's collection, 25 items per page, ordered by when each item was first added to the catalog.

##### Query Parameters
```
page - The page of the collection to fetch. Default 1
```

##### Example Response
```
[
  {
    'id': string,
    'title': string,
    'media_type': string,
    ...
  },
  {},
  ...
]
```

#### PUT /collection/item
Adds an item to the requesting user's collection. If the item isn't in the catalog yet it's created first. If it is (matched on `media_type` and `original_api_id`), the existing catalog entry is reused. The easiest way to build the request body is to send back an item from `GET /search` unchanged.

##### Request Body
```
{
  'title' (string): REQUIRED
  'media_type' (string): REQUIRED - one of ['book', 'movie', 'video_game', 'board_game', 'rpg', 'anime', 'album']
  'release_year' (int): REQUIRED
  'img_link' (string): REQUIRED
  'original_api_id' (string): REQUIRED - the item's ID in its source API
  'created_by' ([string]): REQUIRED
  'isbn', 'printing_year', 'lang', 'summary', 'duration', 'min_players', 'max_players',
  'episodes', 'platforms', 'platform_igdb_ids', 'tracklist', 'genres': optional, as in the Item object
}
```

##### Example Response
When the item was added:
```
{
  'passed': true,
  'already_exists': false,
  'item_id': int,
  'user_id': int
}
```
When the item was already in the collection:
```
{
  'passed': true,
  'already_exists': true,
  'Item': {Item}
}
```

#### PUT /collection/items
As above, but adds several items in one request. Each item is created in the catalog separately, so one bad item doesn't stop the others. The collection entries for all the items that succeeded are then added together.

##### Request Body
A non-empty list of items, each in the same shape as the body of `PUT /collection/item`:
```
[
  {Item},
  {Item},
  ...
]
```

##### Example Response
```
{
  'passed': true,
  'added': [int],
  'already_existed': [int],
  'failed': [
    {
      'item': {
        'title': string,
        'original_api_id': string
      },
      'error': string
    },
    {},
    ...
  ]
}
```
`added` and `already_existed` are database item IDs. Items in `failed` couldn't be created in the catalog, and their `error` names the step that failed, as in a 500's `err_msg`. This endpoint still returns 200 when some items fail, so check `failed`.

#### DELETE /collection/item
Removes an item from the requesting user's collection. The item stays in the catalog and in any of the user's lists.

##### Request Body
```
{
  'id' (int): REQUIRED - the item's database ID, NOT its original_api_id
}
```

##### Example Response
```
{
  'passed': true,
  'rows_deleted': int
}
```
`rows_deleted` is 0 if the item wasn't in the collection.

#### DELETE /collection/items
As above, but removes several items in one request.

##### Request Body
```
{
  'ids' ([int]): REQUIRED - a non-empty list of database item IDs
}
```

##### Example Response
```
{
  'passed': true,
  'rows_deleted': int
}
```

#### GET /lists
Returns every list the requesting user owns, with the image links of up to 10 of its most recently added items, for displaying list previews.

##### Example Response
```
[
  {
    'list_id': int,
    'list_name': string,
    'img_links': [string]
  },
  {},
  ...
]
```

#### POST /lists
Creates a new, empty list for the requesting user.

##### Request Body
```
{
  'list_name' (string): REQUIRED
}
```

##### Example Response
```
{
  'passed': true,
  'list_id': int,
  'list_name': string
}
```

#### GET /lists/names
Returns the ID and name of every list the requesting user owns, oldest first. Lighter than `GET /lists` when you don't need preview images.

##### Example Response
```
[
  {
    'list_id': int,
    'list_name': string
  },
  {},
  ...
]
```

#### GET /lists/\<list_id>
Returns the items in one of the requesting user's lists, 25 per page, most recently added first. Returns 404 if the list doesn't exist or belongs to another user.

##### Request Parameters
```
list_id - The ID of the list
```

##### Query Parameters
```
page - The page of the list to fetch. Default 1
```

##### Example Response
```
[
  {Item},
  {},
  ...
]
```

#### PUT /lists/\<list_id>/rename
Renames one of the requesting user's lists. Returns 404 if the list doesn't exist or belongs to another user.

##### Request Parameters
```
list_id - The ID of the list
```

##### Request Body
```
{
  'list_name' (string): REQUIRED - the new name
}
```

##### Example Response
```
{
  'passed': true,
  'not_found': false,
  'list_id': int,
  'list_name': string
}
```

#### DELETE /lists/\<list_id>
Deletes one of the requesting user's lists and its entries. The items themselves stay in the catalog and in the user's collection. Returns 404 if the list doesn't exist or belongs to another user.

##### Request Parameters
```
list_id - The ID of the list
```

##### Example Response
```
[]
```

#### PUT /lists/\<list_id>/item
Adds an item to one of the requesting user's lists, creating it in the catalog first if needed, exactly like `PUT /collection/item`. This does not add the item to the user's collection, so lists can hold things you don't own yet. Returns 404 if the list doesn't exist or belongs to another user. The item is still created in the catalog in that case.

##### Request Parameters
```
list_id - The ID of the list
```

##### Request Body
The same as `PUT /collection/item`.

##### Example Response
```
{
  'passed': true,
  'not_found': false,
  'already_exists': boolean,
  'item_id': string
}
```
`already_exists` is true if the item was already in the list.

#### DELETE /lists/\<list_id>/item
Removes an item from one of the requesting user's lists. Returns 404 if the list doesn't exist or belongs to another user.

##### Request Parameters
```
list_id - The ID of the list
```

##### Request Body
```
{
  'id' (int): REQUIRED - the item's database ID, NOT its original_api_id
}
```

##### Example Response
```
{
  'passed': true,
  'not_found': false
}
```

#### GET /lists/item/\<item_id>
Returns which of the requesting user's lists contain an item, sorted by list name.

##### Request Parameters
```
item_id - The item's database ID
```

##### Example Response
```
[
  {
    'list_id': int,
    'list_name': string
  },
  {},
  ...
]
```

#### POST /webhooks/clerk
Receives user events from Clerk. This doesn't take a session token. Instead, the request must carry valid Svix signature headers (`svix-id`, `svix-timestamp` and `svix-signature`), checked against `CLERK_WEBHOOK_SECRET`. Missing headers or a bad signature return 400.

Two event types are handled:
* `user.created` - Creates the user. Their username is their first email address, or their first and last name if they have no email, or `Unknown`. If the user already exists, nothing changes
* `user.deleted` - Deletes the user, their collection and their lists (see UserWorker in [Architecture](https://www.github.com/Asylumrunner/CollectionDatabase#architecture))

Any other event type is ignored and returns 200.

##### Request Body
A Clerk webhook event, as sent by Clerk:
```
{
  'type': string,
  'data': {
    'id': string,
    'email_addresses': [{'email_address': string}, ...],
    'first_name': string,
    'last_name': string,
    ...
  }
}
```

##### Example Response
```
{
  'passed': true,
  'clerk_user_id': string,
  'already_exists': boolean,
  'message': string
}
```
For `user.deleted`, the response contains only `passed` and `message`.
