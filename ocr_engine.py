"""
PokeParser — main.py
Pokemon summary screenshot OCR → styled XLSX → Google Drive
"""

import os, sys, threading, queue, platform
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

# ── Resource path (works frozen + dev) ────────────────────────────────────────
def resource_path(rel):
    base = getattr(sys, '_MEIPASS', os.path.dirname(__file__))
    return os.path.join(base, rel)

# ── Tesseract PATH fix ─────────────────────────────────────────────────────────
# PyInstaller frozen apps don't inherit the system PATH.
# Explicitly tell pytesseract where Tesseract lives on each platform.
def _configure_tesseract():
    import pytesseract
    # Already findable — nothing to do
    try:
        pytesseract.get_tesseract_version()
        return True
    except Exception:
        pass

    candidates = []
    if platform.system() == "Windows":
        candidates = [
            r"C:\Program Files\Tesseract-OCR\tesseract.exe",
            r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
            os.path.join(os.environ.get("LOCALAPPDATA", ""), r"Programs\Tesseract-OCR\tesseract.exe"),
            os.path.join(os.environ.get("ProgramFiles", ""), r"Tesseract-OCR\tesseract.exe"),
        ]
    elif platform.system() == "Darwin":
        candidates = [
            "/usr/local/bin/tesseract",
            "/opt/homebrew/bin/tesseract",
        ]
    else:
        candidates = ["/usr/bin/tesseract", "/usr/local/bin/tesseract"]

    for path in candidates:
        if os.path.isfile(path):
            pytesseract.pytesseract.tesseract_cmd = path
            try:
                pytesseract.get_tesseract_version()
                return True
            except Exception:
                continue
    return False

_TESSERACT_OK = _configure_tesseract()

# ── Heavy imports ──────────────────────────────────────────────────────────────
import settings as cfg_module
import gdrive
from ocr_engine import parse_screenshot
from spreadsheet import build_spreadsheet, make_output_path

# ── Try real drag-and-drop; fall back gracefully ───────────────────────────────
try:
    from tkinterdnd2 import TkinterDnD, DND_FILES
    _DND = True
except ImportError:
    _DND = False

# ── Colours ────────────────────────────────────────────────────────────────────
C_BLUE       = "#3667AF"
C_BLUE_DARK  = "#2A5298"
C_BLUE_LT    = "#4A7EC7"
C_YELLOW     = "#FFCA09"
C_YELLOW_DK  = "#E6B600"
C_BG         = "#1A1A2E"
C_SURFACE    = "#16213E"
C_SURFACE2   = "#0F3460"
C_CARD       = "#1E2D4A"
C_TEXT       = "#E0E0E0"
C_DIM        = "#9E9E9E"
C_GREEN      = "#4CAF50"
C_RED        = "#FF5252"

FONT_BODY  = ("Segoe UI", 10)
FONT_SMALL = ("Segoe UI", 9)
FONT_BOLD  = ("Segoe UI", 10, "bold")


# ── App ────────────────────────────────────────────────────────────────────────
class PokeParserApp(TkinterDnD.Tk if _DND else tk.Tk):
    def __init__(self):
        super().__init__()
        self.settings   = cfg_module.load()
        self.queue_items: list[str] = []
        self.results:     list[dict] = []
        self.processing   = False
        self.msg_q        = queue.Queue()
        self._last_output: str | None = None

        self._build_ui()
        self._poll()

        if not _TESSERACT_OK:
            messagebox.showwarning(
                "Tesseract Not Found",
                "PokeParser could not find Tesseract OCR.\n\n"
                "Install it from:\n"
                "https://github.com/UB-Mannheim/tesseract/wiki\n\n"
                "Keep the default install path:\n"
                "C:\\Program Files\\Tesseract-OCR\\\n\n"
                "Then restart PokeParser."
            )

    # ── UI ─────────────────────────────────────────────────────────────────────
    def _build_ui(self):
        self.title("PokeParser")
        self.geometry("960x680")
        self.minsize(800, 560)
        self.configure(bg=C_BG)

        try:
            icon = resource_path("assets/icon.png")
            if os.path.exists(icon):
                self.iconphoto(True, tk.PhotoImage(file=icon))
        except Exception:
            pass

        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure("TFrame", background=C_BG)
        style.configure("Card.TFrame", background=C_CARD)
        style.configure("TLabel", background=C_BG, foreground=C_TEXT, font=FONT_BODY)
        style.configure("Horizontal.TProgressbar",
                        background=C_YELLOW, troughcolor=C_SURFACE2,
                        bordercolor=C_SURFACE2, lightcolor=C_YELLOW,
                        darkcolor=C_YELLOW_DK)
        style.configure("TScrollbar", background=C_SURFACE2,
                        troughcolor=C_SURFACE, arrowcolor=C_TEXT)

        self._header()
        self._body()
        self._status_bar()

    def _header(self):
        hdr = tk.Frame(self, bg=C_BLUE_DARK, height=72)
        hdr.pack(fill=tk.X)
        hdr.pack_propagate(False)
        inner = tk.Frame(hdr, bg=C_BLUE_DARK)
        inner.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)

        title = tk.Frame(inner, bg=C_BLUE_DARK)
        title.pack(side=tk.LEFT)
        tk.Label(title, text="Poké", font=("Segoe UI", 22, "bold"),
                 bg=C_BLUE_DARK, fg=C_YELLOW).pack(side=tk.LEFT)
        tk.Label(title, text="Parser", font=("Segoe UI", 22, "bold"),
                 bg=C_BLUE_DARK, fg="white").pack(side=tk.LEFT)
        tk.Label(title, text="  PokeNexus Screenshot → Spreadsheet",
                 font=FONT_SMALL, bg=C_BLUE_DARK, fg="#AABBDD").pack(
                 side=tk.LEFT, padx=(8, 0))

        btns = tk.Frame(inner, bg=C_BLUE_DARK)
        btns.pack(side=tk.RIGHT)
        self._hbtn(btns, "⚙  Settings",    self._open_settings).pack(side=tk.RIGHT, padx=4)
        self._hbtn(btns, "☁  Drive Setup", self._open_drive_setup).pack(side=tk.RIGHT, padx=4)

    def _hbtn(self, parent, text, cmd):
        return tk.Button(parent, text=text, command=cmd,
                         bg=C_BLUE_LT, fg="white", font=FONT_SMALL,
                         relief=tk.FLAT, padx=10, pady=4, cursor="hand2",
                         activebackground=C_YELLOW, activeforeground=C_BG)

    def _body(self):
        body = tk.Frame(self, bg=C_BG)
        body.pack(fill=tk.BOTH, expand=True, padx=16, pady=10)

        left = tk.Frame(body, bg=C_CARD)
        left.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 8))
        self._queue_panel(left)

        right = tk.Frame(body, bg=C_BG, width=230)
        right.pack(side=tk.RIGHT, fill=tk.Y)
        right.pack_propagate(False)
        self._action_panel(right)
        self._log_panel(right)

    # ── Queue panel ────────────────────────────────────────────────────────────
    def _queue_panel(self, parent):
        # Header bar
        top = tk.Frame(parent, bg=C_BLUE_DARK, height=36)
        top.pack(fill=tk.X)
        top.pack_propagate(False)
        tk.Label(top, text="📋  Screenshot Queue", font=FONT_BOLD,
                 bg=C_BLUE_DARK, fg=C_YELLOW, anchor="w").pack(
                 side=tk.LEFT, padx=12, pady=8)
        self._count_lbl = tk.Label(top, text="0 files", font=FONT_SMALL,
                                   bg=C_BLUE_DARK, fg=C_DIM)
        self._count_lbl.pack(side=tk.RIGHT, padx=12)

        # Drop zone
        dz_bg = C_SURFACE2 if _DND else C_SURFACE
        self._drop_zone = tk.Frame(parent, bg=dz_bg, relief=tk.FLAT, bd=2)
        self._drop_zone.pack(fill=tk.X, padx=8, pady=(8, 4))
        dz_inner = tk.Frame(self._drop_zone, bg=dz_bg)
        dz_inner.pack(pady=14)
        tk.Label(dz_inner, text="⬇", font=("Segoe UI", 26),
                 bg=dz_bg, fg=C_YELLOW).pack()
        drop_text = ("Drop screenshots or folders here" if _DND
                     else "Use buttons below to add screenshots")
        tk.Label(dz_inner, text=drop_text, font=FONT_SMALL,
                 bg=dz_bg, fg=C_DIM, justify="center").pack()
        if not _DND:
            tk.Label(dz_inner, text="(install tkinterdnd2 to enable drag-and-drop)",
                     font=("Segoe UI", 8), bg=dz_bg, fg="#555").pack()

        if _DND:
            self._drop_zone.drop_target_register(DND_FILES)
            self._drop_zone.dnd_bind("<<Drop>>", self._on_drop)
            dz_inner.drop_target_register(DND_FILES)
            dz_inner.dnd_bind("<<Drop>>", self._on_drop)

        # Buttons
        btn_row = tk.Frame(parent, bg=C_CARD)
        btn_row.pack(fill=tk.X, padx=8, pady=4)
        self._btn(btn_row, "+ Files",  self._add_files,  C_BLUE).pack(
            side=tk.LEFT, padx=4, pady=4, fill=tk.X, expand=True)
        self._btn(btn_row, "+ Folder", self._add_folder, C_BLUE).pack(
            side=tk.LEFT, padx=4, pady=4, fill=tk.X, expand=True)
        self._btn(btn_row, "✕ Clear",  self._clear,      "#444").pack(
            side=tk.LEFT, padx=4, pady=4)

        # Listbox
        lf = tk.Frame(parent, bg=C_CARD)
        lf.pack(fill=tk.BOTH, expand=True, padx=8, pady=(0, 8))
        sb = ttk.Scrollbar(lf, orient=tk.VERTICAL)
        self._listbox = tk.Listbox(
            lf, yscrollcommand=sb.set,
            bg=C_SURFACE, fg=C_TEXT, selectbackground=C_BLUE,
            font=FONT_SMALL, relief=tk.FLAT, bd=0, activestyle="none")
        sb.config(command=self._listbox.yview)
        sb.pack(side=tk.RIGHT, fill=tk.Y)
        self._listbox.pack(fill=tk.BOTH, expand=True)
        self._listbox.bind("<Button-3>", self._right_click)
        self._listbox.bind("<Delete>",   lambda e: self._remove_sel())

        if _DND:
            self._listbox.drop_target_register(DND_FILES)
            self._listbox.dnd_bind("<<Drop>>", self._on_drop)

    # ── Action + log ───────────────────────────────────────────────────────────
    def _action_panel(self, parent):
        card = tk.Frame(parent, bg=C_CARD)
        card.pack(fill=tk.X, pady=(0, 8))
        tk.Label(card, text="Actions", font=FONT_BOLD,
                 bg=C_CARD, fg=C_YELLOW).pack(padx=12, pady=(10, 6), anchor="w")

        self._parse_btn = tk.Button(
            card, text="▶  Parse Screenshots", command=self._start,
            bg=C_YELLOW, fg=C_BG, font=("Segoe UI", 11, "bold"),
            relief=tk.FLAT, padx=12, pady=10, cursor="hand2",
            activebackground=C_YELLOW_DK, activeforeground=C_BG)
        self._parse_btn.pack(fill=tk.X, padx=12, pady=(0, 4))

        self._upload_btn = tk.Button(
            card, text="☁  Upload to Drive", command=self._upload,
            bg=C_BLUE, fg="white", font=FONT_BOLD, relief=tk.FLAT,
            padx=12, pady=8, cursor="hand2",
            activebackground=C_BLUE_LT, state=tk.DISABLED)
        self._upload_btn.pack(fill=tk.X, padx=12, pady=(0, 4))

        self._save_btn = tk.Button(
            card, text="💾  Save Locally", command=self._save_local,
            bg=C_SURFACE2, fg=C_TEXT, font=FONT_BOLD, relief=tk.FLAT,
            padx=12, pady=8, cursor="hand2",
            activebackground=C_BLUE, state=tk.DISABLED)
        self._save_btn.pack(fill=tk.X, padx=12, pady=(0, 4))

        self._open_btn = tk.Button(
            card, text="📂  Open Last File", command=self._open_last,
            bg=C_SURFACE2, fg=C_TEXT, font=FONT_BOLD, relief=tk.FLAT,
            padx=12, pady=8, cursor="hand2",
            activebackground=C_BLUE, state=tk.DISABLED)
        self._open_btn.pack(fill=tk.X, padx=12, pady=(0, 4))

        self._prog_var = tk.DoubleVar()
        ttk.Progressbar(card, variable=self._prog_var, maximum=100,
                        style="Horizontal.TProgressbar").pack(
            fill=tk.X, padx=12, pady=(4, 2))
        self._prog_lbl = tk.Label(card, text="Ready", font=FONT_SMALL,
                                  bg=C_CARD, fg=C_DIM)
        self._prog_lbl.pack(padx=12, pady=(0, 10), anchor="w")

    def _log_panel(self, parent):
        card = tk.Frame(parent, bg=C_CARD)
        card.pack(fill=tk.BOTH, expand=True)
        tk.Label(card, text="Log", font=FONT_BOLD,
                 bg=C_CARD, fg=C_YELLOW).pack(padx=12, pady=(10, 4), anchor="w")
        sb = ttk.Scrollbar(card, orient=tk.VERTICAL)
        self._log = tk.Text(card, state=tk.DISABLED, yscrollcommand=sb.set,
                            bg=C_SURFACE, fg=C_TEXT, font=("Consolas", 8),
                            relief=tk.FLAT, bd=0, wrap=tk.WORD,
                            insertbackground=C_TEXT)
        sb.config(command=self._log.yview)
        sb.pack(side=tk.RIGHT, fill=tk.Y, padx=(0, 4), pady=(0, 8))
        self._log.pack(fill=tk.BOTH, expand=True, padx=(12, 0), pady=(0, 8))
        for tag, fg in [("ok", C_GREEN), ("err", C_RED),
                        ("info", C_DIM), ("warn", C_YELLOW)]:
            self._log.tag_configure(tag, foreground=fg)

    def _status_bar(self):
        bar = tk.Frame(self, bg=C_SURFACE, height=24)
        bar.pack(fill=tk.X, side=tk.BOTTOM)
        bar.pack_propagate(False)
        self._status = tk.Label(bar, text="Ready  •  Add screenshots to begin",
                                font=FONT_SMALL, bg=C_SURFACE, fg=C_DIM, anchor="w")
        self._status.pack(side=tk.LEFT, padx=12, pady=4)
        drive_ok = gdrive.is_configured()
        tk.Label(bar,
                 text=("☁ Drive: Connected" if drive_ok else "☁ Drive: Not configured"),
                 font=FONT_SMALL, bg=C_SURFACE,
                 fg=(C_GREEN if drive_ok else C_DIM)).pack(side=tk.RIGHT, padx=12)

    # ── Widget helper ──────────────────────────────────────────────────────────
    def _btn(self, parent, text, cmd, color):
        return tk.Button(parent, text=text, command=cmd, bg=color, fg="white",
                         font=FONT_SMALL, relief=tk.FLAT, padx=8, pady=4,
                         cursor="hand2", activebackground=C_YELLOW,
                         activeforeground=C_BG)

    # ── Drag and drop ──────────────────────────────────────────────────────────
    def _on_drop(self, event):
        # tkinterdnd2 gives space-separated paths; braces wrap paths with spaces
        raw = event.data
        paths = []
        # Parse tcl list format: {path with spaces} or plain/path
        import re
        for item in re.findall(r'\{[^}]+\}|\S+', raw):
            p = item.strip("{}").strip()
            if os.path.isdir(p):
                self._add_folder_path(p)
            elif os.path.isfile(p):
                self._enqueue(p)

    # ── Queue management ───────────────────────────────────────────────────────
    def _add_files(self):
        paths = filedialog.askopenfilenames(
            title="Select PokeNexus Screenshots",
            filetypes=[("Images", "*.png *.jpg *.jpeg *.bmp *.webp"),
                       ("All Files", "*.*")])
        for p in paths:
            self._enqueue(p)

    def _add_folder(self):
        folder = filedialog.askdirectory(title="Select Screenshot Folder")
        if folder:
            self._add_folder_path(folder)

    def _add_folder_path(self, folder):
        exts = {".png", ".jpg", ".jpeg", ".bmp", ".webp"}
        for fn in sorted(os.listdir(folder)):
            if os.path.splitext(fn)[1].lower() in exts:
                self._enqueue(os.path.join(folder, fn))

    def _enqueue(self, path):
        if path not in self.queue_items:
            self.queue_items.append(path)
            self._listbox.insert(tk.END, os.path.basename(path))
            self._update_count()

    def _clear(self):
        self.queue_items.clear()
        self._listbox.delete(0, tk.END)
        self._update_count()

    def _remove_sel(self):
        for idx in reversed(list(self._listbox.curselection())):
            self.queue_items.pop(idx)
            self._listbox.delete(idx)
        self._update_count()

    def _right_click(self, event):
        self._listbox.selection_clear(0, tk.END)
        self._listbox.selection_set(self._listbox.nearest(event.y))
        m = tk.Menu(self, tearoff=0, bg=C_SURFACE2, fg=C_TEXT, font=FONT_SMALL)
        m.add_command(label="Remove", command=self._remove_sel)
        m.tk_popup(event.x_root, event.y_root)

    def _update_count(self):
        n = len(self.queue_items)
        self._count_lbl.config(text=f"{n} file{'s' if n != 1 else ''}")
        self._set_status(f"{n} screenshot{'s' if n != 1 else ''} queued")

    # ── Parsing ────────────────────────────────────────────────────────────────
    def _start(self):
        if not self.queue_items:
            messagebox.showinfo("No Files", "Add screenshots to the queue first.")
            return
        if self.processing:
            return
        self.processing = True
        self.results.clear()
        self._parse_btn.config(state=tk.DISABLED)
        self._upload_btn.config(state=tk.DISABLED)
        self._save_btn.config(state=tk.DISABLED)
        self._open_btn.config(state=tk.DISABLED)
        self._prog_var.set(0)
        threading.Thread(target=self._parse_thread,
                         args=(list(self.queue_items),), daemon=True).start()

    def _parse_thread(self, paths):
        import pytesseract
        # Re-run path detection inside thread (frozen app safety)
        _configure_tesseract()

        total = len(paths)
        for i, path in enumerate(paths):
            fname = os.path.basename(path)
            self.msg_q.put(("info", f"Parsing {fname}…"))
            try:
                r = parse_screenshot(path)
                self.results.append(r)
                errs = [e for e in r.get("parse_errors", []) if e != "name_from_filename"]
                if errs:
                    self.msg_q.put(("warn", f"  ⚠ {fname}: check {', '.join(errs)}"))
                else:
                    name = r.get("pokemon") or "?"
                    lv   = r.get("level") or "?"
                    self.msg_q.put(("ok", f"  ✓ {name} Lv{lv}"))
            except pytesseract.pytesseract.TesseractNotFoundError:
                self.msg_q.put(("err",
                    "  ✗ Tesseract not found. Install from: "
                    "https://github.com/UB-Mannheim/tesseract/wiki"))
                break  # no point continuing
            except Exception as exc:
                self.msg_q.put(("err", f"  ✗ {fname}: {exc}"))
            self.msg_q.put(("prog", (i + 1) / total * 100, f"{i+1}/{total}"))
        self.msg_q.put(("done", len(self.results)))

    def _poll(self):
        try:
            while True:
                msg = self.msg_q.get_nowait()
                kind = msg[0]
                if kind in ("ok", "info", "warn", "err"):
                    self._log_write(msg[1], kind)
                elif kind == "prog":
                    self._prog_var.set(msg[1])
                    self._prog_lbl.config(text=msg[2])
                elif kind == "done":
                    self._parse_done(msg[1])
        except queue.Empty:
            pass
        self.after(80, self._poll)

    def _parse_done(self, count):
        self.processing = False
        self._parse_btn.config(state=tk.NORMAL)
        if count:
            self._upload_btn.config(state=tk.NORMAL)
            self._save_btn.config(state=tk.NORMAL)
        self._log_write(f"Done — {count} Pokémon parsed.", "ok")
        self._set_status(f"Parsed {count} screenshots. Ready to export.")
        self._prog_lbl.config(text=f"Complete: {count} parsed")

    # ── Output ─────────────────────────────────────────────────────────────────
    def _output_path(self):
        d = self.settings.get("output_dir", os.path.expanduser("~"))
        os.makedirs(d, exist_ok=True)
        return make_output_path(d)

    def _build_and_save(self):
        path = self._output_path()
        build_spreadsheet(self.results, path)
        self._last_output = path
        self._open_btn.config(state=tk.NORMAL)
        return path

    def _save_local(self):
        if not self.results:
            return
        path = self._build_and_save()
        self._log_write(f"Saved: {path}", "ok")
        self._set_status(f"Saved to {path}")
        if messagebox.askyesno("Saved", f"Saved:\n{path}\n\nOpen now?"):
            self._open_file(path)

    def _upload(self):
        if not self.results:
            return
        if not gdrive.is_configured():
            messagebox.showwarning("Drive Not Configured",
                "Set up Google Drive credentials via ☁ Drive Setup.")
            return
        path = self._build_and_save()
        self._log_write("Uploading to Google Drive…", "info")
        folder = self.settings.get("gdrive_folder", "PokeParser")
        try:
            link = gdrive.upload_file(path, folder)
            self._log_write(f"Uploaded: {link}", "ok")
            self._set_status("Uploaded to Google Drive ✓")
            messagebox.showinfo("Uploaded", f"File uploaded:\n{link}")
        except Exception as exc:
            self._log_write(f"Upload failed: {exc}", "err")
            messagebox.showerror("Upload Failed", str(exc))

    def _open_last(self):
        if self._last_output and os.path.exists(self._last_output):
            self._open_file(self._last_output)

    @staticmethod
    def _open_file(path):
        import subprocess
        if platform.system() == "Darwin":
            subprocess.call(["open", path])
        elif platform.system() == "Windows":
            os.startfile(path)
        else:
            subprocess.call(["xdg-open", path])

    # ── Dialogs ────────────────────────────────────────────────────────────────
    def _open_settings(self):
        SettingsDialog(self, self.settings)

    def _open_drive_setup(self):
        DriveSetupDialog(self)

    # ── Helpers ────────────────────────────────────────────────────────────────
    def _log_write(self, text, tag="info"):
        self._log.config(state=tk.NORMAL)
        self._log.insert(tk.END, text + "\n", tag)
        self._log.see(tk.END)
        self._log.config(state=tk.DISABLED)

    def _set_status(self, text):
        self._status.config(text=text)


# ── Settings dialog ────────────────────────────────────────────────────────────
class SettingsDialog(tk.Toplevel):
    def __init__(self, parent, settings):
        super().__init__(parent)
        self.parent = parent
        self.settings = settings
        self.title("Settings")
        self.configure(bg=C_BG)
        self.geometry("500x320")
        self.resizable(False, False)
        self.grab_set()
        self.lift()
        self.focus_force()
        try:
            self._build()
        except Exception as exc:
            import traceback
            messagebox.showerror("Settings Error", traceback.format_exc())
            self.destroy()

    def _build(self):
        p = dict(padx=16)
        tk.Label(self, text="PokeParser Settings", font=FONT_BOLD,
                 bg=C_BG, fg=C_YELLOW).pack(**p, anchor="w", pady=(16, 4))

        tk.Label(self, text="Local output directory:", font=FONT_SMALL,
                 bg=C_BG, fg=C_TEXT).pack(**p, anchor="w", pady=6)
        row = tk.Frame(self, bg=C_BG); row.pack(fill=tk.X, **p, pady=6)
        self._out = tk.StringVar(value=self.settings.get("output_dir", ""))
        tk.Entry(row, textvariable=self._out, bg=C_SURFACE, fg=C_TEXT,
                 font=FONT_SMALL, relief=tk.FLAT,
                 insertbackground=C_TEXT).pack(side=tk.LEFT, fill=tk.X, expand=True)
        tk.Button(row, text="Browse", command=self._browse,
                  bg=C_BLUE, fg="white", font=FONT_SMALL,
                  relief=tk.FLAT, padx=8).pack(side=tk.LEFT, padx=(4, 0))

        tk.Label(self, text="Google Drive folder name:", font=FONT_SMALL,
                 bg=C_BG, fg=C_TEXT).pack(**p, anchor="w")
        self._folder = tk.StringVar(value=self.settings.get("gdrive_folder", "PokeParser"))
        tk.Entry(self, textvariable=self._folder, bg=C_SURFACE, fg=C_TEXT,
                 font=FONT_SMALL, relief=tk.FLAT,
                 insertbackground=C_TEXT).pack(fill=tk.X, **p)

        self._smogon = tk.BooleanVar(value=self.settings.get("smogon_lookup", True))
        tk.Checkbutton(self, text="Check Smogon USUM (Gen 7) for good natures",
                       variable=self._smogon, bg=C_BG, fg=C_TEXT,
                       selectcolor=C_SURFACE, font=FONT_SMALL,
                       activebackground=C_BG).pack(**p, anchor="w")

        br = tk.Frame(self, bg=C_BG); br.pack(fill=tk.X, padx=16, pady=16)
        tk.Button(br, text="Save", command=self._save,
                  bg=C_YELLOW, fg=C_BG, font=FONT_BOLD,
                  relief=tk.FLAT, padx=16, pady=6).pack(side=tk.RIGHT)
        tk.Button(br, text="Cancel", command=self.destroy,
                  bg=C_SURFACE2, fg=C_TEXT, font=FONT_SMALL,
                  relief=tk.FLAT, padx=12, pady=6).pack(side=tk.RIGHT, padx=(0, 8))

    def _browse(self):
        d = filedialog.askdirectory()
        if d:
            self._out.set(d)

    def _save(self):
        self.settings.update({
            "output_dir":    self._out.get(),
            "gdrive_folder": self._folder.get(),
            "smogon_lookup": self._smogon.get(),
        })
        cfg_module.save(self.settings)
        self.parent.settings = self.settings
        self.destroy()


# ── Drive setup dialog ─────────────────────────────────────────────────────────
class DriveSetupDialog(tk.Toplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title("Google Drive Setup")
        self.configure(bg=C_BG)
        self.geometry("520x380")
        self.resizable(False, False)
        self.grab_set()
        self.lift()
        self.focus_force()
        try:
            self._build()
        except Exception as exc:
            import traceback
            messagebox.showerror("Drive Setup Error", traceback.format_exc())
            self.destroy()

    def _build(self):
        p = dict(padx=20)
        tk.Label(self, text="Google Drive Setup", font=FONT_BOLD,
                 bg=C_BG, fg=C_YELLOW).pack(**p, anchor="w", pady=(16, 4))
        tk.Label(self, text=(
            "1. Go to console.cloud.google.com\n"
            "2. Create a project → Enable Drive API\n"
            "3. Credentials → OAuth 2.0 Client ID → Desktop App\n"
            "4. Download credentials.json\n"
            "5. Load it below and click Authorise"
        ), font=FONT_SMALL, bg=C_BG, fg=C_TEXT,
           justify="left", wraplength=470).pack(**p, anchor="w")

        row = tk.Frame(self, bg=C_BG); row.pack(fill=tk.X, **p)
        self._creds = tk.StringVar()
        tk.Entry(row, textvariable=self._creds, bg=C_SURFACE, fg=C_TEXT,
                 font=FONT_SMALL, relief=tk.FLAT,
                 insertbackground=C_TEXT).pack(side=tk.LEFT, fill=tk.X, expand=True)
        tk.Button(row, text="Browse", command=self._browse,
                  bg=C_BLUE, fg="white", font=FONT_SMALL,
                  relief=tk.FLAT, padx=8).pack(side=tk.LEFT, padx=(4, 0))

        self._status = tk.Label(self, text="", font=FONT_SMALL, bg=C_BG, fg=C_DIM)
        self._status.pack(**p, anchor="w")

        br = tk.Frame(self, bg=C_BG); br.pack(fill=tk.X, padx=20, pady=12)
        tk.Button(br, text="Authorise with Google", command=self._auth,
                  bg=C_YELLOW, fg=C_BG, font=FONT_BOLD,
                  relief=tk.FLAT, padx=16, pady=6).pack(side=tk.RIGHT)
        tk.Button(br, text="Close", command=self.destroy,
                  bg=C_SURFACE2, fg=C_TEXT, font=FONT_SMALL,
                  relief=tk.FLAT, padx=12, pady=6).pack(side=tk.RIGHT, padx=(0, 8))

    def _browse(self):
        p = filedialog.askopenfilename(
            title="Select credentials.json",
            filetypes=[("JSON", "*.json"), ("All", "*.*")])
        if p:
            self._creds.set(p)

    def _auth(self):
        p = self._creds.get()
        if not p or not os.path.exists(p):
            self._status.config(text="Select a credentials.json file first.", fg=C_RED)
            return
        try:
            gdrive.save_credentials_path(p)
            self._status.config(text="Opening browser for Google auth…", fg=C_YELLOW)
            self.update()
            svc = gdrive.authenticate()
            if svc:
                self._status.config(text="✓ Connected to Google Drive!", fg=C_GREEN)
            else:
                self._status.config(text="Auth failed — check credentials.", fg=C_RED)
        except Exception as exc:
            self._status.config(text=f"Error: {exc}", fg=C_RED)


# ── Entry point ────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    app = PokeParserApp()
    app.mainloop()
