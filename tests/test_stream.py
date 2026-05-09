import pytest
from pydantic import BaseModel

from jstream import JstreamValidationError, parse_stream
from tests.conftest import make_char_stream, make_stream


class Movie(BaseModel):
    title: str = ""
    year: int = 0
    active: bool = False


async def collect(gen) -> list:
    return [item async for item in gen]


async def test_full_json_one_chunk():
    chunks = ['{"title":"Inception","year":2010}']
    results = await collect(parse_stream(make_stream(chunks)))
    assert results[-1] == {"title": "Inception", "year": 2010}


async def test_char_by_char():
    s = '{"title":"Hi","year":2020}'
    results = await collect(parse_stream(make_char_stream(s)))
    assert len(results) >= 1
    assert results[-1] == {"title": "Hi", "year": 2020}


async def test_empty_stream():
    results = await collect(parse_stream(make_stream([])))
    assert results == []


async def test_malformed_final_raises():
    with pytest.raises(JstreamValidationError):

        async def bad_stream():
            yield '{"title":"ok"'
            yield ',"year":"not_an_int"}'

        async for _ in parse_stream(bad_stream(), schema=Movie):
            pass


async def test_yields_progressively_richer_snapshots():
    chunks = ['{"title":"Inception"', ',"year":2010', ',"active":true}']
    results = await collect(parse_stream(make_stream(chunks)))

    assert len(results) == 3
    assert results[0] == {"title": "Inception"}
    assert results[1] == {"title": "Inception", "year": 2010}
    assert results[2] == {"title": "Inception", "year": 2010, "active": True}


async def test_deduplication():
    chunks = ['{"title":"X"', "", "", ""]
    results = await collect(parse_stream(make_stream(chunks)))
    assert results.count({"title": "X"}) == 1


async def test_with_schema_fields_arrive():
    chunks = ['{"title":"Inc', 'eption","year":2010}']
    results = await collect(parse_stream(make_stream(chunks), schema=Movie))
    assert all(isinstance(r, Movie) for r in results)
    assert results[-1].title == "Inception"
    assert results[-1].year == 2010


async def test_with_schema_wrong_type_raises():
    with pytest.raises(JstreamValidationError) as exc_info:

        async def typed_stream():
            yield '{"year":["not","an","int"]}'

        async for _ in parse_stream(typed_stream(), schema=Movie):
            pass

    assert exc_info.value.errors


async def test_with_schema_nested_optional():
    class Inner(BaseModel):
        val: int = 0

    class Outer(BaseModel):
        name: str = ""
        inner: Inner | None = None

    chunks = ['{"name":"test","inner":{"val":42}}']
    results = await collect(parse_stream(make_stream(chunks), schema=Outer))
    assert results[-1].inner is not None
    assert results[-1].inner.val == 42


async def test_none_chunks_are_skipped():
    async def openai_like_stream():
        yield None
        yield '{"title":'
        yield '"Inception"}'
        yield None

    results = await collect(parse_stream(openai_like_stream()))
    assert results[-1] == {"title": "Inception"}
