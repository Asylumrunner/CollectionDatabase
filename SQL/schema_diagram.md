# Collection Database Schema Diagram

```
┌─────────────────────────┐
│        users            │
├─────────────────────────┤
│ PK user_id              │
│    username             │
│    date_added           │
│    last_login           │
└─────────────────────────┘
         │
         │ 1
         │
         │ *
         ├──────────────────────────────────────┐
         │                                      │
         │                                      │
┌────────▼────────────┐              ┌─────────▼──────────┐
│  collection_items   │              │    user_lists      │
├─────────────────────┤              ├────────────────────┤
│ PK,FK item_id       │              │ PK list_id         │
│ PK,FK user_id       │              │ FK user_id         │
│       date_added    │              │    list_name       │
└─────────────────────┘              │    date_added      │
                                     └────────────────────┘
                                              │
                                              │ 1
                                              │
                                              │ *
                                     ┌────────▼──────────┐
                                     │   list_items      │
                                     ├───────────────────┤
                                     │ PK,FK item_id     │
                                     │ PK,FK list_id     │
                                     │       date_added  │
                                     └───────────────────┘


┌─────────────────────────┐
│     media_types         │
├─────────────────────────┤
│ PK id                   │
│    type_name            │
└─────────────────────────┘
         │
         │ 1
         │
         │ *
┌────────▼─────────────────────────┐
│           items                  │
├──────────────────────────────────┤
│ PK id                            │
│    title                         │
│ FK media_type                    │
│    release_year                  │
│    date_added                    │
│    date_last_updated             │
│    img_link                      │
│    original_api_id               │
│    summary                       │
└──────────────────────────────────┘
         │
         │ 1
         │
         ├──────────────┬──────────────┬──────────────┬──────────────┬──────────────┬──────────────┐
         │              │              │              │              │              │              │
         │ *            │ *            │ *            │ *            │ *            │ *            │ *
         │              │              │              │              │              │              │
┌────────▼────────┐ ┌──▼──────┐ ┌────▼─────────┐ ┌──▼──────────┐ ┌─▼────┐ ┌──────▼─┐ ┌─────────▼─┐
│  item_creators  │ │  books  │ │   movies     │ │board_games  │ │ rpgs │ │ anime  │ │  albums   │
├─────────────────┤ ├─────────┤ ├──────────────┤ ├─────────────┤ ├──────┤ ├────────┤ ├───────────┤
│ PK,FK item_id   │ │ PK,FK id│ │ PK,FK id     │ │ PK,FK id    │ │PK,FK │ │PK,FK id│ │ PK,FK id  │
│ PK,FK creator_id│ │    isbn │ │    lang      │ │ min_players │ │   id │ │episodes│ └───────────┘
└─────────────────┘ │ printing│ │    duration  │ │ max_players │ │ isbn │ └────────┘       │
         │          │    _year│ └──────────────┘ │   duration  │ └──────┘                   │ 1
         │          └─────────┘                  └─────────────┘                             │
         │ *                                                                                  │ *
         │                                                                          ┌─────────▼─────────┐
┌────────▼────────┐                                                                │  album_tracks     │
│    creators     │                                                                ├───────────────────┤
├─────────────────┤                                                                │ PK,FK album_id    │
│ PK creator_id   │                                                                │ PK track_number   │
│    creator_name │                                                                │    track_name     │
└─────────────────┘                                                                └───────────────────┘


┌─────────────────────────┐
│       genres            │
├─────────────────────────┤
│ PK genre_id             │
│    genre_name           │
└─────────────────────────┘
         │
         │ *
         │
         │ 1
┌────────▼─────────────────┐
│     item_genres          │
├──────────────────────────┤
│ PK,FK item_id            │
│ PK,FK genre_id           │
└──────────────────────────┘
         │
         │ *
         │
         │ 1
      (items)


┌──────────────────────────┐
│ video_game_platforms     │
├──────────────────────────┤
│ PK platform_id           │
│    platform_name         │
└──────────────────────────┘
         │
         │ *
         │
         │ 1
┌────────▼──────────────────┐
│game_platform_availabilities│
├───────────────────────────┤
│ PK,FK game_id             │
│ PK,FK platform_id         │
└───────────────────────────┘
         │
         │ *
         │
         │ 1
    (video_games)
```

## Table Relationships Summary

### Core Tables
- **items** - Central table for all media items
  - References: media_types (FK)
  - Referenced by: All media type tables, item_creators, item_genres, collection_items, list_items

### User Tables
- **users** - User accounts
- **collection_items** - Many-to-many relationship between users and items they own
- **user_lists** - Custom lists created by users
- **list_items** - Items in user lists

### Media Type Tables (Inheritance)
All extend the items table with specific fields:
- **books** - isbn, printing_year
- **movies** - lang, duration
- **video_games** - (platforms stored separately)
- **board_games** - min_players, max_players, duration
- **rpgs** - isbn
- **anime** - episodes
- **albums** - (tracks stored separately)

### Multi-valued Field Tables
- **creators** + **item_creators** - Many-to-many: items to creators
- **genres** + **item_genres** - Many-to-many: items to genres
- **video_game_platforms** + **game_platform_availabilities** - Many-to-many: video games to platforms
- **album_tracks** - One-to-many: albums to tracks

### Lookup Tables
- **media_types** - Valid media type values (book, movie, video_game, etc.)

## Key Design Patterns

1. **Table Inheritance**: Media-specific tables (books, movies, etc.) inherit from items using a shared primary key
2. **Normalization**: Multi-valued fields (creators, genres, platforms, tracks) are normalized into separate tables
3. **Soft Typing**: The media_type field in items determines which specialized table to join with
4. **Audit Fields**: Timestamps for tracking when records are created and updated
