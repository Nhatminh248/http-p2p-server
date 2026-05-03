

"""
app.sampleapp
~~~~~~~~~~~~~~~~~

"""

import sys
import os
import importlib.util
import json

from daemon import AsynapRous

peer_list = {}

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



# peer_list = {}  # { "username": {"ip": "...", "port": ...} }

@app.route('/submit-info', methods=['POST'])
def submit_info(headers="", body=""):
    data = json.loads(body)
    
    peer_list["username"] = {
        "ip": data["ip"],
        "port": data["port"]
    }
    
    return {"status": "ok"}

@app.route('/get-list', methods=['GET'])
def get_list(header="", body=""):
    return peer_list

def create_sampleapp(ip, port):
    # Prepare and launch the RESTful application
    app.prepare_address(ip, port)
    app.run()

