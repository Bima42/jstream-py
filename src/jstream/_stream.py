import contextlib
from collections.abc import AsyncIterator

from pydantic import BaseModel, ValidationError

from ._parser import parse_partial


class JstreamValidationError(Exception):
    def __init__(self, errors: list[dict], raw: str) -> None:
        self.errors = errors
        self.raw = raw
        super().__init__(f"Stream validation failed: {errors}")


async def parse_stream(
    stream: AsyncIterator[str],
    schema: type[BaseModel] | None = None,
) -> AsyncIterator[dict | BaseModel]:
    """Consume a partial-JSON token stream; yield objects as fields complete."""
    accumulated = ""
    last_emitted: dict | None = None

    async for chunk in stream:
        if not isinstance(chunk, str):
            continue
        accumulated += chunk
        candidate = parse_partial(accumulated)
        if candidate is not None and candidate != last_emitted:
            last_emitted = candidate
            if schema:
                with contextlib.suppress(ValidationError):
                    yield schema.model_validate(candidate)
            else:
                yield candidate

    if accumulated.strip() and schema:
        try:
            schema.model_validate_json(accumulated)
        except ValidationError as e:
            raise JstreamValidationError(errors=e.errors(), raw=accumulated) from e
