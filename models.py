from sqlalchemy import Column, Integer, String, Float, Date, Boolean
from datetime import datetime, date
from database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    full_name = Column(String)
    is_active = Column(Boolean, default=True)
    is_superuser = Column(Boolean, default=False)
    created_at = Column(Date, default=datetime.utcnow)
    reset_password_token = Column(String, nullable=True)
    reset_password_expires = Column(Date, nullable=True)


class Book(Base):
    __tablename__ = "books"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False, index=True)
    author = Column(String, nullable=False, index=True)
    isbn = Column(String, unique=True, index=True)
    price = Column(Float, nullable=True)
    published_date = Column(Date, default=date.today)
    owner_id = Column(Integer, index=True)
