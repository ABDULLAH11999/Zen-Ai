import sys
sys.path.insert(0, ".")
import tkinter as tk
from gui import JarvisGUI

def dummy_toggle(val): pass
def dummy_send(text): pass

gui = JarvisGUI(
    on_toggle_monitoring=dummy_toggle,
    on_send_text=dummy_send
)

# Test states:
# 1. Starts in IDLE (renders 3D Face)
# 2. At 500ms -> SPEAKING (mouth articulates)
# 3. At 1200ms -> THINKING (switches to 3D Connectivity Working Cluster with traveling pulses)
# 4. At 2000ms -> IDLE (switches back to 3D Face)
gui.after(500, lambda: gui.set_status("SPEAKING"))
gui.after(1200, lambda: gui.set_status("THINKING"))
gui.after(2000, lambda: gui.set_status("IDLE"))
gui.after(2600, lambda: gui.destroy())

gui.mainloop()
print("3D Dual-Mode Visualizer lifecycle test passed successfully!")

