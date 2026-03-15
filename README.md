# DevNote API

FastAPI backend for the **DevNote / Notes by Skillz** app.

---

## Project Structure

```
devnote/
├── main.py               # App entry point
├── requirements.txt
├── .env.example
├── core/
│   ├── config.py         # Environment settings
│   └── security.py       # JWT auth + password hashing
├── db/
│   └── database.py       # SQLAlchemy engine + session
├── models/
│   ├── user.py           # User table
│   └── note.py           # Note table
├── schemas/
│   ├── auth.py           # Auth request/response schemas
│   └── note.py           # Note request/response schemas
└── routers/
    ├── auth.py           # /auth endpoints
    └── notes.py          # /notes endpoints
```

---

## Setup & Run

### 1. Install dependencies
```bash
pip install -r requirements.txt
```

### 2. Configure environment
```bash
cp .env.example .env
# Edit .env with your PostgreSQL credentials and secret key
```

### 3. Run the server
```bash
uvicorn main:app --reload
```

### 4. View API docs
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

---

## API Endpoints

### Authentication
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/auth/signup` | Register new user |
| POST | `/auth/login` | Login, returns JWT token |
| GET | `/auth/me` | Get current user |

### Notes (all require Bearer token)
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/notes` | List notes (paginated + search) |
| POST | `/notes` | Create a note |
| GET | `/notes/{id}` | Get a single note |
| PATCH | `/notes/{id}` | Update title/description |
| DELETE | `/notes/{id}` | Delete a note |
| POST | `/notes/{id}/lock` | Lock a note |
| POST | `/notes/{id}/unlock` | Unlock a note |

### Query params for GET /notes
| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `page` | int | 1 | Page number |
| `page_size` | int | 10 | Items per page (max 50) |
| `search` | string | - | Search by title or description |

---

## Authentication Flow

1. User signs up → receives JWT token
2. User logs in → receives JWT token
3. All `/notes` requests require `Authorization: Bearer <token>` header

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
