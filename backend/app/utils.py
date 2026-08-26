import uuid

from app.exceptions import InvalidUUIDError


def parse_uuid(value: str) -> uuid.UUID:
    try:
        return uuid.UUID(value)
    except ValueError:
        raise InvalidUUIDError(value)
