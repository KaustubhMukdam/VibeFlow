"""
app/db/base.py
Shared declarative base for all SQLAlchemy ORM models.
"""
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """All ORM models inherit from this base class."""
    pass
