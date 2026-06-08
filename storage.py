import json
import os

WATCHLIST_FILE = "watchlist.json"

def load_watchlist():
    if not os.path.exists(WATCHLIST_FILE):
        return {}
    with open(WATCHLIST_FILE, "r") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return {}

def save_watchlist(watchlist):
    with open(WATCHLIST_FILE, "w") as f:
        json.dump(watchlist, f, indent=4)

def add_stock(chat_id, symbol, target_type, target_value, direction='below', current_price=None):
    """
    target_type: 'price' or 'percent'
    target_value: float (e.g., 150.50 for price, or 5.0 for percent)
    direction: 'above' or 'below'
    """
    watchlist = load_watchlist()
    chat_id_str = str(chat_id)
    if chat_id_str not in watchlist:
        watchlist[chat_id_str] = {}
    
    watchlist[chat_id_str][symbol] = {
        "target_type": target_type,
        "target_value": target_value,
        "direction": direction,
        "baseline_price": current_price,
        "alerted": False
    }
    save_watchlist(watchlist)

def remove_stock(chat_id, symbol):
    watchlist = load_watchlist()
    chat_id_str = str(chat_id)
    if chat_id_str in watchlist and symbol in watchlist[chat_id_str]:
        del watchlist[chat_id_str][symbol]
        save_watchlist(watchlist)
        return True
    return False

def mark_alerted(chat_id, symbol):
    watchlist = load_watchlist()
    chat_id_str = str(chat_id)
    if chat_id_str in watchlist and symbol in watchlist[chat_id_str]:
        watchlist[chat_id_str][symbol]["alerted"] = True
        save_watchlist(watchlist)

def get_user_watchlist(chat_id):
    watchlist = load_watchlist()
    return watchlist.get(str(chat_id), {})

def get_all_watchlists():
    return load_watchlist()
