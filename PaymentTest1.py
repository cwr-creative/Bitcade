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
                keyboard_controller.press(MAME_COIN_BUTTON)
                keyboard_controller.release(MAME_COIN_BUTTON)
                save_credits()
                print(f"Inserted coin! Remaining credits: {current_credits}")
            else:
                print("No credits left! Insert payment.")
            
            time.sleep(0.5)

        time.sleep(0.05)
