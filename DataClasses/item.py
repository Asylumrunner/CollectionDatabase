from dataclasses import dataclass
from typing import Optional, List
from datetime import date

@dataclass
class Item:
    id: str
    title: str
    media_type: str
    release_year: int
    img_link: str
    original_api_id: str
    created_by: List[str]
    isbn: Optional[str] = None
    printing_year: Optional[int] = None
    lang: Optional[str] = None
    summary: Optional[str] = None
    duration: Optional[int] = None
    min_players: Optional[int] = None
    max_players: Optional[int] = None
    episodes: Optional[int] = None
    platforms: Optional[List[str]] = None
