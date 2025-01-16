import schedule
import time
import argparse
import os, sys, getpass, signal
import logging
import json
import threading
import enum
import uuid

from datetime import datetime
from croniter import croniter
from pythonjsonlogger import jsonlogger
from azure.storage.blob import BlobServiceClient, BlobClient, ContainerClient

import server_command
import database
from rcon_server import rcon_server, response

import backup_logger
from utils import logger

command_threads = {}
database_session = None

class RunType(enum.Enum):
    """
    An enumeration of the different kinds of runs that can be executed.
    """

    CLI = "cli"
    SERVER = "server"
    CRON_SERVER = "cron_server"

def str2bool(v):
  return v.lower() in ("yes", "true", "t", "1")

def job(blob_service_client, container_name, backup_dir, blob_prefix, overwrite_blob, backup_job_id: str):
    logger.info("Job is running...")
    logger.verbose(f"Backing up {backup_dir}...")
    error = None

    try:
        logger.verbose(f"Backing up {os.listdir(backup_dir)}...")

        for root, dirs, files in os.walk(backup_dir):
            logger.verbose(f"Current directory: {root}")
            logger.verbose(f"Files: {files}")
            for file_name in files:
                try:
                    logger.info(f"Current file: {file_name}")
                    file_path = os.path.join(root, file_name)
                    blob_name = os.path.join(blob_prefix, os.path.relpath(file_path, backup_dir))
                    logger.info(f"Found file {file_path}, attempting to upload as blob {blob_name}...")
                    upload_file_to_blob(blob_service_client, container_name, file_path, blob_name, overwrite_blob)
                except Exception as ex:
                    error = ex
    except Exception as ex:
        error = ex

    backup_job = database_session.session.get(database.backup_job.BackupJob, backup_job_id)

    if error:
        logger.error(error)
        backup_job.status = "Failed"
        backup_job.output = error.__str__()

        if type(error) != FileNotFoundError:
            raise error
    else:
        logger.info("Backup completed successfully.")
        backup_job.status = "Completed"
        backup_job.output = "Backup completed."
     
    database_session.session.commit()

    del command_threads[backup_job_id]

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
    parser.add_argument("--action", "-a", type=server_command.CommandType, choices=list(server_command.CommandType), help="Set the run type of the script")

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

def new_audit_log(function, client_addr: str = None, command: str = None, command_response = None, backup_job=None):
    backup_job_id = None
    if backup_job:
        backup_job_id = backup_job.id

    message = None
    if command_response:
        message = command_response.message

    status = None
    if command_response:
        status = command_response.status

    with database_session.session as session:
        audit_entry = database.audit_log.AuditLogEntry(
            function=function,
            client=f"{client_addr[0]}:{client_addr[1]}",
            command=command.__str__(),
            message=message,
            status=status,
            backup_job_id=backup_job_id
        )
        session.add(audit_entry)
        session.commit()

def audit_rcon_server(rconServer: rcon_server.RconServer, rconServerhook: rcon_server.RconServerHook, **kwargs):
  if rconServerhook == rconServerhook.client_socket_post_accept:
    new_audit_log("rcon_server", kwargs['client_addr'])

def process_command(server_context: rcon_server.RconServer, client_addr: str, command: str) -> response.Response:
    success = False
    stop_server = False
    server_cmd = None
    command_response = None

    client_addr_str = f"{client_addr[0]}:{client_addr[1]}"

    logger.info(f"Backup -> Processing command: {command}")
    try:
        server_cmd = server_command.ServerCommand(command)

        new_audit_log("process_command", client_addr=client_addr_str, command=str(server_cmd))
    except ValueError:
        logger.error("Client sent an invalid command")
        new_audit_log("process_command", client_addr=client_addr_str, command=command, message="Client sent an invalid command")
    except Exception as error:
        raise error

    if server_cmd == None:
        command_response = response.Response(False, "Invalid command provided")

    elif server_cmd.command_type == server_command.CommandType.BACKUP:
        logger.info("Backup -> Starting backup job...")
        logger.debug(f"process_command -> {server_cmd} -> Container Name: {args.container_name}, Backup Dir: {args.backup_dir}, Blob Prefix: {args.blob_prefix}, Overwrite: {args.overwrite}")

        # Insert backup job into database
        logger.info("Backup -> Inserting backup job into database...")
        
        backup_job_id = None
        with database_session.session as session:
            backup_job = database.backup_job.BackupJob(
                client=client_addr_str,
                command=command.__str__(),
                status="In Progress"
            )
            session.add(backup_job)
            session.commit()
            backup_job_id = backup_job.id

        # Start thread to run backup job
        backup_job = database_session.session.get(database.backup_job.BackupJob, backup_job_id)
        job_thread = threading.Thread(target=job, args=(blob_service_client, args.container_name, args.backup_dir, args.blob_prefix, args.overwrite, backup_job.id))
        command_threads[backup_job_id] = job_thread
        job_thread.start()
        command_response = response.Response(True, "Backup job start.", data={"job_id": str(backup_job.id)})

        new_audit_log(server_command.CommandType.BACKUP.value, 
            client_addr=client_addr_str,
            command=server_cmd.__str__(),
            command_response=command_response,
            backup_job=backup_job)

    elif server_cmd.command_type == server_command.CommandType.BACKUP_STATUS:
        backup_job = database_session.session.get(database.backup_job.BackupJob, server_cmd.command_args[0])

        logger.info(f"backup_job: {backup_job}")

        if backup_job:
            command_response = response.Response(True, backup_job.status, data=backup_job.json())
        else:
            command_response = response.Response(False, "Unable to find backup job using provided ID")

        new_audit_log(server_command.CommandType.BACKUP_STATUS.value, 
            client_addr=client_addr_str,
            command=server_cmd.__str__(),
            command_response=command_response,
            backup_job=backup_job)

    elif server_cmd.command_type == server_command.CommandType.STOP:
        command_response = response.Response(True, "Stopping backup server...")
        logger.info(command_response)

        server_context.stop_rcon_server()

    else:
        command_response = response.Response(False, error=f"Unknown command: {command}")
        logger.error(command_response)
    
    return command_response

def handler(signum, frame):
    if server:
        server.stop_rcon_server()
    sys.exit(0)

def setup_database():
    logger.verbose(f"Setting up database...")
    database_session = database.database_session.DatabaseSession("backup.db", args.debug)

    return database_session

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

        # Setup Database
        database_session = setup_database()

        schedule_cron(args.cron_schedule, job, blob_service_client, args.container_name, args.backup_dir, args.blob_prefix, args.overwrite)

        while True:
            schedule.run_pending()
            time.sleep(1)

    elif args.run_type == RunType.SERVER:
        logger.info(f"Running in {args.run_type.value} mode...")

        # Setup Database
        database_session = setup_database()
    else:
        logger.error("Invalid run type specified.")
        sys.exit(1)

    if args.enable_rcon_server:
        server = rcon_server.RconServer(logger, args.rcon_server_host, args.rcon_server_port)
        server.register_hook(rcon_server.RconServerHook.client_socket_post_accept, callback=audit_rcon_server)
        server.start_rcon_server(process_command)
    while True:
        time.sleep(1)