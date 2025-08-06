from fastapi import FastAPI, HTTPException
from typing import List, Optional
from models import Book
from schemas import BookCreate, BookOut
from crud import add_book, delete_book, search_books
from fastapi.middleware.cors import CORSMiddleware


app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # React dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
books_db: List[Book] = []

@app.post("/books", response_model=BookOut)
def create_book(book: BookCreate):
    return add_book(book, books_db)

@app.delete("/books/{book_id}")
def remove_book(book_id: int):
    return delete_book(book_id, books_db)

@app.get("/books/search", response_model=List[BookOut])
def search(title: Optional[str] = None, author: Optional[str] = None):
    return search_books(title, author, books_db)
