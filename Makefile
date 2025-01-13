# Variables
MIGRATIONS_DIR = ./src/app/migrations
MIGRATION_NAME ?= example
MIGRATION_FILE = $(shell date +%s)_$(MIGRATION_NAME).sql
PYTHON = python3
DOCKER_IMAGE_NAME = pterodactyl-minecraft-backup-azure
PREFIX ?= backup_server
DB_FILE = $(PREFIX)_$(shell date +%s).sqlite3

# Targets
.PHONY: all create_migration apply_migrations build clean

all: build

create_migration:
	@mkdir -p $(MIGRATIONS_DIR); \
    touch $(MIGRATIONS_DIR)/$(MIGRATION_FILE); \
    echo "Created migration: $(MIGRATIONS_DIR)/$(MIGRATION_FILE)"

apply_migrations:
	@$(PYTHON) -c 'from src.scripts.database import SQLiteDB; db = SQLiteDB("$(DB_FILE)"); db.create_connection(); import os; for file in sorted(os.listdir("$(MIGRATIONS_DIR)")): print(f"Applying migration: {file}"); with open("$(MIGRATIONS_DIR)/" + file, "r") as f: db.execute_query(f.read()); db.close_connection()'

build:
	@echo "Building the Docker image..."
	@docker build -t $(DOCKER_IMAGE_NAME) .

clean:
	@echo "Cleaning up..."
	@rm -rf build dist *.egg-info $(DB_FILE)
	@find . -name "*.pyc" -delete
	@find . -name "__pycache__" -delete
