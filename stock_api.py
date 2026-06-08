import requests

def get_stock_price(symbol: str) -> float:
    """
    Fetches the current or last available price of a stock symbol
    using Yahoo Finance's raw v8 chart API.
    Returns None if the symbol is invalid or data cannot be fetched.
    """
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            data = response.json()
            # Extract regular market price from the meta block
            price = data['chart']['result'][0]['meta']['regularMarketPrice']
            if price is not None and price > 0:
                return float(price)
        return None
    except Exception as e:
        print(f"Error fetching data for {symbol}: {e}")
        return None

def is_valid_symbol(symbol: str) -> bool:
    """
    Basic check to see if a symbol returns valid price data.
    """
    return get_stock_price(symbol) is not None
