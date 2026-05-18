# Custom HTTP Framework and Proxy Project

This project is a custom implementation of an HTTP framework, reverse proxy, and backend server using Python's `socket` and `threading` modules. It is designed to demonstrate core concepts of computer networking, including HTTP protocol handling, load balancing, and P2P communication.

## Project Structure

```text
.
├── apps/               # Application logic (e.g., sampleapp.py)
├── config/             # Configuration files (e.g., proxy.conf)
├── daemon/             # Core framework logic
│   ├── backend.py      # Backend server implementation
│   ├── proxy.py        # Proxy server implementation
│   ├── httpadapter.py  # HTTP request/response adapter
│   ├── request.py      # HTTP request parsing
│   ├── response.py     # HTTP response generation
│   └── ...
├── db/                 # Simple JSON-based data storage
├── static/             # Static assets (CSS, images)
├── www/                # Static HTML files
├── start_backend.py    # Entry point for a generic backend server
├── start_proxy.py      # Entry point for the reverse proxy
└── start_sampleapp.py  # Entry point for the sample P2P application
```

## Features

- **Custom HTTP Server**: Built from scratch using Python sockets.
- **Reverse Proxy**: Supports virtual hosting and round-robin load balancing.
- **RESTful Routing**: Easy-to-use routing system similar to Flask.
- **Concurrency Models**: Supports multi-threading, callback-based event loops, and non-blocking I/O using selectors.
- **Session Management**: Basic authentication and session tracking via cookies.
- **P2P Chat Application**:
  - Peer discovery and messaging.
  - Direct and broadcast communication.
  - Channel-based chat.
  - Gossip protocol for decentralized peer list synchronization.

## Prerequisites

- Python 3.x (Standard library only, no external dependencies required).

## How to Run

### 1. Start the Backend Server
You can start a generic backend server that serves the files in the `www/` directory.

```bash
python3 start_backend.py --server-ip 127.0.0.1 --server-port 9000
```

### 2. Start the Reverse Proxy
The proxy routes incoming requests to one or more backend servers based on the configuration in `config/proxy.conf`.

```bash
python3 start_proxy.py --server-ip 127.0.0.1 --server-port 8080
```

**Proxy Configuration (`config/proxy.conf`):**
The proxy uses an Nginx-like configuration format:
```nginx
host "127.0.0.1:8080" {
    proxy_pass http://127.0.0.1:9001;
    proxy_pass http://127.0.0.1:9002;
    dist_policy round-robin
}
```

### 3. Start the Sample Application
The sample application includes the P2P chat features. You can run multiple instances to test P2P communication.

```bash
# Instance 1
python3 start_sampleapp.py --server-port 9001 --peer-port 5001

# Instance 2
python3 start_sampleapp.py --server-port 9002 --peer-port 5002
```

## Usage

- Access the web interface at `http://localhost:8080` (via proxy) or directly at the application port (e.g., `http://localhost:9001`).
- The login system uses credentials stored in `db/users.json`.
- P2P chat features can be accessed via the `/chat.html` page (if available) or by interacting with the REST API endpoints.

## Core Components

- **`HttpAdapter`**: Handles the lifecycle of an HTTP request, from parsing the raw socket data to invoking route handlers and sending the response.
- **`Request` & `Response`**: Custom classes for modeling HTTP messages.
- **`AsynapRous`**: The main framework class (found in `daemon/asynaprous.py`) for defining routes and running the application.
