from datetime import datetime, date, timedelta
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field, validator, field_validator


class MovieStatusEnum(str, Enum):
    RELEASED = "Released"
    POST_PRODUCTION = "Post Production"
    IN_PRODUCTION = "In Production"


class LanguageSchema(BaseModel):
    id: int
    name: str


class CountrySchema(BaseModel):
    id: int
    code: str
    name: Optional[str]


class ActorSchema(BaseModel):
    id: int
    name: str


class GenreSchema(BaseModel):
    id: int
    name: str


class MovieBaseSchema(BaseModel):
    id: int
    name: str
    date: date
    score: float
    overview: str
    status: MovieStatusEnum
    budget: float
    revenue: float
    country_id: int
    country: CountrySchema
    genres: List[GenreSchema]
    actors: List[ActorSchema]
    language: List[LanguageSchema]

    class Config:
        orm_mode = True


class MovieDetailSchema(BaseModel):
    id: int
    name: str
    date: Optional[date]
    score: float
    overview: str
    status: MovieStatusEnum
    budget: float
    revenue: float
    country: CountrySchema
    genres: Optional[List[GenreSchema]]
    actors: Optional[List[ActorSchema]]
    languages: Optional[List[LanguageSchema]]


class MovieListItemSchema(BaseModel):
    id: int
    name: str
    date: Optional[date]
    score: float
    overview: str

    class Config:
        orm_mode = True


class MovieListResponseSchema(BaseModel):
    movies: List[MovieListItemSchema]
    prev_page: str
    next_page: str
    total_pages: int
    total_items: int


class MovieCreateSchema(BaseModel):
    name: str = Field(..., max_length=255)
    date: Optional[date]
    score: float = Field(..., ge=0, le=100)
    overview: str
    status: MovieStatusEnum
    budget: float = Field(..., ge=0)
    revenue: float = Field(..., ge=0)
    country: int
    genres: List[int]
    actors: List[int]
    languages: List[int]

    @field_validator("date")
    @classmethod
    def validate_date(cls, value: date) -> date:
        max_date = date.today() + timedelta(days=365)
        if value > max_date:
            raise ValueError("The date must not be more than one year in the future")
        return value


class MovieUpdateSchema(BaseModel):
    name: Optional[str] = None
    date: Optional[date] = None
    score: Optional[float] = None
    overview: Optional[str] = None
    status: Optional[MovieStatusEnum] = None
    budget: Optional[float] = None
    revenue: Optional[float] = None
    country_id: Optional[int] = None
    genre_ids: Optional[List[int]] = None
    actor_ids: Optional[List[int]] = None
    language_ids: Optional[List[int]] = None


class MovieDeleteSchema(BaseModel):
    pass
