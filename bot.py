import logging
import requests
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

# Token API dari BotFather
TOKEN = "YOUR_TELEGRAM_BOT_TOKEN"
# API DexScreener
DEXSCREENER_API = "https://api.dexscreener.com/latest/dex/tokens/"

# Setup logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# Command: /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Halo! Saya adalah Sniper Bot. Gunakan /help untuk melihat perintah yang tersedia.")

# Command: /help
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("""
    Perintah yang tersedia:
    /start - Mulai bot
    /help - Tampilkan bantuan
    /snipe <token_address> - Pantau harga token di DexScreener
    """)

# Command: /snipe
async def snipe(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        token_address = context.args[0]  # Ambil alamat token dari argumen
        url = f"{DEXSCREENER_API}{token_address}"
        response = requests.get(url)
        
        if response.status_code == 200:
            data = response.json()
            pair = data['pairs'][0]
            message = (
                f"🔍 Token: {pair['baseToken']['name']} ({pair['baseToken']['symbol']})\n"
                f"💰 Harga: ${pair['priceUsd']}\n"
                f"📈 Pair: {pair['pairAddress']}\n"
                f"🔄 Volume 24h: ${pair['volume']['h24']}\n"
                f"📊 Liquidity: ${pair['liquidity']['usd']}"
            )
            await update.message.reply_text(message)
        else:
            await update.message.reply_text("Gagal mengambil data dari DexScreener.")
    except IndexError:
        await update.message.reply_text("Gunakan format: /snipe <token_address>")
    except Exception as e:
        await update.message.reply_text(f"Terjadi error: {e}")

if __name__ == '__main__':
    # Buat aplikasi bot
    application = ApplicationBuilder().token(TOKEN).build()

    # Tambahkan handler untuk command
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("snipe", snipe))

    # Jalankan bot
    application.run_polling()
