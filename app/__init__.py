"""
Keep package imports side-effect free.

Alembic imports `app.*` modules during migration generation/execution; importing
AWS/boto dependencies here breaks migrations in environments that don't install
those optional dependencies.
"""
