import time
import subprocess
import requests
import qrcode
import json
import threading
import keyboard
from pynput.keyboard import Controller
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

credits_lock = threading.Lock()
credits = 0
keyboard_controller = Controller()

# Load/save credits
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

def send_coin():
    subprocess.run(["xdotool", "key", "c"])

def periodic_saver():
    while True:
        save_credits()
        time.sleep(SAVE_INTERVAL)

# Payment processor logic
def derive_address_from_xpub(xpub):
    index = int(time.time())
    hdkey = HDKey(xpub)
    new_address = hdkey.child_public(index).address()
    print(f"Derived address (index {index}): {new_address}")
    return new_address

def get_btc_price():
    response = requests.get(EXCHANGE_RATE_API)
    data = response.json()
    return data["bitcoin"]["usd"]

def generate_payment_qr(amount_btc, address):
    payment_uri = f"bitcoin:{address}?amount={amount_btc}"
    print(f"Payment URL: {payment_uri}")
    qr = qrcode.make(payment_uri)
    qr.show()

def payment_processor():
    global credits

    btc_address = derive_address_from_xpub(XPUB_KEY)

    btc_price = get_btc_price()
    cost_per_credit_btc = CREDIT_COST_USD / btc_price
    num_credits = int(input("Enter the number of credits to purchase: "))
    total_btc = cost_per_credit_btc * num_credits

    print(f"Total cost in BTC: {total_btc:.8f}")
    print("Generating payment QR code...")
    generate_payment_qr(total_btc, btc_address)

    # ----- Test mode block -----
    print("Test mode: Simulating payment received immediately!")
    time.sleep(2)
    with credits_lock:
        credits += num_credits
    save_credits()
    print(f"Payment received (test mode)! Awarding {num_credits} credits!")
    return
    # ---------------------------

    # Real mempool watch code is still here (commented for now)
    """
    start_time = time.time()
    MEMPOOL_API = f"https://mempool.space/testnet4/api/address/{btc_address}/txs/mempool"

    while time.time() - start_time < TIMEOUT_SECONDS:
        received_btc = check_for_payment(btc_address)
        if received_btc and received_btc >= total_btc:
            with credits_lock:
                credits += num_credits
            save_credits()
            return
        time.sleep(2)

    print("Payment not detected. Returning to Attract Mode.")
    """

# Key watcher daemon
def key_watcher():
    global credits
    print("Key watcher running.")

    while True:
        if keyboard.is_pressed(INSERT_BUTTON):
            # Check credits safely
            with credits_lock:
                if credits > 0:
                    credits -= 1
                    current_credits = credits  # copy value locally
                    should_insert_coin = True
                else:
                    should_insert_coin = False

            # Act outside the lock (this prevents blocking)
            if should_insert_coin:
                send_coin()
                save_credits()
                print(f"Inserted coin! Remaining credits: {current_credits}")
            else:
                print("No credits left! Insert payment.")
            
            time.sleep(0.5)

        time.sleep(0.05)

def main():
    global credits
    load_credits()

    # Start background saver + key watcher
    threading.Thread(target=periodic_saver, daemon=True).start()
    threading.Thread(target=key_watcher, daemon=True).start()

    # Main loop: wait for "v" when credits == 0
    while True:
        with credits_lock:
            current_credits = credits

        if current_credits == 0:
            print("No credits left. Waiting for player to press V to begin payment...")

            # Wait until V is pressed
            while not keyboard.is_pressed(INSERT_BUTTON):
                time.sleep(0.1)

            # Player pressed V → begin payment processor
            payment_processor()

        time.sleep(1)

if __name__ == "__main__":
    main()
