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
import pandas as pd

# ~~~~~============== CONFIGURATION  ==============~~~~~
team_name = "yeouidostreet"

# Parameters for moving averages
short_window = 5  # Short-term moving average period
long_window = 10  # Long-term moving average period
delta = 1  # Delta to add for placing buy/sell orders
trades_log = {}  # To log trades

def main():
    args = parse_arguments()

    exchange = ExchangeConnection(args=args)

    hello_message = exchange.read_message()
    print("First message from exchange:", hello_message)

    last_prices = []  # To store last prices for each trade
    price_df = pd.DataFrame(columns=['Price'])  # DataFrame to calculate moving averages

    while True:
        message = exchange.read_message()

        if message["type"] == "close":
            print("The round has ended")
            break
        elif message["type"] == "error":
            print(message)
        elif message["type"] == "reject":
            print(message)
        elif message["type"] == "fill":
            print(message)
        elif message["type"] == "trade":
            price = message['price']
            last_prices.append(price)
            price_df = price_df.append({'Price': price}, ignore_index=True)

            # Maintain enough data points for moving averages
            if len(price_df) >= long_window:
                price_df['Short_MA'] = price_df['Price'].rolling(window=short_window).mean()
                price_df['Long_MA'] = price_df['Price'].rolling(window=long_window).mean()

                # Check the latest values for trading decision
                latest_short_ma = price_df['Short_MA'].iloc[-1]
                latest_long_ma = price_df['Long_MA'].iloc[-1]

                # Generate trading signals
                if latest_short_ma > latest_long_ma:
                    # Bullish crossover (potential buy opportunity)
                    sell_price = price + delta
                    exchange.send_add_message(order_id=len(trades_log)+1, symbol="BOND", dir=Dir.SELL, price=sell_price, size=1)
                    trades_log[len(trades_log)+1] = {'action': 'SELL', 'price': sell_price}

                elif latest_short_ma < latest_long_ma:
                    # Bearish crossover (potential sell opportunity)
                    buy_price = price - delta
                    exchange.send_add_message(order_id=len(trades_log)+1, symbol="BOND", dir=Dir.BUY, price=buy_price, size=1)
                    trades_log[len(trades_log)+1] = {'action': 'BUY', 'price': buy_price}

                # Log current trades
                print(f'Trades log: {trades_log}')

# ~~~~~============== PROVIDED CODE ==============~~~~~

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
        """Read a single message from the exchange"""
        message = json.loads(self.reader.readline())
        if "dir" in message:
            message["dir"] = Dir(message["dir"])
        return message

    def send_add_message(self, order_id: int, symbol: str, dir: Dir, price: int, size: int):
        """Add a new order"""
        self._write_message({
            "type": "add",
            "order_id": order_id,
            "symbol": symbol,
            "dir": dir,
            "price": price,
            "size": size,
        })

    def send_cancel_message(self, order_id: int):
        """Cancel an existing order"""
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
    test_exchange_port_offsets = {"prod-like": 0, "slower": 1, "empty": 2}
    parser = argparse.ArgumentParser(description="Trade on an ETC exchange!")
    exchange_address_group = parser.add_mutually_exclusive_group(required=True)
    exchange_address_group.add_argument("--production", action="store_true", help="Connect to the production exchange.")
    exchange_address_group.add_argument("--test", type=str, choices=test_exchange_port_offsets.keys(), help="Connect to a test exchange.")
    args = parser.parse_args()
    args.add_socket_timeout = True

    if args.production:
        args.exchange_hostname = "production"
        args.port = 25000
    elif args.test:
        args.exchange_hostname = "test-exch-" + team_name
        args.port = 25000 + test_exchange_port_offsets[args.test]

    return args

if __name__ == "__main__":
    assert team_name != "REPLAC" + "EME", "Please put your team name in the variable [team_name]."
    main()