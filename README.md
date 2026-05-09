# `jstream`

Turn a raw LLM token structured output stream into validated objects as fields complete.

```
"{"                                  → (nothing yet)
'{"title":"Inception",'              → {"title": "Inception"}
'{"title":"Inception","year":2010}'  → {"title": "Inception", "year": 2010}
```

## Install

```bash
pip install jstream
```

## Usage

### Without a schema — yields plain dicts

```python
from jstream import parse_stream

async for partial in parse_stream(token_stream):
    print(partial)  # {"title": "Inception"}, then {"title": "Inception", "year": 2010}, ...
```

### With a Pydantic schema — yields model instances

```python
from pydantic import BaseModel
from jstream import parse_stream

class Film(BaseModel):
    title: str = ""
    year: int = 0
    rating: float = 0.0

async for film in parse_stream(token_stream, schema=Film):
    print(film.title)  # populated as soon as "title" field closes
```

Incomplete fields receive model defaults. Extra keys are ignored by Pydantic, preserved in plain-dict mode.

### With the OpenAI SDK (and OpenRouter)

`delta.content` can be `None` on the first and last chunks — `jstream` skips them automatically.

```python
from openai import AsyncOpenAI
from jstream import parse_stream

client = AsyncOpenAI(base_url="https://openrouter.ai/api/v1", api_key="...")

async def token_stream(response):
    async for chunk in response:
        yield chunk.choices[0].delta.content  # None chunks are skipped

response = await client.chat.completions.create(
    model="openai/gpt-4o-mini",
    messages=[{"role": "user", "content": "..."}],
    response_format={"type": "json_schema", "json_schema": {"name": "film", "strict": True, "schema": schema}},
    stream=True,
)

async for film in parse_stream(token_stream(response), schema=Film):
    print(film.title)
```

## API

```python
async def parse_stream(
    stream: AsyncIterator[str],
    schema: type[BaseModel] | None = None,
) -> AsyncIterator[dict | BaseModel]:
```

`stream` — any async iterator of raw string chunks. Chunks need not align to field boundaries.

`schema` — optional Pydantic model. When provided, yields model instances; raises `JstreamValidationError` after the stream closes if the complete JSON fails validation.

## Behavior

| Situation                                       | Behavior                             |
| ----------------------------------------------- | ------------------------------------ |
| Chunk arrives mid-field                         | Silent — no yield until field closes |
| Chunk produces no new completed fields          | No yield (deduplicated)              |
| Stream closes on valid JSON                     | No error, even with schema           |
| Stream closes on invalid JSON (schema provided) | Raises `JstreamValidationError`      |
| Stream closes on invalid JSON (no schema)       | No error                             |
| Whitespace-only chunks                          | Skipped                              |
| `None` chunks                                   | Skipped (safe with OpenAI SDK deltas)|

## Error Handling

`JstreamValidationError` is raised after the stream is fully consumed, never mid-stream. Partial JSON during streaming is always silent.

```python
from jstream import parse_stream, JstreamValidationError

try:
    async for item in parse_stream(token_stream, schema=Film):
        ...
except JstreamValidationError as e:
    print(e.errors)  # Pydantic error list
    print(e.raw)     # the complete accumulated string
```
