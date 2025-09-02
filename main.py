import uvicorn
from datetime import date
from typing import List, Optional
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from schemas import BookCreate, BookOut
from crud import add_book, delete_book, search_books
from database import get_db, engine, Base
import models  # ensure models are imported so tables are registered


# Initialize FastAPI app with debug mode
app = FastAPI(debug=True)

# Configure CORS as the first middleware
origins = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "*"  # For testing only, restrict in production
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
    max_age=600,
)

# Add middleware to log all requests for debugging
@app.middleware("http")
async def log_requests(request, call_next):
    print(f"Incoming request: {request.method} {request.url}")
    print(f"Headers: {request.headers}")
    response = await call_next(request)
    print(f"Response status: {response.status_code}")
    return response
@app.on_event("startup")
def on_startup():
    Base.metadata.create_all(bind=engine)

@app.post("/books", response_model=BookOut)
def create_book(book: BookCreate, db: Session = Depends(get_db)):
    return add_book(book, db)

@app.delete("/books/{book_id}")
def remove_book(book_id: int, db: Session = Depends(get_db)):
    ok = delete_book(book_id, db)
    if not ok:
        raise HTTPException(status_code=404, detail="Book not found")
    return {"detail": "Book deleted"}

@app.get("/books/search", response_model=List[BookOut])
def search(
    title: Optional[str] = None,
    author: Optional[str] = None,
    isbn: Optional[str] = None,
    min_price: Optional[float] = None,
    max_price: Optional[float] = None,
    published_after: Optional[date] = None,
    published_before: Optional[date] = None,
    db: Session = Depends(get_db)
):
    try:
        print("Searching books with params:", {
            "title": title,
            "author": author,
            "isbn": isbn,
            "min_price": min_price,
            "max_price": max_price,
            "published_after": published_after,
            "published_before": published_before
        })
        result = search_books(
            title=title,
            author=author,
            isbn=isbn,
            min_price=min_price,
            max_price=max_price,
            published_after=published_after,
            published_before=published_before,
            db=db
        )
        print(f"Found {len(result)} books")
        return result
    except Exception as e:
        print(f"Error in search: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

# Add this to run the application directly
if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=9000,
        reload=True
    )

#ddsdsf