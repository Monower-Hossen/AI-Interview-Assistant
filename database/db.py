from collections.abc import Generator
from contextlib import contextmanager

from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import NullPool

from config.settings import settings
from database.models import Base

engine = None
SessionLocal: sessionmaker | None = None
_MAX_DETACH_REFRESH = 50


def _detach_all(db: Session) -> None:
    """Detach every instance with its column values loaded.

    Commits and rollbacks mark column attributes as expired, and closed
    sessions cannot reload them, so callers that keep rows around after the
    context block would hit DetachedInstanceError. Refreshing first makes the
    objects detached but fully readable.
    """
    try:
        db.flush()
    except Exception:
        db.rollback()

    instances = list(db.identity_map.values())
    if len(instances) <= _MAX_DETACH_REFRESH:
        for instance in instances:
            try:
                db.refresh(instance)
            except Exception:
                pass

    db.expunge_all()


def init_database() -> None:
    global engine, SessionLocal

    if engine is not None:
        engine.dispose()

    database_url = f"sqlite:///{settings.database_path}"

    engine = create_engine(
        database_url,
        connect_args={"check_same_thread": False},
        poolclass=NullPool,
        pool_pre_ping=True,
        echo=False,
    )

    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA synchronous=NORMAL")
        cursor.close()

    SessionLocal = sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=engine,
        expire_on_commit=False,
    )

    Base.metadata.create_all(bind=engine)


def get_db() -> Generator[Session, None, None]:
    if SessionLocal is None:
        init_database()

    assert SessionLocal is not None
    db = SessionLocal()
    try:
        yield db
    finally:
        _detach_all(db)
        db.close()


@contextmanager
def get_db_context() -> Generator[Session, None, None]:
    """Transactional session that stays readable after the block exits.

    ORM objects are detached on close instead of expired, so UI code can keep
    rendering rows fetched inside the ``with`` block.
    """
    if SessionLocal is None:
        init_database()

    assert SessionLocal is not None
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        _detach_all(db)
        db.close()


@contextmanager
def get_readonly_db() -> Generator[Session, None, None]:
    """Read-only session context: no commit, rollback on error, safe for reporting."""
    if SessionLocal is None:
        init_database()

    assert SessionLocal is not None
    db = SessionLocal()
    try:
        yield db
    except Exception:
        db.rollback()
        raise
    finally:
        _detach_all(db)
        db.close()


def create_session() -> Session:
    """Create a new SQLAlchemy Session without a context manager."""
    if SessionLocal is None:
        init_database()

    assert SessionLocal is not None
    return SessionLocal()


def close_database() -> None:
    global engine
    if engine:
        engine.dispose()
        engine = None
