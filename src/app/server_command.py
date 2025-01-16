import enum
from utils import logger

class CommandType(enum.Enum):
    """
    An enumeration of the different kinds of commands that can be sent to the server.
    """

    BACKUP = "backup"
    BACKUP_STATUS = "backup-status"
    STOP = "stop"

class ServerCommand:
    """
    A class representing a command that can be sent to the server.
    """

    # The type of command that this is.
    command_type = None
    # The arguments to the command.
    command_args = []
    
    def __init__(self, command_str: str):
        self.parse_command(command_str)

    def parse_command(self, command_str: str):
        """
        Parse the command string into a CommandType and a command string.
        """
        command_parts = command_str.split(" ")

        self.command_type = CommandType(command_parts[0])
        self.command_args = command_parts[1:]

    def __str__(self):
        return f"{self.command_type.value} {' '.join(self.command_args)}"

    def __repr__(self):
        return f"Command('{self.command_type.value}', {' '.join(self.command_args)})"