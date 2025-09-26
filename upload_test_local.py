import requests
import os

# Quick local uploader script to test POST /books/ with multipart/form-data
# Usage:
#   set PCLOUD_UPLOAD_TOKEN and PCLOUD_FOLDER_ID in your shell if you want server to upload to pCloud
#   python upload_test_local.py <image_path>

BASE = os.environ.get('BASE_URL', 'http://localhost:9000')
TOKEN = os.environ.get('TEST_TOKEN')  # if you have a JWT token, set this env var for Authorization

import sys
if len(sys.argv) < 2:
    print('Usage: python upload_test_local.py <image_path>')
    sys.exit(1)

img = sys.argv[1]

book_json = {
    "accession_number": "ACC-UPLOAD-TEST-1",
    "title": "Upload Test Book",
    "author": "Tester",
    "publisher": "Local",
    "isbn": "TEST-ISBN-1234",
    "price": 1.23
}

files = {
    'book': (None, requests.utils.json.dumps(book_json), 'application/json'),
    'file': (os.path.basename(img), open(img, 'rb'), 'application/octet-stream')
}

headers = {}
if TOKEN:
    headers['Authorization'] = f'Bearer {TOKEN}'

resp = requests.post(f"{BASE}/books/", files=files, headers=headers)
print('status', resp.status_code)
print(resp.text)
