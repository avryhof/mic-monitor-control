#!/usr/bin/env python3
import tkinter as tk
from tkinter import ttk, messagebox
import subprocess
import shutil
import sys

# --------------------------
# Dependency check
# --------------------------
def check_dependencies():
    return shutil.which("pactl") is not None

def install_pavucontrol():
    sudo_tool = shutil.which("gksudo") or shutil.which("kdesudo")
    if not sudo_tool:
        messagebox.showerror("Error", "Neither gksudo nor kdesudo is installed.\nPlease install one and try again.")
        return
    subprocess.Popen([sudo_tool, "apt", "install", "-y", "pavucontrol"])

# --------------------------
# Audio functions
# --------------------------
# Get a list of (internal_name, friendly_name) for sinks/sources
def get_sinks():
    out = subprocess.check_output(["pactl", "list", "short", "sinks"], text=True)
    sinks = []
    for line in out.strip().split("\n"):
        if line:
            parts = line.split("\t")
            internal_name = parts[1]
            friendly_name = parts[1]  # fallback
            # Try to get Description for friendly display
            try:
                desc_out = subprocess.check_output(["pactl", "list", "sinks"], text=True)
                lines = desc_out.splitlines()
                for i, l in enumerate(lines):
                    if internal_name in l and l.strip().startswith("Name:"):
                        # look ahead for Description:
                        for j in range(i, min(i+10, len(lines))):
                            if "Description:" in lines[j]:
                                friendly_name = lines[j].split("Description:")[1].strip()
                                break
                        break
            except:
                pass
            sinks.append((internal_name, friendly_name))
    return sinks

def get_sources():
    out = subprocess.check_output(["pactl", "list", "short", "sources"], text=True)
    sources = []
    for line in out.strip().split("\n"):
        if line:
            parts = line.split("\t")
            internal_name = parts[1]
            friendly_name = parts[1]
            try:
                desc_out = subprocess.check_output(["pactl", "list", "sources"], text=True)
                lines = desc_out.splitlines()
                for i, l in enumerate(lines):
                    if internal_name in l and l.strip().startswith("Name:"):
                        for j in range(i, min(i+10, len(lines))):
                            if "Description:" in lines[j]:
                                friendly_name = lines[j].split("Description:")[1].strip()
                                break
                        break
            except:
                pass
            sources.append((internal_name, friendly_name))
    return sources

def start_loopback(source, sink):
    subprocess.call(["pactl", "load-module", "module-loopback", f"source={source}", f"sink={sink}"])

def stop_loopbacks():
    out = subprocess.check_output(["pactl", "list", "short", "modules"]).decode()
    for line in out.strip().split("\n"):
        if "module-loopback" in line:
            module_id = line.split("\t")[0]
            subprocess.call(["pactl", "unload-module", module_id])

def set_volume(target, percent, kind="sink"):
    subprocess.call(["pactl", f"set-{kind}-volume", target, f"{percent}%"])

def get_volume(target, kind="sink"):
    """Return volume (int 0-150) and mute state (bool)."""
    vol_out = subprocess.check_output(["pactl", f"get-{kind}-volume", target]).decode()
    mute_out = subprocess.check_output(["pactl", f"get-{kind}-mute", target]).decode()
    vol_percent = int(vol_out.split("/")[1].strip().replace("%", ""))
    is_muted = "yes" in mute_out.lower()
    return vol_percent, is_muted

def toggle_mute(target, kind="sink"):
    subprocess.call(["pactl", f"set-{kind}-mute", target, "toggle"])

# --------------------------
# GUI setup
# --------------------------
def launch_gui():
    root = tk.Tk()
    root.title("Mic Monitor Control")
    root.resizable(False, False)  # disables both horizontal and vertical resizing

    main_frame = tk.Frame(root, padx=15, pady=15)
    main_frame.pack()

    sources = get_sources()  # list of (internal_name, friendly_name)
    sinks = get_sinks()      # list of (internal_name, friendly_name)

    monitoring = {"state": False}

    def toggle_loopback(event=None):
        if not monitoring["state"]:
            stop_loopbacks()
            start_loopback(source_combo_internal(), sink_combo_internal())
            toggle_btn.config(text="Stop Monitoring")
            monitoring["state"] = True
        else:
            stop_loopbacks()
            toggle_btn.config(text="Start Monitoring")
            monitoring["state"] = False

    def sink_combo_internal():
        return sinks[sink_combo.current()][0]

    def source_combo_internal():
        return sources[source_combo.current()][0]

    # --- Output controls ---
    out_label_frame = tk.LabelFrame(main_frame, text="Output (Speakers)", padx=10, pady=10)
    out_label_frame.pack(fill="x", pady=5)

    tk.Label(out_label_frame, text="Output Device:").grid(row=0, column=0, sticky="w")
    sink_combo = ttk.Combobox(out_label_frame, values=[f[1] for f in sinks], width=30)
    sink_combo.current(0)
    sink_combo.grid(row=0, column=1, sticky="w", padx=5)

    out_slider = tk.Scale(out_label_frame, from_=0, to=150, orient="horizontal", length=300,
                          command=lambda v: set_volume(sink_combo_internal(), v, "sink"))
    out_slider.grid(row=1, column=0, columnspan=2, sticky="we", pady=5)

    out_mute_btn = tk.Button(out_label_frame, text="Mute Output",
                             command=lambda: toggle_mute(sink_combo_internal(), "sink"))
    out_mute_btn.grid(row=2, column=0, columnspan=2, pady=5)

    # --- Input controls ---
    in_label_frame = tk.LabelFrame(main_frame, text="Input (Microphone)", padx=10, pady=10)
    in_label_frame.pack(fill="x", pady=5)

    tk.Label(in_label_frame, text="Input Device:").grid(row=0, column=0, sticky="w")
    source_combo = ttk.Combobox(in_label_frame, values=[f[1] for f in sources], width=30)
    source_combo.current(0)
    source_combo.grid(row=0, column=1, sticky="w", padx=5)

    in_slider = tk.Scale(in_label_frame, from_=0, to=150, orient="horizontal", length=300,
                         command=lambda v: set_volume(source_combo_internal(), v, "source"))
    in_slider.grid(row=1, column=0, columnspan=2, sticky="we", pady=5)

    in_mute_btn = tk.Button(in_label_frame, text="Mute Mic",
                            command=lambda: toggle_mute(source_combo_internal(), "source"))
    in_mute_btn.grid(row=2, column=0, columnspan=2, pady=5)

    # --- Monitoring toggle ---
    toggle_btn = tk.Button(main_frame, text="Start Monitoring", command=toggle_loopback)
    toggle_btn.pack(pady=10)

    # --- Launch pavucontrol if available ---
    if shutil.which("pavucontrol"):
        tk.Button(main_frame, text="Open PulseAudio Volume Control",
                  command=lambda: subprocess.Popen(["pavucontrol"])).pack(pady=5)
    elif shutil.which("pavucontrol-qt"):
        tk.Button(main_frame, text="Open PulseAudio Volume Control",
                  command=lambda: subprocess.Popen(["pavucontrol-qt"])).pack(pady=5)

    # Refresh sliders/mute state
    def refresh_levels():
        try:
            out_vol, out_muted = get_volume(sink_combo_internal(), "sink")
            in_vol, in_muted = get_volume(source_combo_internal(), "source")

            out_slider.set(out_vol)
            in_slider.set(in_vol)

            out_mute_btn.config(text="Unmute Output" if out_muted else "Mute Output")
            in_mute_btn.config(text="Unmute Mic" if in_muted else "Mute Mic")
        except Exception:
            pass
        root.after(2000, refresh_levels)

    refresh_levels()
    root.mainloop()

# --------------------------
# Main
# --------------------------
if __name__ == "__main__":
    if not check_dependencies():
        root = tk.Tk()
        root.title("Missing Dependency")
        tk.Label(root, text="PulseAudio / PipeWire tools are missing.\nYou need 'pactl' installed.").pack(pady=10)
        tk.Button(root, text="Install pavucontrol", command=install_pavucontrol).pack(pady=5)
        tk.Button(root, text="Quit", command=root.quit).pack(pady=5)
        root.mainloop()
        sys.exit(1)
    else:
        launch_gui()
