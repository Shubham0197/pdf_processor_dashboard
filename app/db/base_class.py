"""
Re-exports the SQLAlchemy Base class from the main database module.
This maintains compatibility with imports that expect app.db.base_class.Base
"""

from app.database import Base

# Re-export Base for backward compatibility
# This allows models to import from app.db.base_class without changes
