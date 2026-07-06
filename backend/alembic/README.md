# Database Migrations (Alembic)

The DB URL is read automatically from application settings (`.env`).

```bash
# Autogenerate a migration from model changes
alembic revision --autogenerate -m "describe change"

# Apply migrations
alembic upgrade head

# Roll back one revision
alembic downgrade -1
```

For local development the app also calls `create_all` on startup, so migrations
are optional there. In staging/production, use Alembic as the source of truth.
