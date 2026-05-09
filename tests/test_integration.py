import json
import random

from pydantic import BaseModel

from jstream import parse_stream
from tests.conftest import make_stream


class Film(BaseModel):
    title: str = ""
    year: int = 0
    rating: float = 0.0
    active: bool = False


FULL_JSON = '{"title":"Inception","year":2010,"rating":8.8,"active":true}'


async def collect(gen) -> list:
    return [item async for item in gen]


async def test_random_split_stream():
    s = FULL_JSON
    seed = 42
    rng = random.Random(seed)
    chunks = []
    i = 0
    while i < len(s):
        size = rng.randint(1, 5)
        chunks.append(s[i : i + size])
        i += size

    results = await collect(parse_stream(make_stream(chunks), schema=Film))
    assert results[-1] == Film.model_validate_json(FULL_JSON)


async def test_monotonically_growing_state():
    chunks = ['{"title":"Inc', 'eption","year":2010}']
    results = await collect(parse_stream(make_stream(chunks)))
    keys_seen: set[str] = set()
    for r in results:
        assert isinstance(r, dict)
        assert keys_seen.issubset(r.keys())
        keys_seen.update(r.keys())


async def test_final_state_matches_model():
    results = await collect(parse_stream(make_stream([FULL_JSON]), schema=Film))
    assert results[-1] == Film.model_validate_json(FULL_JSON)


async def test_whitespace_only_chunks():
    chunks = ["   ", '{"title":"X"}', "   "]
    results = await collect(parse_stream(make_stream(chunks)))
    assert results[-1] == {"title": "X"}


async def test_stream_stops_mid_string():
    chunks = ['{"title":"unterminated']
    results = await collect(parse_stream(make_stream(chunks)))
    assert results == []


async def test_extra_keys_plain_dict():
    chunks = ['{"title":"X","extra_key":99}']
    results = await collect(parse_stream(make_stream(chunks)))
    assert results[-1]["extra_key"] == 99


async def test_extra_keys_ignored_by_schema():
    chunks = ['{"title":"X","extra_key":99,"year":2020}']
    results = await collect(parse_stream(make_stream(chunks), schema=Film))
    assert not hasattr(results[-1], "extra_key")
    assert results[-1].title == "X"


class Award(BaseModel):
    name: str = ""
    year: int = 0
    won: bool = False


class Person(BaseModel):
    name: str = ""
    birth_year: int = 0
    awards: list[Award] = []


class Review(BaseModel):
    source: str = ""
    score: float = 0.0
    excerpt: str = ""


class Production(BaseModel):
    studio: str = ""
    budget_m: float = 0.0
    countries: list[str] = []


class DeepFilm(BaseModel):
    title: str = ""
    year: int = 0
    director: Person = Person()
    cast: list[Person] = []
    reviews: list[Review] = []
    production: Production = Production()


DEEP_JSON = json.dumps(
    {
        "title": "Inception",
        "year": 2010,
        "director": {
            "name": "Christopher Nolan",
            "birth_year": 1970,
            "awards": [
                {"name": "Saturn Award", "year": 2011, "won": True},
                {"name": "Hugo Award", "year": 2011, "won": False},
            ],
        },
        "cast": [
            {
                "name": "Leonardo DiCaprio",
                "birth_year": 1974,
                "awards": [{"name": "Oscar", "year": 2016, "won": True}],
            },
            {
                "name": "Joseph Gordon-Levitt",
                "birth_year": 1981,
                "awards": [],
            },
        ],
        "reviews": [
            {"source": "Variety", "score": 9.1, "excerpt": "Mind-bending"},
            {"source": "IGN", "score": 8.5, "excerpt": "Visually stunning"},
        ],
        "production": {
            "studio": "Warner Bros",
            "budget_m": 160.0,
            "countries": ["USA", "UK"],
        },
    }
)


async def test_deeply_nested_model_stream():
    rng = random.Random(7)
    s = DEEP_JSON
    chunks = []
    i = 0
    while i < len(s):
        size = rng.randint(1, 8)
        chunks.append(s[i : i + size])
        i += size

    results = await collect(parse_stream(make_stream(chunks), schema=DeepFilm))

    assert len(results) >= 1
    final: DeepFilm = results[-1]

    assert final == DeepFilm.model_validate_json(DEEP_JSON)

    assert final.title == "Inception"
    assert final.director.name == "Christopher Nolan"
    assert final.director.awards[0].name == "Saturn Award"
    assert final.director.awards[0].won is True
    assert final.director.awards[1].won is False

    assert len(final.cast) == 2
    assert final.cast[0].name == "Leonardo DiCaprio"
    assert final.cast[0].awards[0].year == 2016
    assert final.cast[1].name == "Joseph Gordon-Levitt"
    assert final.cast[1].awards == []

    assert final.reviews[0].source == "Variety"
    assert final.reviews[1].score == 8.5

    assert final.production.studio == "Warner Bros"
    assert final.production.countries == ["USA", "UK"]

    titles_seen = [r.title for r in results if r.title]
    assert all(t == "Inception" for t in titles_seen)


async def test_stress_1000_fields():
    data = {f"field_{i}": i for i in range(1000)}
    full = json.dumps(data)

    class BigModel(BaseModel):
        model_config = {"extra": "allow"}

    results = await collect(parse_stream(make_stream([full]), schema=BigModel))
    assert len(results) >= 1
    final = results[-1]
    assert final.field_0 == 0
    assert final.field_999 == 999
