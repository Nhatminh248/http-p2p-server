# Computer Network Assignment 1: Asynaprous Guide

## Project Overview
This assignment involves implementing a non-blocking HTTP server and a hybrid chat application (Client-Server + P2P).

## Task List

### 1. Non-blocking HTTP Server
- [ ] **Asynchronous I/O Implementation**: 
    - Modify `CO3094-asynaprous/daemon/proxy.py` to handle incoming connections asynchronously.
    - Modify `CO3094-asynaprous/daemon/backend.py` to process requests without blocking.
    - Utilize `asyncio` or `selectors` as per the implementation requirements in Section 2.1.
- [ ] **Proxy Routing**: Ensure the proxy correctly forwards requests to the appropriate backend pool based on `config/proxy.conf`.

### 2. HTTP Authentication & Session Management
- [ ] **Authentication**:
    - Implement Basic/Digest authentication in `CO3094-asynaprous/daemon/httpadapter.py`.
    - Handle `WWW-Authenticate` and `Authorization` headers.
- [ ] **Cookies**:
    - Implement cookie handling in `CO3094-asynaprous/daemon/request.py` and `CO3094-asynaprous/daemon/response.py`.
    - Support session persistence using `Set-Cookie`.

### 3. Hybrid Chat Application
- [ ] **Client-Server Initialization**:
    - Implement peer registration and tracker updates.
    - API: `GET /get-list` to discover active peers.
- [ ] **Peer-to-Peer Chatting**:
    - Implement direct socket communication between peers for chatting.
    - Support message broadcasting to all connected peers.
- [ ] **API Implementation**:
    - `/login`: User authentication.
    - `/submit-info`: Register peer info.
    - `/add-list`/`/get-list`: Tracker management.
    - `/connect-peer`/`/send-peer`: P2P communication.

### 4. Testing & Validation
- [ ] Run `start_proxy.py`, `start_backend.py`, and `start_sampleapp.py`.
- [ ] Verify non-blocking behavior with multiple concurrent clients.
- [ ] Test authentication and cookie persistence in the browser.
- [ ] Validate P2P message exchange between multiple chat instances.

## Technical Requirements
- **Language**: Python 3.x
- **Style**: Adhere to PEP 8 and PEP 257 (Docstrings).
- **Restrictions**: No external JavaScript frameworks; use pure Python for backend logic.

## Submission Checklist
- [ ] Source code organized as per Section 1.2.
- [ ] Report included in the source directory.
- [ ] Compressed as `assignment_STUDENTID.zip`.
