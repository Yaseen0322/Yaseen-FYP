"""
Database configuration, session management, and migration verification.
"""
from pathlib import Path
from urllib.parse import unquote

from alembic.config import Config
from alembic.runtime.migration import MigrationContext
from alembic.script import ScriptDirectory
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from .config import settings


BACKEND_ROOT = Path(__file__).resolve().parents[2]
BASE_DIR = BACKEND_ROOT
DEFAULT_SQLITE_DATABASE = "activity_tracker.db"


def sqlite_file_url(database_path: Path) -> str:
    """
    Build a Linux-safe SQLAlchemy SQLite URL for an absolute filesystem path.
    Absolute paths require four leading slashes: sqlite:////home/user/app.db
    """
    absolute_path = database_path.expanduser().resolve()
    absolute_path.parent.mkdir(parents=True, exist_ok=True)
    return f"sqlite:////{absolute_path.as_posix().lstrip('/')}"


def normalize_database_url(database_url: str) -> str:
    if not database_url.startswith("sqlite:///"):
        return database_url

    sqlite_path = unquote(database_url.removeprefix("sqlite:///"))
    if sqlite_path == ":memory:":
        return database_url

    if not sqlite_path:
        sqlite_path = DEFAULT_SQLITE_DATABASE

    path = Path(sqlite_path).expanduser()
    if path.is_absolute():
        if path.exists() or path.parent.exists():
            return sqlite_file_url(path)

        # A renamed project folder can leave .env pointing at the old absolute
        # directory. Preserve the intended database filename but re-home it to
        # the current backend root instead of crashing on a missing parent.
        return sqlite_file_url(BACKEND_ROOT / path.name)

    return sqlite_file_url(BACKEND_ROOT / path)


def get_engine_kwargs(database_url: str) -> dict:
    kwargs = {"pool_pre_ping": True}
    if database_url.startswith("sqlite"):
        kwargs["connect_args"] = {"check_same_thread": False}
    else:
        kwargs["pool_size"] = 10
        kwargs["max_overflow"] = 20
    return kwargs


def create_db_engine(database_url: str | None = None):
    resolved_url = normalize_database_url(database_url or settings.DATABASE_URL)
    return create_engine(
        resolved_url,
        **get_engine_kwargs(resolved_url),
    )


def build_alembic_config(database_url: str | None = None) -> Config:
    config = Config(str(BASE_DIR / "alembic.ini"))
    config.set_main_option("script_location", str(BASE_DIR / "migrations"))
    config.set_main_option(
        "sqlalchemy.url",
        normalize_database_url(database_url or settings.DATABASE_URL),
    )
    return config


# Create database engine
engine = create_db_engine()

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for models
Base = declarative_base()


def get_db():
    """
    Dependency to get database session
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def verify_schema_up_to_date(engine_instance=None, database_url: str | None = None):
    """
    Ensure the connected database is migrated to the current Alembic head.
    """
    if settings.ENVIRONMENT == "test":
        return

    config = build_alembic_config(database_url)
    script = ScriptDirectory.from_config(config)
    expected_heads = set(script.get_heads())

    connection_engine = engine_instance or create_db_engine(database_url)
    should_dispose = engine_instance is None
    try:
        with connection_engine.connect() as connection:
            context = MigrationContext.configure(connection)
            current_heads = set(context.get_current_heads())
    finally:
        if should_dispose:
            connection_engine.dispose()

    if not current_heads:
        raise RuntimeError(
            "Database schema is not initialized. Run `alembic upgrade head` before starting the backend."
        )

    if current_heads != expected_heads:
        raise RuntimeError(
            "Database schema is not up to date. Run `alembic upgrade head` before starting the backend."
        )
