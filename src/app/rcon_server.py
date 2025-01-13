import socket
import os
import enum
import collections
import struct
import enum
import threading
import time

class PacketKind(enum.IntEnum):
    """
    An enumeration of the different kinds of packets that can be sent to the
    server.
    """

    COMMAND = 2
    RCON_PASSWORD = 3


class Ident(enum.IntEnum):
    """
    An enumeration of the different kinds of packets that can be sent to the
    """

    SUCCESS = 0
    FAILURE = 1


Packet = collections.namedtuple("Packet", ("ident", "kind", "payload"))

PASSWORD = ""


class IncompletePacket(Exception):
    def __init__(self, minimum):
        self.minimum = minimum

class RconServer:
    logger = None
    host = None
    port = None
    password = ""
    client_threads = []
    stop_server = False
    server_socket = None

    def __init__(self, logger, host, port, password=""):
        self.logger = logger
        self.host = host
        self.port = port
        self.password = password

    def decode_packet(self, data):
        """
        Decodes a packet from the beginning of the given byte string. Returns a
        2-tuple, where the first element is a ``Packet`` instance and the second
        element is a byte string containing any remaining data after the packet.
        """
        if len(data) < 14:
            raise IncompletePacket(14)

        length = struct.unpack("<i", data[:4])[0] + 4
        if len(data) < length:
            raise IncompletePacket(length)

        ident, kind = struct.unpack("<ii", data[4:12])
        payload, padding = data[12:length-2], data[length-2:length]
        assert padding == b"\x00\x00"
        return Packet(ident, kind, payload), data[length:]


    def encode_packet(self, packet):
        """
        Encodes a packet from the given ``Packet` instance. Returns a byte string.
        """
        data = struct.pack("<ii", packet.ident, packet.kind) + packet.payload + b"\x00\x00"
        return struct.pack("<i", len(data)) + data


    def send_packet(self, sock, packet):
        """
        Send a packet to the given socket.
        """
        self.logger.debug(f"Sending packet: {packet}")
        sock.sendall(self.encode_packet(packet))


    def receive_packet(self, sock):
        """
        Receive a packet from the given socket. Returns a ``Packet`` instance.
        """

        data = b""
        while True:
            try:
                return self.decode_packet(data)[0]
            except IncompletePacket as exc:
                while len(data) < exc.minimum:
                    data += sock.recv(exc.minimum - len(data))


    def process_client(self, sock, addr, _callback=None):
        self.logger.verbose(f"Connection from {addr}")
        decodedPacket = self.receive_packet(sock)
        stop_client = False

        self.logger.debug(f"Request Decoded: '{decodedPacket}'")

        if decodedPacket.kind == PacketKind.RCON_PASSWORD:
            if str.encode(PASSWORD) == decodedPacket.payload:
                self.logger.verbose(f"Sending password accepted message to {addr}")
                self.send_packet(sock, Packet(Ident.SUCCESS.value, PacketKind.RCON_PASSWORD.value, "Password accepted!".encode("utf8")))

                while not stop_client:
                    decodedPacket = self.receive_packet(sock)
                    self.logger.debug(f"Request Decoded: '{decodedPacket}'")

                    if decodedPacket.kind == PacketKind.COMMAND:
                        self.logger.verbose(f"Received command: {decodedPacket.payload}")
                        command_status = Ident.SUCCESS
                        command_output = ""

                        if _callback:
                            command_output, successful = _callback(self, addr, decodedPacket.payload.decode("utf8"))
                            if not successful:
                                command_status = Ident.FAILURE

                        # Return the results of the commend
                        self.send_packet(sock, Packet(command_status.value, PacketKind.COMMAND.value, command_output.encode("utf8")))
                        stop_client = True

                self.logger.info(f"Stopping connection from {addr}")
            else:
                self.logger.info(f"Sending password rejected message to {addr}")
                self.send_packet(sock, Packet(Ident.FAILURE, PacketKind.RCON_PASSWORD, "Password rejected!".encode("utf8")))
                sock.close()


    def stop_rcon_server(self):
        self.logger.info("stop_rcon_server-> Stopping server...")
        self.stop_server = True


    def monitor_server(self):
        while not self.stop_server:
            self.logger.debug("Server should remain alive, sleeping...")
            time.sleep(1)
        
        self.logger.info("Stopping server...")

        self.logger.verbose("Stopping server socket...")
        self.server_socket.close()
        self.logger.verbose("Stopped server socket...")


    def start_rcon_server(self, _callback=None):
        monitor_thread = threading.Thread(target=self.monitor_server)
        monitor_thread.start()

        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.bind((self.host, self.port))
        self.server_socket.listen(5)
        self.server_socket.settimeout(1.0)
        self.logger.info(f"Server started at {self.host}:{self.port}")

        while not self.stop_server:
            if self.stop_server:
                break
            try:
                self.logger.debug("Waiting for connection...")
                client_socket, addr = self.server_socket.accept()
                self.logger.info(f"Connection from {addr}")
                self.process_client(client_socket, addr, _callback)

                # client_thread = {
                #     "thread": threading.Thread(target=self.process_client, args=(client_socket, addr, _callback)),
                #     "socket": client_socket,
                # }
                # client_thread["thread"].start()
                # self.client_threads.append(client_thread)

            except socket.timeout as e:
                # self.logger.warn("start_rcon_server -> Server socket timeout reached...")
                pass
        
        self.logger.info("start_rcon_server -> Server stopped...")
        
        # Stop monitoring thread
        self.logger.info("Stopping monitor thread...")
        monitor_thread.join()
