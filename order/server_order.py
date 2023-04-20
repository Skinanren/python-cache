import json
import os
from http.server import HTTPServer, BaseHTTPRequestHandler
from loguru import logger
from io import BytesIO
import requests
import pandas as pd
import socket
import threading


NUM_THREADS = 3
ERROR_RESPONSE = {
    "error": {
        "code": 404,
        "message": "stock not found",
    }
}
FRONTEND_PORT = 8000
frontend = os.getenv("FRONTEND_HOST", "localhost")
FRONTEND_HOSTNAME = f"http://{frontend}:{FRONTEND_PORT}"

CATALOG_PORT = 8001
catalog = os.getenv("CATALOG_HOST", "localhost")
CATALOG_HOSTNAME = f"http://{catalog}:{CATALOG_PORT}"

ORDER_PORT = 8002
order = os.getenv("ORDER_HOST", "localhost")
ORDER_HOSTNAME = f"http://{order}:{ORDER_PORT}"
logger.debug(f"FRONTEND_HOSTNAME:{FRONTEND_HOSTNAME}, CATALOG_HOSTNAME:{CATALOG_HOSTNAME}, ORDER_HOSTNAME:{ORDER_HOSTNAME}")

readwrite_lock = threading.Lock()
PATH = os.path.join(os.getcwd(), 'data')
os.makedirs(PATH, exist_ok=True)
logger.debug(f"PATH: {PATH}")
LOGS_DF_NAME = f"{PATH}/order_logs.csv" # where logs will be loaded/saved
LOGS = []
LOG_CUR_COUNT = 0

def load_logs(fname):
    logs = LOGS
    log_cur_count = LOG_CUR_COUNT
    if os.path.exists(fname):
        logs_df = pd.read_csv(fname)
        log_cur_count = max(logs_df["transaction_number"]) + 1
        logs = logs_df.to_dict("records")
    return logs, log_cur_count

def update_logs(transaction_num, post_data):
    LOGS.append({
        "transaction_number": transaction_num,
        "company_name": post_data["name"],  # stock name
        "order_type": post_data["type"],
        "quantity": post_data["quantity"],
    })
    df = pd.DataFrame(LOGS)
    df.to_csv(LOGS_DF_NAME, index=False)    # save to file

def process_request(post_data):
    r = requests.post(f"{CATALOG_HOSTNAME}/orders", data=post_data.encode())  # send request to order server
    response = r.json()
    logger.debug(f"POST request response: {response}")
    if "error" in response:
        return False, response    # means request not successful
    return True, response

class RequestHandler(BaseHTTPRequestHandler):
    def do_POST(self):  # endpoint called by the Order Service
        global LOG_CUR_COUNT
        logger.debug("POST request")
        self.send_response(200)
        self.end_headers()
        response = BytesIO()

        sample_json = ERROR_RESPONSE
        if self.path == "/orders":
            content_length = int(self.headers['Content-Length']) # Gets the size of data from client
            post_data = self.rfile.read(content_length).decode("utf-8") # Gets the data itself
            logger.debug(f"post_data: {post_data}")
            is_successful, post_response = process_request(post_data=post_data)
            sample_json = post_response
            if is_successful:
                readwrite_lock.acquire()
                sample_json = {
                    "data": {
                        "transaction_number": LOG_CUR_COUNT,    # TODO: store (unique) transaction numbers and logs
                    }
                }
                update_logs(LOG_CUR_COUNT, json.loads(post_data))
                LOG_CUR_COUNT += 1
                readwrite_lock.release()
        # response.write(json.dumps(sample_json).encode())
        response.write(json.dumps(post_response).encode())
        self.wfile.write(response.getvalue())

LOGS, LOG_CUR_COUNT = load_logs(fname=LOGS_DF_NAME)
print(f"LOG_CUR_COUNT: {LOG_CUR_COUNT}")
logger.info(f"Order Server Starting...")

# Threadpool implementation from https://stackoverflow.com/a/46228009
addr = ('0.0.0.0', ORDER_PORT)
sock = socket.socket (socket.AF_INET, socket.SOCK_STREAM)
sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
sock.bind(addr)
sock.listen(5)

class Thread(threading.Thread):
    def __init__(self, i):
        threading.Thread.__init__(self)
        self.i = i
        self.daemon = True
        self.start()
    def run(self):
        httpd = HTTPServer(addr, RequestHandler, False)

        # Prevent the HTTP server from re-binding every handler.
        # https://stackoverflow.com/questions/46210672/
        httpd.socket = sock
        httpd.server_bind = self.server_close = lambda self: None
        httpd.serve_forever()   # handle http requests
[Thread(i) for i in range(NUM_THREADS)] # threadpool
while True:
    pass