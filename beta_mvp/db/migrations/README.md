# Database Migrations

This folder is reserved for Alembic migration scripts.

Initialize Alembic in this project and generate the initial migration
based on the models in `db/models.py`:

```bash
alembic init db/migrations
alembic revision --autogenerate -m "initial schema"
alembic upgrade head
```
