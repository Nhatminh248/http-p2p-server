
"""
daemon.backend
~~~~~~~~~~~~~~~~~

This module provides a backend object to manage and persist backend daemon. 
It implements a basic backend server using Python's socket and threading libraries.
It supports handling multiple client connections concurrently and routing requests using a
custom HTTP adapter.

Requirements:
--------------
- socket: provide socket networking interface.
- threading: Enables concurrent client handling via threads.
- response: response utilities.
- httpadapter: the class for handling HTTP requests.
- CaseInsensitiveDict: provides dictionary for managing headers or routes.


Notes:
------
- The server create daemon threads for client handling.
- The current implementation error handling is minimal, socket errors are printed to the console.
- The actual request processing is delegated to the HttpAdapter class.

Usage Example:
--------------
>>> create_backend("127.0.0.1", 9000, routes={})

"""

import socket
import threading
import argparse

from .response import *
from .httpadapter import HttpAdapter
from .dictionary import CaseInsensitiveDict

import selectors
sel = selectors.DefaultSelector()

# mode_async = "callback"
mode_async = "coroutine"
# mode_async = "threading"

def handle_client(ip, port, conn, addr, routes):
    """
    Initializes an HttpAdapter instance and delegates the client handling logic to it.

    :param ip (str): IP address of the server.
    :param port (int): Port number the server is listening on.
    :param conn (socket.socket): Client connection socket.
    :param addr (tuple): client address (IP, port).
    :param routes (dict): Dictionary of route handlers.
    """
    print("[Backend] Invoke handle_client accepted connection from {}".format(addr))
    daemon = HttpAdapter(ip, port, conn, addr, routes)

    # Handle client
    daemon.handle_client(conn, addr, routes)


def selector_server(ip="0.0.0.0", port=7000, routes={}):
    """
    Non-blocking server using selectors for I/O multiplexing (replaces asyncio coroutine mode).
    Accepts and handles all connections in a single event loop thread — no threads spawned.

    :param ip (str): IP address to bind.
    :param port (int): Port number to listen on.
    :param routes (dict): Route handlers.
    """
    print("[Backend] selector_server **SELECTOR** listening on port {}".format(port))
    if routes:
        print("[Backend] route settings")
        for key, value in routes.items():
            print("   + ('{}', '{}'): {}".format(key[0], key[1], str(value)))

    _sel = selectors.DefaultSelector()
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind((ip, port))
    server.listen(50)
    server.setblocking(False)
    _sel.register(server, selectors.EVENT_READ, data=None)

    try:
        while True:
            events = _sel.select(timeout=None)
            for key, mask in events:
                if key.data is None:
                    # Server socket ready: accept a new connection
                    conn, addr = key.fileobj.accept()
                    conn.setblocking(True)
                    _sel.register(conn, selectors.EVENT_READ, data=(addr, routes))
                else:
                    # Client socket ready: read and handle inline
                    addr, _routes = key.data
                    conn = key.fileobj
                    _sel.unregister(conn)
                    handle_client(ip, port, conn, addr, _routes)
    except KeyboardInterrupt:
        pass
    finally:
        _sel.close()
        server.close()


def run_backend(ip, port, routes):
    """
    Starts the backend server, binds to the specified IP and port, and listens for incoming
    connections. Each connection is handled in a separate thread. The backend accepts incoming
    connections and spawns a thread for each client.


    :param ip (str): IP address to bind the server.
    :param port (int): Port number to listen on.
    :param routes (dict): Dictionary of route handlers.
    """
    # This global variable to configure the asynchrnous mode or not
    global mode_async

    print("[Backend] run_backend with routes={}".format(routes))
    # Process async stream for registering the service and terminate
    if mode_async == "coroutine":
        selector_server(ip, port, routes)
        return

    # Process socket object
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    try:
        server.bind((ip, port))
        server.listen(50)

        print("[Backend] Listening on port {}".format(port))
        if routes != {}:
            print("[Backend] route settings")
            for key, value in routes.items():
               print("   + ('{}', '{}'): {}".format(key[0], key[1], str(value)))

        if mode_async == "callback":
            server.setblocking(False)
            sel.register(server, selectors.EVENT_READ, (ip, port, routes))

        while True:
            if mode_async == "callback":
                # Event-driven: selector drives accept, thread handles each connection
                events = sel.select(timeout=None)
                for key, mask in events:
                    _ip, _port, _routes = key.data
                    conn, addr = key.fileobj.accept()
                    conn.setblocking(True)
                    t = threading.Thread(target=handle_client, args=(_ip, _port, conn, addr, _routes))
                    t.daemon = True
                    t.start()

            else:
                # Blocking accept for threading mode
                conn, addr = server.accept()
                if mode_async == "threading":
                    t = threading.Thread(target=handle_client, args=(ip, port, conn, addr, routes))
                    t.start()


    except socket.error as e:
      print("Socket error: {}".format(e))

def create_backend(ip, port, routes={}):
    """
    Entry point for creating and running the backend server.

    :param ip (str): IP address to bind the server.
    :param port (int): Port number to listen on.
    :param routes (dict, optional): Dictionary of route handlers. Defaults to empty dict.
    """

    run_backend(ip, port, routes)
