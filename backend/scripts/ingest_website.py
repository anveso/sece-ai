"""
One-off / re-runnable script: pull a curated list of sece.ac.in pages into
the SHARED institutional knowledge base, so every user's chat can search
official college content (not just what individuals happen to upload).

This does NOT crawl the whole site automatically - it fetches a fixed list
of URLs you give it. That's deliberate: a real crawler would also vacuum up
menus, cookie notices, and other low-value boilerplate, and could hammer
the site or wander into pages you didn't intend to publish into the shared
KB. Curate the URL list instead (a starter list is below).

Usage (run from the backend/ directory, with its virtualenv active and
requirements installed - beautifulsoup4 was just added, so re-run
`pip install -r requirements.txt` first if you set this venv up earlier):

    # Point at your PRODUCTION database - do NOT run this against your
    # local dev DB unless that's actually what you want. Get this value
    # from Render: sece-ai-db -> Connect -> "External Database URL".
    export DATABASE_URL="postgresql://...render.com/sece_ai"
    export OPENAI_API_KEY="sk-..."   # needed to generate embeddings

    python scripts/ingest_website.py --owner-email you@sece.ac.in

    # Or supply your own URL list instead of the built-in starter list:
    python scripts/ingest_website.py --owner-email you@sece.ac.in \\
        --urls https://sece.ac.in/admissions/,https://sece.ac.in/academics/

Re-running this script is safe: it replaces any existing shared document
with the same source URL rather than duplicating it, so you can re-run it
after the college website changes to refresh the shared knowledge base.
"""
import argparse
import sys
import time
from pathlib import Path

import httpx
from bs4 import BeautifulSoup

# Let this script import the `app` package when run as `python scripts/x.py`
# from the backend/ directory.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.database import SessionLocal, init_db  # noqa: E402
from app.models import Document, DocumentChunk, User  # noqa: E402
from app.rag.chunking import chunk_text  # noqa: E402
from app.rag.embeddings import embed_texts  # noqa: E402

# Starter list based on sece.ac.in's main navigation as of Sept 2026.
# Edit this freely - add department pages, specific policy pages, etc.
DEFAULT_URLS = [
    "https://sece.ac.in/",
    "https://sece.ac.in/governance/",
    "https://sece.ac.in/leadership/",
    "https://sece.ac.in/academics/",
    "https://sece.ac.in/research/",
    "https://sece.ac.in/innovation/",
    "https://sece.ac.in/international-relations-3/",
    "https://sece.ac.in/career-development/",
    "https://sece.ac.in/campus-life/",
    "https://sece.ac.in/admissions/",
    "https://sece.ac.in/iqac/",
]

HEADERS = {
    "User-Agent": "SECE-AI-Ingest/1.0 (+internal institutional knowledge base import)"
}


def fetch_page_text(url: str) -> str:
    resp = httpx.get(url, headers=HEADERS, timeout=30, follow_redirects=True)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")

    for tag in soup(["script", "style", "nav", "footer", "header", "noscript"]):
        tag.decompose()

    text = soup.get_text(separator="\n")
    lines = [line.strip() for line in text.splitlines()]
    return "\n".join(line for line in lines if line)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--owner-email",
        required=True,
        help="Existing user account these shared documents will be filed under "
        "(any account works - shared docs are visible to everyone regardless "
        "of who technically owns them).",
    )
    parser.add_argument(
        "--urls",
        help="Comma-separated URL list to ingest instead of the built-in starter list.",
    )
    args = parser.parse_args()

    urls = args.urls.split(",") if args.urls else DEFAULT_URLS

    init_db()  # make sure tables/columns exist before we touch them
    db = SessionLocal()

    owner = db.query(User).filter(User.email == args.owner_email).first()
    if not owner:
        print(f"No user found with email {args.owner_email!r}. Register that "
              f"account in the app first, then re-run this script.")
        sys.exit(1)

    for url in urls:
        url = url.strip()
        if not url:
            continue

        print(f"Fetching {url} ...")
        try:
            text = fetch_page_text(url)
        except Exception as exc:  # noqa: BLE001
            print(f"  FAILED to fetch: {exc}")
            continue

        if len(text) < 200:
            print(f"  Skipping - only {len(text)} chars of text extracted "
                  f"(likely a JS-rendered or mostly-empty page).")
            continue

        # Replace any previous ingest of this same URL so re-running the
        # script refreshes content instead of duplicating it.
        existing = (
            db.query(Document)
            .filter(Document.filename == url, Document.is_shared.is_(True))
            .first()
        )
        if existing:
            db.delete(existing)
            db.commit()

        document = Document(
            owner_id=owner.id,
            filename=url,
            content_type="text/html",
            status="processing",
            is_shared=True,
        )
        db.add(document)
        db.commit()
        db.refresh(document)

        chunks = chunk_text(text)
        if not chunks:
            document.status = "error"
            document.error_message = "No extractable text."
            db.commit()
            print("  No text after chunking - marked as error.")
            continue

        try:
            vectors = embed_texts(chunks)
        except Exception as exc:  # noqa: BLE001
            document.status = "error"
            document.error_message = str(exc)
            db.commit()
            print(f"  Embedding failed: {exc}")
            continue

        for index, (chunk, vector) in enumerate(zip(chunks, vectors)):
            db.add(
                DocumentChunk(
                    document_id=document.id,
                    chunk_index=index,
                    content=chunk,
                    embedding=vector,
                )
            )
        document.status = "ready"
        db.commit()
        print(f"  Ingested {len(chunks)} chunks.")

        time.sleep(1)  # be polite to the source site between requests

    db.close()
    print("Done.")


if __name__ == "__main__":
    main()
