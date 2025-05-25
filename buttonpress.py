from gamepad import VirtualGamepad  # Assuming the class above is saved in gamepad.py
import time

gamepad = VirtualGamepad()

time.sleep(5.5)

gamepad.toggle_pause()

print(f"button press complete")