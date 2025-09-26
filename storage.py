import shutil
from pathlib import Path
from fastapi import UploadFile, HTTPException
import os


BASE_DIR = Path(__file__).parent
UPLOAD_DIR = BASE_DIR / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp"}


def _secure_filename(filename: str) -> str:
    name = Path(filename).name
    name = name.replace(' ', '_')
    name = name.replace('..', '')
    return name


def save_upload_file(upload_file: UploadFile, dest_dir: Path = UPLOAD_DIR) -> Path:
    """Save UploadFile to disk and return the Path."""
    filename = _secure_filename(upload_file.filename or "file")
    ext = filename.rsplit('.', 1)[-1].lower() if '.' in filename else ''
    if ext and ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail=f"Unsupported file extension: {ext}")

    dest = dest_dir / filename
    counter = 1
    while dest.exists():
        stem = filename.rsplit('.', 1)[0]
        dest = dest_dir / f"{stem}_{counter}.{ext}"
        counter += 1

    try:
        with dest.open("wb") as buffer:
            shutil.copyfileobj(upload_file.file, buffer)
    finally:
        try:
            upload_file.file.close()
        except Exception:
            pass

    return dest
