"""OCR Macro MVP for ordinary screen text.

Requires on the target Windows machine: Pillow, pytesseract, pyautogui,
and the Tesseract OCR engine. The engine path can be selected in the GUI.
"""
from __future__ import annotations

import json
import os
import threading
import time
from datetime import datetime
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

try:
    from PIL import ImageGrab, ImageOps, ImageEnhance, ImageFilter
except ImportError:
    ImageGrab = None
try:
    import pytesseract
except ImportError:
    pytesseract = None
try:
    import pyautogui
except ImportError:
    pyautogui = None
try:
    import pyperclip
except ImportError:
    pyperclip = None

if pyautogui is not None:
    # Sicherheitsabstand zwischen einzelnen Aktionen.
    pyautogui.PAUSE = 0.15
    pyautogui.FAILSAFE = True

APP_TITLE = "OCR Macro - schlanker MVP"
DEFAULT_CONFIG = {
    "steps": [], "schedule_enabled": False,
    "schedule_time": "09:00", "interval_minutes": 0,
    "tesseract_path": ""
}
STEP_TYPES = ("Klick", "OCR kopieren", "OCR einfuegen", "Enter", "Timer")


class SelectionOverlay:
    def __init__(self, parent, mode, callback):
        self.parent, self.mode, self.callback = parent, mode, callback
        self.win = tk.Toplevel(parent)
        self.win.attributes("-fullscreen", True)
        self.win.attributes("-topmost", True)
        self.win.attributes("-alpha", 0.25)
        self.win.configure(bg="black")
        self.canvas = tk.Canvas(self.win, bg="black", cursor="crosshair", highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)
        self.start = None
        self.rect = None
        self.canvas.bind("<ButtonPress-1>", self.begin)
        self.canvas.bind("<B1-Motion>", self.drag)
        self.canvas.bind("<ButtonRelease-1>", self.finish)
        self.win.bind("<Escape>", lambda e: self.close())
        self.canvas.focus_set()

    def begin(self, event):
        self.start = (event.x, event.y)
        if self.rect:
            self.canvas.delete(self.rect)
        self.rect = self.canvas.create_rectangle(event.x, event.y, event.x, event.y, outline="#00ff99", width=3)

    def drag(self, event):
        if self.start and self.rect:
            self.canvas.coords(self.rect, self.start[0], self.start[1], event.x, event.y)

    def finish(self, event):
        if not self.start:
            return
        x1, y1 = self.start
        x2, y2 = event.x, event.y
        self.close()
        if self.mode == "region":
            x1, x2 = sorted((x1, x2)); y1, y2 = sorted((y1, y2))
            if x2 - x1 >= 3 and y2 - y1 >= 3:
                self.callback((x1, y1, x2, y2))
        else:
            self.callback((x2, y2))

    def close(self):
        if self.win.winfo_exists():
            self.win.destroy()


class OCRMacroApp:
    def __init__(self, root):
        self.root = root
        self.root.title(APP_TITLE)
        self.root.geometry("650x500")
        self.root.minsize(600, 440)
        self.config = dict(DEFAULT_CONFIG)
        self.steps = []
        self.selected_step = None
        self.running = False
        self.scheduler_thread = None
        self.last_run_date = None
        self.status = tk.StringVar(value="Bereit - bitte im Edit-Modus konfigurieren.")
        self.file_var = tk.StringVar(value="Keine Konfiguration geladen")
        self.ocr_var = tk.StringVar(value="Nicht festgelegt")
        self.target_var = tk.StringVar(value="Nicht festgelegt")
        self.delay_var = tk.StringVar(value="0.4")
        self.enter_var = tk.BooleanVar(value=False)
        self.schedule_var = tk.BooleanVar(value=False)
        self.time_var = tk.StringVar(value="09:00")
        self.tess_var = tk.StringVar(value="")
        self.build_ui()
        self.root.protocol("WM_DELETE_WINDOW", self.close)

    def build_ui(self):
        style = ttk.Style()
        try:
            style.theme_use("vista")
        except tk.TclError:
            pass
        top = ttk.Frame(self.root, padding=14); top.pack(fill="x")
        ttk.Label(top, text=APP_TITLE, font=("Segoe UI", 16, "bold")).pack(side="left")
        ttk.Label(top, text="EDIT", foreground="#146c43", font=("Segoe UI", 11, "bold")).pack(side="right")

        book = ttk.Notebook(self.root); book.pack(fill="both", expand=True, padx=12, pady=(0, 8))
        edit = ttk.Frame(book, padding=14); run = ttk.Frame(book, padding=14)
        book.add(edit, text="Edit-Modus"); book.add(run, text="Run-Modus")

        steps_box = ttk.LabelFrame(edit, text="Ablauf - maximal 10 Schritte", padding=10); steps_box.pack(fill="both", expand=True, pady=(0, 8))
        self.step_list = tk.Listbox(steps_box, height=8, activestyle="dotbox", exportselection=False)
        self.step_list.pack(side="left", fill="both", expand=True); self.step_list.bind("<<ListboxSelect>>", self.step_selected)
        controls = ttk.Frame(steps_box); controls.pack(side="left", fill="y", padx=(10, 0))
        ttk.Button(controls, text="+ Klick", command=lambda: self.add_step("Klick")).pack(fill="x", pady=2)
        ttk.Button(controls, text="+ OCR kopieren", command=lambda: self.add_step("OCR kopieren")).pack(fill="x", pady=2)
        ttk.Button(controls, text="+ OCR einfuegen", command=lambda: self.add_step("OCR einfuegen")).pack(fill="x", pady=2)
        ttk.Button(controls, text="+ Enter", command=lambda: self.add_step("Enter")).pack(fill="x", pady=2)
        ttk.Button(controls, text="+ Timer", command=lambda: self.add_step("Timer")).pack(fill="x", pady=2)
        ttk.Separator(controls).pack(fill="x", pady=6)
        ttk.Button(controls, text="Bearbeiten", command=self.edit_step).pack(fill="x", pady=2)
        ttk.Button(controls, text="Loeschen", command=self.delete_step).pack(fill="x", pady=2)
        ttk.Button(controls, text="Nach oben", command=lambda: self.move_step(-1)).pack(fill="x", pady=2)
        ttk.Button(controls, text="Nach unten", command=lambda: self.move_step(1)).pack(fill="x", pady=2)

        sched = ttk.LabelFrame(edit, text="Zeitplan", padding=8); sched.pack(fill="x", pady=(0, 8))
        ttk.Checkbutton(sched, text="Taeglich um", variable=self.schedule_var).grid(row=0, column=0, sticky="w")
        ttk.Entry(sched, textvariable=self.time_var, width=8).grid(row=0, column=1, padx=6)
        ttk.Label(sched, text="oder Intervall in Minuten (0 = aus):").grid(row=0, column=2, sticky="w")
        self.interval_var = tk.StringVar(value="0")
        ttk.Entry(sched, textvariable=self.interval_var, width=7).grid(row=0, column=3, padx=6)

        tess = ttk.LabelFrame(edit, text="OCR", padding=8); tess.pack(fill="x", pady=(0, 8))
        ttk.Label(tess, text="Tesseract-Pfad:").pack(side="left")
        ttk.Entry(tess, textvariable=self.tess_var).pack(side="left", fill="x", expand=True, padx=8)
        ttk.Button(tess, text="Auswaehlen", command=self.choose_tesseract).pack(side="right")

        actions = ttk.Frame(edit); actions.pack(fill="x", pady=8)
        ttk.Button(actions, text="Konfiguration speichern", command=self.save_config).pack(side="left")
        ttk.Button(actions, text="Konfiguration laden", command=self.load_config).pack(side="left", padx=8)

        ttk.Label(run, text="Bereit fuer die Ausfuehrung", font=("Segoe UI", 14, "bold")).pack(anchor="w", pady=(5, 12))
        ttk.Label(run, text="Der Ablauf liest gewoehnlichen Bildschirmtext per OCR und uebertraegt ihn in das markierte Zielfeld.", wraplength=550).pack(anchor="w")
        buttons = ttk.Frame(run); buttons.pack(fill="x", pady=25)
        ttk.Button(buttons, text="Einmal jetzt ausfuehren", command=self.run_once).pack(side="left")
        self.stop_button = ttk.Button(buttons, text="Run-Modus stoppen", command=self.stop, state="disabled")
        self.stop_button.pack(side="left", padx=8)
        ttk.Label(run, textvariable=self.file_var, foreground="#555").pack(anchor="w", pady=5)
        ttk.Label(run, text="Abbruch: Maus in die linke obere Bildschirmecke bewegen.", wraplength=550, foreground="#8a4b08").pack(anchor="w", pady=14)

        bottom = ttk.Frame(self.root, padding=(14, 4)); bottom.pack(fill="x")
        ttk.Separator(bottom).pack(fill="x", pady=(0, 6))
        ttk.Label(bottom, textvariable=self.status).pack(side="left")
        ttk.Button(bottom, text="Run-Zeitplan starten", command=self.start_scheduler).pack(side="right")

    def refresh_steps(self):
        self.step_list.delete(0, tk.END)
        for i, step in enumerate(self.steps, 1):
            detail = ""
            if step["type"] == "Klick": detail = " - Bereich/Punkt festgelegt" if step.get("target") else " - nicht konfiguriert"
            elif step["type"] == "OCR kopieren": detail = " - Bereich festgelegt" if step.get("region") else " - nicht konfiguriert"
            elif step["type"] == "Timer": detail = f" - {step.get('seconds', 1)} s"
            self.step_list.insert(tk.END, f"{i}. {step['type']}{detail}")

    def step_selected(self, event=None):
        sel = self.step_list.curselection(); self.selected_step = sel[0] if sel else None

    def add_step(self, kind):
        if len(self.steps) >= 10: messagebox.showwarning("Maximal 10 Schritte", "Bitte zuerst einen vorhandenen Schritt loeschen."); return
        step = {"type": kind}
        if kind == "Timer":
            step["seconds"] = 1.0
        self.steps.append(step); self.refresh_steps(); self.step_list.selection_set(len(self.steps)-1); self.step_selected()
        if kind in ("Klick", "OCR kopieren"): self.edit_step()

    def edit_step(self):
        if self.selected_step is None: messagebox.showinfo("Schritt auswaehlen", "Bitte zuerst einen Schritt auswaehlen."); return
        step = self.steps[self.selected_step]; kind = step["type"]
        if kind == "Klick":
            self.root.withdraw(); self.root.after(250, lambda: SelectionOverlay(self.root, "region", lambda v: self.set_step_value("target", v)))
        elif kind == "OCR kopieren":
            self.root.withdraw(); self.root.after(250, lambda: SelectionOverlay(self.root, "region", lambda v: self.set_step_value("region", v)))
        elif kind == "Timer":
            dialog = tk.Toplevel(self.root); dialog.title("Timer bearbeiten"); dialog.transient(self.root); dialog.grab_set()
            ttk.Label(dialog, text="Wartezeit in Sekunden:").pack(padx=15, pady=(15, 5)); var = tk.StringVar(value=str(step.get("seconds", 1)))
            ttk.Entry(dialog, textvariable=var, width=12).pack(padx=15, pady=5)
            def save():
                try: value = max(0.0, float(var.get().replace(",", ".")))
                except ValueError: messagebox.showerror("Eingabe pruefen", "Bitte eine Zahl eingeben.", parent=dialog); return
                step["seconds"] = value; dialog.destroy(); self.refresh_steps()
            ttk.Button(dialog, text="Speichern", command=save).pack(pady=12)

    def set_step_value(self, key, value):
        self.root.deiconify(); self.steps[self.selected_step][key] = value; self.refresh_steps(); self.step_list.selection_set(self.selected_step); self.status.set("Schritt gespeichert.")

    def delete_step(self):
        if self.selected_step is not None: self.steps.pop(self.selected_step); self.selected_step = None; self.refresh_steps()

    def move_step(self, direction):
        i = self.selected_step; j = i + direction if i is not None else -1
        if i is not None and 0 <= j < len(self.steps):
            self.steps[i], self.steps[j] = self.steps[j], self.steps[i]; self.selected_step = j; self.refresh_steps(); self.step_list.selection_set(j)

    def choose_tesseract(self):
        path = filedialog.askopenfilename(title="Tesseract auswaehlen", filetypes=[("Anwendung", "*.exe"), ("Alle Dateien", "*.*")])
        if path: self.tess_var.set(path); self.config["tesseract_path"] = path

    def collect_config(self):
        try: interval = max(0.0, float(self.interval_var.get().replace(",", ".")))
        except ValueError: raise ValueError("Das Intervall muss eine Zahl sein.")
        try: datetime.strptime(self.time_var.get(), "%H:%M")
        except ValueError: raise ValueError("Die Uhrzeit muss im Format HH:MM stehen.")
        self.config.update(steps=self.steps, schedule_enabled=self.schedule_var.get(), schedule_time=self.time_var.get(), interval_minutes=interval, tesseract_path=self.tess_var.get())
        return self.config

    def apply_config(self, data):
        self.config = dict(DEFAULT_CONFIG); self.config.update(data)
        self.steps = self.config.get("steps", [])[:10]
        self.schedule_var.set(self.config["schedule_enabled"]); self.time_var.set(self.config["schedule_time"]); self.interval_var.set(str(self.config.get("interval_minutes", 0))); self.tess_var.set(self.config["tesseract_path"])
        self.refresh_steps()

    def save_config(self):
        try: data = self.collect_config()
        except ValueError as e: messagebox.showerror("Eingabe pruefen", str(e)); return
        path = filedialog.asksaveasfilename(defaultextension=".json", filetypes=[("JSON-Konfiguration", "*.json")])
        if not path: return
        with open(path, "w", encoding="utf-8") as f: json.dump(data, f, indent=2)
        self.file_var.set(f"Gespeichert: {os.path.basename(path)}"); self.status.set("Konfiguration gespeichert.")

    def load_config(self):
        path = filedialog.askopenfilename(filetypes=[("JSON-Konfiguration", "*.json")])
        if not path: return
        try:
            with open(path, encoding="utf-8") as f: self.apply_config(json.load(f))
        except Exception as e: messagebox.showerror("Laden fehlgeschlagen", str(e)); return
        self.file_var.set(f"Geladen: {os.path.basename(path)}"); self.status.set("Konfiguration geladen.")

    def validate(self):
        self.collect_config()
        if not self.steps: raise ValueError("Bitte zuerst mindestens einen Schritt anlegen.")
        for number, step in enumerate(self.steps, 1):
            if step["type"] == "Klick" and not step.get("target"): raise ValueError(f"Schritt {number}: bitte Klickbereich markieren.")
            if step["type"] == "OCR kopieren" and not step.get("region"): raise ValueError(f"Schritt {number}: bitte OCR-Bereich markieren.")
        if ImageGrab is None or pytesseract is None or pyautogui is None or pyperclip is None:
            raise ValueError("Bitte zuerst pillow, pytesseract, pyautogui und pyperclip installieren.")

    def ocr_text(self, region):
        if self.config["tesseract_path"] and os.path.isfile(self.config["tesseract_path"]): pytesseract.pytesseract.tesseract_cmd = self.config["tesseract_path"]
        image = ImageGrab.grab(bbox=tuple(region)); image = ImageOps.grayscale(image)
        image = image.resize((image.width * 2, image.height * 2))
        image = ImageEnhance.Contrast(image).enhance(2.0).filter(ImageFilter.SHARPEN)
        return " ".join(pytesseract.image_to_string(image, config="--psm 7").strip().split())

    def execute_steps(self):
        clipboard_text = ""
        for number, step in enumerate(self.steps, 1):
            if not self.running: return
            kind = step["type"]
            if kind == "Klick":
                x1, y1, x2, y2 = map(int, step["target"]); x, y = (x1 + x2) // 2, (y1 + y2) // 2
                pyautogui.moveTo(x, y, duration=0.25); pyautogui.click(x, y)
            elif kind == "OCR kopieren":
                clipboard_text = self.ocr_text(step["region"])
                if not clipboard_text: raise RuntimeError(f"Schritt {number}: kein OCR-Text erkannt.")
                pyperclip.copy(clipboard_text)
            elif kind == "OCR einfuegen":
                pyautogui.hotkey("ctrl", "v")
            elif kind == "Enter":
                pyautogui.press("enter")
            elif kind == "Timer":
                time.sleep(float(step.get("seconds", 1)))
            self.root.after(0, lambda n=number: self.status.set(f"Schritt {n}/{len(self.steps)} ausgefuehrt."))
        self.root.after(0, lambda: self.status.set("Ablauf erfolgreich beendet."))

    def run_once(self):
        try: self.validate()
        except ValueError as e: messagebox.showerror("Konfiguration pruefen", str(e)); return
        if self.running: return
        self.running = True; self.stop_button.configure(state="normal"); self.status.set("OCR und Eingabe laufen ...")
        threading.Thread(target=self.worker, daemon=True).start()

    def worker(self):
        try:
            self.execute_steps()
        except Exception as e:
            self.root.after(0, lambda: self.status.set(f"Fehler: {e}"))
        finally:
            self.running = False; self.root.after(0, lambda: self.stop_button.configure(state="disabled"))

    def start_scheduler(self):
        try: self.validate()
        except ValueError as e: messagebox.showerror("Konfiguration pruefen", str(e)); return
        self.schedule_var.set(True); self.config["schedule_enabled"] = True
        if self.scheduler_thread and self.scheduler_thread.is_alive(): self.status.set("Zeitplan laeuft bereits."); return
        self.scheduler_thread = threading.Thread(target=self.scheduler, daemon=True); self.scheduler_thread.start()
        self.stop_button.configure(state="normal"); self.status.set(f"Tageszeitplan aktiv: taeglich um {self.time_var.get()} Uhr.")

    def scheduler(self):
        interval = float(self.config.get("interval_minutes", 0) or 0)
        next_interval = time.monotonic() + interval * 60 if interval > 0 else None
        while self.config.get("schedule_enabled"):
            now = datetime.now()
            daily_due = now.strftime("%H:%M") == self.config.get("schedule_time", "09:00") and self.last_run_date != now.date().isoformat()
            interval_due = next_interval is not None and time.monotonic() >= next_interval
            if (daily_due or interval_due) and not self.running:
                if daily_due: self.last_run_date = now.date().isoformat()
                if interval_due: next_interval = time.monotonic() + interval * 60
                self.run_once()
            time.sleep(1)

    def stop(self):
        self.config["schedule_enabled"] = False; self.schedule_var.set(False); self.running = False
        self.status.set("Gestoppt."); self.stop_button.configure(state="disabled")

    def close(self): self.config["schedule_enabled"] = False; self.root.destroy()


if __name__ == "__main__":
    root = tk.Tk(); OCRMacroApp(root); root.mainloop()
