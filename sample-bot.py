#!/usr/bin/env python3
# ~~~~~==============   HOW TO RUN   ==============~~~~~
# 1) Configure things in CONFIGURATION section
# 2) Change permissions: chmod +x bot.py
# 3) Run in loop: while true; do ./bot.py --test prod-like; sleep 1; done

import argparse
from collections import deque
from enum import Enum
import time
import socket
import json



class Dir(str, Enum):
    BUY = "BUY"
    SELL = "SELL"


# ~~~~~============== CONFIGURATION  ==============~~~~~
# Replace "REPLACEME" with your team name!
team_name = "BREAKFASTBLEND"

# ~~~~~============== MAIN LOOP ==============~~~~~

# You should put your code here! We provide some starter code as an example,
# but feel free to change/remove/edit/update any of it as you'd like. If you
# have any questions about the starter code, or what to do next, please ask us!
#
# To help you get started, the sample code below tries to buy BOND for a low
# price, and it prints the current prices for VALE every second. The sample
# code is intended to be a working example, but it needs some improvement
# before it will start making good trades!

BONDBUY= []
BONDSELL = []

VALBUY = []
VALSELL = []
VALBZBUY = []
VALBZSELL = []

ADR_CONVERT = 10
XLF_CONVERT = 100

currOrderId = 0

def handleBook(message):
    global BONDBUY, BONDSELL, currOrderId

    if message["symbol"] == "BOND":
        # print("BOND MESSAGE" + str(message))
        BONDBUY = message["buy"]
        BONDSELL = message["sell"]
    elif message["symbol"] == "VALE":
        VALBUY = message["buy"]
        VALSELL = message["sell"]
    elif message["symbol"] == "VALBZ":
        VALBZBUY = message["buy"]
        VALBZSELL = message["sell"]
    

def handleADR(exchange):
    priceval = (VALBUY[0][0] + VALSELL[0][0])/2
    pricevalbz = (VALBZBUY[0][0] + VALBZSELL[0][0])/2

    if priceval - pricevalbz > ADR_CONVERT + 2:
        exchange.send_add_message(currOrderId, "VALBZ", Dir.BUY, pricevalbz)
        currOrderId += 1
        exchange.send_convert_message()



def handleBond(exchange):
    global BONDBUY, BONDSELL, currOrderId
    # 0 is buy
    # 1 is sell
    if BONDBUY and BONDBUY[0][0] > 1000:
        exchange.send_add_message(currOrderId, "BOND", Dir.SELL, 1001, 10)
        print("Sold bonds.")
        currOrderId += 1  

    if BONDSELL and BONDSELL[0][0] < 1000:
        exchange.send_add_message(currOrderId, "BOND", Dir.BUY, 999, 10)
        print("Bought bonds.")
        currOrderId += 1  


def main():
    args = parse_arguments()

    exchange = ExchangeConnection(args=args)

    # Store and print the "hello" message received from the exchange. This
    # contains useful information about your positions. Normally you start with
    # all positions at zero, but if you reconnect during a round, you might
    # have already bought/sold symbols and have non-zero positions.
    hello_message = exchange.read_message()
    print("First message from exchange:", hello_message)

    # # Send an order for BOND at a good price, but it is low enough that it is
    # # unlikely it will be traded against. Maybe there is a better price to
    # # pick? Also, you will need to send more orders over time.
    # exchange.send_add_message(order_id=1, symbol="BOND", dir=Dir.BUY, price=990, size=1)

    # # Set up some variables to track the bid and ask price of a symbol. Right
    # # now this doesn't track much information, but it's enough to get a sense
    # # of the VALE market.
    # vale_bid_price, vale_ask_price = None, None
    # vale_last_print_time = time.time()

    # Here is the main loop of the program. It will continue to read and
    # process messages in a loop until a "close" message is received. You
    # should write to code handle more types of messages (and not just print
    # the message). Feel free to modify any of the starter code below.
    #
    # Note: a common mistake people make is to call write_message() at least
    # once for every read_message() response.
    #
    # Every message sent to the exchange generates at least one response
    # message. Sending a message in response to every exchange message will
    # cause a feedback loop where your bot's messages will quickly be
    # rate-limited and ignored. Please, don't do that!
    while True:
        message = exchange.read_message()

        # Some of the message types below happen infrequently and contain
        # important information to help you understand what your bot is doing,
        # so they are printed in full. We recommend not always printing every
        # message because it can be a lot of information to read. Instead, let
        # your code handle the messages and just print the information
        # important for you!
        if message["type"] == "close":
            print("The round has ended")
            break
        elif message["type"] == "error":
            print(message)
        elif message["type"] == "reject":
            # print(message)
            pass
        elif message["type"] == "fill":
            # print(message)
            pass
        elif message["type"] == "book":
            handleBook(message)
            # print(message)
        elif message['type'] == 'ack':
            # print(message)
            pass
        elif message['type'] == 'trade':
            # print(message)
            pass
    
        handleBond(exchange)
        time.sleep(0.01)
            # if message["symbol"] == "VALE":

            #     def best_price(side):
            #         if message[side]:
            #             return message[side][0][0]

            #     vale_bid_price = best_price("buy")
            #     vale_ask_price = best_price("sell")

            #     now = time.time()

            #     if now > vale_last_print_time + 1:
            #         vale_last_print_time = now
            #         print(
            #             {
            #                 "vale_bid_price": vale_bid_price,
            #                 "vale_ask_price": vale_ask_price,
            #             }
            #         )


# ~~~~~============== PROVIDED CODE ==============~~~~~

# You probably don't need to edit anything below this line, but feel free to
# ask if you have any questions about what it is doing or how it works. If you
# do need to change anything below this line, please feel free to


class ExchangeConnection:
    def __init__(self, args):
        self.message_timestamps = deque(maxlen=500)
        self.exchange_hostname = args.exchange_hostname
        self.port = args.port
        self.exchange_socket = self._connect(add_socket_timeout=args.add_socket_timeout)

        self._write_message({"type": "hello", "team": team_name.upper()})

    def read_message(self):
        """Read a single message from the exchange"""
        message = json.loads(self.exchange_socket.readline())
        if "dir" in message:
            message["dir"] = Dir(message["dir"])
        return message

    def send_add_message(
        self, order_id: int, symbol: str, dir: Dir, price: int, size: int
    ):
        """Add a new order"""
        self._write_message(
            {
                "type": "add",
                "order_id": order_id,
                "symbol": symbol,
                "dir": dir,
                "price": price,
                "size": size,
            }
        )

    def send_convert_message(self, order_id: int, symbol: str, dir: Dir, size: int):
        """Convert between related symbols"""
        self._write_message(
            {
                "type": "convert",
                "order_id": order_id,
                "symbol": symbol,
                "dir": dir,
                "size": size,
            }
        )

    def send_cancel_message(self, order_id: int):
        """Cancel an existing order"""
        self._write_message({"type": "cancel", "order_id": order_id})

    def _connect(self, add_socket_timeout):
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        if add_socket_timeout:
            # Automatically raise an exception if no data has been recieved for
            # multiple seconds. This should not be enabled on an "empty" test
            # exchange.
            s.settimeout(5)
        s.connect((self.exchange_hostname, self.port))
        return s.makefile("rw", 1)

    def _write_message(self, message):
        json.dump(message, self.exchange_socket)
        self.exchange_socket.write("\n")

        now = time.time()
        self.message_timestamps.append(now)
        if len(
            self.message_timestamps
        ) == self.message_timestamps.maxlen and self.message_timestamps[0] > (now - 1):
            print(
                "WARNING: You are sending messages too frequently. The exchange will start ignoring your messages. Make sure you are not sending a message in response to every exchange message."
            )

def parse_arguments():
    test_exchange_port_offsets = {"prod-like": 0, "slower": 1, "empty": 2}

    parser = argparse.ArgumentParser(description="Trade on an ETC exchange!")
    exchange_address_group = parser.add_mutually_exclusive_group(required=True)
    exchange_address_group.add_argument(
        "--production", action="store_true", help="Connect to the production exchange."
    )
    exchange_address_group.add_argument(
        "--test",
        type=str,
        choices=test_exchange_port_offsets.keys(),
        help="Connect to a test exchange.",
    )

    # Connect to a specific host. This is only intended to be used for debugging.
    exchange_address_group.add_argument(
        "--specific-address", type=str, metavar="HOST:PORT", help=argparse.SUPPRESS
    )

    args = parser.parse_args()
    args.add_socket_timeout = True

    if args.production:
        args.exchange_hostname = "production"
        args.port = 25000
    elif args.test:
        args.exchange_hostname = "test-exch-" + team_name
        args.port = 25000 + test_exchange_port_offsets[args.test]
        if args.test == "empty":
            args.add_socket_timeout = False
    elif args.specific_address:
        args.exchange_hostname, port = args.specific_address.split(":")
        args.port = int(port)

    return args

if __name__ == "__main__":
    # Check that [team_name] has been updated.
    assert (
        team_name != "REPLACEME"
    ), "Please put your team name in the variable [team_name]."

    while True:
        try:
            main()
        except socket.error:
            print("Can't connect to socket")
            time.sleep(0.1)


    