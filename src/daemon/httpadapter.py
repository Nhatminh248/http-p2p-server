
"""
daemon.httpadapter
~~~~~~~~~~~~~~~~~

This module provides a http adapter object to manage and persist 
http settings (headers, bodies). The adapter supports both
raw URL paths and RESTful route definitions, and integrates with
Request and Response objects to handle client-server communication.
"""

from .request import Request
from .response import Response
from .dictionary import CaseInsensitiveDict

import json
import secrets

sessions = {}

def create_session(username):
    token = secrets.token_hex(16)
    sessions[username] = token 
    return token

def verify_session(token):
    return token in sessions.values()

class HttpAdapter:
    """
    A mutable :class:`HTTP adapter <HTTP adapter>` for managing client connections
    and routing requests.

    The `HttpAdapter` class encapsulates the logic for receiving HTTP requests,
    dispatching them to appropriate route handlers, and constructing responses.
    It supports RESTful routing via hooks and integrates with :class:`Request <Request>` 
    and :class:`Response <Response>` objects for full request lifecycle management.

    Attributes:
        ip (str): IP address of the client.
        port (int): Port number of the client.
        conn (socket): Active socket connection.
        connaddr (tuple): Address of the connected client.
        routes (dict): Mapping of route paths to handler functions.
        request (Request): Request object for parsing incoming data.
        response (Response): Response object for building and sending replies.
    """

    __attrs__ = [
        "ip",
        "port",
        "conn",
        "connaddr",
        "routes",
        "request",
        "response",
    ]

    def __init__(self, ip, port, conn, connaddr, routes):
        """
        Initialize a new HttpAdapter instance.

        :param ip (str): IP address of the client.
        :param port (int): Port number of the client.
        :param conn (socket): Active socket connection.
        :param connaddr (tuple): Address of the connected client.
        :param routes (dict): Mapping of route paths to handler functions.
        """

        #: IP address.
        self.ip = ip
        #: Port.
        self.port = port
        #: Connection
        self.conn = conn
        #: Conndection address
        self.connaddr = connaddr
        #: Routes
        self.routes = routes
        #: Request
        self.request = Request()
        #: Response
        self.response = Response(port=port)

    def handle_client(self, conn, addr, routes):
        """
        Handle an incoming client connection.

        This method reads the request from the socket, prepares the request object,
        invokes the appropriate route handler if available, builds the response,
        and sends it back to the client.

        :param conn (socket): The client socket connection.
        :param addr (tuple): The client's address.
        :param routes (dict): The route mapping for dispatching requests.
        """

        # Connection handler.
        self.conn = conn        
        # Connection address.
        self.connaddr = addr
        # Request handler
        req = self.request
        # Response handler
        resp = self.response

        # Handle the request
        msg = conn.recv(1024).decode()
        
        # Check if we need to read more based on Content-Length
        if "\r\n\r\n" in msg:
            header_part, body_part = msg.split("\r\n\r\n", 1)
            content_length = 0
            for line in header_part.splitlines():
                if line.lower().startswith("content-length:"):
                    try:
                        content_length = int(line.split(":", 1)[1].strip())
                    except ValueError:
                        pass
                    break
            
            # If body is incomplete, read the rest
            while len(body_part.encode()) < content_length:
                chunk = conn.recv(1024).decode()
                if not chunk:
                    break
                body_part += chunk
                msg = header_part + "\r\n\r\n" + body_part

        req.prepare(msg, routes)
        if req.headers is not None and addr:
            req.headers['x-client-ip'] = addr[0]
        if req.path is None:
            conn.sendall(resp.build_notfound())
            conn.close()
            return
        print("[HttpAdapter] Invoke handle_client connection {}".format(addr))

        # CORS preflight
        if req.method == 'OPTIONS':
            conn.sendall(self._cors_preflight())
            conn.close()
            return

        # Login: requires Basic Auth credentials
        if req.path == '/login':
            if hasattr(req, 'auth') and req.auth:
                username, password = req.auth
                if not self.verify_auth(username, password):
                    conn.sendall(resp.build_401())
                    conn.close()
                    return
                token = create_session(username)
                conn.sendall(resp.build_200_with_cookie(token))
                conn.close()
                return
            conn.sendall(resp.build_401())
            conn.close()
            return

        # All other paths: session cookie check only (ignore any auth header)
        if req.cookies:
            cookie_name = f"session_{self.port}"
            token = req.cookies.get(cookie_name, None)
            if token and not verify_session(token):
                conn.sendall(resp.build_401())
                conn.close()
                return

        if req.hook:
            result = req.hook(req.headers, req.body)
            response = self.build_json_response(req, result)
        else:
            response = resp.build_response(req)

        conn.sendall(response)
        conn.close()

    def extract_cookies(self, req, resp):
        """
        Build cookies from the :class:`Request <Request>` headers.

        :param req:(Request) The :class:`Request <Request>` object.
        :param resp: (Response) The res:class:`Response <Response>` object.
        :rtype: cookies - A dictionary of cookie key-value pairs.
        """
        cookies = {}
        cookie_str = req.headers.get('cookie', '')
        for pair in cookie_str.split(';'):
            if '=' in pair:
                key, value = pair.strip().split('=', 1)
                cookies[key] = value
        return cookies

    def build_response(self, req, resp):
        """Builds a :class:`Response <Response>` object 

        :param req: The :class:`Request <Request>` used to generate the response.
        :param resp: The  response object.
        :rtype: Response
        """
        response = Response()

        # Set encoding.
        response.encoding = get_encoding_from_headers(response.headers)
        response.raw = resp
        response.reason = response.raw.reason

        if isinstance(req.url, bytes):
            response.url = req.url.decode("utf-8")
        else:
            response.url = req.url

        # Add new cookies from the server.
        response.cookies = extract_cookies(req)

        # Give the Response some context.
        response.request = req
        response.connection = self

        return response

    def _cors_preflight(self):
        return (
            "HTTP/1.1 200 OK\r\n"
            "Access-Control-Allow-Origin: *\r\n"
            "Access-Control-Allow-Methods: GET, POST, PUT, DELETE, OPTIONS\r\n"
            "Access-Control-Allow-Headers: Content-Type, Authorization\r\n"
            "Content-Length: 0\r\n"
            "Connection: close\r\n"
            "\r\n"
        ).encode('utf-8')

    def build_json_response(self, req, content):
        """Builds an HTTP 200 response with JSON body as bytes.

        :param req: The :class:`Request <Request>` used to generate the response.
        :param content: The handler return value — bytes, dict, or str.
        :rtype: bytes
        """
        if isinstance(content, dict):
            body = json.dumps(content).encode('utf-8')
        elif isinstance(content, bytes):
            body = content
        else:
            body = str(content).encode('utf-8')

        header = (
            "HTTP/1.1 200 OK\r\n"
            "Content-Type: application/json\r\n"
            "Access-Control-Allow-Origin: *\r\n"
            "Content-Length: {}\r\n"
            "Connection: close\r\n"
            "\r\n"
        ).format(len(body))
        return header.encode('utf-8') + body


    # def get_connection(self, url, proxies=None):
        # """Returns a url connection for the given URL. 

        # :param url: The URL to connect to.
        # :param proxies: (optional) A Requests-style dictionary of proxies used on this request.
        # :rtype: int
        # """

        # proxy = select_proxy(url, proxies)

        # if proxy:
            # proxy = prepend_scheme_if_needed(proxy, "http")
            # proxy_url = parse_url(proxy)
            # if not proxy_url.host:
                # raise InvalidProxyURL(
                    # "Please check proxy URL. It is malformed "
                    # "and could be missing the host."
                # )
            # proxy_manager = self.proxy_manager_for(proxy)
            # conn = proxy_manager.connection_from_url(url)
        # else:
            # # Only scheme should be lower case
            # parsed = urlparse(url)
            # url = parsed.geturl()
            # conn = self.poolmanager.connection_from_url(url)

        # return conn


    def add_headers(self, request):
        """
        Add headers to the request.

        This method is intended to be overridden by subclasses to inject
        custom headers. It does nothing by default.

        
        :param request: :class:`Request <Request>` to add headers to.
        """
        pass

    def build_proxy_headers(self, proxy):
        """Returns a dictionary of the headers to add to any request sent
        through a proxy. 

        :class:`HttpAdapter <HttpAdapter>`.

        :param proxy: The url of the proxy being used for this request.
        :rtype: dict
        """
        headers = {}
        #
        # TODO: build your authentication here
        #       username, password =...
        # we provide dummy auth here
        #
        username, password = ("user1", "password")

        if username:
            headers["Proxy-Authorization"] = (username, password)

        return headers

    def verify_auth(self, username, password):
        with open('db/users.json', 'r', encoding='utf-8') as file:
            data = json.load(file)
        for user in data["users"]:
            if user["username"] == username and user["password"] == password:
                return True
        return False
    

        
        
