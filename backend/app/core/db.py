import os
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from .config import DATABASE_URL

os.makedirs("data", exist_ok=True)

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SeesionLocal = sessionmaker(bind=engine, autoflush=False)

class Base(DeclarativeBase):
    pass


def get_db():
    db = SeesionLocal()
    try:
        yield db
    finally:
        db.close()