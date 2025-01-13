from database.base_model import BaseModel


class Database(BaseModel):
    def __init__(self, db_file):
        super().__init__(db_file)