import time
import requests
import qrcode
import json
from bitcoinlib.keys import HDKey

# Configuration
XPUB_KEY = "vpub5VHC6VtRuxj8PFkaYsNHXx56tVZHqQiPoiPxGfzuGAj2HFH6eFeAqPT99FsR5Hn11vCGVDQyz6hXeMTGRnMuxnhPCeR1jHaAH3phymriHyp"  # Public key to generate addresses
CREDIT_COST_USD = 0.50  # Cost of one credit in USD
EXCHANGE_RATE_API = "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd"
TIMEOUT_SECONDS = 200  # How long to wait for a payment before returning to attract mode

def derive_address_from_xpub(xpub):
    """Generate a unique Bitcoin address using the Unix timestamp as an index."""
    index = int(time.time())  # Current timestamp as index
    hdkey = HDKey(xpub)

    # Use .subkey(index) instead of .child(index)
    new_address = hdkey.child_public(index).address()
    
    print(f"Derived address (index {index}): {new_address}")
    return new_address

# Now that the function is defined, we can use it to set BTC_ADDRESS
BTC_ADDRESS = derive_address_from_xpub(XPUB_KEY)
MEMPOOL_API = f"https://mempool.space/testnet4/api/address/{BTC_ADDRESS}/txs"

# Function to get the current BTC/USD exchange rate
def get_btc_price():
    response = requests.get(EXCHANGE_RATE_API)
    data = response.json()
    return data["bitcoin"]["usd"]

# Function to generate a Bitcoin payment QR code
def generate_payment_qr(amount_btc):
    payment_uri = f"bitcoin:{BTC_ADDRESS}?amount={amount_btc}"
    print(f"Payment URL: {payment_uri}")  # Prints URL
    qr = qrcode.make(payment_uri)    # Generates QR Code
    qr.show()

# Function to check for unconfirmed transactions
def check_for_payment(payment_address):
    """Checks the mempool for an unconfirmed transaction to the given payment address."""
    MEMPOOL_API = f"https://mempool.space/testnet4/api/address/{payment_address}/txs/mempool"

    try:
        response = requests.get(MEMPOOL_API)
        print(f"Response status code: {response.status_code}")  # Debugging API response
        if response.status_code != 200:
            print("Error: Failed to retrieve transactions from mempool API")
            return None
        
        transactions = response.json()
        print(f"Raw API Response: {json.dumps(transactions, indent=2)}")  # Debugging

        for tx in transactions:
            for output in tx.get("vout", []):
                if "scriptpubkey_address" in output and output["scriptpubkey_address"] == payment_address:
                    btc_amount = output["value"]  # Removed Satoshi conversion
                    print(f"✅ Payment detected! TxID: {tx['txid']}, Amount: {btc_amount} BTC")
                    return btc_amount

        print("No unconfirmed transactions found for this address.")
    except Exception as e:
        print(f"Error while checking mempool: {e}")
    
    return None

# Main program loop
def main():
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
            return num_credits
        time.sleep(2)
    
    print("Payment not detected. Returning to Attract Mode.")
    return 0

if __name__ == "__main__":
    credits = main()
    print(f"Current Credits: {credits}")