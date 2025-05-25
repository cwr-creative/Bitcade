import time
import subprocess
import requests
import qrcode
import json
import threading
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
SAVE_INTERVAL = 10  # seconds between saving credits.json

credits_lock = threading.RLock()
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

def periodic_saver():
    while True:
        save_credits()
        time.sleep(SAVE_INTERVAL)

# Launching Attract Mode and monitoring status
mame_is_running = False

def monitor_attract_stdout():
    global mame_is_running

    print("🧠 Starting Attract Mode monitor...")

    process = subprocess.Popen(
        ["attract"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True
    )

    for line in process.stdout:
        """print(f"[Attract] {line.strip()}")""" # Optional live log, commented out

        if "*** Running:" in line and "mame" in line:
            print("🎮 MAME launched")
            mame_is_running = True

        elif "exit_game" in line or "Returned from" in line:
            print("🏁 MAME exited")
            mame_is_running = False

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
from gamepad import VirtualGamepad  # Assuming the class above is saved in gamepad.py
from pynput import keyboard as pynput_keyboard
gamepad = VirtualGamepad()

def key_watcher():

    def on_press(key):
        global credits
        try:
            if key.char == INSERT_BUTTON:
                with credits_lock:
                    if credits > 0:
                        credits -= 1
                        current_credits = credits
                        gamepad.insert_coin()
                        save_credits()
                        print(f"Inserted coin! Remaining credits: {current_credits}")
                    else:
                        print("No credits. Launching payment processor...")
                        threading.Thread(target=payment_processor, daemon=True).start()
        except AttributeError:
            pass

    listener = pynput_keyboard.Listener(on_press=on_press)
    listener.start()

    while True:
        time.sleep(0.1)  # keep thread alive

def main():
    global credits
    load_credits()

    # Start Attract Mode and monitor
    threading.Thread(target=monitor_attract_stdout, daemon=True).start()
    
    # Start background saver + key watcher as daemons
    threading.Thread(target=periodic_saver, daemon=True).start()
    threading.Thread(target=key_watcher, daemon=True).start()

    # Main loop
    while True:
        with credits_lock:
            current_credits = credits

        time.sleep(1)

if __name__ == "__main__":
    main()
