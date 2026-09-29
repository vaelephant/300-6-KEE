from sqlalchemy import create_engine, text, inspect
from sqlalchemy.orm import sessionmaker
from app.core.config import settings

url = settings.database_url.replace("sqlite+aiosqlite://", "sqlite+pysqlite://").replace(
    "postgresql+asyncpg://", "postgresql+psycopg://"
)
engine = create_engine(
    url,
    future=True,
    connect_args={"check_same_thread": False} if url.startswith("sqlite") else {},
)
SessionLocal = sessionmaker(engine, expire_on_commit=False)


def _ensure_columns():
    """Additive patches for existing DBs (create_all does not ALTER)."""
    insp = inspect(engine)
    patches: list[tuple[str, str, str]] = [
        ("documents", "domain", "VARCHAR(128) DEFAULT 'general'"),
        ("documents", "job_id", "VARCHAR(64)"),
        ("documents", "error", "TEXT"),
        ("documents", "updated_at", "TIMESTAMP"),
    ]
    with engine.begin() as conn:
        for table, col, typedef in patches:
            if table not in insp.get_table_names():
                continue
            existing = {c["name"] for c in insp.get_columns(table)}
            if col not in existing:
                conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {col} {typedef}"))


def init_db():
    from app.db.tables import Base

    Base.metadata.create_all(engine)
    try:
        _ensure_columns()
    except Exception:
        pass
