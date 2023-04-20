# References:
# https://blog.anvileight.com/posts/simple-python-http-server/
# https://stackoverflow.com/questions/18346583/how-do-i-map-incoming-path-requests-when-using-httpserver
# https://stackoverflow.com/questions/33003498/typeerror-a-bytes-like-object-is-required-not-str
# https://gist.github.com/mdonkers/63e115cc0c79b4f6b8b3a6b797e485c7

from http.server import HTTPServer, BaseHTTPRequestHandler
from io import BytesIO
from loguru import logger
import json
import os
import requests
from multiprocessing.pool import ThreadPool
import socket, threading
import ast


cache = []
cache2 = []
 
PATH = os.path.join(os.getcwd(), 'data')
os.makedirs(PATH, exist_ok=True)
logger.debug(f"PATH: {PATH}")

# Additional Code 
FIlE_NAME = f"{PATH}/cache_data.json"   
COM_NAME = ''

NUM_THREADS = 3
ERROR_RESPONSE = {
    "error": {
        "code": 404,
        "message": "stock not found",
    }
}
CHECK_ERR = {
    "error":{
        "message":"You have already checked",
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

class RequestHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        response = BytesIO()
        
        logger.debug(f"GET request. path: {self.path}")
        path = self.path.split("/")
        sample_json = ERROR_RESPONSE

        if len(path)==3:
            _, endpoint, company_name = self.path.split("/")
            COM_NAME = '{}'.format(company_name)
            if endpoint == "stocks":
                logger.info(f"Getting data for: {company_name}")

                targeturl = '{}{}{}'.format(CATALOG_HOSTNAME,"/stock/",company_name)
                print(targeturl)

                if targeturl not in cache:
                    cache.append(targeturl)
                    print(cache)

                 # r = requests.get(f"{CATALOG_HOSTNAME}/stocks/{company_name}")   # send request to catalog server
                    
                    r = requests.get(targeturl)   # send request to catalog server
                    sample_json = r.json()
                    # print(sample_json)
                    newdata = {
                        'price':sample_json['price'],
                        "trade_vol": sample_json['trade_vol'],
                        "quantity": sample_json['quantity']
                    }
                    with open(FIlE_NAME, "r+") as outfile:
                        file_data = json.load(outfile)
                  
                    if COM_NAME not in file_data:
                        file_data[COM_NAME] = newdata
                        print('hello')
                        print(file_data)
                    with open(FIlE_NAME, "r+") as outfile:
                         json.dump(file_data,outfile,indent=4)
                    print('newdata = ',newdata)
                else:
                    with open(FIlE_NAME,"r") as json_data:
                        file_data = json.load(json_data)
                    if COM_NAME in file_data:
                        print('Hello Print response')
                        print('response = ',file_data[COM_NAME])
                        sample_json = file_data[COM_NAME]
            response.write(json.dumps(sample_json).encode())
            self.wfile.write(response.getvalue())
            
    def do_POST(self):
        logger.debug("POST request")
        self.send_response(200)
        self.end_headers()
        response = BytesIO()

        sample_json = ERROR_RESPONSE
        if self.path == "/orders":
            content_length = int(self.headers['Content-Length']) # Gets the size of data from client
            post_data = self.rfile.read(content_length).decode("utf-8") # Gets the data itself
            logger.debug(f"post_data: {post_data}")

            # new part
            my_dict = ast.literal_eval(post_data)
            print('post_data =', my_dict['name'])
            targeturl ='{}{}{}'.format(my_dict['name'],my_dict['quantity'],my_dict['type'])
            if targeturl not in cache2:
                cache2.append(targeturl)
                print(cache2)
                r = requests.post(f"{ORDER_HOSTNAME}/orders", data=post_data.encode())  # send request to order server
                sample_json = r.json()

            else:
                print("You have already checked")
            # r = requests.post(f"{ORDER_HOSTNAME}/orders", data=post_data.encode())  # send request to order server
            # sample_json = r.json()

        response.write(json.dumps(sample_json).encode())
        self.wfile.write(response.getvalue())


logger.info(f"Frontend Server Starting...")

# Threadpool implementation from https://stackoverflow.com/a/46228009
addr = ('0.0.0.0', FRONTEND_PORT)
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