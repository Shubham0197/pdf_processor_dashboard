"""
Custom column types for SQLAlchemy ORM
"""
import uuid
from sqlalchemy.dialects.postgresql import UUID as _UUID
from sqlalchemy.types import TypeDecorator, CHAR
from sqlalchemy.dialects.postgresql import UUID as PostgresUUID

class UUID(TypeDecorator):
    """Platform-independent UUID type.
    
    Uses PostgreSQL's UUID type when available, otherwise uses
    CHAR(36), storing as a string.
    """
    impl = CHAR
    cache_ok = True
    
    def __init__(self, as_uuid=False, **kw):
        """Initialize the UUID type.
        
        :param as_uuid: If True, values will be returned as uuid.UUID objects rather than strings
        """
        self.as_uuid = as_uuid
        super(UUID, self).__init__(**kw)

    def load_dialect_impl(self, dialect):
        if dialect.name == 'postgresql':
            return dialect.type_descriptor(PostgresUUID(as_uuid=self.as_uuid))
        else:
            return dialect.type_descriptor(CHAR(36))

    def process_bind_param(self, value, dialect):
        if value is None:
            return value
        elif dialect.name == 'postgresql':
            return str(value)
        else:
            if not isinstance(value, uuid.UUID):
                return str(uuid.UUID(value))
            else:
                return str(value)

    def process_result_value(self, value, dialect):
        if value is None:
            return value
        if self.as_uuid and not isinstance(value, uuid.UUID):
            try:
                return uuid.UUID(value)
            except (AttributeError, ValueError):
                return None
        return value
