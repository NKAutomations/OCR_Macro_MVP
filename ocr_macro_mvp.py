"""OCR Macro MVP for ordinary screen text.

Requires on the target Windows machine: Pillow, pytesseract, pyautogui,
and the Tesseract OCR engine. The engine path can be selected in the GUI.
"""
from __future__ import annotations

import json
import os
import threading
import time
import ctypes
import webbrowser
from datetime import datetime, timedelta
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

APP_TITLE = "OCR Macro MVP Designer"
APP_VERSION = "1.0.1"
DEVELOPER = "Niclas Kersting"
REPOSITORY_URL = "https://github.com/NKAutomations/OCR_Macro_MVP"
LATEST_RELEASE_URL = f"{REPOSITORY_URL}/releases/latest"
SETTINGS_DIR = os.path.join(os.environ.get("APPDATA", os.path.expanduser("~")), "OCRMacro")
SETTINGS_FILE = os.path.join(SETTINGS_DIR, "settings.json")
DEFAULT_LOG_PATH = os.path.join(SETTINGS_DIR, "ocr_macro.log")
DEFAULT_CONFIG = {
    "steps": [], "schedule_enabled": False,
    "schedule_mode": "off", "schedule_time": "09:00", "interval_minutes": 0,
    "tesseract_path": "", "last_config_path": "", "start_delay": 0.0, "minimize_on_start": False,
    "step_delay": 0.6
}
STEP_TYPES = ("Klick", "OCR kopieren", "OCR einfuegen", "Text einfuegen", "Tab-Taste", "Tastenkombination", "Text löschen", "Kommentar/Notiz", "Enter", "Timer")


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
        self.win.bind("<Escape>", lambda e: self.cancel())
        self.canvas.bind("<Escape>", lambda e: self.cancel())
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
                self.parent.deiconify()
        else:
            self.callback((x2, y2))

    def close(self):
        if self.win.winfo_exists():
            self.win.destroy()

    def cancel(self):
        self.close()
        self.parent.deiconify()


class OCRMacroApp:
    def __init__(self, root):
        self.root = root
        self.root.title(APP_TITLE)
        screen_height = self.root.winfo_screenheight()
        initial_height = min(800, max(650, screen_height - 70))
        self.root.geometry(f"1000x{initial_height}")
        self.root.minsize(900, min(650, max(560, screen_height - 70)))
        self.config = dict(DEFAULT_CONFIG)
        self.steps = []
        self.selected_step = None
        self.running = False
        self.scheduler_thread = None
        self.scheduler_next_run = None
        self.schedule_mode_var = tk.StringVar(value="off")
        self.status = tk.StringVar(value="Bereit - bitte im Edit-Modus konfigurieren.")
        self.next_run_var = tk.StringVar(value="Nächster Zeitplan: keiner")
        self.file_var = tk.StringVar(value="Keine Konfiguration geladen")
        self.ocr_var = tk.StringVar(value="Nicht festgelegt")
        self.target_var = tk.StringVar(value="Nicht festgelegt")
        self.delay_var = tk.StringVar(value="0.4")
        self.start_delay_var = tk.StringVar(value="0")
        self.step_delay_var = tk.StringVar(value="0.6")
        self.minimize_var = tk.BooleanVar(value=False)
        self.enter_var = tk.BooleanVar(value=False)
        self.time_var = tk.StringVar(value="09:00")
        self.tess_var = tk.StringVar(value="")
        self.log_var = tk.StringVar(value=DEFAULT_LOG_PATH)
        self.log_lock = threading.Lock()
        self.load_settings()
        self.log_event("Programmstart")
        self.build_ui()
        self.root.protocol("WM_DELETE_WINDOW", self.close)
        self.load_last_config()
        self.hotkey_running = True
        self.root.bind_all("<Control-Alt-Key-q>", lambda event: self.stop(from_hotkey=True))
        if os.name == "nt":
            threading.Thread(target=self.hotkey_listener, daemon=True).start()

    def build_ui(self):
        style = ttk.Style()
        try:
            style.theme_use("vista")
        except tk.TclError:
            pass
        style.configure("ScheduleActive.TButton", foreground="white", background="#198754")
        style.configure("ScheduleOff.TButton", foreground="white", background="#b02a37")
        top = ttk.Frame(self.root, padding=14); top.pack(fill="x")
        ttk.Label(top, text=APP_TITLE, font=("Segoe UI", 16, "bold")).pack(side="left")
        info = ttk.Frame(top); info.pack(side="right")
        ttk.Label(info, text=f"Version {APP_VERSION}  ·  Entwickler: {DEVELOPER}", foreground="#555").pack(side="left", padx=(0, 12))
        repo_link = tk.Label(info, text="GitHub · aktuelles Release", foreground="#0969da", cursor="hand2")
        repo_link.pack(side="left")
        repo_link.bind("<Button-1>", lambda event: webbrowser.open(LATEST_RELEASE_URL))

        book = ttk.Notebook(self.root); book.pack(fill="both", expand=True, padx=12, pady=(0, 8))
        edit = ttk.Frame(book, padding=14); run = ttk.Frame(book, padding=14); settings = ttk.Frame(book, padding=14)
        book.add(edit, text="Edit-Modus"); book.add(run, text="Run-Modus"); book.add(settings, text="Einstellungen")

        steps_box = ttk.LabelFrame(edit, text="Ablauf - keine feste Schrittgrenze (empfohlen: bis 1000)", padding=10); steps_box.pack(fill="both", expand=True, pady=(0, 8))
        list_area = ttk.Frame(steps_box); list_area.pack(side="left", fill="both", expand=True)
        self.step_list = tk.Listbox(
            list_area,
            height=16,
            activestyle="dotbox",
            exportselection=False,
            selectbackground="#cfe8ff",
            selectforeground="#000000",
        )
        step_scroll = ttk.Scrollbar(list_area, orient="vertical", command=self.step_list.yview)
        self.step_list.configure(yscrollcommand=step_scroll.set)
        self.step_list.pack(side="left", fill="both", expand=True); step_scroll.pack(side="right", fill="y")
        self.step_list.bind("<<ListboxSelect>>", self.step_selected)
        self.step_list.bind("<Double-Button-1>", lambda e: self.edit_step())
        controls = ttk.Frame(steps_box); controls.pack(side="left", fill="y", padx=(10, 0))
        control_specs = (
            ("+ Klick", "Klick"), ("+ OCR kopieren", "OCR kopieren"),
            ("+ OCR einfuegen", "OCR einfuegen"), ("+ Text einfuegen", "Text einfuegen"),
            ("+ Tab-Taste", "Tab-Taste"), ("+ Tastenkombination", "Tastenkombination"),
            ("+ Text löschen", "Text löschen"), ("+ Kommentar/Notiz", "Kommentar/Notiz"),
            ("+ Enter", "Enter"), ("+ Timer", "Timer"),
        )
        for index, (label, kind) in enumerate(control_specs):
            ttk.Button(controls, text=label, command=lambda step_kind=kind: self.add_step(step_kind)).grid(
                row=index // 2, column=index % 2, sticky="ew", padx=2, pady=2
            )
        controls.columnconfigure(0, weight=1); controls.columnconfigure(1, weight=1)
        action_row = len(control_specs) // 2 + 1
        ttk.Separator(controls).grid(row=action_row - 1, column=0, columnspan=2, sticky="ew", pady=6)
        self.edit_button = ttk.Button(controls, text="Bearbeiten", command=self.edit_step)
        self.edit_button.grid(row=action_row, column=0, columnspan=2, sticky="ew", padx=2, pady=2)
        ttk.Button(controls, text="Loeschen", command=self.delete_step).grid(row=action_row + 1, column=0, columnspan=2, sticky="ew", padx=2, pady=2)
        ttk.Button(controls, text="Nach oben", command=lambda: self.move_step(-1)).grid(row=action_row + 2, column=0, sticky="ew", padx=2, pady=2)
        ttk.Button(controls, text="Nach unten", command=lambda: self.move_step(1)).grid(row=action_row + 2, column=1, sticky="ew", padx=2, pady=2)

        sched = ttk.LabelFrame(edit, text="Zeitplan", padding=8); sched.pack(fill="x", pady=(0, 8))
        ttk.Radiobutton(sched, text="Deaktiviert", variable=self.schedule_mode_var, value="off").grid(row=0, column=0, sticky="w")
        ttk.Radiobutton(sched, text="Täglich um", variable=self.schedule_mode_var, value="daily").grid(row=0, column=1, sticky="w", padx=(12, 0))
        ttk.Entry(sched, textvariable=self.time_var, width=8).grid(row=0, column=2, padx=6)
        ttk.Radiobutton(sched, text="Intervall", variable=self.schedule_mode_var, value="interval").grid(row=0, column=3, sticky="w", padx=(12, 0))
        self.interval_var = tk.StringVar(value="0")
        ttk.Spinbox(sched, from_=0.1, to=100000, increment=1, textvariable=self.interval_var, width=9).grid(row=0, column=4, padx=6)
        ttk.Label(sched, text="Minuten").grid(row=0, column=5, sticky="w")
        ttk.Label(sched, text="Beim Start wird genau der ausgewählte Modus verwendet.", foreground="#555").grid(row=1, column=0, columnspan=6, sticky="w", pady=(7, 0))

        actions = ttk.Frame(edit); actions.pack(fill="x", pady=8)
        ttk.Button(actions, text="Konfiguration speichern", command=self.save_config).pack(side="left")
        ttk.Button(actions, text="Konfiguration laden", command=self.load_config).pack(side="left", padx=8)

        ttk.Label(run, text="Bereit fuer die Ausfuehrung", font=("Segoe UI", 14, "bold")).pack(anchor="w", pady=(5, 12))
        ttk.Label(run, text="Der Ablauf liest gewoehnlichen Bildschirmtext per OCR und uebertraegt ihn in das markierte Zielfeld.", wraplength=550).pack(anchor="w")
        run_options = ttk.LabelFrame(run, text="Startoptionen", padding=12); run_options.pack(fill="x", pady=20)
        ttk.Label(run_options, text="Startverzögerung (Sekunden):").grid(row=0, column=0, sticky="w")
        ttk.Spinbox(run_options, from_=0, to=3600, increment=0.5, textvariable=self.start_delay_var, width=10).grid(row=0, column=1, padx=8, sticky="w")
        ttk.Label(run_options, text="Mindestpause zwischen Schritten (Sekunden):").grid(row=1, column=0, sticky="w", pady=(10, 0))
        ttk.Spinbox(run_options, from_=0, to=60, increment=0.1, textvariable=self.step_delay_var, width=10).grid(row=1, column=1, padx=8, sticky="w", pady=(10, 0))
        ttk.Checkbutton(run_options, text="Designer-Fenster beim Start minimieren", variable=self.minimize_var).grid(row=2, column=0, columnspan=2, sticky="w", pady=(10, 0))
        ttk.Label(run_options, text="Die Mindestpause wird automatisch zwischen den Schritten eingefügt und nicht als Schritt angezeigt.", foreground="#555", wraplength=700).grid(row=3, column=0, columnspan=2, sticky="w", pady=(8, 0))
        buttons = ttk.Frame(run); buttons.pack(fill="x", pady=8)
        ttk.Button(buttons, text="Einmal jetzt ausfuehren", command=self.run_once).pack(side="left")
        self.stop_button = ttk.Button(buttons, text="Aktuellen Ablauf stoppen", command=lambda: self.stop_run(show_popup=True), state="disabled")
        self.stop_button.pack(side="left", padx=8)
        ttk.Label(run, textvariable=self.file_var, foreground="#555").pack(anchor="w", pady=5)
        ttk.Label(run, text="Sofortiger Abbruch: Strg+Alt+Q drücken.", wraplength=550, foreground="#8a4b08").pack(anchor="w", pady=14)

        ttk.Label(settings, text="Einstellungen", font=("Segoe UI", 14, "bold")).pack(anchor="w", pady=(5, 15))
        tess = ttk.LabelFrame(settings, text="OCR / Tesseract", padding=12); tess.pack(fill="x", anchor="n")
        ttk.Label(tess, text="Pfad zu tesseract.exe:").grid(row=0, column=0, sticky="w")
        ttk.Entry(tess, textvariable=self.tess_var).grid(row=1, column=0, sticky="ew", pady=(8, 0))
        ttk.Button(tess, text="Auswählen", command=self.choose_tesseract).grid(row=1, column=1, padx=(8, 0), pady=(8, 0))
        tess.columnconfigure(0, weight=1)
        log_box = ttk.LabelFrame(settings, text="Protokoll / Logdatei", padding=12); log_box.pack(fill="x", anchor="n", pady=(12, 0))
        ttk.Label(log_box, text="Pfad zur Logdatei:").grid(row=0, column=0, sticky="w")
        ttk.Entry(log_box, textvariable=self.log_var).grid(row=1, column=0, sticky="ew", pady=(8, 0))
        ttk.Button(log_box, text="Auswählen", command=self.choose_log_file).grid(row=1, column=1, padx=(8, 0), pady=(8, 0))
        log_box.columnconfigure(0, weight=1)
        ttk.Label(log_box, text="Alle Ausführungen, Schritte, Fehler und erkannten OCR-Texte werden mit Zeitstempel protokolliert.", foreground="#555", wraplength=700).grid(row=2, column=0, columnspan=2, sticky="w", pady=(8, 0))
        ttk.Button(settings, text="Einstellungen speichern", command=self.save_settings).pack(anchor="w", pady=12)
        ttk.Label(settings, text=f"Gespeichert unter: {SETTINGS_FILE}", foreground="#555", wraplength=700).pack(anchor="w")

        bottom = ttk.Frame(self.root, padding=(14, 4)); bottom.pack(fill="x")
        ttk.Separator(bottom).pack(fill="x", pady=(0, 6))
        ttk.Label(bottom, textvariable=self.status).pack(side="left")
        ttk.Label(bottom, textvariable=self.next_run_var, foreground="#555").pack(side="left", padx=20)
        self.schedule_button = tk.Button(bottom, text="Run-Zeitplan starten", command=self.toggle_scheduler, bg="#b02a37", fg="white", activebackground="#842029", activeforeground="white", relief="raised", padx=8, pady=3)
        self.schedule_button.pack(side="right")

    def refresh_steps(self):
        self.step_list.delete(0, tk.END)
        for i, step in enumerate(self.steps, 1):
            detail = ""
            if step["type"] == "Klick": detail = " - Bereich/Punkt festgelegt" if step.get("target") else " - nicht konfiguriert"
            elif step["type"] == "OCR kopieren": detail = " - Bereich festgelegt" if step.get("region") else " - nicht konfiguriert"
            elif step["type"] == "Text einfuegen":
                text = " ".join(str(step.get("text", "")).split())
                detail = f" - \"{text[:45]}{'...' if len(text) > 45 else ''}\"" if text else " - nicht konfiguriert"
            elif step["type"] == "Tastenkombination": detail = f" - {step.get('keys', '')}" if step.get("keys") else " - nicht konfiguriert"
            elif step["type"] == "Kommentar/Notiz":
                note = " ".join(str(step.get("text", "")).split())
                detail = f" - {note[:45]}{'...' if len(note) > 45 else ''}" if note else " - leer"
            elif step["type"] == "Timer": detail = f" - {step.get('seconds', 1)} s"
            self.step_list.insert(tk.END, f"{i}. {step['type']}{detail}")
            if step["type"] == "Kommentar/Notiz":
                self.step_list.itemconfig(tk.END, background="#fff3b0", foreground="#5f4b00")

    def step_selected(self, event=None):
        sel = self.step_list.curselection(); self.selected_step = sel[0] if sel else None
        if hasattr(self, "edit_button"):
            is_note = self.selected_step is not None and self.steps[self.selected_step]["type"] == "Kommentar/Notiz"
            self.edit_button.configure(state="disabled" if is_note else "normal")

    def add_step(self, kind):
        step = {"type": kind}
        if kind == "Timer":
            step["seconds"] = 1.0
        elif kind == "Text einfuegen":
            step["text"] = ""
        elif kind in ("Tastenkombination", "Kommentar/Notiz"):
            step["keys" if kind == "Tastenkombination" else "text"] = ""
        self.steps.append(step); self.refresh_steps(); self.step_list.selection_set(len(self.steps)-1); self.step_selected()
        if kind in ("Klick", "OCR kopieren", "Text einfuegen", "Tastenkombination"): self.edit_step()
        elif kind == "Kommentar/Notiz":
            self.edit_text_step(step, "Kommentar/Notiz anlegen", "Notiz (nach dem Speichern schreibgeschützt):", allow_empty=True)

    def edit_step(self):
        if self.selected_step is None: messagebox.showinfo("Schritt auswaehlen", "Bitte zuerst einen Schritt auswaehlen."); return
        step = self.steps[self.selected_step]; kind = step["type"]
        if kind == "Kommentar/Notiz":
            messagebox.showinfo("Notiz schreibgeschützt", "Notizen sind nach dem Anlegen schreibgeschützt.", parent=self.root)
            return
        if kind == "Klick":
            self.root.withdraw(); self.root.after(250, lambda: SelectionOverlay(self.root, "region", lambda v: self.set_step_value("target", v)))
        elif kind == "OCR kopieren":
            self.root.withdraw(); self.root.after(250, lambda: SelectionOverlay(self.root, "region", lambda v: self.set_step_value("region", v)))
        elif kind in ("Text einfuegen", "Kommentar/Notiz"):
            title = "Text bearbeiten" if kind == "Text einfuegen" else "Kommentar/Notiz bearbeiten"
            description = "Text, der beim Ausführen eingefügt werden soll:" if kind == "Text einfuegen" else "Notiz (wird nicht ausgeführt):"
            self.edit_text_step(step, title, description, allow_empty=kind == "Kommentar/Notiz")
        elif kind == "Tastenkombination":
            dialog = tk.Toplevel(self.root); dialog.title("Tastenkombination bearbeiten"); dialog.transient(self.root); dialog.grab_set(); dialog.resizable(False, False)
            frame = ttk.Frame(dialog, padding=16); frame.pack()
            ttk.Label(frame, text="Tasten mit + trennen, z. B. ctrl+shift+s:").pack(anchor="w")
            var = tk.StringVar(value=str(step.get("keys", "")))
            entry = ttk.Entry(frame, textvariable=var, width=30); entry.pack(pady=(8, 12)); entry.focus_set()
            def save_hotkey():
                keys = "+".join(part.strip().lower() for part in var.get().split("+") if part.strip())
                if not keys:
                    messagebox.showerror("Eingabe prüfen", "Bitte eine Tastenkombination eingeben.", parent=dialog); return
                step["keys"] = keys; dialog.destroy(); self.refresh_steps(); self.step_list.selection_set(self.selected_step)
            ttk.Button(frame, text="Speichern", command=save_hotkey).pack(anchor="e")
            dialog.bind("<Return>", lambda e: save_hotkey())
            self.position_dialog(dialog)
        elif kind == "Timer":
            dialog = tk.Toplevel(self.root); dialog.title("Timer bearbeiten"); dialog.transient(self.root); dialog.grab_set()
            dialog.resizable(False, False)
            frame = ttk.Frame(dialog, padding=16); frame.pack()
            ttk.Label(frame, text="Wartezeit in Sekunden:").grid(row=0, column=0, sticky="w")
            var = tk.StringVar(value=str(step.get("seconds", 1)))
            entry = ttk.Spinbox(frame, from_=0, to=86400, increment=0.1, textvariable=var, width=14)
            entry.grid(row=1, column=0, sticky="ew", pady=(8, 12)); entry.focus_set(); entry.selection_range(0, tk.END)
            def save():
                try: value = max(0.0, float(var.get().replace(",", ".")))
                except ValueError: messagebox.showerror("Eingabe pruefen", "Bitte eine Zahl eingeben.", parent=dialog); return
                step["seconds"] = value; dialog.destroy(); self.refresh_steps()
            ttk.Button(frame, text="Speichern", command=save).grid(row=2, column=0, sticky="e")
            dialog.bind("<Return>", lambda e: save())
            dialog.update_idletasks()
            x = self.root.winfo_pointerx() + 12
            y = self.root.winfo_pointery() + 12
            max_x = self.root.winfo_screenwidth() - dialog.winfo_width() - 8
            max_y = self.root.winfo_screenheight() - dialog.winfo_height() - 8
            dialog.geometry(f"+{max(8, min(x, max_x))}+{max(8, min(y, max_y))}")

    def position_dialog(self, dialog):
        dialog.update_idletasks()
        x = self.root.winfo_pointerx() + 12
        y = self.root.winfo_pointery() + 12
        max_x = self.root.winfo_screenwidth() - dialog.winfo_width() - 8
        max_y = self.root.winfo_screenheight() - dialog.winfo_height() - 8
        dialog.geometry(f"+{max(8, min(x, max_x))}+{max(8, min(y, max_y))}")

    def edit_text_step(self, step, title, description, allow_empty=False):
        dialog = tk.Toplevel(self.root); dialog.title(title); dialog.transient(self.root); dialog.grab_set(); dialog.resizable(True, True)
        frame = ttk.Frame(dialog, padding=16); frame.pack(fill="both", expand=True)
        ttk.Label(frame, text=description).pack(anchor="w")
        text_entry = tk.Text(frame, width=48, height=6, wrap="word")
        text_entry.pack(fill="both", expand=True, pady=(8, 12)); text_entry.insert("1.0", str(step.get("text", ""))); text_entry.focus_set()
        def save_text():
            text = text_entry.get("1.0", "end-1c")
            if not allow_empty and not text:
                messagebox.showerror("Eingabe prüfen", "Bitte einen Text eingeben.", parent=dialog); return
            step["text"] = text; dialog.destroy(); self.refresh_steps(); self.step_list.selection_set(self.selected_step)
        ttk.Button(frame, text="Speichern", command=save_text).pack(anchor="e")
        dialog.bind("<Control-Return>", lambda e: save_text())
        self.position_dialog(dialog)

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
        if path:
            self.tess_var.set(path); self.config["tesseract_path"] = path; self.save_settings(silent=True)

    def choose_log_file(self):
        path = filedialog.asksaveasfilename(
            title="Logdatei auswählen",
            initialfile=os.path.basename(self.log_var.get() or "ocr_macro.log"),
            defaultextension=".log",
            filetypes=[("Logdatei", "*.log"), ("Alle Dateien", "*.*")]
        )
        if path:
            self.log_var.set(path)
            self.save_settings(silent=True)

    def log_event(self, message):
        path = getattr(self, "log_var", None)
        path = path.get().strip() if path else DEFAULT_LOG_PATH
        if not path:
            path = DEFAULT_LOG_PATH
        try:
            os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
            with self.log_lock:
                with open(path, "a", encoding="utf-8") as log_file:
                    log_file.write(f"[{timestamp}] {message}\n")
        except OSError:
            # Logging darf die eigentliche Makro-Ausführung nicht blockieren.
            pass

    def load_settings(self):
        try:
            with open(SETTINGS_FILE, encoding="utf-8") as f:
                settings = json.load(f)
            self.tess_var.set(settings.get("tesseract_path", ""))
            self.last_config_path = settings.get("last_config_path", "")
            self.log_var.set(settings.get("log_path", DEFAULT_LOG_PATH))
        except (OSError, ValueError):
            self.last_config_path = ""
            self.log_var.set(DEFAULT_LOG_PATH)

    def save_settings(self, silent=False):
        path = self.tess_var.get().strip()
        if path and not os.path.isfile(path):
            if not silent: messagebox.showwarning("Pfad prüfen", "Die ausgewählte Datei wurde nicht gefunden.")
            return
        try:
            os.makedirs(SETTINGS_DIR, exist_ok=True)
            log_path = self.log_var.get().strip() or DEFAULT_LOG_PATH
            with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
                json.dump({"tesseract_path": path, "last_config_path": getattr(self, "last_config_path", ""), "log_path": log_path}, f, indent=2)
            self.config["tesseract_path"] = path
            self.log_var.set(log_path)
            if not silent: self.status.set("Einstellungen gespeichert.")
        except OSError as e:
            if not silent: messagebox.showerror("Speichern fehlgeschlagen", str(e))

    def load_last_config(self):
        path = getattr(self, "last_config_path", "")
        if not path or not os.path.isfile(path):
            return
        try:
            with open(path, encoding="utf-8") as f:
                self.apply_config(json.load(f))
            self.file_var.set(f"Automatisch geladen: {os.path.basename(path)}")
            self.status.set("Letzte Konfiguration automatisch geladen.")
        except (OSError, ValueError, TypeError) as e:
            self.status.set(f"Letzte Konfiguration konnte nicht geladen werden: {e}")

    def collect_config(self):
        mode = self.schedule_mode_var.get()
        interval = 0.0
        if mode == "interval":
            try: interval = max(0.1, float(self.interval_var.get().replace(",", ".")))
            except ValueError: raise ValueError("Das Intervall muss eine Zahl größer als 0 sein.")
        if mode == "daily":
            try: datetime.strptime(self.time_var.get(), "%H:%M")
            except ValueError: raise ValueError("Die Uhrzeit muss im Format HH:MM stehen.")
        try: start_delay = max(0.0, float(self.start_delay_var.get().replace(",", ".")))
        except ValueError: raise ValueError("Die Startverzögerung muss eine Zahl sein.")
        try: step_delay = max(0.0, float(self.step_delay_var.get().replace(",", ".")))
        except ValueError: raise ValueError("Die Mindestpause zwischen Schritten muss eine Zahl sein.")
        self.config.update(steps=self.steps, schedule_enabled=mode != "off", schedule_mode=mode, schedule_time=self.time_var.get(), interval_minutes=interval, tesseract_path=self.tess_var.get(), start_delay=start_delay, minimize_on_start=self.minimize_var.get(), step_delay=step_delay)
        return self.config

    def apply_config(self, data):
        self.config = dict(DEFAULT_CONFIG); self.config.update(data)
        self.steps = self.config.get("steps", [])
        mode = self.config.get("schedule_mode")
        if mode not in ("off", "daily", "interval"):
            mode = "interval" if self.config.get("schedule_enabled") and self.config.get("interval_minutes", 0) else ("daily" if self.config.get("schedule_enabled") else "off")
        self.schedule_mode_var.set(mode); self.time_var.set(self.config["schedule_time"]); self.interval_var.set(str(self.config.get("interval_minutes", 0)))
        self.start_delay_var.set(str(self.config.get("start_delay", 0))); self.step_delay_var.set(str(self.config.get("step_delay", 0.6))); self.minimize_var.set(self.config.get("minimize_on_start", False))
        self.refresh_steps()

    def save_config(self):
        try: data = self.collect_config()
        except ValueError as e: messagebox.showerror("Eingabe pruefen", str(e)); return
        path = filedialog.asksaveasfilename(defaultextension=".json", filetypes=[("JSON-Konfiguration", "*.json")])
        if not path: return
        with open(path, "w", encoding="utf-8") as f: json.dump(data, f, indent=2)
        self.last_config_path = path
        self.save_settings(silent=True)
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
            if step["type"] == "Text einfuegen" and not str(step.get("text", "")): raise ValueError(f"Schritt {number}: bitte einen Text eingeben.")
            if step["type"] == "Tastenkombination" and not str(step.get("keys", "")): raise ValueError(f"Schritt {number}: bitte eine Tastenkombination eingeben.")
        if ImageGrab is None or pytesseract is None or pyautogui is None or pyperclip is None:
            raise ValueError("Bitte zuerst pillow, pytesseract, pyautogui und pyperclip installieren.")

    def ocr_text(self, region):
        if self.config["tesseract_path"] and os.path.isfile(self.config["tesseract_path"]): pytesseract.pytesseract.tesseract_cmd = self.config["tesseract_path"]
        image = ImageGrab.grab(bbox=tuple(region)); image = ImageOps.grayscale(image)
        image = image.resize((image.width * 2, image.height * 2))
        image = ImageEnhance.Contrast(image).enhance(2.0).filter(ImageFilter.SHARPEN)
        text = " ".join(pytesseract.image_to_string(image, config="--psm 7").strip().split())
        self.log_event(f"OCR erkannt: {text if text else '[kein Text]'}")
        return text

    def execute_steps(self):
        clipboard_text = ""
        self.log_event(f"Schrittkette gestartet ({len(self.steps)} Schritte)")
        for number, step in enumerate(self.steps, 1):
            if not self.running: return
            kind = step["type"]
            self.log_event(f"Schritt {number} gestartet: {kind}")
            if kind == "Klick":
                x1, y1, x2, y2 = map(int, step["target"]); x, y = (x1 + x2) // 2, (y1 + y2) // 2
                pyautogui.moveTo(x, y, duration=0.25); pyautogui.click(x, y)
            elif kind == "OCR kopieren":
                clipboard_text = self.ocr_text(step["region"])
                if not clipboard_text: raise RuntimeError(f"Schritt {number}: kein OCR-Text erkannt.")
                pyperclip.copy(clipboard_text)
            elif kind == "OCR einfuegen":
                pyautogui.hotkey("ctrl", "v")
            elif kind == "Text einfuegen":
                pyperclip.copy(step.get("text", ""))
                pyautogui.hotkey("ctrl", "v")
                self.log_event(f"Text eingefügt: {step.get('text', '')}")
            elif kind == "Tab-Taste":
                pyautogui.press("tab")
            elif kind == "Tastenkombination":
                keys = [key.strip() for key in str(step.get("keys", "")).split("+") if key.strip()]
                pyautogui.hotkey(*keys)
            elif kind == "Text löschen":
                pyautogui.hotkey("ctrl", "a")
                pyautogui.press("backspace")
            elif kind == "Kommentar/Notiz":
                self.log_event(f"Kommentar/Notiz: {step.get('text', '')}")
            elif kind == "Enter":
                pyautogui.press("enter")
            elif kind == "Timer":
                self.wait_interruptible(float(step.get("seconds", 1)))
            self.root.after(0, lambda n=number: self.status.set(f"Schritt {n}/{len(self.steps)} ausgefuehrt."))
            self.log_event(f"Schritt {number} abgeschlossen: {kind}")
            if number < len(self.steps):
                self.wait_interruptible(float(self.config.get("step_delay", 0.6)))
        self.log_event("Schrittkette erfolgreich beendet")
        self.root.after(0, lambda: self.status.set("Ablauf erfolgreich beendet."))

    def wait_interruptible(self, seconds):
        end = time.monotonic() + max(0.0, seconds)
        while self.running and time.monotonic() < end:
            time.sleep(min(0.1, end - time.monotonic()))

    def run_once(self):
        try: self.validate()
        except ValueError as e: messagebox.showerror("Konfiguration pruefen", str(e)); return
        if self.running: return
        start_delay = float(self.start_delay_var.get().replace(",", "."))
        if self.minimize_var.get(): self.root.iconify()
        self.running = True; self.stop_button.configure(state="normal"); self.status.set("OCR und Eingabe laufen ...")
        threading.Thread(target=self.worker, args=(start_delay,), daemon=True).start()

    def worker(self, start_delay):
        try:
            if start_delay > 0:
                self.root.after(0, lambda: self.status.set(f"Start in {start_delay:g} Sekunden ..."))
                end = time.monotonic() + start_delay
                while self.running and time.monotonic() < end:
                    time.sleep(min(0.1, end - time.monotonic()))
            if not self.running: return
            self.execute_steps()
        except Exception as e:
            self.log_event(f"FEHLER: {e}")
            self.root.after(0, lambda error=str(e): self.report_execution_error(error))
        finally:
            self.running = False; self.root.after(0, lambda: self.stop_button.configure(state="disabled"))

    def report_execution_error(self, error):
        self.status.set(f"Ausführung fehlgeschlagen: {error}")
        self.show_user_message("error", "Ausführung fehlgeschlagen", f"Die Schrittfolge konnte nicht vollständig ausgeführt werden.\n\n{error}")

    def show_user_message(self, kind, title, message):
        self.root.deiconify()
        self.root.lift()
        self.root.attributes("-topmost", True)
        try:
            if kind == "error":
                messagebox.showerror(title, message, parent=self.root)
            else:
                messagebox.showinfo(title, message, parent=self.root)
        finally:
            self.root.attributes("-topmost", False)

    def start_scheduler(self):
        try: self.validate()
        except ValueError as e: messagebox.showerror("Konfiguration pruefen", str(e)); return
        mode = self.schedule_mode_var.get()
        if mode == "off":
            messagebox.showinfo("Zeitplan auswählen", "Bitte Täglich oder Intervall auswählen.")
            return
        if self.scheduler_thread and self.scheduler_thread.is_alive(): self.status.set("Zeitplan laeuft bereits."); return
        self.config["schedule_enabled"] = True; self.config["schedule_mode"] = mode
        self.log_event(f"Zeitplan gestartet: {mode}")
        self.scheduler_next_run = self.calculate_next_run(datetime.now(), mode)
        self.scheduler_thread = threading.Thread(target=self.scheduler, daemon=True); self.scheduler_thread.start()
        self.schedule_button.configure(text="Run-Zeitplan stoppen", bg="#198754", activebackground="#146c43")
        self.update_next_run_display()
        description = f"täglich um {self.time_var.get()} Uhr" if mode == "daily" else f"alle {self.interval_var.get()} Minuten"
        self.status.set(f"Zeitplan aktiv: {description}.")

    def toggle_scheduler(self):
        if self.config.get("schedule_enabled"):
            self.stop_scheduler()
        else:
            self.start_scheduler()

    def calculate_next_run(self, now, mode):
        if mode == "daily":
            scheduled = datetime.strptime(self.config.get("schedule_time", "09:00"), "%H:%M").time()
            next_run = datetime.combine(now.date(), scheduled)
            if next_run <= now: next_run += timedelta(days=1)
            return next_run
        if mode == "interval":
            return now + timedelta(minutes=float(self.config.get("interval_minutes", 0)))
        return None

    def update_next_run_display(self):
        if self.scheduler_next_run is None:
            self.next_run_var.set("Nächster Zeitplan: keiner")
        else:
            self.next_run_var.set(f"Nächster Termin: {self.scheduler_next_run.strftime('%d.%m.%Y %H:%M:%S')}")

    def scheduler(self):
        while self.config.get("schedule_enabled"):
            now = datetime.now()
            if self.scheduler_next_run and now >= self.scheduler_next_run and not self.running:
                self.scheduler_next_run = self.calculate_next_run(now, self.config.get("schedule_mode", "off"))
                self.root.after(0, self.update_next_run_display)
                self.root.after(0, self.run_once)
            time.sleep(0.5)

    def stop_run(self, show_popup=False):
        if self.running:
            self.running = False
            self.log_event("Aktueller Ablauf manuell abgebrochen")
            self.status.set("Aktueller Ablauf gestoppt.")
            self.stop_button.configure(state="disabled")
            if show_popup:
                self.show_user_message("info", "Ablauf abgebrochen", "Der aktuelle Ablauf wurde manuell abgebrochen.")

    def stop_scheduler(self):
        self.config["schedule_enabled"] = False; self.config["schedule_mode"] = "off"; self.schedule_mode_var.set("off")
        self.log_event("Zeitplan gestoppt")
        self.scheduler_next_run = None
        self.update_next_run_display()
        self.schedule_button.configure(text="Run-Zeitplan starten", bg="#b02a37", activebackground="#842029")
        self.status.set("Zeitplan gestoppt.")

    def stop(self, from_hotkey=False):
        was_active = self.running or self.config.get("schedule_enabled", False)
        self.stop_run()
        self.stop_scheduler()
        if from_hotkey and was_active:
            self.show_user_message("info", "Abbruch", "Der Ablauf wurde über Strg+Alt+Q abgebrochen.")

    def hotkey_listener(self):
        user32 = ctypes.windll.user32
        pressed = False
        while self.hotkey_running:
            ctrl = bool(user32.GetAsyncKeyState(0x11) & 0x8000)
            alt = bool(user32.GetAsyncKeyState(0x12) & 0x8000)
            q = bool(user32.GetAsyncKeyState(0x51) & 0x8000)
            combination = ctrl and alt and q
            if combination and not pressed:
                self.root.after(0, lambda: self.stop(from_hotkey=True))
            pressed = combination
            time.sleep(0.05)

    def close(self):
        self.hotkey_running = False
        self.config["schedule_enabled"] = False
        self.root.destroy()


if __name__ == "__main__":
    root = tk.Tk(); OCRMacroApp(root); root.mainloop()
