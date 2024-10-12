#!/usr/bin/env python3
import argparse
from collections import deque
from enum import Enum
import time
import socket
import json

team_name = "JavaJabba"

# Define the stocks and delta
regular_stocks = ['BOND', 'GS', 'MS', 'VALBZ', 'VALE', 'WFC', 'XLF']
delta = 1  # You can adjust this value as needed
sales_log = {stock: [] for stock in regular_stocks}  # Logging sales for each stock
# one unique order id for each asset and side, e.g. 'WFC' and 'B'
oid = {}
BASE_OID = 0
for asset in regular_stocks:
    oid[asset+'B'] = BASE_OID+1
    oid[asset+'S'] = BASE_OID+2
    BASE_OID += 2

def main():
    args = parse_arguments()

    exchange = ExchangeConnection(args=args)

    hello_message = exchange.read_message()
    print("First message from exchange:", hello_message)

    last_price = {}

    while True:
        message = exchange.read_message()

        # Handle the closing of the round
        if message["type"] == "close":
            print("The round has ended")
            break

        # Display error messages
        elif message["type"] in ['error', 'reject', 'fill']:
            print(message)

        # Handle trade messages where we can get the last sold stock
        elif message["type"] == "trade":
            sym = message["symbol"]
            price = message['price']
            last_price[sym] = price  # Track the last price for each stock

            b_oid = oid[sym+'B']
            s_oid = oid[sym+'S']

            # Only proceed if the stock is one of the regular stocks
            if sym in regular_stocks:
                exchange.send_cancel_message(order_id=b_oid)
                exchange.send_cancel_message(order_id=s_oid)

                print(f"Last sold {sym} at price {price}")

                # Execute a SELL order at last sold price + delta
                sell_price = price + delta
                exchange.send_add_message(order_id=s_oid, symbol=sym, dir=Dir.SELL, price=sell_price, size=1)
                sales_log[sym].append({"action": "sell", "price": sell_price})

                # Execute a BUY order at last sold price + delta
                buy_price = price + delta
                exchange.send_add_message(order_id=b_oid, symbol=sym, dir=Dir.BUY, price=buy_price, size=1)
                sales_log[sym].append({"action": "buy", "price": buy_price})

            # Logging sales for each stock
            print(f"Current sales log for {sym}: {sales_log[sym]}")

        # Update this section as needed to capture additional types of messages
        # ...

class Dir(str, Enum):
    BUY = "BUY"
    SELL = "SELL"

class ExchangeConnection:
    def __init__(self, args):
        self.message_timestamps = deque(maxlen=500)
        self.exchange_hostname = args.exchange_hostname
        self.port = args.port
        exchange_socket = self._connect(add_socket_timeout=args.add_socket_timeout)
        self.reader = exchange_socket.makefile("r", 1)
        self.writer = exchange_socket
        self._write_message({"type": "hello", "team": team_name.upper()})

    def read_message(self):
        message = json.loads(self.reader.readline())
        if "dir" in message:
            message["dir"] = Dir(message["dir"])
        return message

    def send_add_message(self, order_id: int, symbol: str, dir: Dir, price: int, size: int):
        self._write_message({
            "type": "add",
            "order_id": order_id,
            "symbol": symbol,
            "dir": dir,
            "price": price,
            "size": size,
        })

    def send_cancel_message(self, order_id: int):
        self._write_message({"type": "cancel", "order_id": order_id})

    def _connect(self, add_socket_timeout):
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        if add_socket_timeout:
            s.settimeout(5)
        s.connect((self.exchange_hostname, self.port))
        return s

    def _write_message(self, message):
        what_to_write = json.dumps(message) + "\n"
        self.writer.sendall(what_to_write.encode("utf-8"))

def parse_arguments():
    parser = argparse.ArgumentParser(description="Trade on an ETC exchange!")
    exchange_address_group = parser.add_mutually_exclusive_group(required=True)
    exchange_address_group.add_argument("--production", action="store_true", help="Connect to the production exchange.")
    exchange_address_group.add_argument("--test", type=str, choices=["prod-like", "slower", "empty"], help="Connect to a test exchange.")
    args = parser.parse_args()
    args.add_socket_timeout = True

    if args.production:
        args.exchange_hostname = "production"
        args.port = 25000
    elif args.test:
        args.exchange_hostname = "test-exch-" + team_name
        args.port = 25000 + {"prod-like": 0, "slower": 1, "empty": 2}[args.test]

    return args

if __name__ == "__main__":
    assert team_name != "REPLAC" + "EME", "Please put your team name in the variable [team_name]."
    main()