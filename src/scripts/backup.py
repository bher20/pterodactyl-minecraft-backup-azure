import schedule
import time
from datetime import datetime
from croniter import croniter
import argparse
import os, sys, getpass
import logging
from pythonjsonlogger import jsonlogger
from azure.storage.blob import BlobServiceClient, BlobClient, ContainerClient
import json
import threading
import rcon_server, backup_logger
import enum
import signal
import uuid

logger = backup_logger.BackupLogger().get_logger("backup", logging.INFO)
command_threads = {}

class RunType(enum.Enum):
    """
    An enumeration of the different kinds of runs that can be executed.
    """

    CLI = "cli"
    SERVER = "server"
    CRON_SERVER = "cron_server"

class Command(enum.Enum):
    """
    An enumeration of the different kinds of commands that can be sent to the server.
    """

    BACKUP = "backup"
    BACKUP_STATUS = "backup_status"
    STOP = "stop"

def str2bool(v):
  return v.lower() in ("yes", "true", "t", "1")

def job(blob_service_client, container_name, backup_dir, blob_prefix, overwrite_blob, job_id):
    logger.info("Job is running...")
    logger.verbose(f"Backing up {backup_dir}...")
    logger.verbose(f"Backing up {os.listdir(backup_dir)}...")
    for root, dirs, files in os.walk(backup_dir):
        logger.verbose(f"Current directory: {root}")
        logger.verbose(f"Files: {files}")
        for file_name in files:
            logger.info(f"Current file: {file_name}")
            file_path = os.path.join(root, file_name)
            blob_name = os.path.join(blob_prefix, os.path.relpath(file_path, backup_dir))
            logger.info(f"Found file {file_path}, attempting to upload as blob {blob_name}...")
            upload_file_to_blob(blob_service_client, container_name, file_path, blob_name, overwrite_blob)

    logger.verbose("Backup job completed, removing job from command_threads map...")
    del command_threads[job_id]

def schedule_cron(cron_expression, job_function, *args):
    base_time = datetime.now()
    cron = croniter(cron_expression, base_time)
    next_run = cron.get_next(datetime)
    
    def wrapper():
        nonlocal next_run
        now = datetime.now()
        if now >= next_run:
            job_function(*args)
            next_run = cron.get_next(datetime)
    
    schedule.every().second.do(wrapper)

def upload_file_to_blob(blob_service_client, container_name, file_path, blob_name, overwrite_blob=False):
    try:
        blob_client = blob_service_client.get_blob_client(container=container_name, blob=blob_name)

        if not overwrite_blob:
            # Check if the blob already exists
            if blob_client.exists():
                logger.info(f"Blob {blob_name} already exists in container {container_name}. Skipping upload.")
                return

        with open(file_path, "rb") as data:
            blob_client.upload_blob(data, overwrite=True)
        logger.info(f"File {file_path} uploaded to blob {blob_name} in container {container_name}.")
    except Exception as ex:
        logger.error(f"An error occurred: {ex}")

# Parse command-line arguments
def parse_args():
    parser = argparse.ArgumentParser(description="Backs up a given Minecraft server directory to Azure Blob Storage.")

    parser.add_argument("--run_type", "-r", type=RunType, choices=list(RunType), default=RunType(os.getenv('RUN_TYPE', RunType.SERVER.value)), help="Set the run type of the script")
    parser.add_argument("--action", "-a", type=Command, choices=list(Command), help="Set the run type of the script")

    parser.add_argument("--cron-schedule", type=str, default=os.getenv("CRON_SCHEDULE", None), help="Cron schedule expression")
    parser.add_argument("--connection-string", type=str, default=os.getenv('AZURE_STORAGE_CONNECTION_STRING', None), help="Azure Storage connection string")
    parser.add_argument("--container-name", type=str, default=os.getenv("CONTAINER_NAME", None), help="Azure Storage container name")
    parser.add_argument("--backup-dir", type=str, default=os.getenv("BACKUP_DIR", "/backups"), help="Path to the directory containing files to upload")
    parser.add_argument("--blob-prefix", type=str, default=os.getenv("BLOB_PREFIX", ""), help="Prefix for the blob names")
    parser.add_argument("--overwrite", "-o", action="store_true", default=str2bool(os.getenv('OVERWRITE_BLOB', "False")), help="Overwrite existing blobs")
    parser.add_argument("--verbose", "-v", action="store_true", default=(os.getenv('LOGGING_LEVEL', "").lower() == "verbose"), help="Enable verbose logging")
    parser.add_argument("--debug", "-d", action="store_true", default=(os.getenv('LOGGING_LEVEL', "").lower() == "debug"), help="Enable debug logging")

    rcon_server_arguments = parser.add_argument_group("RCON Server")
    rcon_server_arguments.add_argument("--enable-rcon-server", action="store_true", default=str2bool(os.getenv('ENABLE_RCON_SERVER', "False")), help="Start the RCON server")
    rcon_server_arguments.add_argument('--rcon-server-host', type=str, default=os.getenv('RCON_HOST', '127.0.0.1'), help="Set the TCP server host")
    rcon_server_arguments.add_argument('--rcon-server-port', type=int, default=int(os.getenv('RCON_PORT', '65432')), help="Set the TCP server port")

    return parser.parse_args()

def process_command(server_context: rcon_server.RconServer, command: str) :
    success = False
    output = None
    stop_server = False

    logger.info(f"Backup -> Processing command: {command}")
    if command == Command.BACKUP.value:
        logger.info("Backup -> Starting backup job...")
        logger.debug(f"process_command -> {command} -> Container Name: {args.container_name}, Backup Dir: {args.backup_dir}, Blob Prefix: {args.blob_prefix}, Overwrite: {args.overwrite}")

        # Start thread to run backup job
        job_id = uuid.uuid4()
        job_thread = threading.Thread(target=job, args=(blob_service_client, args.container_name, args.backup_dir, args.blob_prefix, args.overwrite, job_id))
        command_threads[job_id] = {
          "thread": job_thread,
          "command": command
        }
        job_thread.start()
        output = json.dumps({"status": "success", "message": "Backup job started.", "job_id": str(job_id)})
        success = True
    elif command == Command.BACKUP_STATUS.value:
      # TODO: Implement backup status command
      output = json.dumps({"status": "failed", "message": "NOT YET IMPLEMENTED."})
      success = False
    elif command == Command.STOP.value:
        output = "Backup -> Stopping backup server..."
        logger.info(output)
        server_context.stop_rcon_server()
        success = True
    else:
        output = f"Backup -> Unknown command: {command}"
        logger.error(output)
    
    return output, success

def handler(signum, frame):
    if server:
        server.stop_rcon_server()
    sys.exit(0)

server = None
blob_service_client = None

if __name__ == "__main__":
    # Set up signal handler for handling ctrl+c
    signal.signal(signal.SIGINT, handler)

    # Parse command-line arguments
    args = parse_args()

    # Set logging level
    if args.debug:
        logger.setLevel(logging.DEBUG)
        logger.info("DEBUG logging enabled.")
    elif args.verbose:
        logger.setLevel(backup_logger.BackupLogger.VERBOSE)
        logger.info("VERBOSE logging enabled.")
    else:
        logger.setLevel(logging.INFO)

    # Validate required parameters
    if not args.connection_string:
        raise ValueError("Azure Storage connection string must be provided as a parameter or environment variable.")
    if not args.container_name:
        raise ValueError("Azure Storage container name must be provided as a parameter or environment variable.")
    if not args.backup_dir and not os.path.exists(args.backup_dir):
        raise ValueError("Directory path must be provided as a parameter or environment variable.")

    if args.run_type == RunType.CLI and not args.action:
        raise ValueError(f"An action [{'|'.join(Command)}] must be specifed if running in {RunType.CLI.value} mode.")
    elif args.run_type == RunType.CRON_SERVER and not args.cron_schedule:
        raise ValueError(f"Cron schedule must be provided as a parameter or environment variable if running in {RunType.CRON_SERVER.value}.")

    # Create the BlobServiceClient object which will be used to upload the backups
    blob_service_client = BlobServiceClient.from_connection_string(args.connection_string)

    if args.run_type == RunType.CLI:
        logger.info(f"Running in {args.run_type.value} mode...")
        job(blob_service_client, args.container_name, args.backup_dir, args.blob_prefix, args.overwrite)

    elif args.run_type == RunType.CRON_SERVER:
        logger.info(f"Running in {args.run_type.value} mode...")
        schedule_cron(args.cron_schedule, job, blob_service_client, args.container_name, args.backup_dir, args.blob_prefix, args.overwrite)

        while True:
            schedule.run_pending()
            time.sleep(1)

    elif args.run_type == RunType.SERVER:
        logger.info(f"Running in {args.run_type.value} mode...")
        if args.enable_rcon_server:
            server = rcon_server.RconServer(logger, args.rcon_server_host, args.rcon_server_port)
            server.start_rcon_server(process_command)
    else:
        logger.error("Invalid run type specified.")
        sys.exit(1)