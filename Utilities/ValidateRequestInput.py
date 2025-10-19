import logging
from datetime import datetime
from pydantic import BaseModel, PositiveInt, Field, BeforeValidator, AnyUrl
from typing import Annotated

StrippedStr = Annotated[str, BeforeValidator(lambda v: v.strip() if isinstance(v, str) else v)]
SharedStrField = Annotated[StrippedStr, Field(max_length=255)]
Year = Annotated[int, Field(gt=0, lt=2050)]
ISBN = Annotated[int, Field(max_length=13, min_length=10)]
Summary = Annotated[StrippedStr, Field(max_length=512)]

class Album(BaseModel):
    id: PositiveInt
    title: SharedStrField
    release_year: Year
    created_by: SharedStrField
    img_link: AnyUrl
    original_api_id: str
    summary: Summary

class Anime(BaseModel):
    id: PositiveInt
    title: SharedStrField
    release_year: Year
    created_by: SharedStrField
    img_link: AnyUrl
    original_api_id: str
    episodes: PositiveInt

class BoardGame(BaseModel):
    id: PositiveInt
    title: SharedStrField
    release_year: Year
    created_by: SharedStrField
    img_link: AnyUrl
    original_api_id: str
    minimum_players: PositiveInt
    maximum_players: PositiveInt
    summary: Summary
    duration: PositiveInt

class Book(BaseModel):
    id: PositiveInt
    title: SharedStrField
    release_year: Year
    created_by: SharedStrField
    img_link: AnyUrl
    original_api_id: str
    isbn: ISBN
    printing_year: Year

class Movie(BaseModel):
    id: PositiveInt
    title: SharedStrField
    release_year: Year
    created_by: SharedStrField
    img_link: AnyUrl
    original_api_id: str
    lang: str
    summary: Summary
    duration: PositiveInt

class RPG(BaseModel):
    id: PositiveInt
    title: SharedStrField
    release_year: Year
    created_by: SharedStrField
    img_link: AnyUrl
    original_api_id: str
    isbn: ISBN
    summary: Summary

class VideoGame(BaseModel):
    id: PositiveInt
    title: SharedStrField
    release_year: Year
    created_by: SharedStrField
    img_link: AnyUrl
    original_api_id: str
    summary: Summary

def fail_because(reason_string):
    response = {
        'valid': False,
        'reason': reason_string
    }
    logging.error(reason_string)
    return response