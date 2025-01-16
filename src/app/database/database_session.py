from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

from .base import Base

class DatabaseSession:
    engine = None
    session = None
    db_file = None

    def __init__(self, db_file, engine_echo=False):
        self.engine = create_engine(f"sqlite:///{db_file}", echo=engine_echo)
        Base.metadata.create_all(self.engine)
        Session = sessionmaker(bind=self.engine)
        Session.configure(bind=self.engine)
        self.session = Session()