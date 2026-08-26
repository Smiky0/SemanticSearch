import urllib.parse
from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.config import get_settings

settings = get_settings()

_db_url = settings.database_url

ssl_mode = None
_ASYNCPG_UNSUPPORTED = {"sslmode", "channel_binding"}

if "?" in _db_url:
    base, query = _db_url.split("?", 1)
    params = dict(urllib.parse.parse_qsl(query))
    ssl_mode = params.pop("sslmode", None)
    for key in list(params):
        if key in _ASYNCPG_UNSUPPORTED:
            del params[key]
    _db_url = base
    if params:
        _db_url += "?" + urllib.parse.urlencode(params)

if _db_url.startswith("postgresql+psycopg://"):
    _db_url = _db_url.replace("postgresql+psycopg://", "postgresql+asyncpg://", 1)
elif _db_url.startswith("postgresql://"):
    _db_url = _db_url.replace("postgresql://", "postgresql+asyncpg://", 1)

_connect_args = {}
if ssl_mode:
    _connect_args["ssl"] = ssl_mode

_engine_kwargs: dict = {"echo": False}
if _connect_args:
    _engine_kwargs["connect_args"] = _connect_args

engine = create_async_engine(_db_url, **_engine_kwargs)
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with async_session() as session:
        yield session
