import logging
from datetime import datetime
from pydantic import BaseModel, PositiveInt

class Album(BaseModel):
    id: int
    title: str
    release_year: int
    created_by: str
    img_link: str
    original_api_id: str
    summary: str

class Anime(BaseModel):
    id: int
    title: str
    release_year: int
    created_by: str
    img_link: str
    original_api_id: str
    episodes: int

class BoardGame(BaseModel):
    id: int
    title: str
    release_year: int
    created_by: str
    img_link: str
    original_api_id: str
    minimum_players: int
    maximum_players: int
    summary: str
    duration: int

class Book(BaseModel):
    id: int
    title: str
    release_year: int
    created_by: str
    img_link: str
    original_api_id: str
    isbn: int
    printing_year: str

class Movie(BaseModel):
    id: int
    title: str
    release_year: int
    created_by: str
    img_link: str
    original_api_id: str
    lang: str
    summary: str
    duration: int

class RPG(BaseModel):
    id: int
    title: str
    release_year: int
    created_by: str
    img_link: str
    original_api_id: str
    isbn: int
    summary: str

class VideoGame(BaseModel):
    id: int
    title: str
    release_year: int
    created_by: str
    img_link: str
    original_api_id: str
    summary: str


def fail_because(reason_string):
    response = {
        'valid': False,
        'reason': reason_string
    }
    logging.error(reason_string)
    return response