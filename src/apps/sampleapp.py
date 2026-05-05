

"""
app.sampleapp
~~~~~~~~~~~~~~~~~

"""

import sys
import os
import importlib.util
import json
import asyncio

from daemon import AsynapRous

import socket
import threading

peer_list = {}
peer_connections = {}
received_messages = []  # stores dicts: {"from": addr, "text": msg, "channel": name or ""}
channels = {}        # tracker-side: {channel_name: [username, ...]}
_local_channels = {} # peer-side cache: {channel_name: [username, ...]}
_state_lock = threading.Lock()
_self_p2p_port = None  # set at startup; used to skip self in broadcast

app = AsynapRous()

@app.route('/login', methods=['POST'])
def login(headers="guest", body="anonymous"):
    """
    Handle user login via POST request.

    This route simulates a login process and prints the provided headers and body
    to the console.

    :param headers (str): The request headers or user identifier.
    :param body (str): The request body or login payload.
    """
    print("[SampleApp] Logging in {} to {}".format(headers, body))
    data = {"message": "Welcome to the RESTful TCP WebApp"}

    # Convert to JSON string
    json_str = json.dumps(data)
    return (json_str.encode("utf-8"))

@app.route("/echo", methods=["POST"])
def echo(headers="guest", body="anonymous"):
    print("[SampleApp] received body {}".format(body))

    try:
        message = json.loads(body)
        data = {"received": message }
        # Convert to JSON string
        json_str = json.dumps(data)
        return (json_str.encode("utf-8"))
    except json.JSONDecodeError:
        data = {"error": "Invalid JSON"}
        # Convert to JSON string
        json_str = json.dumps(data)
        return (json_str.encode("utf-8"))


@app.route('/hello', methods=['PUT'])
async def hello(headers, body):
    """
    Handle greeting via PUT request.

    This route prints a greeting message to the console using the provided headers
    and body.

    :param headers (str): The request headers or user identifier.
    :param body (str): The request body or message payload.
    """
    print("[SampleApp] ['PUT'] **ASYNC** Hello in {} to {}".format(headers, body))
    data =  {"id": 1, "name": "Alice", "email": "alice@example.com"}

    # Convert to JSON string
    json_str = json.dumps(data)
    return (json_str.encode("utf-8"))


@app.route('/slow', methods=['GET'])
async def slow(headers="", body=""):
    await asyncio.sleep(5)
    return json.dumps({"message": "slow response after 5s"}).encode("utf-8")

@app.route('/fast', methods=['GET'])
async def fast(headers="", body=""):
    return json.dumps({"message": "fast response"}).encode("utf-8")

@app.route('/submit-info', methods=['POST'])
def submit_info(headers="", body=""):
    try:
        data = json.loads(body)
    except json.JSONDecodeError:
        return json.dumps({"error": "Invalid JSON"}).encode("utf-8")
    with _state_lock:
        peer_list[data["username"]] = {
            "ip": data["ip"],
            "port": data["port"]
        }
    return json.dumps({"status": "ok"}).encode("utf-8")

@app.route('/add-list', methods=['POST'])
def add_list(headers="", body=""):
    try:
        data = json.loads(body)
    except json.JSONDecodeError:
        return json.dumps({"error": "Invalid JSON"}).encode("utf-8")
    with _state_lock:
        peer_list[data["username"]] = {
            "ip": data["ip"],
            "port": data["port"]
        }
    return json.dumps({"status": "ok"}).encode("utf-8")

@app.route('/get-list', methods=['GET'])
def get_list(headers="", body=""):
    with _state_lock:
        return json.dumps(peer_list).encode("utf-8")

@app.route('/get-messages', methods=['GET'])
def get_messages(headers="", body=""):
    with _state_lock:
        return json.dumps(received_messages).encode("utf-8")

@app.route('/connect-peer', methods=['POST'])
def connect_peer(headers="", body=""):
    """
    Establish a direct TCP connection to another peer.

    Steps:
    1. json.loads(body) → { "username": target_username }
    2. Look up target_username in peer_list → get ip and port
       - If not found, return JSON error bytes: {"error": "peer not found"}
    3. Create a new socket: socket.socket(AF_INET, SOCK_STREAM)
    4. sock.connect((ip, port))
    5. Store in peer_connections[target_username] = sock
    6. Return JSON bytes: {"status": "connected", "to": target_username}

    Important: the port you connect to is the PEER_LISTEN_PORT of the target peer,
    which is the port they reported when they called /submit-info.

    :param headers: request headers dict
    :param body: JSON string
    :rtype: bytes
    """
    try:
        data = json.loads(body)
    except json.JSONDecodeError:
        return json.dumps({"error": "Invalid JSON"}).encode("utf-8")
    target = data["username"]
    with _state_lock:
        if target not in peer_list:
            return json.dumps({"error": "peer not found"}).encode("utf-8")
        info = peer_list[target]
    
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.connect((info["ip"], info["port"]))
    except (OSError, socket.timeout):
        return json.dumps({"error": "connection failed"}).encode("utf-8")
    
    with _state_lock:
        peer_connections[target] = sock
    return json.dumps({"status": "connected", "to": target}).encode("utf-8")

@app.route('/send-peer', methods=['POST'])
def send_peer(headers="", body=""):
    """
    Send a message directly to a single peer over TCP.

    Steps:
    1. json.loads(body) → { "username": target, "message": msg_string }
    2. Check if peer_connections[target] exists and is alive
       - If not, connect first (same logic as /connect-peer)
    3. sock.sendall(msg_string.encode("utf-8"))
    4. Return JSON bytes: {"status": "sent", "to": target}

    Error cases to handle:
    - peer not in peer_list → {"error": "peer not found"}
    - socket send fails (broken pipe, connection refused) → {"error": "send failed"}
      Remove the stale entry from peer_connections on failure.

    Note: you do NOT need to wait for a reply. This is one-way fire-and-forget.

    :param headers: request headers dict
    :param body: JSON string
    :rtype: bytes
    """
    try:
        data = json.loads(body)
    except json.JSONDecodeError:
        return json.dumps({"error": "Invalid JSON"}).encode("utf-8")
    target = data["username"]
    msg = data["message"]
    sender = data.get("from", "")

    with _state_lock:
        if target not in peer_list:
            return json.dumps({"error": "peer not found"}).encode("utf-8")
        info = peer_list[target]

    payload = json.dumps({"from": sender, "text": msg}).encode("utf-8")
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.connect((info["ip"], info["port"]))
        sock.sendall(payload)
    except (OSError, socket.timeout):
        return json.dumps({"error": "send failed"}).encode("utf-8")
    finally:
        sock.close()
    with _state_lock:
        received_messages.append({"from": "You → " + target, "text": msg, "channel": ""})
    return json.dumps({"status": "sent", "to": target}).encode("utf-8")


@app.route('/broadcast-peer', methods=['POST'])
def broadcast_peer(headers="", body=""):
    """
    Send a message to all registered peers.

    Steps:
    1. json.loads(body) → { "message": msg_string }
    2. sent_count = 0
    3. For each (username, info) in peer_list.items():
       a. Reuse or create socket to (info["ip"], info["port"])
          - Same connect logic as /connect-peer
       b. sock.sendall(msg_string.encode("utf-8"))
       c. If send succeeds, sent_count += 1
       d. If send fails, skip that peer (don't abort the whole broadcast)
    4. Return JSON bytes: {"status": "broadcast sent", "count": sent_count}

    Important: wrap each individual send in try/except so one failing peer
    does not stop the broadcast to the rest.

    :param headers: request headers dict
    :param body: JSON string
    :rtype: bytes
    """
    try:
        data = json.loads(body)
    except json.JSONDecodeError:
        return json.dumps({"error": "Invalid JSON"}).encode("utf-8")
    msg = data["message"]
    sender = data.get("from", "")
    sent_count = 0

    with _state_lock:
        targets = list(peer_list.items())

    payload = json.dumps({"from": sender, "text": msg}).encode("utf-8")
    for username, info in targets:
        if info["port"] == _self_p2p_port:
            continue
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            sock.connect((info["ip"], info["port"]))
            sock.sendall(payload)
            sent_count += 1
        except (OSError, socket.timeout):
            pass
        finally:
            sock.close()
    with _state_lock:
        received_messages.append({"from": "You → all", "text": msg, "channel": ""})
    return json.dumps({"status": "broadcast sent", "count": sent_count}).encode("utf-8")


# ── Channel routes ────────────────────────────────────────────────────────────────────────────

@app.route('/create-channel', methods=['POST'])
def create_channel(headers="", body=""):
    try:
        data = json.loads(body)
    except json.JSONDecodeError:
        return json.dumps({"error": "Invalid JSON"}).encode("utf-8")
    name = data.get("channel", "").strip()
    username = data.get("username", "")
    if not name:
        return json.dumps({"error": "channel name required"}).encode("utf-8")
    with _state_lock:
        if name not in channels:
            channels[name] = []
        if username and username not in channels[name]:
            channels[name].append(username)
    return json.dumps({"status": "created", "channel": name}).encode("utf-8")

@app.route('/join-channel', methods=['POST'])
def join_channel(headers="", body=""):
    try:
        data = json.loads(body)
    except json.JSONDecodeError:
        return json.dumps({"error": "Invalid JSON"}).encode("utf-8")
    name = data.get("channel", "")
    username = data.get("username", "")
    with _state_lock:
        if name not in channels:
            return json.dumps({"error": "channel not found"}).encode("utf-8")
        if username not in channels[name]:
            channels[name].append(username)
    return json.dumps({"status": "joined", "channel": name}).encode("utf-8")

@app.route('/leave-channel', methods=['POST'])
def leave_channel(headers="", body=""):
    try:
        data = json.loads(body)
    except json.JSONDecodeError:
        return json.dumps({"error": "Invalid JSON"}).encode("utf-8")
    name = data.get("channel", "")
    username = data.get("username", "")
    with _state_lock:
        if name in channels and username in channels[name]:
            channels[name].remove(username)
    return json.dumps({"status": "left", "channel": name}).encode("utf-8")

@app.route('/list-channels', methods=['GET'])
def list_channels(headers="", body=""):
    with _state_lock:
        return json.dumps(channels).encode("utf-8")

@app.route('/sync-channel', methods=['POST'])
def sync_channel(headers="", body=""):
    try:
        data = json.loads(body)
    except json.JSONDecodeError:
        return json.dumps({"error": "Invalid JSON"}).encode("utf-8")
    with _state_lock:
        _local_channels[data.get("channel", "")] = data.get("members", [])
    return json.dumps({"status": "ok"}).encode("utf-8")

@app.route('/send-channel', methods=['POST'])
def send_channel(headers="", body=""):
    try:
        data = json.loads(body)
    except json.JSONDecodeError:
        return json.dumps({"error": "Invalid JSON"}).encode("utf-8")
    channel = data.get("channel", "")
    msg = data.get("message", "")
    sender = data.get("from", "")

    with _state_lock:
        if channel not in _local_channels:
            return json.dumps({"error": "channel unknown locally, refresh first"}).encode("utf-8")
        members = list(_local_channels[channel])
        local_pl = dict(peer_list)

    payload = json.dumps({"from": sender, "text": msg, "channel": channel}).encode("utf-8")
    sent_count = 0
    for username in members:
        if username == sender:
            continue
        if username not in local_pl:
            continue
        info = local_pl[username]
        if info["port"] == _self_p2p_port:
            continue
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            sock.connect((info["ip"], info["port"]))
            sock.sendall(payload)
            sent_count += 1
        except (OSError, socket.timeout):
            pass
        finally:
            sock.close()
    with _state_lock:
        received_messages.append({"from": "You → #" + channel, "text": msg, "channel": channel})
    return json.dumps({"status": "sent", "channel": channel, "count": sent_count}).encode("utf-8")


def create_sampleapp(ip, port, peer_port=5000):
    global _self_p2p_port
    _self_p2p_port = peer_port
    # Start P2P listener in background daemon thread
    t = threading.Thread(target=start_peer_listener, args=(peer_port,))
    t.daemon = True
    t.start()
    # Prepare and launch the RESTful application
    app.prepare_address(ip, port)
    app.run()

def handle_peer_message(conn, addr):
    """
    Called in a new thread for each incoming P2P connection.

    Responsibilities:
    - conn.recv(4096) to read the raw bytes sent by the remote peer
    - Decode the bytes (UTF-8) to get the message string
    - Print or store the message so the user can see it
    - Close conn when done

    :param conn: accepted socket from the listener
    :param addr: (ip, port) of the connecting peer
    """
    try:
        chunks = []
        while True:
            chunk = conn.recv(4096)
            if not chunk:
                break
            chunks.append(chunk)
        data = b''.join(chunks)
        if data:
            raw = data.decode('utf-8')
            try:
                payload = json.loads(raw)
                sender = payload.get("from") or "{}:{}".format(addr[0], addr[1])
                text = payload.get("text", "")
            except (json.JSONDecodeError, AttributeError):
                sender = "{}:{}".format(addr[0], addr[1])
                text = raw
            print(f"[P2P] Message from {sender}: {text}")
            with _state_lock:
                received_messages.append({"from": sender, "text": text, "channel": payload.get("channel", "") if isinstance(payload, dict) else ""})
    finally:
        conn.close()


def start_peer_listener(port):
    """
    Runs a simple TCP server that accepts incoming peer connections forever.
    Must be called in a background daemon thread so it does not block the HTTP server.

    Implementation steps:
    1. Create a TCP socket (socket.AF_INET, socket.SOCK_STREAM)
    2. Set SO_REUSEADDR so the port can be reused after restart
    3. Bind to ("0.0.0.0", port)
    4. socket.listen(10)
    5. Loop forever:
       a. conn, addr = server.accept()
       b. Spawn a daemon Thread targeting handle_peer_message(conn, addr)
       c. t.start()

    :param port: the port to listen on
    """
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind(("0.0.0.0", port))
    server.listen(10)
    print(f"[P2P] Listening on port {port}")
    while True:
        conn, addr = server.accept()
        t = threading.Thread(target=handle_peer_message, args=(conn, addr))
        t.daemon = True
        t.start()
