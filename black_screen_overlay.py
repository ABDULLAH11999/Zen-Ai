import sys
import tkinter as tk

def main():
    try:
        root = tk.Tk()
        root.title("ZEN_BlackScreen")
        root.configure(bg="black")
        root.attributes("-fullscreen", True)
        root.attributes("-topmost", True)
        root.config(cursor="none")
        
        # Immediate close on any keyboard or mouse click on laptop
        def close_app(event=None):
            try:
                root.destroy()
            except Exception:
                sys.exit(0)
                
        root.bind("<Escape>", close_app)
        root.bind("<Key>", close_app)
        root.bind("<Button-1>", close_app)
        root.bind("<Button-2>", close_app)
        root.bind("<Button-3>", close_app)
        root.bind("<Motion>", lambda e: None)
        
        root.mainloop()
    except Exception:
        sys.exit(0)

if __name__ == "__main__":
    main()
