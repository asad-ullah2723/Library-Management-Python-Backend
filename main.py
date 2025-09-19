import uvicorn
from datetime import date, datetime
from typing import List, Optional
from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from schemas import BookCreate, BookOut
from crud import add_book, delete_book, search_books, get_books, get_book_by_id, update_book
from schemas import MemberCreate, MemberOut, MemberUpdate
from crud import add_member, get_members, get_member_by_id, update_member, delete_member
from schemas import StaffCreate, StaffOut, StaffUpdate
from crud import add_staff, get_staff, get_staff_by_id, update_staff, delete_staff
from database import get_db, engine, Base
import models  # ensure models are imported so tables are registered
from auth import router as auth_router
import auth_utils


# Initialize FastAPI app with debug mode
app = FastAPI(debug=True)

# Configure CORS as the first middleware
origins = [
    "http://localhost:3000",
    "http://127.0.0.1:3000"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
    max_age=600
)

# Add middleware to log all requests for debugging
@app.middleware("http")
async def log_requests(request, call_next):
    print(f"Incoming request: {request.method} {request.url}")
    print(f"Headers: {request.headers}")
    response = await call_next(request)
    print(f"Response status: {response.status_code}")
    return response
# Include auth router
app.include_router(auth_router)

@app.on_event("startup")
def on_startup():
    Base.metadata.create_all(bind=engine)
    # Create a default admin user if not exists
    db = next(get_db())
    admin_email = "admin@example.com"
    admin_password = "admin123"
    admin_user = db.query(models.User).filter(models.User.email == admin_email).first()
    if not admin_user:
        hashed_password = auth_utils.get_password_hash(admin_password)
        admin_user = models.User(
            email=admin_email,
            hashed_password=hashed_password,
            full_name="Admin User",
            is_superuser=True,
            created_at=datetime.utcnow()
        )
        db.add(admin_user)
        db.commit()
        print(f"Created default admin user with email: {admin_email} and password: {admin_password}")
    db.close()

@app.get("/books/", response_model=List[BookOut])
def list_books(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """
    Retrieve all books with pagination.
    - **skip**: Number of records to skip (for pagination)
    - **limit**: Maximum number of records to return (for pagination)
    """
    books = get_books(db, skip=skip, limit=limit)
    return books

@app.post("/books/", response_model=BookOut)
def create_book(book: BookCreate, db: Session = Depends(get_db)):
    try:
        return add_book(book, db)
    except Exception as e:
        # Log and convert to HTTP error so clients see a concise message
        import traceback
        print("Error creating book:", e)
        traceback.print_exc()
        raise HTTPException(status_code=400, detail=str(e))

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


@app.get("/books/{book_id}", response_model=BookOut)
def retrieve_book(book_id: int, db: Session = Depends(get_db)):
    b = get_book_by_id(book_id, db)
    if not b:
        raise HTTPException(status_code=404, detail="Book not found")
    return b


@app.put("/books/{book_id}", response_model=BookOut)
def modify_book(book_id: int, book: BookCreate, db: Session = Depends(get_db)):
    updated = update_book(book_id, book, db)
    if not updated:
        raise HTTPException(status_code=404, detail="Book not found")
    return updated


@app.get("/members/", response_model=List[MemberOut])
def list_members(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """List members with pagination"""
    return get_members(db, skip=skip, limit=limit)


@app.post("/members/", response_model=MemberOut)
def create_member(member: MemberCreate, db: Session = Depends(get_db)):
    return add_member(member, db)


@app.get("/members/{member_id}", response_model=MemberOut)
def retrieve_member(member_id: int, db: Session = Depends(get_db)):
    m = get_member_by_id(member_id, db)
    if not m:
        raise HTTPException(status_code=404, detail="Member not found")
    return m


@app.put("/members/{member_id}", response_model=MemberOut)
def modify_member(member_id: int, member: MemberUpdate, db: Session = Depends(get_db)):
    updated = update_member(member_id, member, db)
    if not updated:
        raise HTTPException(status_code=404, detail="Member not found")
    return updated


@app.delete("/members/{member_id}")
def remove_member(member_id: int, db: Session = Depends(get_db)):
    ok = delete_member(member_id, db)
    if not ok:
        raise HTTPException(status_code=404, detail="Member not found")
    return {"detail": "Member deleted"}


@app.get("/staff/", response_model=List[StaffOut])
def list_staff(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return get_staff(db, skip=skip, limit=limit)


@app.post("/staff/", response_model=StaffOut)
def create_staff(staff: StaffCreate, db: Session = Depends(get_db)):
    return add_staff(staff, db)


@app.get("/staff/{staff_id}", response_model=StaffOut)
def retrieve_staff(staff_id: int, db: Session = Depends(get_db)):
    s = get_staff_by_id(staff_id, db)
    if not s:
        raise HTTPException(status_code=404, detail="Staff not found")
    return s


@app.put("/staff/{staff_id}", response_model=StaffOut)
def modify_staff(staff_id: int, staff: StaffUpdate, db: Session = Depends(get_db)):
    updated = update_staff(staff_id, staff, db)
    if not updated:
        raise HTTPException(status_code=404, detail="Staff not found")
    return updated


@app.delete("/staff/{staff_id}")
def remove_staff(staff_id: int, db: Session = Depends(get_db)):
    ok = delete_staff(staff_id, db)
    if not ok:
        raise HTTPException(status_code=404, detail="Staff not found")
    return {"detail": "Staff deleted"}

# Add this to run the application directly
if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=9000,
        reload=True
    )

#ddsdsf