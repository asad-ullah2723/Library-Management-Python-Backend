import os
import requests
from typing import Optional

# pCloud helper that talks to the official pCloud REST API when possible.
#
# Configuration via environment variables:
# - PCLOUD_UPLOAD_ENDPOINT: optional custom upload endpoint (your proxy). If set, we POST the file to this endpoint
#   and expect a JSON response containing a public URL (keys: url, public_url, link).
# - PCLOUD_UPLOAD_TOKEN: required unless you provide PCLOUD_UPLOAD_ENDPOINT; this should be a pCloud access token
#   (the OAuth2 access token or a long-lived token). If present we call api.pcloud.com endpoints directly.
# - PCLOUD_FOLDER_ID: optional numeric folder id to upload into (default: 0 / root)

PCLOUD_ENDPOINT = os.environ.get("PCLOUD_UPLOAD_ENDPOINT")
PCLOUD_TOKEN = os.environ.get("PCLOUD_UPLOAD_TOKEN")
PCLOUD_FOLDER_ID = os.environ.get("PCLOUD_FOLDER_ID")  # optional folder id


def is_configured() -> bool:
    """Return True if we have at least a token or custom endpoint configured."""
    return bool(PCLOUD_ENDPOINT or PCLOUD_TOKEN)


def _choose_filename(path: str, filename: Optional[str]) -> str:
    return filename or os.path.basename(path)


def upload_file_to_pcloud(path: str, filename: Optional[str] = None, folder_id: Optional[int] = None) -> str:
    """Upload a local file at `path` to pCloud and return a public URL.

    Behavior:
    - If PCLOUD_ENDPOINT is set, POST to that endpoint with the file form field named `file` and
      expect a JSON response with a URL under keys `url`, `public_url` or `link`.
    - Otherwise, if PCLOUD_UPLOAD_TOKEN is set, call the official pCloud API endpoints:
        1) POST https://api.pcloud.com/uploadfile?access_token=...&folderid=... with multipart file field `file`.
        2) On success read returned `metadata.fileid` or `fileid` and then call publishfile to obtain a public link.

    Raises RuntimeError on failure with a helpful message.
    """
    if not is_configured():
        raise RuntimeError("pCloud upload not configured. Set PCLOUD_UPLOAD_ENDPOINT or PCLOUD_UPLOAD_TOKEN.")

    filename = _choose_filename(path, filename)

    # 1) Use custom endpoint if provided
    if PCLOUD_ENDPOINT:
        with open(path, 'rb') as fh:
            files = {"file": (filename, fh)}
            headers = {"Authorization": f"Bearer {PCLOUD_TOKEN}"} if PCLOUD_TOKEN else {}
            resp = requests.post(PCLOUD_ENDPOINT, files=files, headers=headers, timeout=60)
        if resp.status_code not in (200, 201):
            raise RuntimeError(f"Custom pCloud endpoint upload failed: {resp.status_code} {resp.text}")
        data = resp.json()
        url = data.get("url") or data.get("public_url") or data.get("link")
        if not url:
            raise RuntimeError(f"Custom pCloud endpoint returned unexpected response: {data}")
        return url

    # 2) Use official pCloud API
    if not PCLOUD_TOKEN:
        raise RuntimeError("PCLOUD_UPLOAD_TOKEN is required to use the official pCloud API")

    # folder id preference: explicit param -> env var -> 0
    try:
        fid = int(folder_id) if folder_id is not None else (int(PCLOUD_FOLDER_ID) if PCLOUD_FOLDER_ID else 0)
    except Exception:
        fid = 0

    upload_url = f"https://api.pcloud.com/uploadfile"
    params = {"access_token": PCLOUD_TOKEN, "folderid": fid}
    with open(path, 'rb') as fh:
        files = {"file": (filename, fh)}
        resp = requests.post(upload_url, params=params, files=files, timeout=60)

    if resp.status_code != 200:
        raise RuntimeError(f"pCloud uploadfile failed: {resp.status_code} {resp.text}")

    data = resp.json()
    # The API typically returns something like: {"metadata": {"fileid": 12345, ...}, "result": 0}
    fileid = None
    if isinstance(data, dict):
        # try common locations
        metadata = data.get('metadata') or data.get('files') or {}
        if isinstance(metadata, dict):
            fileid = metadata.get('fileid') or metadata.get('id')
        # fallback: top-level fileid
        if not fileid:
            fileid = data.get('fileid') or data.get('id')

    if not fileid:
        raise RuntimeError(f"pCloud upload returned unexpected response, missing file id: {data}")

    # Publish the file to get a public link
    publish_url = f"https://api.pcloud.com/publishfile"
    params = {"access_token": PCLOUD_TOKEN, "fileid": fileid}
    resp2 = requests.get(publish_url, params=params, timeout=30)
    if resp2.status_code != 200:
        raise RuntimeError(f"pCloud publishfile failed: {resp2.status_code} {resp2.text}")
    data2 = resp2.json()
    # typical response: {"result":0, "publiclink":"https://..."}
    publiclink = data2.get('publiclink') or data2.get('public_url') or data2.get('link') or data2.get('url')
    if not publiclink:
        # Some setups might return a `hosts` + `path` fields; as a last resort return a fileid-based link
        # but inform the caller
        raise RuntimeError(f"pCloud publishfile returned unexpected response: {data2}")

    return publiclink
