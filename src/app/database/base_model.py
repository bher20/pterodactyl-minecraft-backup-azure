import uuid, sqlite3
import os

class BaseModel:
    db_file = None

    def __init__(self, db_file, check_same_thread=False):
        self.db_file = db_file
        self.conn = sqlite3.connect(self.db_file, check_same_thread=check_same_thread)
        self.conn.row_factory = sqlite3.Row

    def execute_query(self, query, params=None):
        cursor = self.conn.cursor()
        if params:
            cursor.execute(query, params)
        else:
            cursor.execute(query)
        self.conn.commit()
        return cursor

    def execute_script(self, script):
        cursor = self.conn.cursor()
        
        cursor.executescript(script)
        
        self.conn.commit()
        return cursor

    def fetch_all(self, query, params=None):
        cursor = self.execute_query(query, params)
        return cursor.fetchall()

    def fetch_one(self, query, params=None):
        cursor = self.execute_query(query, params)
        return cursor.fetchone()

    def run_migrations(self, migrations_path):
        """
        Run SQL migrations from files in the specified directory.
        
        :param migrations_path: Path to the directory containing SQL migration files.
        """
        for filename in os.listdir(migrations_path):
            if filename.endswith(".sql"):
                with open(os.path.join(migrations_path, filename), 'r') as file:
                    migration = file.read()
                    self.execute_script(migration)

    def close_connection(self):
        if self.conn:
            self.conn.close()

    def __del__(self):
        self.close_connection()

    def __str__(self):
        return f"{type(self).__name__}(db_file: {self.db_file})"