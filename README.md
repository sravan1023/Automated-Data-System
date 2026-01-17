# Automated Data System (FLowDoc)
Automated document generation platform that transforms your data into formatted PDFs using customizable templates.

## Features

- Upload CSV/Excel files and preview data
- Create HTML/CSS templates with Monaco editor and Jinja2 templating
- Batch generate personalized PDFs
- Multi-workspace organization
- Download individual PDFs or ZIP archives

## Tech Stack

**Backend:** FastAPI, SQLAlchemy, PostgreSQL, Celery, Redis, Playwright, MinIO  
**Frontend:** Next.js 14, TypeScript, TailwindCSS, shadcn/ui, TanStack Query

## Quick Start

### Prerequisites

- **Docker Desktop** (Windows/Mac) or Docker & Docker Compose (Linux)
- **Node.js 20+** and npm
- Git

### Setup & Run

#### 1. Clone the repository
```bash
git clone https://github.com/sravan1023/Automated-Data-System.git
cd Automated-Data-System
```

#### 2. Configure environment
```bash
cp .env.example .env

# Edit .env if needed (default values work for local development)
```

#### 3. Start all backend services (Docker)
```bash
cd infrastructure/docker
docker compose up -d
```

This starts:
- PostgreSQL (database) on port 5432
- Redis (cache/queue) on port 6379
- MinIO (storage) on ports 9000-9001
- FastAPI backend on port 8000
- Celery worker (PDF generation)
- Celery beat (scheduled tasks)

#### 4. Run database migrations
```bash
# From the project root
docker exec docker-backend-1 alembic upgrade head
```

#### 5. Install dependencies and start Next.js
```bash
# From the project root
npm install
npm run dev
```

#### 6. Access the application
- **Web App:** http://localhost:3000
- **MinIO Console:** http://localhost:9001 (minioadmin / minioadmin)

### Verify Setup

Check if all services are running:
```bash
cd infrastructure/docker
docker compose ps
```

All containers should show "Up" or "healthy" status.

### Stop Services

```bash
# Stop all Docker services
cd infrastructure/docker
docker compose down
```

### Troubleshooting

**Docker services not starting:**
```bash
docker compose logs backend
docker compose logs worker
```

**Database connection errors:**
```bash
# Restart backend after database is fully ready
docker compose restart backend
```

## Project Structure

```
├── server/               # FastAPI backend
│   ├── api/             # API routes
│   ├── models/          # Database models
│   ├── schemas/         # Pydantic schemas
│   ├── services/        # Business logic
│   └── workers/         # Celery tasks
├── src/                 # Next.js frontend
│   ├── app/            # App Router pages
│   ├── components/     # React components
│   └── lib/            # Utilities & API client
├── alembic/            # Database migrations
├── infrastructure/     # Docker configs
│   └── docker/         # docker-compose.yml
├── .env                
└── README.md
```


## License

MIT
