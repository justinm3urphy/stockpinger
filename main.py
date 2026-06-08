import os
import logging
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

import storage
import stock_api

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

load_dotenv()
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

CHECK_INTERVAL = 300  # 5 minutes in seconds

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a message when the command /start is issued."""
    welcome_message = (
        "Welcome to Stock Pinger Bot! 📈\n\n"
        "I can monitor stocks and alert you when they hit your targets.\n\n"
        "Commands:\n"
        "/add <symbol> <target_price> - Alert when stock drops below OR rises above price (automatically detected). (e.g. /add AAPL 150)\n"
        "/add_pct <symbol> <percent> - Alert when stock drops by percent (e.g. /add_pct TSLA 5)\n"
        "/add_pct_up <symbol> <percent> - Alert when stock rises by percent (e.g. /add_pct_up NVDA 10)\n"
        "/list - See your current watchlist\n"
        "/remove <symbol> - Remove a stock from watchlist\n"
    )
    await update.message.reply_text(welcome_message)

async def add_stock(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Add a stock with absolute target price."""
    chat_id = update.effective_chat.id
    args = context.args

    if len(args) != 2:
        await update.message.reply_text("Usage: /add <symbol> <target_price>\nExample: /add AAPL 150")
        return

    symbol = args[0].upper()
    try:
        target_price = float(args[1])
    except ValueError:
        await update.message.reply_text("Please provide a valid number for the target price.")
        return

    current_price = stock_api.get_stock_price(symbol)
    if current_price is None:
        await update.message.reply_text(f"Could not fetch data for '{symbol}'. Is the symbol correct?")
        return

    # Automatically detect if we should wait for it to drop or rise
    direction = 'above' if target_price >= current_price else 'below'
    
    storage.add_stock(chat_id, symbol, target_type='price', target_value=target_price, direction=direction)
    
    dir_text = "goes ABOVE or hits" if direction == 'above' else "drops BELOW or hits"
    msg = (f"✅ Added {symbol} to watchlist.\n"
           f"Current price: ${current_price:.2f}\n"
           f"Alert set for when price {dir_text}: ${target_price:.2f}")
    await update.message.reply_text(msg)

async def add_pct(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Add a stock with percentage drop target."""
    chat_id = update.effective_chat.id
    args = context.args

    if len(args) != 2:
        await update.message.reply_text("Usage: /add_pct <symbol> <percent_drop>\nExample: /add_pct TSLA 5")
        return

    symbol = args[0].upper()
    try:
        percent_drop = float(args[1])
        if percent_drop <= 0:
            raise ValueError
    except ValueError:
        await update.message.reply_text("Please provide a valid positive number for the percent drop.")
        return

    current_price = stock_api.get_stock_price(symbol)
    if current_price is None:
        await update.message.reply_text(f"Could not fetch data for '{symbol}'. Is the symbol correct?")
        return

    storage.add_stock(chat_id, symbol, target_type='percent', target_value=percent_drop, direction='below', current_price=current_price)
    
    target_price = current_price * (1 - (percent_drop / 100))
    msg = (f"✅ Added {symbol} to watchlist.\n"
           f"Current price: ${current_price:.2f}\n"
           f"Alert set for a {percent_drop}% DROP (<= ${target_price:.2f})")
    await update.message.reply_text(msg)

async def add_pct_up(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Add a stock with percentage rise target."""
    chat_id = update.effective_chat.id
    args = context.args

    if len(args) != 2:
        await update.message.reply_text("Usage: /add_pct_up <symbol> <percent_rise>\nExample: /add_pct_up NVDA 10")
        return

    symbol = args[0].upper()
    try:
        percent_rise = float(args[1])
        if percent_rise <= 0:
            raise ValueError
    except ValueError:
        await update.message.reply_text("Please provide a valid positive number for the percent rise.")
        return

    current_price = stock_api.get_stock_price(symbol)
    if current_price is None:
        await update.message.reply_text(f"Could not fetch data for '{symbol}'. Is the symbol correct?")
        return

    storage.add_stock(chat_id, symbol, target_type='percent', target_value=percent_rise, direction='above', current_price=current_price)
    
    target_price = current_price * (1 + (percent_rise / 100))
    msg = (f"✅ Added {symbol} to watchlist.\n"
           f"Current price: ${current_price:.2f}\n"
           f"Alert set for a {percent_rise}% RISE (>= ${target_price:.2f})")
    await update.message.reply_text(msg)

async def list_stocks(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """List watched stocks for the user."""
    chat_id = update.effective_chat.id
    watchlist = storage.get_user_watchlist(chat_id)
    
    if not watchlist:
        await update.message.reply_text("Your watchlist is currently empty.")
        return

    lines = ["📋 **Your Watchlist:**"]
    for symbol, data in watchlist.items():
        direction = data.get('direction', 'below') # default below for old entries
        dir_symbol = ">=" if direction == 'above' else "<="
        dir_text = "RISE" if direction == 'above' else "DROP"
        
        if data['target_type'] == 'price':
            lines.append(f"• {symbol}: Alert when {dir_symbol} ${data['target_value']:.2f}")
        elif data['target_type'] == 'percent':
            baseline = data['baseline_price']
            if direction == 'above':
                target = baseline * (1 + (data['target_value'] / 100))
            else:
                target = baseline * (1 - (data['target_value'] / 100))
            lines.append(f"• {symbol}: Alert on {data['target_value']}% {dir_text} (from ${baseline:.2f}, target: {dir_symbol} ${target:.2f})")
            
    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")

async def remove(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Remove a stock from the watchlist."""
    chat_id = update.effective_chat.id
    args = context.args

    if len(args) != 1:
        await update.message.reply_text("Usage: /remove <symbol>\nExample: /remove AAPL")
        return

    symbol = args[0].upper()
    success = storage.remove_stock(chat_id, symbol)
    
    if success:
        await update.message.reply_text(f"✅ Removed {symbol} from watchlist.")
    else:
        await update.message.reply_text(f"❌ {symbol} is not in your watchlist.")

async def check_prices(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Background job to check prices and send alerts."""
    all_watchlists = storage.get_all_watchlists()
    
    # We want to cache prices so we don't query the same stock multiple times if multiple users watch it
    price_cache = {}

    for chat_id_str, user_watchlist in all_watchlists.items():
        chat_id = int(chat_id_str)
        stocks_to_remove = []

        for symbol, data in user_watchlist.items():
            if symbol not in price_cache:
                price = stock_api.get_stock_price(symbol)
                price_cache[symbol] = price
            
            current_price = price_cache[symbol]
            if current_price is None:
                continue

            alert_triggered = False
            message = ""
            direction = data.get('direction', 'below')

            if data['target_type'] == 'price':
                if direction == 'below' and current_price <= data['target_value']:
                    alert_triggered = True
                    message = f"🚨 **ALERT: {symbol}** 🚨\nPrice dropped to **${current_price:.2f}** (Target was <= ${data['target_value']:.2f})"
                elif direction == 'above' and current_price >= data['target_value']:
                    alert_triggered = True
                    message = f"🚀 **ALERT: {symbol}** 🚀\nPrice rose to **${current_price:.2f}** (Target was >= ${data['target_value']:.2f})"
            elif data['target_type'] == 'percent':
                baseline = data['baseline_price']
                if direction == 'below':
                    target_price = baseline * (1 - (data['target_value'] / 100))
                    if current_price <= target_price:
                        alert_triggered = True
                        message = f"🚨 **ALERT: {symbol}** 🚨\nPrice dropped by **{data['target_value']}%** from ${baseline:.2f} to **${current_price:.2f}**!"
                elif direction == 'above':
                    target_price = baseline * (1 + (data['target_value'] / 100))
                    if current_price >= target_price:
                        alert_triggered = True
                        message = f"🚀 **ALERT: {symbol}** 🚀\nPrice rose by **{data['target_value']}%** from ${baseline:.2f} to **${current_price:.2f}**!"

            if alert_triggered:
                try:
                    await context.bot.send_message(chat_id=chat_id, text=message, parse_mode="Markdown")
                    # Remove from watchlist after alert to avoid spam
                    stocks_to_remove.append(symbol)
                except Exception as e:
                    logger.error(f"Failed to send message to {chat_id}: {e}")

        for symbol in stocks_to_remove:
            storage.remove_stock(chat_id, symbol)


def main() -> None:
    """Start the bot."""
    if not TOKEN:
        logger.error("No TELEGRAM_BOT_TOKEN provided in environment variables.")
        return

    application = Application.builder().token(TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("add", add_stock))
    application.add_handler(CommandHandler("add_pct", add_pct))
    application.add_handler(CommandHandler("add_pct_up", add_pct_up))
    application.add_handler(CommandHandler("list", list_stocks))
    application.add_handler(CommandHandler("remove", remove))

    # Job Queue for checking prices
    job_queue = application.job_queue
    job_queue.run_repeating(check_prices, interval=CHECK_INTERVAL, first=10) # start first check 10 seconds after boot

    logger.info("Bot is running...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
