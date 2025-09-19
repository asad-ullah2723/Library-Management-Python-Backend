from fastapi.testclient import TestClient
import main
import traceback
from datetime import date

client = TestClient(main.app)

print("-- GET /books/ --")
try:
    resp = client.get('/books/')
    print('STATUS:', resp.status_code)
    print('BODY:', resp.json())
except Exception:
    print('EXCEPTION during GET:')
    traceback.print_exc()

print("\n-- POST /books/ --")
sample = {
    "title": "QWQW",
    "author": "QWQ",
    "accession_number": "42",
    "publisher": "QWQ",
    "edition": "QWW",
    "isbn": "11111111111",
    "genre": "QWQ",
    "language": "QWQW",
    "pages": 121,
    "price": 1212,
    "date_of_purchase": "2025-09-01",
    "published_date": "2025-09-01",
    "current_status": "Available",
    "shelf_number": "121"
}
try:
    resp = client.post('/books/', json=sample)
    print('STATUS:', resp.status_code)
    print('BODY:', resp.json())
except Exception:
    print('EXCEPTION during POST:')
    traceback.print_exc()
