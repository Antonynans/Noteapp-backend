# Quill API

FastAPI backend for the **Quill** app.

---
## Setup & Run

### 1. Install dependencies
```bash
pip install -r requirements.txt
```

### 2. Configure environment
```bash
cp .env.example .env
```

### 3. Run the server
```bash
uvicorn main:app --reload
```

### 4. View API docs
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

---

## Database

Uses **PostgreSQL** via SQLAlchemy. Tables are auto-created on startup.

For production, use **Alembic** for migrations:
```bash
pip install alembic
alembic init migrations
alembic revision --autogenerate -m "initial"
alembic upgrade head
```
# Noteapp-backend
