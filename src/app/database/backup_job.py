import json

from sqlalchemy import Column, Integer, String, DateTime, BINARY
from sqlalchemy.sql import func

from .base import Base

class BackupJob(Base):
    __tablename__ = 'backup_jobs'

    client = Column(String)
    command = Column(String)
    status = Column(String)
    output = Column(String)

    def __repr__(self) -> str:
        return f"BackupJob(id={self.id!r}, client={self.client!r}, command={self.command!r}), status={self.status!r}), output={self.output!r}), created_at={self.created_at!r}), updated_at={self.updated_at!r})"

    def json(self) -> str:
        return json.dumps({
            'id': str(self.id),
            'client': self.client,
            'command': self.command,
            'status': self.status,
            'output': self.output
        })
