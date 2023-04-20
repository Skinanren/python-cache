# https://www.digitalocean.com/community/tutorials/python-http-client-request-get-post
# https://stackoverflow.com/questions/48908044/how-to-disable-ssl-verification-for-http-client-httpsconnection-class-in-python
# https://stackoverflow.com/questions/25582875/set-port-in-requests

from loguru import logger
import requests
import json
import random
import os
import sys
import time

# Set level of logging
logger.remove()
logger.add(sys.stderr, level="DEBUG") # set to "INFO" for benchmarking. Otherwise "DEBUG"

FRONTEND_PORT = 8000
frontend = os.getenv("FRONTEND_HOST", "localhost")
FRONTEND_HOSTNAME = f"http://{frontend}:{FRONTEND_PORT}"
logger.debug(FRONTEND_HOSTNAME)

p = 0.5 # probability from 0 to 1
company_names = [
    "GameStart", 
    "FishCo",
    "BoarCo",
    "MenhirCo",
    # "wrongname",    # Include a name that's not in the stock catalog
]
num_requests = 20 # the number of lookup-order requests to do

if __name__=="__main__":
    start_time = time.time()    # time in seconds
    for _ in range(num_requests):
        # # Lookup Request
        company_name = random.choice(company_names)
        r = requests.get(f"{FRONTEND_HOSTNAME}/stocks/{company_name}")  # send lookup request to frontend
        r = r.json()
        # if "data" not in r:
        #     continue
        # qty = r["data"]["quantity"]
        logger.debug(f"GET Response: {r}")
        print('hello')

        # # Order Request
        # if qty > 0:
        #     to_order = random.choices([0,1], weights=[1-p, p], k=1)[0]  # whether or not to order with probability p for ordering
        #     if to_order:
        #         # Randomly choose the parameters in the order
        company_name = random.choice(company_names)
        order_qty = random.randint(1,2)
        order_type = random.choice(["buy", "sell"])

        request_data = {"name": company_name, "quantity": order_qty, "type": order_type,}
        logger.debug(f"POST Request: {request_data}")
        r = requests.post(f"{FRONTEND_HOSTNAME}/orders", data=json.dumps(request_data).encode())     # send order request to frontend
        r = r.json()
        print('hello')
        logger.debug(f"POST Response: {r}")
    run_time = time.time() - start_time
    # logger.info(f"Runtime: {run_time}")
    print(f"{run_time}")
