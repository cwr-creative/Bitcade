import time
import requests
import qrcode
import json
import threading
import keyboard
import pyautogui
import os
from bitcoinlib.keys import HDKey

# Configuration
XPUB_KEY = "vpub5VHC6VtRuxj8PFkaYsNHXx56tVZHqQiPoiPxGfzuGAj2HFH6eFeAqPT99FsR5Hn11vCGVDQyz6hXeMTGRnMuxnhPCeR1jHaAH3phymriHyp"
CREDIT_COST_USD = 0.50
EXCHANGE_RATE_API = "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd"
TIMEOUT_SECONDS = 200
CREDITS_FILE = "credits.json"
INSERT_BUTTON = "v"
MAME_COIN_BUTTON = "c"
SAVE_INTERVAL = 10  # seconds between saving credits.json

# Shared credits variable
credits_lock = threading.Lock()
credits = 0

def load_credits():
    global credits
    if os.path.exists(CREDITS_FILE):
        with open(CREDITS_FILE, "r") as f:
            data = json.load(f)
            credits = data.get("credits", 0)
    else:
        credits = 0

def save_credits():
    with credits_lock:
        with open(CREDITS_FILE, "w") as f:
            json.dump({"credits": credits}, f)

def periodic_saver():
    while True:
        save_credits()
        time.sleep(SAVE_INTERVAL)

# Payment processor code (intact, with small changes to integrate)
def derive_address_from_xpub(xpub):
    index = int(time.time())
    hdkey = HDKey(xpub)
    new_address = hdkey.child_public(index).address()
    print(f"Derived address (index {index}): {new_address}")
    return new_address

BTC_ADDRESS = derive_address_from_xpub(XPUB_KEY)

def get_btc_price():
    response = requests.get(EXCHANGE_RATE_API)
    data = response.json()
    return data["bitcoin"]["usd"]

def generate_payment_qr(amount_btc):
    payment_uri = f"bitcoin:{BTC_ADDRESS}?amount={amount_btc}"
    print(f"Payment URL: {payment_uri}")
    qr = qrcode.make(payment_uri)
    qr.show()

def check_for_payment(payment_address):
    MEMPOOL_API = f"https://mempool.space/testnet4/api/address/{payment_address}/txs/mempool"

    try:
        response = requests.get(MEMPOOL_API)
        print(f"Response status code: {response.status_code}")
        if response.status_code != 200:
            print("Error: Failed to retrieve transactions from mempool API")
            return None
        
        transactions = response.json()
        print(f"Raw API Response: {json.dumps(transactions, indent=2)}")

        for tx in transactions:
            for output in tx.get("vout", []):
                if "scriptpubkey_address" in output and output["scriptpubkey_address"] == payment_address:
                    btc_amount = output["value"]
                    print(f"✅ Payment detected! TxID: {tx['txid']}, Amount: {btc_amount} BTC")
                    return btc_amount

        print("No unconfirmed transactions found for this address.")
    except Exception as e:
        print(f"Error while checking mempool: {e}")
    
    return None

def payment_processor():
    global credits
    print("Arcade Machine is in Attract Mode. Press any key to purchase credits.")
    input("Press Enter to continue...")

    btc_price = get_btc_price()
    cost_per_credit_btc = CREDIT_COST_USD / btc_price
    num_credits = int(input("Enter the number of credits to purchase: "))
    total_btc = cost_per_credit_btc * num_credits

    print(f"Total cost in BTC: {total_btc:.8f}")
    print("Generating payment QR code...")
    generate_payment_qr(total_btc)

    print("Waiting for payment...")
    start_time = time.time()

    while time.time() - start_time < TIMEOUT_SECONDS:
        received_btc = check_for_payment(BTC_ADDRESS)
        if received_btc and received_btc >= total_btc:
            print(f"Payment received: {received_btc:.8f} BTC. Awarding {num_credits} credits!")
            with credits_lock:
                credits += num_credits
            save_credits()
            return
        time.sleep(2)

    print("Payment not detected. Returning to Attract Mode.")

# Key watcher code
def key_watcher():
    global credits
    print("Key watcher started, waiting for 'v' key...")

    while True:
        if keyboard.is_pressed(INSERT_BUTTON):
            with credits_lock:
                if credits > 0:
                    pyautogui.press(MAME_COIN_BUTTON)
                    credits -= 1
                    print(f"Inserted coin! Remaining credits: {credits}")
                    save_credits()
                    time.sleep(0.5)  # Debounce
                else:
                    print("No credits available!")
                    time.sleep(0.5)
        time.sleep(0.05)

def main():
    load_credits()

    # Start background threads
    saver_thread = threading.Thread(target=periodic_saver, daemon=True)
    key_thread = threading.Thread(target=key_watcher, daemon=True)
    saver_thread.start()
    key_thread.start()

    while True:
        payment_processor()

if __name__ == "__main__":
    main()
