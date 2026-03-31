from fastapi import FastAPI
from sqlalchemy import text

from app.core.database import SessionLocal


app = FastAPI(title="Kuji Inventory")


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/health/db")
def health_db():
    db = SessionLocal()
    try:
        db.execute(text("SELECT 1"))
        return {"status": "ok"}
    finally:
        db.close()

