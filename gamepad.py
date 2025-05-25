from evdev import UInput, ecodes as e, AbsInfo
import time

class VirtualGamepad:
    def __init__(self):
        capabilities = {
            e.EV_ABS: [
                (e.ABS_X, AbsInfo(value=0, min=0, max=255, fuzz=0, flat=0, resolution=0)),
                (e.ABS_Y, AbsInfo(value=0, min=0, max=255, fuzz=0, flat=0, resolution=0)),
            ],
            e.EV_KEY: [e.BTN_JOYSTICK, e.BTN_TRIGGER, e.BTN_THUMB],  # Trigger is coin, thumb is pause
        }

        self.ui = UInput(events=capabilities, name="Virtual Arcade Joystick", version=0x3)

    def insert_coin(self):
        self.ui.write(e.EV_KEY, e.BTN_TRIGGER, 1)
        self.ui.syn()
        time.sleep(0.05)
        self.ui.write(e.EV_KEY, e.BTN_TRIGGER, 0)   
        self.ui.syn()

    def toggle_pause(self):
        self.ui.write(e.EV_KEY, e.BTN_THUMB, 1)
        self.ui.syn()
        time.sleep(0.05)
        self.ui.write(e.EV_KEY, e.BTN_THUMB, 0)
        self.ui.syn()