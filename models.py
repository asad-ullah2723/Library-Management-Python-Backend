from pydantic import BaseModel

class Book:
    id_counter = 1

    def __init__(self, title: str, author: str):
        self.id = Book.id_counter
        self.title = title
        self.author = author
        Book.id_counter += 1
