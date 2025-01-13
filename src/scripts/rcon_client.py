from mcrcon import MCRcon
import argparse

def send_rcon_command(host, port, password, command):
    with MCRcon(host, password, port=port) as mcr:
        response = mcr.command(command)
        print(response)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Send commands to an RCON server")
    parser.add_argument('--host', type=str, required=True, help="RCON server host")
    parser.add_argument('--port', type=int, required=True, help="RCON server port")
    parser.add_argument('--password', type=str, required=True, help="RCON server password")
    parser.add_argument('--command', type=str, required=True, help="Command to send to the RCON server")
    args = parser.parse_args()

    send_rcon_command(args.host, args.port, "", args.command)