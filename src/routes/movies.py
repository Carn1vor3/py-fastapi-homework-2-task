from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from sqlalchemy import select, func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload
from starlette import status

from database import get_db, MovieModel
from database.models import CountryModel, GenreModel, ActorModel, LanguageModel
from schemas import MovieListResponseSchema, MovieDetailSchema
from schemas.movies import MovieDeleteSchema, MovieCreateSchema, MovieUpdateSchema

router = APIRouter()


@router.get("/movies/", response_model=MovieListResponseSchema)
async def get_movies(request: Request,
                     page: int = Query(1, ge=1),
                     per_page: int = Query(10, ge=1, le=20),
                     db: AsyncSession = Depends(get_db)):
    total_items_result = await db.execute(select(func.count()).select_from(MovieModel))
    total_items = total_items_result.scalar()

    total_pages = (total_items + per_page - 1) // per_page
    offset = (page - 1) * per_page

    if page > total_pages:
        raise HTTPException(status_code=404, detail="Page not found")

    result = await db.execute(select(MovieModel).order_by(MovieModel.id.desc()).offset(offset).limit(per_page))
    movies = result.scalars().all()

    if not movies:
        raise HTTPException(status_code=404, detail="No movies found")

    base_url = str(request.url).split("?")[0]

    prev_page = f"{base_url}?page={page - 1}&per_page={per_page}" if page > 1 else None
    next_page = f"{base_url}?page={page + 1}&per_page={per_page}" if page < total_pages else None

    return MovieListResponseSchema(
        movies=movies,
        prev_page=prev_page,
        next_page=next_page,
        total_pages=total_pages,
        total_items=total_items
    )


@router.get("/movies/{movie_id}/", response_model=MovieDetailSchema)
async def get_movie(movie_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(MovieModel)
        .options(
            joinedload(MovieModel.country),
            joinedload(MovieModel.genres),
            joinedload(MovieModel.actors),
            joinedload(MovieModel.languages),
        )
        .where(MovieModel.id == movie_id)
    )
    movie = result.scalar_one_or_none()
    if movie is None:
        raise HTTPException(status_code=404, detail="Movie with the given ID was not found.")
    return movie


@router.delete("/movies/{movie_id}/", status_code=204)
async def delete_movie(movie_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(MovieModel).where(MovieModel.id == movie_id))
    movie = result.scalar_one_or_none()
    if not movie:
        raise HTTPException(status_code=404, detail="Movie with the given ID was not found.")
    await db.delete(movie)
    await db.commit()
    return Response(status_code=204)


async def get_or_create_by_name(session: AsyncSession, model, name: str):
    result = await session.execute(select(model).where(model.name == name))
    obj = result.scalars().first()
    if obj is None:
        obj = model(name=name)
        session.add(obj)
        await session.flush()
    return obj


@router.post("/movies/", response_model=MovieDetailSchema, status_code=status.HTTP_201_CREATED)
async def create_movie(movie: MovieCreateSchema, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(MovieModel).where(MovieModel.name == movie.name, MovieModel.date == movie.date)
    )
    existing_movie = result.scalars().first()
    if existing_movie:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"A movie with the name '{movie.name}' and release date '{movie.date}' already exists."
        )

    country_result = await db.execute(select(CountryModel).where(CountryModel.code == movie.country))
    country = country_result.scalars().first()
    if country is None:
        country = CountryModel(code=movie.country, name=None)
        db.add(country)
        await db.flush()

    genres = []
    for genre_name in movie.genres:
        genre = await get_or_create_by_name(db, GenreModel, genre_name)
        genres.append(genre)

    actors = []
    for actor_name in movie.actors:
        actor = await get_or_create_by_name(db, ActorModel, actor_name)
        actors.append(actor)

    languages = []
    for lang_name in movie.languages:
        lang = await get_or_create_by_name(db, LanguageModel, lang_name)
        languages.append(lang)

    new_movie = MovieModel(
        name=movie.name,
        date=movie.date,
        score=movie.score,
        overview=movie.overview,
        status=movie.status,
        budget=movie.budget,
        revenue=movie.revenue,
        country=country,
        genres=genres,
        actors=actors,
        languages=languages,
    )
    db.add(new_movie)

    try:
        await db.commit()
        await db.refresh(new_movie)
    except Exception:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid input data.")

    return new_movie


@router.patch("/movies/{movie_id}/", status_code=status.HTTP_200_OK)
async def update_movie(
    movie_id: int,
    movie_update: MovieUpdateSchema,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(MovieModel).where(MovieModel.id == movie_id))
    movie = result.scalars().first()
    if not movie:
        raise HTTPException(status_code=404, detail="Movie with the given ID was not found.")

    update_data = movie_update.dict(exclude_unset=True)

    for field, value in update_data.items():
        setattr(movie, field, value)

    try:
        await db.commit()
    except Exception:
        await db.rollback()
        raise HTTPException(status_code=400, detail="Invalid input data.")

    return {"detail": "Movie updated successfully."}
