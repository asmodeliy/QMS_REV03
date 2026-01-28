"""Spec-Center module package."""
from . import routes
from .db import engine
from .models import Base

Base.metadata.create_all(bind=engine)

