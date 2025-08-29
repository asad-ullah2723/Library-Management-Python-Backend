from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# PostgreSQL connection details
# user: postgres
# password: 123
 # db: librarydb
 # host: localhost
 # port: 5432 (default)
DATABASE_URL = "postgresql+psycopg://postgres:123@localhost:5432/librarydb"

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

 # FastAPI dependency

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
