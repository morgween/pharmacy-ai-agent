"""database session helpers"""
from contextlib import contextmanager
from typing import Generator
from sqlalchemy.orm import Session


@contextmanager
def get_db_session(session_factory, commit: bool = False) -> Generator[Session, None, None]:
    """provide a managed session with optional commit and rollback"""
    session = session_factory()
    try:
        yield session
        if commit:
            session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
