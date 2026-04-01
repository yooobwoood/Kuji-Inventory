from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text

from app.core.database import SessionLocal
from app.routers import auth, grades, inventory, pages, products, users

app = FastAPI(title="Kuji Inventory", version="0.2.0")

app.mount("/static", StaticFiles(directory="app/static"), name="static")

app.include_router(pages.router)
app.include_router(products.router)
app.include_router(grades.router)
app.include_router(inventory.router)
app.include_router(users.router)
app.include_router(auth.router)


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

