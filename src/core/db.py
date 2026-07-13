from collections.abc import Generator
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from src.core.config import config


class Base(DeclarativeBase):
    pass


engine = create_engine(
    config.database.url,
    echo=config.database.echo,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Generator[Session]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db(sql_path: str | Path | None = None) -> None:
    if sql_path:
        sql_path = Path(sql_path)
        if sql_path.exists():
            conn = engine.raw_connection()
            try:
                with open(sql_path) as f:
                    conn.executescript(f.read())
                conn.commit()
            finally:
                conn.close()
    else:
        Base.metadata.create_all(bind=engine)


def drop_db() -> None:
    Base.metadata.drop_all(bind=engine)
