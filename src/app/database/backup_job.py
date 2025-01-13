import uuid
from database.base_model import BaseModel


class BackupJob(BaseModel):
    id: str = None
    client: str = None
    command: str = None
    status: str = None
    output: str = None


    def __init__(self, db_file, client_addr, command):
        super().__init__(db_file)
        self.create(client_addr.__str__(), command.__str__())

    def create(self, client: str, command: str):
        self.id = str(uuid.uuid4())
        self.client = client
        self.command = command

        insert_query = "INSERT INTO backup_jobs (id, client, command) VALUES (?, ?, ?)"
        print(f"Inserting job: {self.id}, {client}, {command}")
        self.execute_query(insert_query, (self.id, client, command))

    def get_all(self):
        select_query = "SELECT * FROM backup_jobs"
        return self.fetch_all(select_query)

    def get(self):
        select_query = "SELECT * FROM backup_jobs WHERE id = ?"
        return self.fetch_one(select_query, (self.id,))

    def update(self, client, command):
        update_query = "UPDATE backup_jobs SET client = ?, command = ? WHERE id = ?"
        self.execute_query(update_query, (client, command, self.id))

    def update_status(self, status, output):
        update_query = "UPDATE backup_jobs SET status = ?, output = ? WHERE id = ?"
        self.execute_query(update_query, (status, output, self.id))

    def delete(self):
        delete_query = "DELETE FROM backup_jobs WHERE id = ?"
        self.execute_query(delete_query, (self.id,))
