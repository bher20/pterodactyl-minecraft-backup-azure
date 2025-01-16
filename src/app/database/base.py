from sqlalchemy import Column, DateTime

from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.sql import func

########################
# UUID for SQLite hack #
########################

from sqlalchemy.types import TypeDecorator, CHAR
from sqlalchemy.dialects.postgresql import UUID
import uuid


class GUID(TypeDecorator):
    """Platform-independent GUID type.
    Uses PostgreSQL's UUID type, otherwise uses
    CHAR(32), storing as stringified hex values.
    """
    impl = CHAR
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == 'postgresql':
            return dialect.type_descriptor(UUID())
        else:
            return dialect.type_descriptor(CHAR(32))

    def process_bind_param(self, value, dialect):
        if value is None:
            return value
        elif dialect.name == 'postgresql':
            return str(value)
        else:
            if not isinstance(value, uuid.UUID):
                return "%.32x" % uuid.UUID(value).int
            else:
                # hexstring
                return "%.32x" % value.int

    def process_result_value(self, value, dialect):
        if value is None:
            return value
        else:
            if not isinstance(value, uuid.UUID):
                value = uuid.UUID(value)
            return value

class Base(DeclarativeBase):
    __abstract__ = True

    id = Column(GUID(), primary_key=True, default=lambda: str(uuid.uuid4()))
    created_at = Column(DateTime, default=func.current_timestamp())
    updated_at = Column(DateTime,
                    default=func.current_timestamp(),
                    onupdate=func.current_timestamp())