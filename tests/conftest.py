from collections.abc import AsyncIterator


async def make_stream(chunks: list[str]) -> AsyncIterator[str]:
    for chunk in chunks:
        yield chunk


async def make_char_stream(s: str) -> AsyncIterator[str]:
    for ch in s:
        yield ch
