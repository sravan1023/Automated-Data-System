# AutoDocs AI

Automated document generation platform that transforms your data into beautifully formatted PDFs using customizable templates.

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

- Docker & Docker Compose
- Node.js 20+
- Python 3.11+

### Setup

1. Clone the repository
```bash
git clone https://github.com/sravan1023/flowdoc
cd flowdoc
```

2. Start infrastructure (PostgreSQL, Redis, MinIO)
```bash
docker-compose -f infrastructure/docker/docker-compose.yml up -d
```

3. Set up backend
```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env  # Update with your configuration
alembic upgrade head
```

4. Start Celery worker
```bash
celery -A app.workers.celery_app worker --loglevel=info
```

5. Set up
```bash
npm install
npm run dev
```

Visit [http://localhost:3000](http://localhost:3000)

## Project Structure

```
├── app/                   # FastAPI backend
│   ├── api/              # API routes
│   ├── models/           # Database models
│   ├── schemas/          # Pydantic schemas
│   ├── services/         # Business logic
│   └── workers/          # Celery tasks
├── src/                   # Next.js frontend
│   ├── app/              # Pages
│   ├── components/       # React components
│   └── lib/              # Utilities
├── alembic/              # Database migrations
└── infrastructure/       # Docker configs
```

## API Documentation

- Swagger UI: http://localhost:8000/api/docs
- ReDoc: http://localhost:8000/api/redoc

## License

MIT
