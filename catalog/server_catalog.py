# References
# https://stackoverflow.com/a/46224191

import json
import os
from http.server import HTTPServer, BaseHTTPRequestHandler
from loguru import logger
from io import BytesIO
import threading
import socket


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


COMP_NAME = ''

NUM_THREADS = 3
readwrite_lock = threading.Lock()
PATH = os.path.join(os.getcwd(), 'data')
os.makedirs(PATH, exist_ok=True)
logger.debug(f"PATH: {PATH}")
STOCKS_JSON_FNAME = f"{PATH}/stocks_data.json"    # location to save local stock catalog for persistence
STOCKS = {  # Initialize arbitrary stock catalog
    "GameStart": {"price": 11.2, "trade_vol": 0, "quantity": 100},
    "FishCo": {"price": 10, "trade_vol": 0, "quantity": 100},
    "BoarCo": {"price": 13, "trade_vol": 0, "quantity": 100},
    "MenhirCo": {"price": 12.5, "trade_vol": 0, "quantity": 100},
}

def load_catalog(fname=STOCKS_JSON_FNAME):
    stocks = STOCKS
    if os.path.exists(fname):
        stocks = json.load(open(fname))
    return stocks

def update_local_catalog(stocks, fname=STOCKS_JSON_FNAME):
    with open(fname, "w") as f: # Save stock catalog to file
        json.dump(stocks, f, indent=4)

def update_stocks(company_name, post_data):
    # a buy trade request should succeed only if the remaining quantity of the stock 
    # is greater than the requested quantity, and the quantity should be decremented. 
    # A sell trade request will simply increase the remaining quantity of the stock.
    if company_name in STOCKS:
        qty = post_data["quantity"]
        if post_data["type"]=="sell":
            STOCKS[company_name]["quantity"] += qty  # increase remaining quantity of stock
            STOCKS[company_name]["trade_vol"] += qty
        elif post_data["type"] == "buy":
            if STOCKS[company_name]["quantity"] >= qty:
                STOCKS[company_name]["quantity"] -= qty  # decrease remaining quantity of stock
                STOCKS[company_name]["trade_vol"] += qty
            else:
                return {
                    "error": {
                        "code": 404,
                        "message": f"Buy quantity ({qty}) is more than the remaining ({STOCKS[company_name]['quantity']})",
                    }
                }
    else:
        return ERROR_RESPONSE
    return STOCKS[company_name]
        
class RequestHandler(BaseHTTPRequestHandler):
    def do_GET(self):   # endpoint called by the Front-end Service
        global STOCKS
        self.send_response(200)
        self.end_headers()
        response = BytesIO()

        logger.debug(f"GET request. path: {self.path}")
        path = self.path.split("/")
        sample_json = ERROR_RESPONSE
        mjson = ''
        if len(path) == 3:
            _, endpoint, company_name = self.path.split("/")
            # if company_name in STOCKS:
            #     mjson = json.dumps(STOCKS[company_name]) 
            COMP_NAME = '{}'.format(company_name)
            if endpoint == 'stocks':
                logger.info(f"Getting data for: {company_name}")
                print('hello')    
                if company_name in STOCKS:
                    readwrite_lock.acquire()
                    print('hello')
                    sample_json = {
                        "data": {
                            "name": company_name,
                            **STOCKS[company_name]
                        }
                    }
                    readwrite_lock.release()
        # TODO: Handle other errors (e.g., wrong endpoint, wrong company name)
        print(COMP_NAME)
        response.write(json.dumps(STOCKS[COMP_NAME]).encode())
        # response.write(json.dumps(sample_json).encode())
        self.wfile.write(response.getvalue())

    def do_POST(self):  # endpoint called by the Order Service
        global STOCKS, STOCKS_JSON_FNAME
        logger.debug("POST request")
        self.send_response(200)
        self.end_headers()
        response = BytesIO()

        sample_json = ERROR_RESPONSE
        if self.path == "/orders":
            content_length = int(self.headers['Content-Length']) # Gets the size of data from client
            post_data = self.rfile.read(content_length).decode("utf-8") # Gets the data itself
            post_data = json.loads(post_data)   # Covert to dictionary object from string
            company_name = post_data["name"]

            COMP_NAME = '{}'.format(company_name)

            # Update the stock data
            readwrite_lock.acquire()
            sample_json = update_stocks(company_name, post_data)
            if "error" not in sample_json:
                update_local_catalog(STOCKS, fname=STOCKS_JSON_FNAME)   # Update copy in disk
            readwrite_lock.release()

        response.write(json.dumps(STOCKS[COMP_NAME]).encode())    
        # response.write(json.dumps(sample_json).encode())
        self.wfile.write(response.getvalue())

STOCKS = load_catalog(fname=STOCKS_JSON_FNAME)  # overwrite stocks with disk copy
logger.info(f"Catalog Server Starting...")

# Threadpool implementation from https://stackoverflow.com/a/46228009
addr = ('0.0.0.0', CATALOG_PORT)
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



 
            # if endpoint == "stocks":