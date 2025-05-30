import time
import subprocess
import requests
import qrcode
import json
import threading
from pynput.keyboard import Controller
import os
from bitcoinlib.keys import HDKey
from pathlib import Path

# Configuration
XPUB_KEY = "vpub5VHC6VtRuxj8PFkaYsNHXx56tVZHqQiPoiPxGfzuGAj2HFH6eFeAqPT99FsR5Hn11vCGVDQyz6hXeMTGRnMuxnhPCeR1jHaAH3phymriHyp"
CREDIT_COST_USD = 0.50
EXCHANGE_RATE_API = "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd"
PAYMENT_TIMEOUT = 200
root_dir = Path(__file__).resolve()
CREDITS_FILE = Path(__file__).resolve().parent / "credits.json"
INSERT_BUTTON = "v"
SAVE_INTERVAL = 10  # seconds between saving credits.json

credits_lock = threading.RLock()
credits = 0
keyboard_controller = Controller()

#UI and multiprocessing setup
from multiprocessing import Process, Queue
from bitcadeUI import run_overlay  # assuming correct import path

ui_queue = Queue()
ui_process = Process(target=run_overlay, args=(ui_queue,))
ui_process.start()

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
        ["attract", "--loglevel", "debug"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1
    )

    for line in process.stdout:
        """print(f"[Attract] {line.strip()}")""" # Optional live log, commented out

        if "*** Running:" in line and "mame" in line:
            print("🎮 MAME launched")
            mame_is_running = True

        elif "Created Attract-Mode Window" in line:
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
    start_time = time.time()
    while time.time() - start_time < PAYMENT_TIMEOUT:
        if num_credits > 0:
            time.sleep(2)
            print("Test mode: Simulating payment received immediately!")
            with credits_lock:
                credits += num_credits
                save_credits()
                print(f"Payment received (test mode)! Awarding {num_credits} credits!")
                focus_attract_or_mame()
                gamepad.toggle_pause()
            return
    print("Test mode: Payment not detected. Returning to Attract Mode.")

    # ---------------------------

    # Real mempool watch code is still here (commented for now)
    """
    start_time = time.time()
    MEMPOOL_API = f"https://mempool.space/testnet4/api/address/{btc_address}/txs/mempool"

    while time.time() - start_time < PAYMENT_TIMEOUT:
        received_btc = check_for_payment(btc_address)
        if received_btc and received_btc >= total_btc:
            with credits_lock:
                credits += num_credits
            save_credits()
            focus_attract_or_mame()
            return
        time.sleep(2)

    print("Payment not detected. Returning to Attract Mode.")
    focus_attract_or_mame()
    """
# Pausing MAME and switching window focus

def pause_mame():
    try:
        subprocess.run(["xdotool", "search", "--name", "MAME", "windowactivate", "--sync"])
        time.sleep(1)
        gamepad.toggle_pause()
        print("Cycled MAME pause")
    except Exception as e:
        print(f"[Error] Failed to pause MAME: {e}")

def get_terminal_window_id():
    # Grabs the active terminal window (assumes you're running in gnome-terminal or similar)
    result = subprocess.run(
        ["xdotool", "search", "--class", "gnome-terminal"],
        capture_output=True,
        text=True
    )
    window_ids = result.stdout.strip().split("\n")
    return window_ids[-1]  # Last match is usually the one you launched from

def focus_attract_or_mame():
    try:
        # Try MAME first
        mame_window = subprocess.run(
            ["xdotool", "search", "--name", "MAME"],
            capture_output=True, text=True
        )
        if mame_window.stdout.strip():
            subprocess.run(["xdotool", "windowactivate", mame_window.stdout.strip()])
            time.sleep(1)  # Give it a moment to focus
            print("🔁 Focus returned to MAME")
            return

        # Fallback to Attract Mode
        attract_window = subprocess.run(
            ["xdotool", "search", "--name", "Attract Mode"],
            capture_output=True, text=True
        )
        if attract_window.stdout.strip():
            subprocess.run(["xdotool", "windowactivate", attract_window.stdout.strip()])
            time.sleep(1)  # Give it a moment to focus
            print("🔁 Focus returned to Attract Mode")
    except Exception as e:
        print(f"[Error] Could not refocus frontend: {e}")

# Key watcher daemon
from gamepad import VirtualGamepad  # Saved in gamepad.py
from pynput import keyboard as pynput_keyboard
gamepad = VirtualGamepad()

def key_watcher():

    def on_press(key):
        global credits
        try:
            if key.char == INSERT_BUTTON:
                with credits_lock:
                    if mame_is_running:
                        if credits > 0:
                            credits -= 1
                            current_credits = credits
                            previous_credits = current_credits + 1
                            gamepad.insert_coin()
                            save_credits()
                            ui_queue.put(("show_credits", (previous_credits, current_credits)))
                            print(f"Inserted coin! Remaining credits: {current_credits}")
                        else:
                            print("No credits. Launching payment processor...")
                            gamepad.toggle_pause()  # Pause MAME
                            # Switch focus to terminal (or payment window)
                            try:
                                subprocess.run(["xdotool", "windowactivate", "--sync", str(get_terminal_window_id())])
                                print("🔄 Focused terminal for payment")
                            except Exception as e:
                                print(f"[Error] Could not focus terminal: {e}")
                            threading.Thread(target=payment_processor, daemon=True).start()
                    else:
                        print("MAME is not running. Cannot insert coin.")
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
