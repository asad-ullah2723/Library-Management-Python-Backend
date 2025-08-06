from models import Book
from schemas import BookCreate
from typing import List, Optional

def add_book(book_data: BookCreate, db: List[Book]) -> Book:
    new_book = Book(title=book_data.title, author=book_data.author)
    db.append(new_book)
    return new_book

def delete_book(book_id: int, db: List[Book]):
    for book in db:
        if book.id == book_id:
            db.remove(book)
            return {"detail": "Book deleted"}
    raise Exception("Book not found")

def search_books(title: Optional[str], author: Optional[str], db: List[Book]) -> List[Book]:
    results = db
    if title:
        results = [b for b in results if title.lower() in b.title.lower()]
    if author:
        results = [b for b in results if author.lower() in b.author.lower()]
    return results
