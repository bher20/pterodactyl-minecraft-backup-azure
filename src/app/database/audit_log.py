import json

from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import mapped_column, Mapped
from uuid import uuid4

from .base import Base

class AuditLogEntry(Base):
    __tablename__ = 'audit_log_entries'

    client = Column(String)
    function = Column(String)
    command = Column(String)
    command_raw = Column(String)
    status = Column(String)
    output = Column(String)
    message = Column(String)
    backup_job_id: Mapped[str] = mapped_column(ForeignKey("backup_jobs.id"), nullable=True)

    def __repr__(self) -> str:
        return f"AuditLogEntry(id={self.id!r}, client={self.client!r}, command={self.command!r}), status={self.status!r}), output={self.output!r}), created_at={self.created_at!r}), updated_at={self.updated_at!r})"

    def json(self) -> str:
        return json.dumps({
            'id': self.id,
            'function': self.function,
            'client': self.client,
            'command': self.command,
            'status': self.status,
            'output': self.output
        })
