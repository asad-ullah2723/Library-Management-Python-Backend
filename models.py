from sqlalchemy import Column, Integer, String, Float, Date
from datetime import date
from database import Base

class Book(Base):
    __tablename__ = "books"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False, index=True)
    author = Column(String, nullable=False, index=True)
    isbn = Column(String, unique=True, index=True)
    price = Column(Float, nullable=True)
    published_date = Column(Date, default=date.today)
