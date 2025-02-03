import os
import time
import re
import requests
from bs4 import BeautifulSoup
from solana.rpc.api import Client
from solana.rpc.types import TxOpts
from solana.keypair import Keypair
from solana.rpc.commitment import Confirmed

# Use 'solders' instead of 'solana.publickey'
from solders.pubkey import Pubkey
from solders.system_program import TransferParams
from solders.transaction import Transaction
from solders.message import Message
from solders.signature import Signature
from solders.rpc.responses import SendTransactionResp
import snscrape.modules.twitter as sntwitter
from textblob import TextBlob
import psycopg2
from psycopg2.extras import RealDictCursor

# Constants
SOLANA_RPC_URL = "https://api.mainnet-beta.solana.com"
DEXSCREENER_API_URL = "https://api.dexscreener.com/latest/dex/tokens"
SOLSNIFFER_URL = "https://solsniffer.com"
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
KOL_USERNAMES = ["CryptoNobler", "0xChiefy", "Danny_Crypton", "DefiWimar"]

# Initialize Solana client
client = Client(SOLANA_RPC_URL)

# Load wallet
private_key = os.getenv("SOLANA_PRIVATE_KEY")
if not private_key:
    raise ValueError("Please set the SOLANA_PRIVATE_KEY environment variable.")
wallet = Keypair.from_secret_key(bytes.fromhex(private_key))

# Database setup
def create_database():
    DATABASE_URL = os.getenv("DATABASE_URL")
    conn = psycopg2.connect(DATABASE_URL, sslmode='require')
    c = conn.cursor(cursor_factory=RealDictCursor)
    c.execute('''CREATE TABLE IF NOT EXISTS memecoins
                 (id SERIAL PRIMARY KEY, contract_address TEXT, symbol TEXT, price REAL, volume REAL, source TEXT)''')
    conn.commit()
    conn.close()

# Twitter functions
def get_tweets(username, limit=10):
    tweets = []
    for i, tweet in enumerate(sntwitter.TwitterSearchScraper(f'from:{username}').get_items()):
        if i >= limit:
            break
        tweets.append(tweet.content)
    return tweets

def extract_tickers(tweets):
    tickers = set()
    for tweet in tweets:
        words = tweet.split()
        for word in words:
            if word.startswith('$') and len(word) > 1:
                tickers.add(word[1:].upper())
    return list(tickers)

def extract_contract_addresses(tweets):
    contract_addresses = set()
    solana_address_pattern = re.compile(r'\b[1-9A-HJ-NP-Za-km-z]{32,44}\b')
    for tweet in tweets:
        matches = solana_address_pattern.findall(tweet)
        contract_addresses.update(matches)
    return list(contract_addresses)

# DexScreener functions
def get_token_data(contract_address):
    url = f"{DEXSCREENER_API_URL}/{contract_address}"
    response = requests.get(url)
    if response.status_code == 200:
        return response.json()["pairs"]
    else:
        print(f"Failed to fetch data for contract {contract_address}")
        return []

# SolSniffer functions
def get_contract_score(contract_address):
    url = f"{SOLSNIFFER_URL}/{contract_address}"
    response = requests.get(url)
    if response.status_code == 200:
        soup = BeautifulSoup(response.text, 'html.parser')
        score_element = soup.find("div", class_="score")
        if score_element:
            score = float(score_element.text.strip().replace("%", ""))
            return score
        else:
            print(f"Score element not found for contract {contract_address}")
            return None
    else:
        print(f"Failed to fetch data from SolSniffer for contract {contract_address}")
        return None

# Telegram notification
def send_telegram_notification(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message}
    response = requests.post(url, json=payload)
    if response.status_code == 200:
        print("Notification sent successfully")
    else:
        print(f"Failed to send notification: {response.text}")

# Buy and sell functions
def buy_token(token_address, amount_sol=0.01, slippage=15):
    try:
        token_pubkey = Pubkey.from_string(token_address)
        sol_pubkey = Pubkey.from_string(str(wallet.public_key()))
        transfer_ix = transfer(SoldersTransferParams(
            from_pubkey=sol_pubkey,
            to_pubkey=token_pubkey,
            lamports=int(amount_sol * 1e9 * (1 - slippage / 100))  # Adjust for slippage
        ))
        txn = SoldersTransaction().add(transfer_ix)
        txn.sign(wallet)
        response = client.send_transaction(txn, opts=TxOpts(skip_preflight=False, preflight_commitment=Confirmed))
        if response['result']:
            print(f"Buy transaction successful: {response['result']}")
            return True
        else:
            print(f"Buy transaction failed: {response}")
            return False
    except Exception as e:
        print(f"Error in buy_token: {e}")
        return False

def sell_token(token_address, profit_target=0.02, moonbag_percent=20):
    try:
        token_balance = client.get_token_account_balance(token_address)
        if not token_balance['result']:
            print("Failed to fetch token balance")
            return False
        balance = token_balance['result']['value']['amount']
        sell_amount = int(balance * (1 - moonbag_percent / 100))
        sell_ix = transfer(SoldersTransferParams(
            from_pubkey=Pubkey.from_string(token_address),
            to_pubkey=Pubkey.from_string(str(wallet.public_key())),
            lamports=sell_amount
        ))
        txn = SoldersTransaction().add(sell_ix)
        txn.sign(wallet)
        response = client.send_transaction(txn, opts=TxOpts(skip_preflight=False, preflight_commitment=Confirmed))
        if response['result']:
            print(f"Sell transaction successful: {response['result']}")
            return True
        else:
            print(f"Sell transaction failed: {response}")
            return False
    except Exception as e:
        print(f"Error in sell_token: {e}")
        return False

# Main bot logic
def main():
    create_database()
    while True:
        all_contract_addresses = []
        for username in KOL_USERNAMES:
            tweets = get_tweets(username)
            contract_addresses = extract_contract_addresses(tweets)
            all_contract_addresses.extend(contract_addresses)

        for address in all_contract_addresses:
            score = get_contract_score(address)
            if score is not None and score < 85:
                send_telegram_notification(f"⚠️ Contract {address} has a low score: {score}%")

            token_data = get_token_data(address)
            for pair in token_data:
                symbol = pair['baseToken']['symbol']
                price = float(pair['priceUsd'])
                volume = float(pair['volume']['h24'])
                print(f"Token: {symbol}, Price: {price}, Volume: {volume}")

            # Buy and sell logic
            if buy_token(address):
                time.sleep(10)  # Wait for buy to complete
                sell_token(address)

        time.sleep(3600)  # Run every hour

if __name__ == "__main__":
    main()
