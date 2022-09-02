import socket
import struct


# todo make shared library

class SocketNotConnectedException(Exception):
    pass


class SimpleSocket:
    # only supports tcp

    def __init__(self, host, port):
        self._host = host
        self._port = port

        self._socket = None

    def connect(self):
        # force reconnect
        self.close()

        self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._socket.connect((self._host, self._port))

    def __enter__(self):
        if not self._socket:
            self.connect()
        return self

    def close(self):
        if self._socket:
            try:
                self._socket.close()
            except:
                pass
        self._socket = None

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def recv_exactly(self, size):
        if not self._socket:
            raise SocketNotConnectedException("cant receive without connection")

        buffer = b""
        while size > 0:
            received = self._socket.recv(min(size, 1024))
            buffer += received
            size -= len(received)
        return buffer

    def sendall(self, data):
        self._socket.sendall(data)

    def recv_based_on_32bit_integer(self):
        length = struct.unpack("<i", self.recv_exactly(4))[0]
        return self.recv_exactly(length)
