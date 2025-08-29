from typing import List, Optional
from sqlalchemy.orm import Session
from models import Book
from schemas import BookCreate
from datetime import date

def add_book(book_data: BookCreate, db: Session) -> Book:
    new_book = Book(
        title=book_data.title,
        author=book_data.author,
        isbn=book_data.isbn,
        price=book_data.price,
        published_date=book_data.published_date or date.today()
    )
    db.add(new_book)
    db.commit()
    db.refresh(new_book)
    return new_book

def delete_book(book_id: int, db: Session) -> bool:
    book = db.query(Book).filter(Book.id == book_id).first()
    if not book:
        return False
    db.delete(book)
    db.commit()
    return True

def search_books(
    title: Optional[str] = None,
    author: Optional[str] = None,
    isbn: Optional[str] = None,
    min_price: Optional[float] = None,
    max_price: Optional[float] = None,
    published_after: Optional[date] = None,
    published_before: Optional[date] = None,
    db: Session = None
) -> List[Book]:
    query = db.query(Book)
    if title:
        query = query.filter(Book.title.ilike(f"%{title}%"))
    if author:
        query = query.filter(Book.author.ilike(f"%{author}%"))
    if isbn:
        query = query.filter(Book.isbn.ilike(f"%{isbn}%"))
    if min_price is not None:
        query = query.filter(Book.price >= min_price)
    if max_price is not None:
        query = query.filter(Book.price <= max_price)
    if published_after:
        query = query.filter(Book.published_date >= published_after)
    if published_before:
        query = query.filter(Book.published_date <= published_before)
    return query.all()
