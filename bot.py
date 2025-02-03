import os
import json
from solana.rpc.api import Client
from solders.keypair import Keypair
from solders.pubkey import Pubkey

# ✅ 1. Pastikan SOLANA_PRIVATE_KEY ada di environment
private_key = os.getenv("SOLANA_PRIVATE_KEY")

if not private_key:
    raise ValueError("❌ SOLANA_PRIVATE_KEY tidak terdeteksi. Pastikan sudah di-set di environment Render!")

# ✅ 2. Debugging: Cek format private key
print(f"✅ SOLANA_PRIVATE_KEY ditemukan, panjang: {len(private_key)} karakter")
print(f"🔍 5 karakter pertama: {private_key[:5]}...")  # Jangan print full private key demi keamanan

# ✅ 3. Konversi private key ke Keypair
try:
    if private_key.startswith("["):  # Jika private key berbentuk JSON array
        private_key_bytes = bytes(json.loads(private_key))
        wallet = Keypair.from_bytes(private_key_bytes)
    else:  # Jika private key berbentuk Base58, gunakan langsung
        wallet = Keypair.from_base58_string(private_key)

except Exception as e:
    raise ValueError(f"❌ Gagal memproses private key: {e}")

# ✅ 4. Inisialisasi koneksi ke Solana (Mainnet atau Devnet)
RPC_URL = "https://api.mainnet-beta.solana.com"  # Bisa diganti ke "https://api.devnet.solana.com" untuk testing
solana_client = Client(RPC_URL)

# ✅ 5. Cek balance wallet sebelum transaksi
try:
    balance = solana_client.get_balance(wallet.pubkey())["result"]["value"]
    print(f"💰 Wallet Balance: {balance / 1e9} SOL")
    
    if balance == 0:
        raise ValueError("❌ Wallet tidak memiliki saldo. Harap isi saldo terlebih dahulu.")
except Exception as e:
    raise ValueError(f"❌ Gagal mendapatkan balance wallet: {e}")

# ✅ 6. Lanjutkan dengan transaksi atau logika bot Anda...
print("✅ Bot siap dijalankan!")

