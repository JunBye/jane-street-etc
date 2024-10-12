import numpy as np
import pandas as pd

# Sample data: Today's market prices (example list)
market_prices = [100, 102, 101, 105, 107, 106, 110, 112, 115, 114, 117, 120]

# Parameters for moving averages
short_window = 3  # Short-term moving average period
long_window = 5   # Long-term moving average period

# Convert the price list to a pandas DataFrame for easier manipulation
prices_df = pd.DataFrame(market_prices, columns=['Price'])

# Calculate moving averages
prices_df['Short_MA'] = prices_df['Price'].rolling(window=short_window).mean()
prices_df['Long_MA'] = prices_df['Price'].rolling(window=long_window).mean()

# Initialize signals and the position
prices_df['Signal'] = 0
prices_df['Position'] = 0

# Create buy/sell signals
for i in range(1, len(prices_df)):
    if prices_df['Short_MA'].iloc[i] > prices_df['Long_MA'].iloc[i] and \
            prices_df['Short_MA'].iloc[i-1] <= prices_df['Long_MA'].iloc[i-1]:  # Buy signal
        prices_df['Signal'].iloc[i] = 1  # +1 for buy signal
    elif prices_df['Short_MA'].iloc[i] < prices_df['Long_MA'].iloc[i] and \
            prices_df['Short_MA'].iloc[i-1] >= prices_df['Long_MA'].iloc[i-1]:  # Sell signal
        prices_df['Signal'].iloc[i] = -1  # -1 for sell signal

# Position tracking (1 for holding a position, 0 for not)
for i in range(1, len(prices_df)):
    # If there's a buy signal, hold the position (1)
    if prices_df['Signal'].iloc[i] == 1:
        prices_df['Position'].iloc[i] = 1
    # If there's a sell signal, exit the position (0)
    elif prices_df['Signal'].iloc[i] == -1:
        prices_df['Position'].iloc[i] = 0
    else:
        prices_df['Position'].iloc[i] = prices_df['Position'].iloc[i-1]

# Output the results
print(prices_df)

# Example logging trades
trade_history = []

for index, row in prices_df.iterrows():
    if row['Signal'] == 1:
        trade_history.append({'action': 'BUY', 'price': row['Price'], 'index': index})
    elif row['Signal'] == -1:
        trade_history.append({'action': 'SELL', 'price': row['Price'], 'index': index})

# Log trades
print("Trade History:")
for trade in trade_history:
    print(trade)