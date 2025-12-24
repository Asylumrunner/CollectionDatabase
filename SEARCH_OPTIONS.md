# Search Options Documentation

This document describes all available search options for each media type in the CollectionDatabase search functionality.

## Table of Contents
- [Books](#books)
- [Movies](#movies)
- [Video Games](#video-games)
- [Anime](#anime)
- [Music](#music)
- [Board Games](#board-games)
- [RPGs](#rpgs)

---

## Books

**API**: Open Library
**Implementation**: `lookup_book()` in SearchWorker.py

### Available Search Options

#### Direct Search Filters
These parameters are added directly to the query string:

| Parameter | Type | Description | Example |
|-----------|------|-------------|---------|
| `author` | string | Filter by author name | `"author": "Terry Pratchett"` |
| `subject` | string | Filter by subject/topic | `"subject": "fantasy"` |
| `place` | string | Filter by place/location | `"place": "London"` |
| `person` | string | Filter by person mentioned | `"person": "Shakespeare"` |
| `language` | string | Filter by language code | `"language": "eng"` |
| `publisher` | string | Filter by publisher name | `"publisher": "Penguin"` |
| `edition_count` | integer | Filter by number of editions | `"edition_count": "5"` |
| `author_key` | string | Filter by Open Library author key | `"author_key": "/authors/OL23919A"` |

#### Range Parameters
These parameters are abstracted into range queries. Each range requires both `earliest_` and `latest_` parameters (or use `*` for open-ended ranges):

| Parameter Pair | Type | Description | Example |
|----------------|------|-------------|---------|
| `earliest_publish_year`<br>`latest_publish_year` | integer | Filter by publication year range | `"earliest_publish_year": "2000",`<br>`"latest_publish_year": "2023"` |
| `earliest_first_publish_year`<br>`latest_first_publish_year` | integer | Filter by first publication year range | `"earliest_first_publish_year": "1990",`<br>`"latest_first_publish_year": "*"` |
| `min_number_of_pages`<br>`max_number_of_pages` | integer | Filter by page count range | `"min_number_of_pages": "100",`<br>`"max_number_of_pages": "500"` |

**Note**: Range parameters are combined using Open Library's `[min TO max]` syntax internally.

---

## Movies

**API**: The Movie Database (TMDB)
**Implementation**: `lookup_movie()` in SearchWorker.py

### Available Search Options

| Parameter | Type | Description | Example |
|-----------|------|-------------|---------|
| `include_adult` | boolean | Include adult content in results | `"include_adult": true` |
| `language` | string | ISO 639-1 language code | `"language": "en-US"` |
| `primary_release_year` | string/integer | Filter by primary release year | `"primary_release_year": "2023"` |
| `region` | string | ISO 3166-1 region code | `"region": "US"` |
| `year` | string/integer | Filter by any release year | `"year": "2023"` |

---

## Video Games

**API**: IGDB (Internet Game Database)
**Implementation**: `lookup_video_game()` in SearchWorker.py

### Available Search Options

| Parameter | Type | Description | Abstraction | Example |
|-----------|------|-------------|-------------|---------|
| `platform` | string | Platform name (case-insensitive) | Converted to IGDB platform ID | `"platform": "PS4"` |
| `release_date_before` | string | Games released before date | Converted to Unix timestamp | `"release_date_before": "12/31/2023"` |
| `release_date_after` | string | Games released after date | Converted to Unix timestamp | `"release_date_after": "01/01/2020"` |

### Platform Name Abstraction

Platform names are converted from user-friendly strings to IGDB platform IDs using the `igdb_platforms.py` mapping.

**Supported Platforms** (case-insensitive):
- **PlayStation**: ps5, ps4, ps3, ps2, ps1/playstation/psx, ps vita, psp
- **Xbox**: xbox series x|s, xbox one, xbox 360, xbox
- **Nintendo**: switch, wii u, wii, gamecube, n64, snes, nes, 3ds, ds, game boy advance/gba, game boy color/gbc, game boy
- **PC**: pc/windows, mac/macos, linux
- **Mobile**: ios/iphone/ipad, android
- **Retro**: sega genesis/genesis/mega drive, dreamcast, saturn, master system, atari 2600/atari

### Date Format

**Required Format**: `MM/DD/YYYY`

Dates are converted to Unix timestamps internally for the IGDB API.

---

## Anime

**API**: Jikan (MyAnimeList API)
**Implementation**: `lookup_anime()` in SearchWorker.py

### Available Search Options

| Parameter | Type | Description | Example |
|-----------|------|-------------|---------|
| `type` | string | Anime format type | `"type": "tv"` (options: tv, movie, ova, special, ona, music) |
| `status` | string | Airing status | `"status": "airing"` (options: airing, complete, upcoming) |
| `rating` | string | Content rating | `"rating": "pg13"` |
| `genre` | integer | Single genre ID | `"genre": 1` |
| `genres` | string | Multiple genre IDs (comma-separated) | `"genres": "1,2,3"` |
| `genres_exclude` | string | Exclude genre IDs | `"genres_exclude": "9,49"` |
| `score` | float | Exact score | `"score": 7.5` |
| `min_score` | float | Minimum score threshold | `"min_score": 7.0` |
| `max_score` | float | Maximum score threshold | `"max_score": 9.0` |
| `sfw` | boolean | Safe for work filter | `"sfw": true` |
| `order_by` | string | Sort field | `"order_by": "score"` (options: title, start_date, end_date, score, etc.) |
| `sort` | string | Sort direction | `"sort": "desc"` (options: asc, desc) |
| `start_date` | string | Start airing date | `"start_date": "2020-01-01"` |
| `end_date` | string | End airing date | `"end_date": "2023-12-31"` |
| `producers` | integer/string | Producer/studio ID(s) | `"producers": "2"` |

---

## Music

**API**: Discogs
**Implementation**: `lookup_music()` in SearchWorker.py

### Available Search Options

| Parameter | Type | Description | Example |
|-----------|------|-------------|---------|
| `artist` | string | Filter by artist name | `"artist": "Daft Punk"` |
| `genre` | string | Filter by genre | `"genre": "Electronic"` |
| `year` | string/integer | Filter by release year | `"year": "1997"` |
| `format` | string | Filter by release format | `"format": "CD"` (options: Vinyl, CD, Cassette, Digital, etc.) |

**Note**: The album name is always passed as the main search term. All filters are optional and can be combined to narrow down results.

### Common Genres
Electronic, Rock, Pop, Jazz, Hip Hop, Classical, Funk/Soul, Folk World & Country, Stage & Screen, Latin, Reggae, Blues, Non-Music, Children's, Brass & Military

### Common Formats
Vinyl, CD, Cassette, Digital, Box Set, Album, Single, EP, Compilation, Acetate, Flexi-disc, Shellac

---

## Board Games

**API**: BoardGameGeek XML API v2
**Implementation**: `lookup_board_game()` in SearchWorker.py

### Available Search Options

**Currently**: No search options are implemented for board games.

---

## RPGs

**API**: RPGGeek XML API v2
**Implementation**: `lookup_rpg()` in SearchWorker.py

### Available Search Options

**Currently**: No search options are implemented for RPGs.
