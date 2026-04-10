# Assignment 1: Non-blocking HTTP Server and Chat Application

## 1. Tasks Overview
As specified by the lecturer, the assignment consists of the following major tasks:

*   **Task 1: Implement Non-blocking Mechanisms**
*   **Task 2: Implement HTTP Authentication**
*   **Task 3: Implement Hybrid Chat Application**
*   **Task 4: System Integration**

---

## 2. Detailed Task Instructions

### Task 1: Non-blocking Mechanisms Implementation
**Objective:** Transition the server from a synchronous "one-thread-per-connection" model to an asynchronous event-driven model.

#### Step-by-Step Guide:
1.  **Socket Configuration**: Locate the socket initialization in `daemon/backend.py` and `daemon/proxy.py`. Call `s.setblocking(False)` to ensure I/O calls return immediately.
2.  **Event Loop Integration**: Implement the `Runner` class (as shown in Listing 6 of the PDF) to manage the `asyncio` event loop.
3.  **Handling Asynchrony**: Wrap `socket.send()` and `socket.recv()` calls within `try...except BlockingIOError` blocks or use `loop.sock_recv()` and `loop.sock_sendall()`.
4.  **Concurrency Model**: Transition the `handle_client` function into an `async def` coroutine. Use `await` for all I/O operations to allow the event loop to switch tasks while waiting for data.

**Theory Context: I/O Multiplexing**
In traditional **Blocking I/O**, a process waits (sleeps) until data is ready, wasting CPU cycles. **Non-blocking I/O** allows a single process to handle thousands of concurrent connections by using an **Event Loop** (based on system calls like `select`, `poll`, or `epoll`). The loop constantly checks which sockets are "ready" for reading or writing, ensuring high throughput and low resource consumption.

---

### Task 2: HTTP Authentication & State Management
**Objective:** Secure the server and enable session persistence using standard web protocols.

#### Step-by-Step Guide:
1.  **Request Parsing**: Modify `daemon/request.py` to parse the `Authorization` header (for Basic/Digest) and the `Cookie` header.
2.  **Credential Validation**: Implement a verification check against a user database (stored in `db/`).
3.  **Unauthorized Response**: If credentials are missing or invalid, use `daemon/response.py` to return a `401 Unauthorized` status code with the `WWW-Authenticate: Basic realm="Access to Chat"` header.
4.  **Session Persistence**: Upon successful login, generate a session ID and use the `Set-Cookie` header in the response to store it in the user's browser (RFC 6265).

**Theory Context: Stateless vs. Stateful HTTP**
HTTP is a **stateless protocol**, meaning the server treats every request as new. To build applications like a "Chat," we must create a "state." **Basic Authentication** (RFC 7235) handles identity, while **Cookies** (RFC 6265) allow the server to "remember" a client across multiple requests without re-authenticating every single time.

---

### Task 3: Hybrid Chat Application
**Objective:** Build a chat system that combines a centralized tracker for discovery and direct P2P for communication.

#### Step-by-Step Guide:
1.  **Initialization (Client-Server)**:
    *   Implement `/login` API to register the peer's IP/Port.
    *   Implement `/submit-info` to update the tracker with the peer's active status.
    *   Implement `/get-list` to allow peers to fetch the current list of active users.
2.  **P2P Communication (Peer-to-Peer)**:
    *   **Direct Send**: Use the `/send-peer` API to establish a direct TCP connection between two peers using their discovered IPs.
    *   **Broadcast**: Implement `/broadcast-peer` which loops through the fetched peer list and sends the message to each one individually.
3.  **Channel Management**: Implement logic in `apps/sampleapp.py` to filter messages based on channel names and display them in the UI.

**Theory Context: P2P vs. Client-Server Paradigms**
A **Client-Server** model is used here for **Discovery** because a central "Tracker" is the most efficient way to keep track of dynamic IP addresses. Once peers know each other, they switch to a **Peer-to-Peer (P2P)** model for **Data Transfer** (the chat messages), which reduces the load on the central server and improves privacy/scalability.

---

### Task 4: System Integration & Verification
**Objective:** Consolidate all modules into a functional, non-blocking ecosystem.

#### Step-by-Step Guide:
1.  **Configuration**: Define routing rules in `config/proxy.conf` to map hostnames (e.g., `app1.local`) to specific backend ports.
2.  **Process Execution**: 
    *   Start the Proxy: `python start_proxy.py`.
    *   Start the Backend: `python start_backend.py`.
    *   Start the App: `python start_sampleapp.py`.
3.  **Validation**: Use a REST client or browser to verify that the Proxy correctly forwards requests, the Backend enforces Authentication, and the WebApp allows P2P messaging without blocking other users.

**Theory Context: Layered Architecture & Encapsulation**
This task applies the **End-to-End Principle**. By separating the Proxy (Network Edge), Backend (Business Logic), and App (User Interface), we ensure that changes in one layer (like moving from blocking to non-blocking) do not require a complete rewrite of the others, provided the interfaces (HTTP/TCP) remain consistent.

---

## 3. Suggested Folder Structure

```text
CO3094-asynaprous/
├── apps/                # Task 3: Chat Logic & P2P APIs
├── config/              # Task 4: Proxy Routing & Load Balancing
├── daemon/              # Task 1 & 2: Core Non-blocking & Auth Logic
│   ├── asynaprous.py    # Framework entry
│   ├── backend.py       # Non-blocking server
│   ├── request.py       # Header & Auth parsing
│   └── response.py      # Cookie & Status code handling
├── db/                  # Task 2: User credentials
└── www/                 # Task 3: Chat UI (HTML/JS)
```

---

## 4. Useful References
*   [RFC 7235: HTTP Authentication](https://www.rfc-editor.org/rfc/rfc7235)
*   [RFC 6265: HTTP Cookies](https://www.rfc-editor.org/rfc/rfc6265)
*   [Python Asyncio Docs](https://docs.python.org/3/library/asyncio.html)
