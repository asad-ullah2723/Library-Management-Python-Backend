from datetime import date
from pydantic import BaseModel, ConfigDict, Field
from typing import Optional

class BookCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=100)
    author: str = Field(..., min_length=1, max_length=100)
    isbn: str = Field(..., min_length=1, max_length=50)  # More lenient ISBN validation
    price: Optional[float] = Field(None, gt=0, description="Price must be greater than 0")
    published_date: Optional[date] = None

class BookOut(BookCreate):
    id: int
    model_config = ConfigDict(from_attributes=True)