import tkinter as tk
import time
from gui import JarvisGUI

def dummy_toggle(val):
    print("Toggle monitoring:", val)

def dummy_send(text):
    print("Send text:", text)

gui = JarvisGUI(
    on_toggle_monitoring=dummy_toggle,
    on_send_text=dummy_send
)

# Test appending logs
gui.append_log("System", "Integration test active.", tag="system")
gui.append_log("You", "set brightness to 25%", tag="user")
gui.add_chat_card("set brightness to 25%")
gui.update_last_chat_card("Sir, display brightness 25% par set kardi hai.")
gui.set_status("SPEAKING")

# Schedule auto-destroy after 1.5 seconds
gui.after(1500, lambda: gui.destroy())
gui.mainloop()
print("GUI integration test passed successfully!")

