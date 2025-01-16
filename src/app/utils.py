import logging, backup_logger

# Create Logger
logger = backup_logger.BackupLogger().get_logger("backup", logging.INFO)