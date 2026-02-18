from contextlib import contextmanager
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from qcscan.models import Base


def init_db(db_path: str) -> None:
    engine = create_engine(f"sqlite:///{db_path}")
    Base.metadata.create_all(engine)


@contextmanager
def get_session(db_path: str):
    engine = create_engine(f"sqlite:///{db_path}")

    # ✅ Prevent SQLAlchemy from expiring ORM objects on commit.
    # This avoids DetachedInstanceError when we access attributes after the session closes.
    Session = sessionmaker(bind=engine, expire_on_commit=False)

    session = Session()
    try:
        yield session
        session.commit()
    finally:
        session.close()
