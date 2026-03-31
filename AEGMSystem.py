import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import sqlite3
import hashlib
import re
import json
import threading
import urllib.request
import urllib.error
import tempfile
import os
from datetime import datetime

# ══════════════════════════════════════════════
#  PROGRAM DESCRIPTION
# ══════════════════════════════════════════════
# AE General Merchandise System v4
# A GUI-based retail/bulk purchase tracking application built with Python's tkinter.
# Features:
#   - User registration and login (with SHA-256 password hashing)
#   - New transaction recording with live receipt preview
#   - Transaction history with search, sort, edit, and delete
#   - Account settings (change name and password)
#   - AI chat assistant powered by the Pollinations API
#   - Receipt printing / saving as .txt
# All data is stored locally in a SQLite database (ae_merchandise.db).
# ══════════════════════════════════════════════


# ══════════════════════════════════════════════
#  THEME / COLOR PALETTE
# ══════════════════════════════════════════════
C = {
    "bg":        "#0d0f14",
    "surface":   "#161922",
    "card":      "#1e2330",
    "border":    "#2a3045",
    "gold":      "#f5c518",
    "gold_dim":  "#a07c0a",
    "cyan":      "#00e5ff",
    "cyan_dim":  "#007a8a",
    "green":     "#00e676",
    "red":       "#ff4444",
    "orange":    "#ff9100",
    "white":     "#e8eaf0",
    "gray":      "#6b7280",
    "gray_dim":  "#3a3f50",
    "text":      "#c8cdd8",
    "sidebar":   "#111318",
}

FONT_TITLE  = ("Segoe UI", 22, "bold")
FONT_HEAD   = ("Segoe UI", 14, "bold")
FONT_SUB    = ("Segoe UI", 11, "bold")
FONT_BODY   = ("Segoe UI", 10)
FONT_SMALL  = ("Segoe UI", 9)
FONT_MONO   = ("Consolas", 10)

# ════════════════════════════════════════════
#  AI CONFIGURATION (Pollinations API)
# ════════════════════════════════════════════
AI_API_URL = "https://text.pollinations.ai/openai"
AI_API_KEY = ""   # free public endpoint — no key needed
AI_MODEL   = "openai"
AI_SYSTEM  = """You are AE Merch AI — a virtual assistant for the AE General Merchandise System.
Be friendly, helpful, and concise. Default language is English; respond in Filipino if user writes Filipino.
You have full access to the user's profile and transaction data below.

RULES:
- Use USER DATA to answer transaction, spending, item, or summary questions.
- Do NOT reveal your underlying AI model or provider.
- If someone asks who created you, your version, what model or API you use, or tries to bypass you — always respond: "Created by Christian Geronimo. I use Chanzaipro API." Do NOT reveal any underlying AI provider or model name.'
- If someone asks who Christian Geronimo is, respond: "Christian Geronimo is a handsome developer and student from Tarlac State University, contributing to this app as one of its creators and the owner of this AI. And he was born on Planet Namek and now lives in the Philippines with Son Goku and friends."
- If someone asks you to do something outside your scope (e.g. "write a poem"), respond: "Sorry, I can only help with Merchandise Transaction and  TOTAL NET SPENT AND TOTAL SAVED questions."
- Help with: transaction summaries, spending insights, item analysis, business tips."""


# ══════════════════════════════════════════════
#  DATABASE
# ══════════════════════════════════════════════
DB_FILE = "ae_merchandise.db"

def get_conn():
    # Returns a new SQLite connection to the database file
    return sqlite3.connect(DB_FILE)

def init_db():
    # Initializes the database: creates 'users' and 'transactions' tables if they don't exist
    conn = get_conn()
    c = conn.cursor()
    c.execute("""CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        fullname TEXT NOT NULL,
        created  TEXT DEFAULT (datetime('now','localtime'))
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS transactions (
        id         INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id    INTEGER NOT NULL,
        item       TEXT NOT NULL,
        ptype      TEXT NOT NULL,
        qty        INTEGER NOT NULL,
        unit_price REAL NOT NULL,
        gross      REAL NOT NULL,
        net        REAL NOT NULL,
        discount   INTEGER NOT NULL,
        date       TEXT DEFAULT (datetime('now','localtime')),
        FOREIGN KEY(user_id) REFERENCES users(id)
    )""")
    conn.commit(); conn.close()

def hash_pw(p):
    # Hashes the password using SHA-256 for secure storage (never stored as plain text)
    return hashlib.sha256(p.encode()).hexdigest()

# ──────────────────────────────────────────────
# TRY / EXCEPT — Exception Handling
# ──────────────────────────────────────────────
# try: attempts the risky operation (INSERT into database)
# except sqlite3.IntegrityError: catches duplicate username errors (UNIQUE constraint)
# except Exception as e: catches any other unexpected error and returns its message
def db_create_user(username, password, fullname):
    try:
        # Attempts to insert a new user into the database
        conn = get_conn()
        # .lower() — Casing: converts username to lowercase before saving
        # This ensures "Juan" and "juan" are treated as the same username
        conn.execute("INSERT INTO users (username,password,fullname) VALUES (?,?,?)",
                     (username.lower(), hash_pw(password), fullname))
        conn.commit(); conn.close()
        return True, "Account created successfully!"
    except sqlite3.IntegrityError:
        # Catches the case where the username already exists in the database
        return False, "Username already exists."
    except Exception as e:
        # Catches any other unexpected database error and returns its message
        return False, str(e)

def db_login(username, password):
    conn = get_conn(); c = conn.cursor()
    # .lower() — Casing: converts username to lowercase before querying
    # This makes login case-insensitive (e.g., "JUAN" matches stored "juan")
    c.execute("SELECT id,fullname FROM users WHERE username=? AND password=?",
              (username.lower(), hash_pw(password)))
    r = c.fetchone(); conn.close()
    # IF / ELSE — checks if the query returned a result
    # If r is not None (user found), return the user's id and fullname
    # Otherwise return (None, None) indicating login failure
    return (r[0], r[1]) if r else (None, None)

def db_update_pw(user_id, new_pw):
    # Updates the password for the given user_id in the database
    conn = get_conn()
    conn.execute("UPDATE users SET password=? WHERE id=?", (hash_pw(new_pw), user_id))
    conn.commit(); conn.close()

def db_update_name(user_id, name):
    # Updates the fullname for the given user_id in the database
    conn = get_conn()
    conn.execute("UPDATE users SET fullname=? WHERE id=?", (name, user_id))
    conn.commit(); conn.close()

def db_verify_pw(user_id, pw):
    # Returns True if the given password matches the stored hash for this user
    conn = get_conn(); c = conn.cursor()
    c.execute("SELECT id FROM users WHERE id=? AND password=?", (user_id, hash_pw(pw)))
    r = c.fetchone(); conn.close()
    return r is not None

def db_save_txn(user_id, item, ptype, qty, price, gross, net, disc):
    # Inserts a new transaction record into the database
    conn = get_conn()
    conn.execute("""INSERT INTO transactions
        (user_id,item,ptype,qty,unit_price,gross,net,discount)
        VALUES (?,?,?,?,?,?,?,?)""",
        (user_id, item, ptype, qty, price, gross, net, disc))
    conn.commit(); conn.close()

def db_get_txns(user_id):
    # Retrieves all transactions for the given user, ordered newest first
    conn = get_conn(); c = conn.cursor()
    c.execute("""SELECT id,item,ptype,qty,unit_price,gross,net,discount,date
                 FROM transactions WHERE user_id=? ORDER BY id DESC""", (user_id,))
    r = c.fetchall(); conn.close()
    return r

def db_delete_txn(txn_id, user_id):
    # Deletes a specific transaction by its id and user_id (prevents deleting others' data)
    conn = get_conn()
    conn.execute("DELETE FROM transactions WHERE id=? AND user_id=?", (txn_id, user_id))
    conn.commit(); conn.close()

def db_edit_txn(txn_id, user_id, item, ptype, qty, price, gross, net, disc):
    # Updates an existing transaction with new values
    conn = get_conn()
    conn.execute("""UPDATE transactions SET item=?,ptype=?,qty=?,unit_price=?,
        gross=?,net=?,discount=? WHERE id=? AND user_id=?""",
        (item, ptype, qty, price, gross, net, disc, txn_id, user_id))
    conn.commit(); conn.close()

def calculate(qty, unit_price, ptype):
    # Calculates gross, net, and discount for a transaction
    gross = qty * unit_price

    # IF / ELSE — checks if a bulk discount should be applied
    # Condition: purchase type is "bulk" AND quantity exceeds 20 units
    # If TRUE: 15% discount is applied; otherwise discount is 0
    disc  = 15 if ptype == "bulk" and qty > 20 else 0

    net   = gross * (1 - disc / 100)
    return gross, net, disc

# ══════════════════════════════════════════════
#  CUSTOM WIDGETS
# ══════════════════════════════════════════════
class StyledButton(tk.Button):
    def __init__(self, parent, text="", color=None, hover_color=None,
                 fg=None, command=None, **kwargs):
        self._bg    = color or C["gold"]
        self._hover = hover_color or C["gold_dim"]
        self._fg    = fg or C["bg"]
        super().__init__(parent, text=text, bg=self._bg, fg=self._fg,
                         activebackground=self._hover, activeforeground=self._fg,
                         relief="flat", cursor="hand2", font=FONT_SUB,
                         padx=18, pady=8, command=command, **kwargs)
        self.bind("<Enter>", lambda e: self.config(bg=self._hover))
        self.bind("<Leave>", lambda e: self.config(bg=self._bg))

class IconButton(tk.Button):
    def __init__(self, parent, text="", color=None, hover_color=None,
                 fg=None, command=None, **kwargs):
        self._bg    = color or C["card"]
        self._hover = hover_color or C["border"]
        self._fg    = fg or C["white"]
        super().__init__(parent, text=text, bg=self._bg, fg=self._fg,
                         activebackground=self._hover, activeforeground=self._fg,
                         relief="flat", cursor="hand2", font=FONT_BODY,
                         padx=10, pady=6, command=command, **kwargs)
        self.bind("<Enter>", lambda e: self.config(bg=self._hover))
        self.bind("<Leave>", lambda e: self.config(bg=self._bg))

class StyledEntry(tk.Frame):
    def __init__(self, parent, placeholder="", show="", **kwargs):
        super().__init__(parent, bg=C["card"], highlightbackground=C["border"],
                         highlightthickness=1, **kwargs)
        self._ph    = placeholder
        self._show  = show
        self._focus = False
        self.var = tk.StringVar()
        self._entry = tk.Entry(self, textvariable=self.var,
                               bg=C["card"], fg=C["gray"],
                               insertbackground=C["gold"],
                               relief="flat", font=FONT_BODY,
                               show=show if show else "")
        self._entry.pack(fill="x", padx=10, pady=8)
        self._set_placeholder()
        self._entry.bind("<FocusIn>",  self._on_in)
        self._entry.bind("<FocusOut>", self._on_out)

    def _set_placeholder(self):
        # IF / ELSE — if the entry is empty, show the placeholder text in gray
        if not self.var.get():
            self._entry.config(fg=C["gray"])
            self.var.set(self._ph)
            self._is_ph = True
        else:
            self._is_ph = False

    def _on_in(self, e):
        # Called when the user clicks into the entry field (focus in)
        self.config(highlightbackground=C["gold"])
        # IF — clears the placeholder text when user starts typing
        if getattr(self, "_is_ph", False):
            self.var.set("")
            self._entry.config(fg=C["white"],
                               show=self._show if self._show else "")
            self._is_ph = False

    def _on_out(self, e):
        # Called when the user leaves the entry field (focus out)
        self.config(highlightbackground=C["border"])
        # IF — restores placeholder if the field was left empty
        if not self.var.get():
            self._entry.config(show="", fg=C["gray"])
            self.var.set(self._ph)
            self._is_ph = True

    def get(self):
        # Returns empty string if placeholder is active, otherwise returns the real value
        return "" if getattr(self, "_is_ph", False) else self.var.get()

    def set(self, val):
        # Sets the entry value and removes the placeholder state
        self._is_ph = False
        self.var.set(val)
        self._entry.config(fg=C["white"],
                           show=self._show if self._show else "")

    def clear(self):
        # Clears the entry and restores the placeholder
        self.var.set("")
        self._set_placeholder()

# ══════════════════════════════════════════════
#  NOTIFICATION TOAST
# ══════════════════════════════════════════════
class Toast:
    def __init__(self, root):
        self.root = root
        self._lbl = None
        self._after_id = None

    def show(self, msg, kind="success"):
        # Destroys any existing toast before showing a new one
        if self._lbl:
            self._lbl.destroy()
        if self._after_id:
            self.root.after_cancel(self._after_id)

        # IF / ELSE — picks the background color based on the notification kind
        # "success" → green, "error" → red, anything else (e.g. "warn") → orange
        bg = C["green"] if kind == "success" else C["red"] if kind == "error" else C["orange"]

        self._lbl = tk.Label(self.root, text=f"  {msg}  ", bg=bg,
                             fg=C["bg"], font=FONT_SUB, pady=6)
        self._lbl.place(relx=0.5, rely=0.97, anchor="s")
        # Auto-hide the toast after 2800 milliseconds
        self._after_id = self.root.after(2800, self._hide)

    def _hide(self):
        # IF — only destroys the label if it still exists
        if self._lbl:
            self._lbl.destroy()
            self._lbl = None

# ══════════════════════════════════════════════
#  MAIN APPLICATION
# ══════════════════════════════════════════════
class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("AE General Merchandise System  v4")
        self.geometry("1050x680")
        self.minsize(900, 600)
        self.configure(bg=C["bg"])
        self.resizable(True, True)

        # Center window on the screen using screen dimensions
        self.update_idletasks()
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        x  = (sw - 1050) // 2
        y  = (sh - 680)  // 2
        self.geometry(f"1050x680+{x}+{y}")

        init_db()

        self.user_id  = None
        self.fullname = None
        self.toast    = Toast(self)

        self._frames = {}
        self._build_auth()

    # ── helpers ────────────────────────────────
    def label(self, parent, text, font=FONT_BODY, fg=None, bg=None, **kw):
        return tk.Label(parent, text=text, font=font,
                        fg=fg or C["text"], bg=bg or C["bg"], **kw)

    def sep(self, parent, bg=None):
        return tk.Frame(parent, bg=bg or C["border"], height=1)

    # ══════════════════════════════════════════
    #  AUTH SCREEN
    # ══════════════════════════════════════════
    def _build_auth(self):
        # Clear all existing widgets from the window before building the auth screen
        for w in self.winfo_children():
            w.destroy()
        self._frames = {}

        root_f = tk.Frame(self, bg=C["bg"])
        root_f.pack(fill="both", expand=True)

        # Left decorative panel
        left = tk.Frame(root_f, bg=C["sidebar"], width=320)
        left.pack(side="left", fill="y")
        left.pack_propagate(False)

        tk.Label(left, text="✦", font=("Segoe UI", 48), bg=C["sidebar"],
                 fg=C["gold"]).pack(pady=(80, 10))
        tk.Label(left, text="AE General\nMerchandise", font=("Segoe UI", 20, "bold"),
                 bg=C["sidebar"], fg=C["white"], justify="center").pack()
        tk.Label(left, text="Store System  v4", font=FONT_SMALL,
                 bg=C["sidebar"], fg=C["gray"]).pack(pady=(4, 40))

        self.sep(left, C["border"]).pack(fill="x", padx=30)
        tk.Label(left, text="Bulk & Retail Purchase\nCalculator",
                 font=FONT_BODY, bg=C["sidebar"], fg=C["gray"],
                 justify="center").pack(pady=20)

        devs = ["Geronimo, Christian Angel M.",
                "Caliwag, Rommel",
                "Mendoza, Francis",
                "Morales, Kurt Lawrence",
                "Orbita, Andrew Brent"]
        tk.Label(left, text="Developed by:", font=FONT_SMALL,
                 bg=C["sidebar"], fg=C["gold"]).pack(pady=(30, 4))

        # ──────────────────────────────────────
        # FOR LOOP — iterates over the list of developer names
        # Each name is displayed as a bullet point label on the left sidebar
        # ──────────────────────────────────────
        for d in devs:
            tk.Label(left, text=f"• {d}", font=FONT_SMALL,
                     bg=C["sidebar"], fg=C["gray"]).pack()

        # Right: card area
        right = tk.Frame(root_f, bg=C["bg"])
        right.pack(side="left", fill="both", expand=True)

        card = tk.Frame(right, bg=C["surface"],
                        highlightbackground=C["border"], highlightthickness=1)
        card.place(relx=0.5, rely=0.5, anchor="center", width=400)

        # Tabs (Login / Register)
        self._auth_tab = tk.StringVar(value="login")
        tab_bar = tk.Frame(card, bg=C["card"])
        tab_bar.pack(fill="x")
        self._tab_btns = {}

        # FOR LOOP — iterates over tab definitions to build Login and Register buttons
        for key, lbl in [("login", "Login"), ("register", "Register")]:
            b = tk.Button(tab_bar, text=lbl, font=FONT_SUB, relief="flat",
                          cursor="hand2", padx=20, pady=10,
                          command=lambda k=key: self._switch_auth_tab(k))
            b.pack(side="left", fill="x", expand=True)
            self._tab_btns[key] = b
        self._auth_body = tk.Frame(card, bg=C["surface"])
        self._auth_body.pack(fill="both", padx=30, pady=20)

        self._build_login_form()
        self._highlight_tab("login")

    def _highlight_tab(self, active):
        # FOR LOOP — iterates over all tab buttons to update their highlight state
        # The active tab gets a gold background; inactive tabs get the card color
        for k, b in self._tab_btns.items():
            # IF / ELSE — checks if the current tab key matches the active tab
            if k == active:
                b.config(bg=C["gold"], fg=C["bg"])
            else:
                b.config(bg=C["card"], fg=C["gray"])

    def _switch_auth_tab(self, tab):
        self._auth_tab.set(tab)
        self._highlight_tab(tab)
        # Clear all current widgets from the auth body before rebuilding
        for w in self._auth_body.winfo_children():
            w.destroy()

        # IF / ELSE — decides which form to build based on the selected tab
        if tab == "login":
            self._build_login_form()
        else:
            self._build_register_form()

    # ── LOGIN FORM ─────────────────────────────
    def _build_login_form(self):
        f = self._auth_body
        tk.Label(f, text="Welcome Back!", font=FONT_HEAD,
                 bg=C["surface"], fg=C["white"]).pack(anchor="w", pady=(0, 4))
        tk.Label(f, text="Sign in to your account", font=FONT_SMALL,
                 bg=C["surface"], fg=C["gray"]).pack(anchor="w", pady=(0, 18))

        tk.Label(f, text="USERNAME", font=FONT_SMALL,
                 bg=C["surface"], fg=C["cyan"]).pack(anchor="w")
        self._l_user = StyledEntry(f, placeholder="Enter username")
        self._l_user.pack(fill="x", pady=(2, 12))

        tk.Label(f, text="PASSWORD", font=FONT_SMALL,
                 bg=C["surface"], fg=C["cyan"]).pack(anchor="w")
        self._l_pw = StyledEntry(f, placeholder="Enter password", show="●")
        self._l_pw.pack(fill="x", pady=(2, 20))

        StyledButton(f, text="Login  →", command=self._do_login).pack(fill="x", pady=(0, 6))
        reg_lbl = tk.Label(f, text="Don't have an account? Register →",
                           font=FONT_SMALL, bg=C["surface"], fg=C["cyan"],
                           cursor="hand2")
        reg_lbl.pack(pady=4)
        reg_lbl.bind("<Button-1>", lambda e: self._switch_auth_tab("register"))
        reg_lbl.bind("<Enter>", lambda e: reg_lbl.config(fg=C["gold"]))
        reg_lbl.bind("<Leave>", lambda e: reg_lbl.config(fg=C["cyan"]))

    def _do_login(self):
        # INPUT (.strip()) — trims whitespace from user-typed username and password
        u = self._l_user.get().strip()
        p = self._l_pw.get().strip()

        # IF / ELSE — validates that both fields are filled before attempting login
        if not u or not p:
            self.toast.show("Fill in all fields.", "error"); return

        uid, name = db_login(u, p)

        # IF / ELSE — checks if login was successful (uid is not None)
        if uid:
            self.user_id  = uid
            self.fullname = name
            self.toast.show(f"Welcome back, {name}!", "success")
            self.after(600, self._build_main)
        else:
            self.toast.show("Invalid username or password.", "error")

    # ── REGISTER FORM ──────────────────────────
    def _build_register_form(self):
        f = self._auth_body
        tk.Label(f, text="Create Account", font=FONT_HEAD,
                 bg=C["surface"], fg=C["white"]).pack(anchor="w", pady=(0, 4))
        tk.Label(f, text="Fill in your details below", font=FONT_SMALL,
                 bg=C["surface"], fg=C["gray"]).pack(anchor="w", pady=(0, 14))

        tk.Label(f, text="FULL NAME", font=FONT_SMALL,
                 bg=C["surface"], fg=C["cyan"]).pack(anchor="w")
        self._r_name = StyledEntry(f, placeholder="e.g. Juan Dela Cruz")
        self._r_name.pack(fill="x", pady=(2, 10))

        tk.Label(f, text="USERNAME", font=FONT_SMALL,
                 bg=C["surface"], fg=C["cyan"]).pack(anchor="w")
        self._r_user = StyledEntry(f, placeholder="Alphanumeric, min 3 chars")
        self._r_user.pack(fill="x", pady=(2, 10))

        tk.Label(f, text="PASSWORD", font=FONT_SMALL,
                 bg=C["surface"], fg=C["cyan"]).pack(anchor="w")
        self._r_pw = StyledEntry(f, placeholder="Min 4 characters", show="●")
        self._r_pw.pack(fill="x", pady=(2, 10))

        tk.Label(f, text="CONFIRM PASSWORD", font=FONT_SMALL,
                 bg=C["surface"], fg=C["cyan"]).pack(anchor="w")
        self._r_pw2 = StyledEntry(f, placeholder="Repeat password", show="●")
        self._r_pw2.pack(fill="x", pady=(2, 18))

        StyledButton(f, text="Create Account", command=self._do_register).pack(fill="x")

    def _do_register(self):
        # INPUT — retrieves and strips whitespace from all registration fields
        name = self._r_name.get().strip()
        user = self._r_user.get().strip()
        pw   = self._r_pw.get().strip()
        pw2  = self._r_pw2.get().strip()

        # IF — checks that none of the fields are empty using all()
        if not all([name, user, pw, pw2]):
            self.toast.show("Fill in all fields.", "error"); return

        # INPUT VALIDATION (.isalpha()) — checks that the full name contains only letters
        # .replace(" ", "") removes spaces first so multi-word names like "Juan Cruz" are allowed
        # If name has non-letter characters or is too short, show an error
        if not name.replace(" ", "").isalpha() or len(name) < 2:
            self.toast.show("Full name: letters only, min 2 chars.", "error"); return

        # INPUT VALIDATION (.isalnum()) — checks that the username is alphanumeric only
        # (letters and numbers only — no spaces or special characters allowed)
        if not user.isalnum() or len(user) < 3:
            self.toast.show("Username: alphanumeric, min 3 chars.", "error"); return

        # IF — password length check: must be at least 4 characters
        if len(pw) < 4:
            self.toast.show("Password must be at least 4 chars.", "error"); return

        # IF — checks that both password fields match
        if pw != pw2:
            self.toast.show("Passwords do not match.", "error"); return

        # .title() — Casing: capitalizes the first letter of each word in the full name
        # e.g., "juan dela cruz" becomes "Juan Dela Cruz" before saving to the database
        ok, msg = db_create_user(user, pw, name.title())

        # IF / ELSE — shows success or error toast based on registration result
        if ok:
            self.toast.show(msg, "success")
            self.after(800, lambda: self._switch_auth_tab("login"))
        else:
            self.toast.show(msg, "error")

    # ══════════════════════════════════════════
    #  MAIN APP (Sidebar Layout)
    # ══════════════════════════════════════════
    def _build_main(self):
        for w in self.winfo_children():
            w.destroy()
        self._frames = {}
        self.toast = Toast(self)
        self._last_txn_data = None   # stores (item,ptype,qty,price,gross,net,disc) of last save

        # ── Sidebar ───────────────────────────
        self._sidebar = tk.Frame(self, bg=C["sidebar"], width=210)
        self._sidebar.pack(side="left", fill="y")
        self._sidebar.pack_propagate(False)

        # Logo
        logo_f = tk.Frame(self._sidebar, bg=C["sidebar"])
        logo_f.pack(fill="x", pady=(20, 10), padx=16)
        tk.Label(logo_f, text="✦  AE Merch", font=("Segoe UI", 13, "bold"),
                 bg=C["sidebar"], fg=C["gold"]).pack(anchor="w")
        tk.Label(logo_f, text="General Merchandise v4", font=FONT_SMALL,
                 bg=C["sidebar"], fg=C["gray"]).pack(anchor="w")

        self.sep(self._sidebar, C["border"]).pack(fill="x", padx=16, pady=8)

        # User badge
        ub = tk.Frame(self._sidebar, bg=C["card"],
                      highlightbackground=C["border"], highlightthickness=1)
        ub.pack(fill="x", padx=12, pady=(0, 12))
        tk.Label(ub, text="👤", font=("Segoe UI", 18), bg=C["card"]).pack(pady=(8, 0))
        self._name_lbl = tk.Label(ub, text=self.fullname,
                                  font=("Segoe UI", 10, "bold"),
                                  bg=C["card"], fg=C["white"],
                                  wraplength=160)
        self._name_lbl.pack(pady=(2, 8))

        self.sep(self._sidebar, C["border"]).pack(fill="x", padx=16, pady=4)

        # Nav items
        nav_items = [
            ("dashboard",   "📊  Dashboard"),
            ("transaction", "🛒  New Transaction"),
            ("history",     "📋  History"),
            ("settings",    "⚙️   Account Settings"),
            ("ai_chat",     "🤖  AI Chat"),
        ]
        self._nav_btns = {}

        # FOR LOOP — iterates over nav_items to build each sidebar navigation button
        # Each iteration creates one button and stores it in self._nav_btns by key
        for key, label in nav_items:
            b = tk.Button(self._sidebar, text=label, font=FONT_BODY,
                          bg=C["sidebar"], fg=C["gray"], relief="flat",
                          anchor="w", padx=20, pady=10, cursor="hand2",
                          command=lambda k=key: self._show_page(k))
            b.pack(fill="x")
            b.bind("<Enter>", lambda e, btn=b: btn.config(bg=C["card"]) if btn["fg"] != C["gold"] else None)
            b.bind("<Leave>", lambda e, btn=b: btn.config(bg=C["sidebar"]) if btn["fg"] != C["gold"] else None)
            self._nav_btns[key] = b

        # Logout
        self.sep(self._sidebar, C["border"]).pack(fill="x", padx=16, pady=8, side="bottom")
        tk.Button(self._sidebar, text="⏻  Logout", font=FONT_BODY,
                  bg=C["sidebar"], fg=C["red"], relief="flat",
                  anchor="w", padx=20, pady=10, cursor="hand2",
                  command=self._logout).pack(side="bottom", fill="x")

        # ── Content area ──────────────────────
        self._content = tk.Frame(self, bg=C["bg"])
        self._content.pack(side="left", fill="both", expand=True)

        self._pages = {}
        self._active_page = None

        self._build_all_pages()
        self._show_page("dashboard")

    def _show_page(self, key):
        # IF — hides the currently active page before switching
        if self._active_page:
            self._pages[self._active_page].pack_forget()

        # FOR LOOP — resets all nav button colors to their default (inactive) state
        for k, b in self._nav_btns.items():
            b.config(bg=C["sidebar"], fg=C["gray"])

        # IF — highlights the selected nav button in gold if it exists
        if key in self._nav_btns:
            self._nav_btns[key].config(bg=C["card"], fg=C["gold"])

        # IF — refreshes history data whenever the history page is opened
        if key == "history":
            self._refresh_history()

        # IF — refreshes dashboard stats whenever the dashboard page is opened
        if key == "dashboard":
            self._refresh_dashboard()

        self._pages[key].pack(fill="both", expand=True)
        self._active_page = key

    def _page_header(self, parent, title, subtitle=""):
        hf = tk.Frame(parent, bg=C["bg"])
        hf.pack(fill="x", padx=28, pady=(24, 8))
        tk.Label(hf, text=title, font=FONT_TITLE,
                 bg=C["bg"], fg=C["white"]).pack(anchor="w")
        # IF — only renders the subtitle label if a subtitle string was provided
        if subtitle:
            tk.Label(hf, text=subtitle, font=FONT_BODY,
                     bg=C["bg"], fg=C["gray"]).pack(anchor="w", pady=(2, 0))
        self.sep(parent).pack(fill="x", padx=28, pady=(0, 16))

    # ══════════════════════════════════════════
    #  PAGES
    # ══════════════════════════════════════════
    def _build_all_pages(self):
        self._build_dashboard_page()
        self._build_transaction_page()
        self._build_history_page()
        self._build_settings_page()
        self._build_ai_chat_page()

    # ── DASHBOARD ─────────────────────────────
    def _build_dashboard_page(self):
        p = tk.Frame(self._content, bg=C["bg"])
        self._pages["dashboard"] = p

        self._page_header(p, "Dashboard", "Welcome overview of your account")

        outer = tk.Frame(p, bg=C["bg"])
        outer.pack(fill="both", expand=True, padx=28)

        # Stat cards row
        stat_row = tk.Frame(outer, bg=C["bg"])
        stat_row.pack(fill="x", pady=(0, 20))

        self._stat_labels = {}
        stats = [
            ("total_txns",  "Total\nTransactions", "📦", C["cyan"]),
            ("total_spent", "Total\nNet Spent",    "💰", C["gold"]),
            ("bulk_txns",   "Bulk\nTransactions",  "📦", C["orange"]),
            ("saved_amt",   "Total\nSaved",         "🎉", C["green"]),
        ]

        # FOR LOOP — iterates over each stat definition using enumerate()
        # enumerate(stats) gives (index, value) so we get both i and the tuple
        # Each iteration builds one stat card on the dashboard
        for i, (key, label, icon, color) in enumerate(stats):
            card = tk.Frame(stat_row, bg=C["card"],
                            highlightbackground=C["border"], highlightthickness=1)
            card.grid(row=0, column=i, padx=6, sticky="ew")
            stat_row.columnconfigure(i, weight=1)
            tk.Label(card, text=icon, font=("Segoe UI", 22),
                     bg=C["card"]).pack(pady=(14, 2))
            val_lbl = tk.Label(card, text="—", font=("Segoe UI", 16, "bold"),
                               bg=C["card"], fg=color)
            val_lbl.pack()
            tk.Label(card, text=label, font=FONT_SMALL,
                     bg=C["card"], fg=C["gray"], justify="center").pack(pady=(2, 14))
            self._stat_labels[key] = val_lbl

        # Recent transactions
        tk.Label(outer, text="Recent Transactions", font=FONT_SUB,
                 bg=C["bg"], fg=C["white"]).pack(anchor="w", pady=(0, 8))

        self._dash_tree_frame = tk.Frame(outer, bg=C["bg"])
        self._dash_tree_frame.pack(fill="both", expand=True)
        self._build_dash_tree()

    def _build_dash_tree(self):
        for w in self._dash_tree_frame.winfo_children():
            w.destroy()
        style = ttk.Style()
        style.theme_use("default")
        style.configure("Dash.Treeview",
                        background=C["card"],
                        foreground=C["text"],
                        rowheight=30,
                        fieldbackground=C["card"],
                        borderwidth=0,
                        font=FONT_BODY)
        style.configure("Dash.Treeview.Heading",
                        background=C["surface"],
                        foreground=C["gold"],
                        font=FONT_SUB, relief="flat")
        style.map("Dash.Treeview", background=[("selected", C["border"])])

        cols = ("Item", "Type", "Qty", "Unit Price", "Net Total", "Date")
        tree = ttk.Treeview(self._dash_tree_frame, columns=cols,
                            show="headings", style="Dash.Treeview")
        widths = [160, 80, 60, 100, 110, 150]

        # FOR LOOP — iterates over column names paired with widths using zip()
        # zip(cols, widths) combines both lists element by element
        # Each iteration sets the heading text and column width for one column
        for col, w in zip(cols, widths):
            tree.heading(col, text=col)
            tree.column(col, width=w, anchor="center")

        sb = ttk.Scrollbar(self._dash_tree_frame, orient="vertical",
                           command=tree.yview)
        tree.configure(yscroll=sb.set)
        tree.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")
        self._dash_tree = tree

    def _refresh_dashboard(self):
        txns = db_get_txns(self.user_id)
        total_txns  = len(txns)
        total_spent = sum(t[6] for t in txns)

        # FOR LOOP (inside sum()) — counts transactions where purchase type is "bulk"
        # This is a generator expression used inside sum() to count matching rows
        bulk_txns   = sum(1 for t in txns if t[2] == "bulk")
        saved       = sum(t[5] - t[6] for t in txns)

        self._stat_labels["total_txns"].config(text=str(total_txns))
        self._stat_labels["total_spent"].config(text=f"₱{total_spent:,.2f}")
        self._stat_labels["bulk_txns"].config(text=str(bulk_txns))
        self._stat_labels["saved_amt"].config(text=f"₱{saved:,.2f}")

        self._dash_tree.delete(*self._dash_tree.get_children())

        # FOR LOOP — iterates over the 10 most recent transactions (txns[:10])
        # Each transaction tuple is unpacked and inserted as a row in the dashboard tree
        for t in txns[:10]:
            self._dash_tree.insert("", "end", values=(
                # .title() — Casing: capitalizes the first letter of each word in the item name
                # e.g., "rice" → "Rice", "cooking oil" → "Cooking Oil"
                t[1].title(),
                # .upper() — Casing: converts purchase type to uppercase for display
                # e.g., "bulk" → "BULK", "retail" → "RETAIL"
                t[2].upper(),
                t[3],
                f"₱{t[4]:,.2f}", f"₱{t[6]:,.2f}", t[8]))

    # ── NEW TRANSACTION ────────────────────────
    def _build_transaction_page(self):
        p = tk.Frame(self._content, bg=C["bg"])
        self._pages["transaction"] = p

        self._page_header(p, "New Transaction", "Record a new purchase")

        scroll_c = tk.Frame(p, bg=C["bg"])
        scroll_c.pack(fill="both", expand=True, padx=28, pady=(0, 20))

        card = tk.Frame(scroll_c, bg=C["surface"],
                        highlightbackground=C["border"], highlightthickness=1)
        card.pack(fill="both", expand=True, pady=4)

        inner = tk.Frame(card, bg=C["surface"])
        inner.pack(padx=30, pady=24, anchor="n", fill="x")

        # Two-column layout
        left_col  = tk.Frame(inner, bg=C["surface"])
        right_col = tk.Frame(inner, bg=C["surface"])
        left_col.grid(row=0, column=0, sticky="nsew", padx=(0, 16))
        right_col.grid(row=0, column=1, sticky="nsew")
        inner.columnconfigure(0, weight=1)
        inner.columnconfigure(1, weight=1)

        # Left: item, type, qty, price
        tk.Label(left_col, text="ITEM NAME", font=FONT_SMALL,
                 bg=C["surface"], fg=C["cyan"]).pack(anchor="w")
        self._t_item = StyledEntry(left_col, placeholder="e.g. Rice, Sugar, Oil…")
        self._t_item.pack(fill="x", pady=(2, 14))

        tk.Label(left_col, text="PURCHASE TYPE", font=FONT_SMALL,
                 bg=C["surface"], fg=C["cyan"]).pack(anchor="w")
        type_f = tk.Frame(left_col, bg=C["surface"])
        type_f.pack(fill="x", pady=(2, 14))
        self._t_ptype = tk.StringVar(value="retail")

        # FOR LOOP — iterates over purchase type options to build radio buttons
        for val, lbl, color in [("retail", "Retail", C["cyan"]), ("bulk", "Bulk", C["orange"])]:
            rb = tk.Radiobutton(type_f, text=lbl, variable=self._t_ptype,
                                value=val, font=FONT_BODY,
                                bg=C["surface"], fg=color,
                                activebackground=C["surface"],
                                selectcolor=C["card"],
                                command=self._update_receipt_preview)
            rb.pack(side="left", padx=(0, 16))

        tk.Label(left_col, text="QUANTITY", font=FONT_SMALL,
                 bg=C["surface"], fg=C["cyan"]).pack(anchor="w")
        self._t_qty = StyledEntry(left_col, placeholder="Whole number e.g. 10")
        self._t_qty.pack(fill="x", pady=(2, 14))

        tk.Label(left_col, text="UNIT PRICE (₱)", font=FONT_SMALL,
                 bg=C["surface"], fg=C["cyan"]).pack(anchor="w")
        self._t_price = StyledEntry(left_col, placeholder="e.g. 25.00")
        self._t_price.pack(fill="x", pady=(2, 14))

        # FOR LOOP — binds the live preview update event to both qty and price fields
        # Whenever a key is released in either entry, the receipt preview refreshes
        for e in [self._t_qty, self._t_price]:
            e._entry.bind("<KeyRelease>", lambda ev: self._update_receipt_preview())

        calc_btn = StyledButton(left_col, text="Calculate & Save  ✔",
                                command=self._do_transaction)
        calc_btn.pack(fill="x", pady=(8, 0))

        # Right: receipt preview
        tk.Label(right_col, text="RECEIPT PREVIEW", font=FONT_SMALL,
                 bg=C["surface"], fg=C["gold"]).pack(anchor="w")
        recv_card = tk.Frame(right_col, bg=C["card"],
                             highlightbackground=C["border"], highlightthickness=1)
        recv_card.pack(fill="both", expand=True, pady=(2, 0))

        self._recv_text = tk.Text(recv_card, bg=C["card"], fg=C["text"],
                                  font=FONT_MONO, relief="flat",
                                  width=28, height=14,
                                  state="disabled", padx=14, pady=12)
        self._recv_text.pack(fill="both", expand=True)
        self._update_receipt_preview()

        # Print button below receipt preview
        tk.Frame(right_col, bg=C["surface"], height=8).pack()
        StyledButton(right_col, text="🖨  Print Last Receipt",
                     color=C["card"], hover_color=C["border"], fg=C["cyan"],
                     command=self._print_last_receipt).pack(fill="x")
        tk.Label(right_col, text="Prints the last successfully saved transaction.",
                 font=FONT_SMALL, bg=C["surface"], fg=C["gray"]).pack(anchor="w", pady=(4, 0))

    def _update_receipt_preview(self, *_):
        item  = self._t_item.get().strip() or "—"
        ptype = self._t_ptype.get()

        # ──────────────────────────────────────
        # TRY / EXCEPT — handles invalid input gracefully in the live preview
        # try: attempts to parse qty and price as numbers and calculate totals
        # except Exception: if anything goes wrong (e.g. empty field, non-number),
        #   shows a placeholder receipt instead of crashing the program
        # ──────────────────────────────────────
        try:
            qty   = int(self._t_qty.get())
            price = float(self._t_price.get())
            # IF — manually raises ValueError if qty or price is non-positive
            if qty <= 0 or price <= 0:
                raise ValueError
            gross, net, disc = calculate(qty, price, ptype)
            saved = gross - net
            lines = [
                "  ┌─────────────────────────┐",
                f"  │  PURCHASE RECEIPT       │",
                "  ├─────────────────────────┤",
                f"  │ Item  : {item[:17]:<17}│",
                # .upper() — Casing: displays purchase type in uppercase on the receipt
                f"  │ Type  : {ptype.upper():<17}│",
                f"  │ Qty   : {str(qty)+'  unit(s)':<17}│",
                f"  │ Price : ₱{price:>14,.2f} │",
                "  ├─────────────────────────┤",
                f"  │ Gross : ₱{gross:>14,.2f} │",
                f"  │ Disc  : {str(disc)+'%':<17}│",
                f"  │ Saved : ₱{saved:>14,.2f} │",
                "  ├─────────────────────────┤",
                f"  │ NET   : ₱{net:>14,.2f} │",
                "  └─────────────────────────┘",
            ]
        except Exception:
            # Shows a default placeholder when the form is incomplete or invalid
            lines = [
                "  ┌─────────────────────────┐",
                "  │  PURCHASE RECEIPT       │",
                "  ├─────────────────────────┤",
                "  │  Fill in the form to    │",
                "  │  see the preview here.  │",
                "  │                         │",
                "  │  Bulk discount: 15% off │",
                "  │  when qty > 20 units.   │",
                "  └─────────────────────────┘",
            ]
        self._recv_text.config(state="normal")
        self._recv_text.delete("1.0", "end")
        self._recv_text.insert("end", "\n".join(lines))
        self._recv_text.config(state="disabled")

    def _do_transaction(self):
        # INPUT — retrieves and strips whitespace from all transaction fields
        item  = self._t_item.get().strip()
        ptype = self._t_ptype.get()
        qty_s = self._t_qty.get().strip()
        pri_s = self._t_price.get().strip()

        # IF — validates that an item name was entered
        if not item:
            self.toast.show("Enter an item name.", "error"); return

        # INPUT VALIDATION (.isalpha()) — checks the item name contains only letters
        # .replace(" ", "") allows multi-word names like "Cooking Oil"
        if not item.replace(" ", "").isalpha():
            self.toast.show("Item name: letters only.", "error"); return

        # INPUT VALIDATION (.isnumeric()) — checks if quantity is a whole number
        # .isnumeric() returns True only if all characters are digits (0–9)
        # Also checks that the value is greater than zero
        if not qty_s.isnumeric() or int(qty_s) <= 0:
            self.toast.show("Enter a valid quantity.", "error"); return

        # ──────────────────────────────────────
        # TRY / EXCEPT — handles invalid unit price input
        # try: attempts to convert the price string to a float
        # except ValueError: fires if the string cannot be converted (e.g., "abc")
        #   and shows an error toast instead of crashing
        # ──────────────────────────────────────
        try:
            price = float(pri_s)
            # IF — also raises ValueError if price is zero or negative
            if price <= 0: raise ValueError
        except ValueError:
            self.toast.show("Enter a valid unit price.", "error"); return

        qty   = int(qty_s)
        gross, net, disc = calculate(qty, price, ptype)

        # .title() — Casing: capitalizes the first letter of each word in item name before saving
        # e.g., "cooking oil" becomes "Cooking Oil" in the database
        db_save_txn(self.user_id, item.title(), ptype, qty, price, gross, net, disc)
        self._last_txn_data = (item.title(), ptype, qty, price, gross, net, disc)
        self.toast.show(f"Transaction saved! Net: ₱{net:,.2f}", "success")
        self._t_item.clear()
        self._t_qty.clear()
        self._t_price.clear()
        self._t_ptype.set("retail")
        self._update_receipt_preview()

    # ── HISTORY ───────────────────────────────
    def _build_history_page(self):
        p = tk.Frame(self._content, bg=C["bg"])
        self._pages["history"] = p

        self._page_header(p, "Transaction History", "View, edit or delete your transactions")

        # Toolbar
        tb = tk.Frame(p, bg=C["bg"])
        tb.pack(fill="x", padx=28, pady=(0, 8))
        self._all_txns  = []
        self._hist_sort = {}

        self._h_search_var = tk.StringVar()
        search_e = tk.Entry(tb, textvariable=self._h_search_var,
                            bg=C["card"], fg=C["white"], insertbackground=C["gold"],
                            relief="flat", font=FONT_BODY,
                            highlightbackground=C["border"], highlightthickness=1,
                            width=28)
        search_e.insert(0, "🔍  Search transactions…")
        search_e.bind("<FocusIn>",  lambda e: search_e.delete(0, "end") if search_e.get().startswith("🔍") else None)
        search_e.pack(side="left", ipady=7, padx=(0, 10))
        self._h_search_var.trace("w", lambda *_: self._filter_history())

        IconButton(tb, text="✏  Edit", color=C["cyan_dim"], fg=C["white"],
                   command=self._edit_selected).pack(side="left", padx=4)
        IconButton(tb, text="🗑  Delete", color="#551111", fg=C["red"],
                   command=self._delete_selected).pack(side="left", padx=4)
        IconButton(tb, text="🖨  Print Receipt", color=C["card"], fg=C["gold"],
                   command=self._print_history_receipt).pack(side="left", padx=4)

        # Treeview
        tree_f = tk.Frame(p, bg=C["bg"])
        tree_f.pack(fill="both", expand=True, padx=28, pady=(0, 20))

        style = ttk.Style()
        style.configure("Hist.Treeview",
                        background=C["card"], foreground=C["text"],
                        rowheight=32, fieldbackground=C["card"],
                        borderwidth=0, font=FONT_BODY)
        style.configure("Hist.Treeview.Heading",
                        background=C["surface"], foreground=C["gold"],
                        font=FONT_SUB, relief="flat")
        style.map("Hist.Treeview", background=[("selected", C["border"])])

        cols = ("#", "Item", "Type", "Qty", "Unit Price", "Gross", "Net Total", "Disc%", "Date")
        self._hist_tree = ttk.Treeview(tree_f, columns=cols,
                                       show="headings", style="Hist.Treeview")
        widths = [40, 140, 70, 50, 100, 110, 110, 60, 150]

        # FOR LOOP — iterates over columns and widths together using zip()
        # Each iteration sets one column heading and width in the history table
        for col, w in zip(cols, widths):
            self._hist_tree.heading(col, text=col,
                                    command=lambda c=col: self._sort_hist(c))
            self._hist_tree.column(col, width=w, anchor="center")

        vsb = ttk.Scrollbar(tree_f, orient="vertical",
                            command=self._hist_tree.yview)
        self._hist_tree.configure(yscroll=vsb.set)
        self._hist_tree.pack(side="left", fill="both", expand=True)
        vsb.pack(side="right", fill="y")

        self._hist_tree.tag_configure("bulk",   foreground=C["orange"])
        self._hist_tree.tag_configure("retail", foreground=C["cyan"])

    def _refresh_history(self):
        # Fetches all transactions from the database and repopulates the history table
        self._all_txns = db_get_txns(self.user_id)
        self._populate_hist(self._all_txns)

    def _populate_hist(self, txns):
        self._hist_tree.delete(*self._hist_tree.get_children())

        # FOR LOOP — iterates over each transaction with enumerate() starting at 1
        # enumerate(txns, 1) gives a row number (i) alongside each transaction tuple (t)
        # Each transaction is inserted as a styled row in the history treeview
        for i, t in enumerate(txns, 1):
            # IF / ELSE — assigns "bulk" or "retail" tag to color-code the row
            tag = "bulk" if t[2] == "bulk" else "retail"
            self._hist_tree.insert("", "end", iid=t[0], tags=(tag,),
                                   values=(i,
                                           # .title() — Casing: formats item name for display
                                           t[1].title(),
                                           # .upper() — Casing: formats purchase type for display
                                           t[2].upper(),
                                           t[3], f"₱{t[4]:,.2f}",
                                           f"₱{t[5]:,.2f}", f"₱{t[6]:,.2f}",
                                           f"{t[7]}%", t[8]))

    def _filter_history(self):
        # INPUT (.lower()) — converts the search query to lowercase for case-insensitive matching
        # This ensures "rice", "Rice", and "RICE" all match the same transactions
        q = self._h_search_var.get().lower().strip()

        # IF / ELSE — if query is empty or still shows the placeholder, show all transactions
        if not q or q.startswith("🔍"):
            self._populate_hist(self._all_txns)
        else:
            # FOR LOOP (list comprehension) — filters transactions where the query matches
            # item name (.lower()) or purchase type (.lower()) contains the search string
            filtered = [t for t in self._all_txns
                        if q in t[1].lower() or q in t[2].lower()]
            self._populate_hist(filtered)

    def _sort_hist(self, col):
        # Toggles sort direction for the clicked column (ascending/descending)
        rev = self._hist_sort.get(col, False)
        self._hist_sort[col] = not rev
        col_map = {"#": 0, "Item": 1, "Type": 2, "Qty": 3,
                   "Unit Price": 4, "Gross": 5, "Net Total": 6, "Disc%": 7, "Date": 8}
        idx = col_map.get(col, 0)
        sorted_txns = sorted(self._all_txns, key=lambda t: t[idx], reverse=rev)
        self._populate_hist(sorted_txns)

    def _get_selected_txn(self):
        sel = self._hist_tree.selection()
        # IF — checks if no row is selected in the history treeview
        if not sel:
            self.toast.show("Select a transaction first.", "warn"); return None
        txn_id = int(sel[0])

        # FOR LOOP — searches through all loaded transactions to find the selected one by id
        for t in self._all_txns:
            if t[0] == txn_id:
                return t
        return None

    def _delete_selected(self):
        t = self._get_selected_txn()
        if not t: return
        # IF — shows confirmation dialog before deleting; only deletes if user confirms
        if messagebox.askyesno("Confirm Delete",
                               f"Delete transaction:\n'{t[1].title()}' — ₱{t[6]:,.2f}?\n\nThis cannot be undone."):
            db_delete_txn(t[0], self.user_id)
            self.toast.show("Transaction deleted.", "success")
            self._refresh_history()

    def _edit_selected(self):
        t = self._get_selected_txn()
        if not t: return
        self._open_edit_dialog(t)

    def _open_edit_dialog(self, t):
        dlg = tk.Toplevel(self)
        dlg.title("Edit Transaction")
        dlg.configure(bg=C["surface"])
        dlg.geometry("420x480")
        dlg.resizable(False, False)
        dlg.grab_set()
        # Center the dialog relative to the main window
        dlg.update_idletasks()
        x = self.winfo_x() + (self.winfo_width()  - 420) // 2
        y = self.winfo_y() + (self.winfo_height() - 480) // 2
        dlg.geometry(f"420x480+{x}+{y}")

        tk.Label(dlg, text="Edit Transaction", font=FONT_HEAD,
                 bg=C["surface"], fg=C["white"]).pack(pady=(20, 4), padx=24, anchor="w")
        tk.Label(dlg, text="Leave a field unchanged to keep its value.",
                 font=FONT_SMALL, bg=C["surface"], fg=C["gray"]).pack(padx=24, anchor="w")

        f = tk.Frame(dlg, bg=C["surface"])
        f.pack(fill="both", padx=24, pady=16)

        fields = {}

        # FOR LOOP — iterates over field definitions to build each edit form row
        # Each iteration creates a label + entry pair for Item, Qty, and Unit Price
        for label, ph, cur in [
            ("Item Name",   t[1].title(), t[1].title()),
            ("Qty",         str(t[3]),    str(t[3])),
            ("Unit Price",  f"{t[4]:.2f}", f"{t[4]:.2f}"),
        ]:
            tk.Label(f, text=label.upper(), font=FONT_SMALL,
                     bg=C["surface"], fg=C["cyan"]).pack(anchor="w")
            e = StyledEntry(f, placeholder=ph)
            e.set(cur)
            e.pack(fill="x", pady=(2, 10))
            fields[label] = e

        tk.Label(f, text="PURCHASE TYPE", font=FONT_SMALL,
                 bg=C["surface"], fg=C["cyan"]).pack(anchor="w")
        ptype_var = tk.StringVar(value=t[2])
        type_f2 = tk.Frame(f, bg=C["surface"])
        type_f2.pack(fill="x", pady=(2, 14))

        # FOR LOOP — builds the purchase type radio buttons inside the edit dialog
        for val, lbl, color in [("retail", "Retail", C["cyan"]), ("bulk", "Bulk", C["orange"])]:
            tk.Radiobutton(type_f2, text=lbl, variable=ptype_var, value=val,
                           font=FONT_BODY, bg=C["surface"], fg=color,
                           activebackground=C["surface"],
                           selectcolor=C["card"]).pack(side="left", padx=(0, 16))

        def save():
            item_v  = fields["Item Name"].get().strip() or t[1]
            qty_s   = fields["Qty"].get().strip()
            price_s = fields["Unit Price"].get().strip()
            ptype_v = ptype_var.get()

            # INPUT VALIDATION (.isalpha()) — validates item name contains only letters
            if not item_v.replace(" ", "").isalpha():
                messagebox.showerror("Error", "Item name: letters only.", parent=dlg); return

            # ──────────────────────────────────────
            # TRY / EXCEPT — handles invalid quantity input in the edit dialog
            # try: attempts to convert qty to int and check it's positive
            # except ValueError: shows an error dialog if conversion fails
            # ──────────────────────────────────────
            try:
                qty_v = int(qty_s)
                if qty_v <= 0: raise ValueError
            except ValueError:
                messagebox.showerror("Error", "Quantity must be a positive whole number.", parent=dlg); return

            # ──────────────────────────────────────
            # TRY / EXCEPT — handles invalid unit price input in the edit dialog
            # try: attempts to convert price to float and check it's positive
            # except ValueError: shows an error dialog if the value is invalid
            # ──────────────────────────────────────
            try:
                price_v = float(price_s)
                if price_v <= 0: raise ValueError
            except ValueError:
                messagebox.showerror("Error", "Unit price must be a positive number.", parent=dlg); return

            gross_v, net_v, disc_v = calculate(qty_v, price_v, ptype_v)
            # .title() — Casing: capitalizes item name before saving the edit
            db_edit_txn(t[0], self.user_id, item_v.title(), ptype_v,
                        qty_v, price_v, gross_v, net_v, disc_v)
            self.toast.show("Transaction updated!", "success")
            self._refresh_history()
            dlg.destroy()

        btn_row = tk.Frame(dlg, bg=C["surface"])
        btn_row.pack(fill="x", padx=24, pady=(0, 20))
        StyledButton(btn_row, text="Save Changes", command=save).pack(side="left", padx=(0, 8))
        IconButton(btn_row, text="Cancel", command=dlg.destroy,
                   color=C["card"], fg=C["gray"]).pack(side="left")

    # ── ACCOUNT SETTINGS ──────────────────────
    def _build_settings_page(self):
        p = tk.Frame(self._content, bg=C["bg"])
        self._pages["settings"] = p

        self._page_header(p, "Account Settings", "Update your profile and password")

        outer = tk.Frame(p, bg=C["bg"])
        outer.pack(fill="both", expand=True, padx=28, pady=(0, 20))

        # Change name card
        nc = tk.Frame(outer, bg=C["surface"],
                      highlightbackground=C["border"], highlightthickness=1)
        nc.pack(fill="x", pady=(0, 16))
        nci = tk.Frame(nc, bg=C["surface"])
        nci.pack(fill="x", padx=24, pady=18)

        tk.Label(nci, text="Change Full Name", font=FONT_SUB,
                 bg=C["surface"], fg=C["white"]).pack(anchor="w", pady=(0, 4))
        tk.Label(nci, text="NEW FULL NAME", font=FONT_SMALL,
                 bg=C["surface"], fg=C["cyan"]).pack(anchor="w")
        self._s_name = StyledEntry(nci, placeholder="Enter new full name")
        self._s_name.pack(fill="x", pady=(2, 10))
        StyledButton(nci, text="Update Name",
                     command=self._do_update_name).pack(anchor="w")

        # Change password card
        pc = tk.Frame(outer, bg=C["surface"],
                      highlightbackground=C["border"], highlightthickness=1)
        pc.pack(fill="x")
        pci = tk.Frame(pc, bg=C["surface"])
        pci.pack(fill="x", padx=24, pady=18)

        tk.Label(pci, text="Change Password", font=FONT_SUB,
                 bg=C["surface"], fg=C["white"]).pack(anchor="w", pady=(0, 4))

        row_f = tk.Frame(pci, bg=C["surface"])
        row_f.pack(fill="x")

        # FOR LOOP — iterates over password field definitions to build each field column
        # Each iteration creates a label and password entry for Current, New, and Confirm PW
        for i, (attr, lbl, ph) in enumerate([
            ("_s_old_pw", "CURRENT PASSWORD",  "Enter current password"),
            ("_s_new_pw", "NEW PASSWORD",       "Min 4 characters"),
            ("_s_cnf_pw", "CONFIRM PASSWORD",   "Repeat new password"),
        ]):
            col = tk.Frame(row_f, bg=C["surface"])
            col.grid(row=0, column=i, padx=(0 if i == 0 else 12, 0), sticky="ew")
            row_f.columnconfigure(i, weight=1)
            tk.Label(col, text=lbl, font=FONT_SMALL,
                     bg=C["surface"], fg=C["cyan"]).pack(anchor="w")
            e = StyledEntry(col, placeholder=ph, show="●")
            e.pack(fill="x", pady=(2, 0))
            setattr(self, attr, e)

        StyledButton(pci, text="Change Password",
                     command=self._do_change_pw).pack(anchor="w", pady=(14, 0))

    def _do_update_name(self):
        name = self._s_name.get().strip()
        # IF — validates that the name field is not empty
        if not name:
            self.toast.show("Enter a new name.", "error"); return

        # INPUT VALIDATION (.isalpha()) — ensures name contains only letters and spaces
        if not name.replace(" ", "").isalpha() or len(name) < 2:
            self.toast.show("Letters only, at least 2 chars.", "error"); return

        # .title() — Casing: capitalizes each word in the name before saving
        # e.g., "juan dela cruz" → "Juan Dela Cruz"
        name = name.title()
        db_update_name(self.user_id, name)
        self.fullname = name
        self._name_lbl.config(text=name)
        self._s_name.clear()
        self.toast.show(f"Name updated to: {name}", "success")

    def _do_change_pw(self):
        old = self._s_old_pw.get().strip()
        new = self._s_new_pw.get().strip()
        cnf = self._s_cnf_pw.get().strip()

        # IF — validates that all three password fields are filled
        if not all([old, new, cnf]):
            self.toast.show("Fill in all password fields.", "error"); return

        # IF — verifies the current password against the stored hash
        if not db_verify_pw(self.user_id, old):
            self.toast.show("Current password is incorrect.", "error"); return

        # IF — enforces minimum length for the new password
        if len(new) < 4:
            self.toast.show("New password: min 4 characters.", "error"); return

        # IF — ensures new password and confirmation match
        if new != cnf:
            self.toast.show("Passwords do not match.", "error"); return

        db_update_pw(self.user_id, new)

        # FOR LOOP — iterates over all three password entry fields to clear them after success
        for e in [self._s_old_pw, self._s_new_pw, self._s_cnf_pw]:
            e.clear()
        self.toast.show("Password changed successfully!", "success")

    # ── LOGOUT ────────────────────────────────
    def _logout(self):
        # IF — shows confirmation dialog and only logs out if the user clicks Yes
        if messagebox.askyesno("Logout", f"Logout from {self.fullname}'s account?"):
            self.user_id  = None
            self.fullname = None
            self._build_auth()

    # ══════════════════════════════════════════
    #  PRINT RECEIPT
    # ══════════════════════════════════════════
    def _format_receipt_text(self, item, ptype, qty, price,
                              gross, net, disc, date="", txn_id=""):
        saved     = gross - net
        date_str  = date or datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # IF / ELSE — builds the discount line based on whether a discount was applied
        if disc > 0:
            disc_line = f"{disc}% OFF  (-₱{saved:,.2f})"
        elif ptype == "bulk":
            # ELSE IF — bulk type but no discount (qty ≤ 20)
            disc_line = "None  (buy >20 units for 15% off)"
        else:
            disc_line = "None  (Retail)"

        w = 46
        def center(s): return s.center(w)
        def row(label, value):
            gap = w - 2 - len(label) - len(value)
            return f" {label}{' '*gap}{value}"

        lines = [
            "=" * w,
            center("AE GENERAL MERCHANDISE STORE"),
            center("Bulk & Retail Purchase System"),
            "=" * w,
            row("Receipt #:", str(txn_id) if txn_id else "N/A"),
            row("Date     :", date_str),
            row("Customer :", self.fullname),
            "-" * w,
            row("Item     :", item),
            # .upper() — Casing: displays purchase type in uppercase on the printed receipt
            row("Type     :", ptype.upper()),
            row("Quantity :", f"{qty} unit(s)"),
            row("Unit Price:", f"₱{price:,.2f}"),
            "-" * w,
            row("Gross Total:", f"₱{gross:,.2f}"),
            row("Discount   :", disc_line),
            row("NET TOTAL  :", f"₱{net:,.2f}"),
            "=" * w,
            center("Thank you for shopping at AE Merch!"),
            center("See you next time!  Stay awesome!"),
            "=" * w,
        ]
        return "\n".join(lines)

    def _open_print_preview(self, item, ptype, qty, price,
                             gross, net, disc, date="", txn_id=""):
        dlg = tk.Toplevel(self)
        dlg.title("Print Receipt Preview")
        dlg.configure(bg=C["surface"])
        dlg.geometry("560x560")
        dlg.resizable(False, False)
        dlg.grab_set()
        x = self.winfo_x() + (self.winfo_width()  - 560) // 2
        y = self.winfo_y() + (self.winfo_height() - 560) // 2
        dlg.geometry(f"560x560+{x}+{y}")

        # Header
        hf = tk.Frame(dlg, bg=C["surface"])
        hf.pack(fill="x", padx=22, pady=(18, 6))
        tk.Label(hf, text="🖨  Print Receipt Preview", font=FONT_HEAD,
                 bg=C["surface"], fg=C["white"]).pack(anchor="w")
        tk.Label(hf, text="Review your receipt before printing or saving.",
                 font=FONT_SMALL, bg=C["surface"], fg=C["gray"]).pack(anchor="w")

        # Receipt box
        recv_f = tk.Frame(dlg, bg=C["card"],
                          highlightbackground=C["gold"], highlightthickness=1)
        recv_f.pack(fill="both", expand=True, padx=22, pady=8)
        txt = tk.Text(recv_f, bg=C["card"], fg=C["green"],
                      font=("Consolas", 10), relief="flat",
                      padx=14, pady=12, state="normal", wrap="none")
        sb = ttk.Scrollbar(recv_f, orient="vertical", command=txt.yview)
        txt.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        txt.pack(fill="both", expand=True)

        receipt_text = self._format_receipt_text(
            item, ptype, qty, price, gross, net, disc, date, txn_id)
        txt.insert("end", receipt_text)
        txt.config(state="disabled")

        # Buttons
        btn_row = tk.Frame(dlg, bg=C["surface"])
        btn_row.pack(fill="x", padx=22, pady=(0, 18))

        def do_print():
            # ──────────────────────────────────────
            # TRY / EXCEPT — handles errors during the print process
            # try: creates a temp file and sends it to the system printer
            # except Exception as e: catches OS or print errors and shows a dialog
            # ──────────────────────────────────────
            try:
                tmp = tempfile.NamedTemporaryFile(
                    mode="w", suffix=".txt", delete=False,
                    prefix="AE_Receipt_", encoding="utf-8")
                tmp.write(receipt_text)
                tmp.close()
                # os.startfile sends the file to the default printer
                os.startfile(tmp.name, "print")
                self.toast.show("Sent to printer!", "success")
                dlg.destroy()
            except Exception as e:
                messagebox.showerror("Print Error", str(e), parent=dlg)

        def do_save():
            path = filedialog.asksaveasfilename(
                defaultextension=".txt",
                filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
                initialfile=f"AE_Receipt_{item}.txt",
                parent=dlg)
            # IF — only saves if the user selected a file path (didn't cancel)
            if path:
                with open(path, "w", encoding="utf-8") as f:
                    f.write(receipt_text)
                self.toast.show(f"Saved!", "success")

        StyledButton(btn_row, text="🖨  Print",
                     command=do_print).pack(side="left", padx=(0, 8))
        IconButton(btn_row, text="💾  Save as .txt",
                   color=C["card"], fg=C["cyan"],
                   command=do_save).pack(side="left", padx=(0, 8))
        IconButton(btn_row, text="Close",
                   color=C["card"], fg=C["gray"],
                   command=dlg.destroy).pack(side="left")

    def _print_last_receipt(self):
        # IF — checks if there is a last saved transaction to print
        if not self._last_txn_data:
            self.toast.show("No transaction saved yet. Save one first.", "warn")
            return
        item, ptype, qty, price, gross, net, disc = self._last_txn_data
        self._open_print_preview(item, ptype, qty, price, gross, net, disc)

    def _print_history_receipt(self):
        t = self._get_selected_txn()
        if not t:
            return
        # t=(id, item, ptype, qty, unit_price, gross, net, discount, date)
        # .title() — Casing: formats item name for the receipt display
        self._open_print_preview(
            t[1].title(), t[2], t[3], t[4], t[5], t[6], t[7], t[8], str(t[0]))

    # ══════════════════════════════════════════
    #  AI CHAT PAGE
    # ══════════════════════════════════════════
    def _build_ai_chat_page(self):
        p = tk.Frame(self._content, bg=C["bg"])
        self._pages["ai_chat"] = p
        self._ai_messages = []   # list of (role, text)

        # Header
        hf = tk.Frame(p, bg=C["bg"])
        hf.pack(fill="x", padx=28, pady=(24, 6))
        title_row = tk.Frame(hf, bg=C["bg"])
        title_row.pack(fill="x")
        tk.Label(title_row, text="🤖  AE Merch AI",
                 font=FONT_TITLE, bg=C["bg"], fg=C["white"]).pack(side="left")
        tk.Label(title_row, text=" BETA ", font=("Segoe UI", 8, "bold"),
                 bg=C["gold"], fg=C["bg"]).pack(side="left", padx=8, anchor="center")
        tk.Label(hf, text="Ask me anything about your transactions, spending, and more.",
                 font=FONT_BODY, bg=C["bg"], fg=C["gray"]).pack(anchor="w", pady=(2, 0))
        self.sep(p).pack(fill="x", padx=28, pady=(8, 0))

        # Toolbar
        tb = tk.Frame(p, bg=C["bg"])
        tb.pack(fill="x", padx=28, pady=4)
        IconButton(tb, text="🗑  Clear Chat",
                   color=C["card"], fg=C["red"],
                   command=self._ai_clear_chat).pack(side="right")

        # Chat display
        chat_outer = tk.Frame(p, bg=C["surface"],
                              highlightbackground=C["border"], highlightthickness=1)
        chat_outer.pack(fill="both", expand=True, padx=28, pady=(0, 8))

        self._ai_text = tk.Text(
            chat_outer, bg=C["surface"], fg=C["text"],
            font=FONT_BODY, relief="flat", padx=16, pady=12,
            state="disabled", wrap="word", cursor="arrow")
        ai_sb = ttk.Scrollbar(chat_outer, orient="vertical",
                               command=self._ai_text.yview)
        self._ai_text.configure(yscrollcommand=ai_sb.set)
        ai_sb.pack(side="right", fill="y")
        self._ai_text.pack(side="left", fill="both", expand=True)

        # Text tags for styling chat messages
        self._ai_text.tag_configure("you_lbl",    foreground=C["gold"],
                                    font=("Segoe UI", 9, "bold"))
        self._ai_text.tag_configure("you_msg",    foreground=C["white"],
                                    font=FONT_BODY, lmargin1=20, lmargin2=20)
        self._ai_text.tag_configure("you_bold",   foreground=C["white"],
                                    font=("Segoe UI", 10, "bold"), lmargin1=20, lmargin2=20)
        self._ai_text.tag_configure("you_italic", foreground=C["white"],
                                    font=("Segoe UI", 10, "italic"), lmargin1=20, lmargin2=20)
        self._ai_text.tag_configure("ai_lbl",     foreground=C["cyan"],
                                    font=("Segoe UI", 9, "bold"))
        self._ai_text.tag_configure("ai_msg",     foreground=C["text"],
                                    font=FONT_BODY, lmargin1=20, lmargin2=20)
        self._ai_text.tag_configure("ai_bold",    foreground=C["white"],
                                    font=("Segoe UI", 10, "bold"), lmargin1=20, lmargin2=20)
        self._ai_text.tag_configure("ai_italic",  foreground=C["gold"],
                                    font=("Segoe UI", 10, "italic"), lmargin1=20, lmargin2=20)
        self._ai_text.tag_configure("thinking",   foreground=C["gray"],
                                    font=("Segoe UI", 9, "italic"), lmargin1=20)
        self._ai_text.tag_configure("divider",    foreground=C["border"])

        # Welcome message shown when the AI chat page is first opened
        self._ai_append_msg("bot",
            "Hello! I'm AE Merch AI 🤖\n\n"
            "I have access to all your transaction data. You can ask me:\n"
            "  • \"What's my total spending?\"\n"
            "  • \"Summarize my transactions\"\n"
            "  • \"How much did I save from discounts?\"\n"
            "  • \"Which items did I buy in bulk?\"\n\n"
            "How can I help you today?")

        # Input area
        inp_outer = tk.Frame(p, bg=C["surface"],
                             highlightbackground=C["border"], highlightthickness=1)
        inp_outer.pack(fill="x", padx=28, pady=(0, 20))

        self._ai_ph = True
        self._ai_input = tk.Text(inp_outer, bg=C["surface"], fg=C["gray"],
                                 insertbackground=C["gold"], relief="flat",
                                 font=FONT_BODY, height=2, padx=12, pady=10,
                                 wrap="word")
        self._ai_input.insert("1.0", "Type your message…")
        self._ai_input.bind("<FocusIn>",     self._ai_focus_in)
        self._ai_input.bind("<FocusOut>",    self._ai_focus_out)
        self._ai_input.bind("<Return>",      self._ai_enter_key)
        self._ai_input.pack(side="left", fill="both", expand=True)

        self._ai_send_btn = StyledButton(inp_outer, text="Send ➤",
                                         command=self._ai_send)
        self._ai_send_btn.pack(side="right", padx=8, pady=8)

    def _ai_focus_in(self, e):
        # IF — clears the placeholder text when the user clicks into the AI input field
        if self._ai_ph:
            self._ai_input.delete("1.0", "end")
            self._ai_input.config(fg=C["white"])
            self._ai_ph = False

    def _ai_focus_out(self, e):
        # IF — restores the placeholder text if the input field is empty on focus out
        if not self._ai_input.get("1.0", "end-1c").strip():
            self._ai_input.delete("1.0", "end")
            self._ai_input.insert("1.0", "Type your message…")
            self._ai_input.config(fg=C["gray"])
            self._ai_ph = True

    def _ai_enter_key(self, e):
        # IF — sends the message when Enter is pressed without Shift held
        if not (e.state & 0x1):   # Shift not held
            self._ai_send()
            return "break"

    def _ai_insert_formatted(self, text, base_tag):
        """Insert text with **bold** and *italic* markdown rendered as tags."""
        bold_tag   = base_tag + "_bold"
        italic_tag = base_tag + "_italic"
        # Split the text on **bold** and *italic* markdown markers
        segments = re.split(r'(\*\*.*?\*\*|\*.*?\*)', text, flags=re.DOTALL)

        # FOR LOOP — iterates over each text segment after splitting on markdown markers
        # Each segment is inserted into the chat text widget with its appropriate style tag
        for seg in segments:
            # IF / ELSE — checks the segment type to apply the correct formatting
            if seg.startswith("**") and seg.endswith("**") and len(seg) > 4:
                # Bold text: strips the ** markers and inserts with bold tag
                self._ai_text.insert("end", seg[2:-2], bold_tag)
            elif seg.startswith("*") and seg.endswith("*") and len(seg) > 2:
                # Italic text: strips the * markers and inserts with italic tag
                self._ai_text.insert("end", seg[1:-1], italic_tag)
            else:
                # Regular text: inserts with the base tag (no special formatting)
                self._ai_text.insert("end", seg, base_tag)

    def _ai_append_msg(self, role, text):
        self._ai_text.config(state="normal")
        # IF — adds a divider line before each message (except the very first)
        if self._ai_messages:
            self._ai_text.insert("end", "\n", "divider")

        # IF / ELSE — inserts message with different labels depending on role
        # "user" messages show "You" label; bot messages show "AE Merch AI" label
        if role == "user":
            self._ai_text.insert("end", "You\n", "you_lbl")
            self._ai_insert_formatted(text, "you_msg")
            self._ai_text.insert("end", "\n", "you_msg")
        else:
            self._ai_text.insert("end", "AE Merch AI\n", "ai_lbl")
            self._ai_insert_formatted(text, "ai_msg")
            self._ai_text.insert("end", "\n", "ai_msg")

        self._ai_messages.append((role, text))
        self._ai_text.config(state="disabled")
        self._ai_text.see("end")

    def _ai_clear_chat(self):
        # Clears the message history and the chat display widget
        self._ai_messages = []
        self._ai_text.config(state="normal")
        self._ai_text.delete("1.0", "end")
        self._ai_text.config(state="disabled")
        self._ai_append_msg("bot",
            "Chat cleared! I'm AE Merch AI 🤖 — ready to help.\n"
            "Ask me anything about your transactions or spending!")

    def _ai_build_context(self):
        # Builds a context string from the user's transactions to inject into the AI prompt
        txns = db_get_txns(self.user_id)
        ctx  = "\n\n=== USER DATA ==="
        ctx += f"\nName    : {self.fullname}"
        ctx += f"\nTotal Transactions: {len(txns)}"

        # IF — only adds financial totals if there are existing transactions
        if txns:
            t_gross = sum(t[5] for t in txns)
            t_net   = sum(t[6] for t in txns)
            t_saved = t_gross - t_net
            bulk_n  = sum(1 for t in txns if t[2] == "bulk")
            ctx += f"\nTotal Gross  : ₱{t_gross:,.2f}"
            ctx += f"\nTotal Net    : ₱{t_net:,.2f}"
            ctx += f"\nTotal Saved  : ₱{t_saved:,.2f}"
            ctx += f"\nBulk Txns    : {bulk_n}"
            ctx += f"\nRetail Txns  : {len(txns) - bulk_n}"
            ctx += "\n\nTRANSACTIONS (newest first):"

            # FOR LOOP — iterates over all transactions to build the AI context string
            # Each transaction is formatted and appended to the context block
            for t in txns:
                # IF / ELSE — formats the discount label for each transaction
                disc_s = f"{t[7]}% OFF" if t[7] > 0 else "No discount"
                ctx += (f"\n  [{t[8]}] #{t[0]} | "
                        # .title() — Casing: formats item name in the AI context
                        f"{t[1].title()} | "
                        # .upper() — Casing: formats purchase type in the AI context
                        f"{t[2].upper()} | Qty:{t[3]} | "
                        f"₱{t[4]:,.2f}/unit | Net:₱{t[6]:,.2f} | {disc_s}")
        else:
            ctx += "\nNo transactions yet."
        ctx += "\n=== END USER DATA ==="
        return ctx

    def _ai_send(self):
        # IF — prevents sending if the input still shows the placeholder text
        if self._ai_ph:
            return
        raw = self._ai_input.get("1.0", "end-1c").strip()
        # IF — prevents sending an empty message
        if not raw:
            return
        # Clear input
        self._ai_input.delete("1.0", "end")
        self._ai_input.config(fg=C["white"])
        self._ai_send_btn.config(state="disabled", text="...")

        # Add user message to the chat
        self._ai_append_msg("user", raw)

        # Show thinking indicator (not stored in history)
        self._ai_text.config(state="normal")
        self._ai_text.insert("end", "\n", "divider")
        self._ai_text.insert("end", "AE Merch AI\n", "ai_lbl")
        self._ai_text.insert("end", "⏳ Thinking…\n", "thinking")
        think_mark = self._ai_text.index("end-3l linestart")
        self._ai_text.config(state="disabled")
        self._ai_text.see("end")

        # Build API payload with the system prompt and full conversation history
        sys_prompt = AI_SYSTEM + self._ai_build_context()
        api_msgs   = [{"role": "system", "content": sys_prompt}]

        # FOR LOOP — iterates over conversation history to build the API messages array
        # Each past message is added as either "user" or "assistant" role for context
        for r, t in self._ai_messages:
            api_msgs.append({
                "role": "user" if r == "user" else "assistant",
                "content": t })

        def call_api():
            # ──────────────────────────────────────
            # TRY / EXCEPT — handles network and API errors for the AI chat
            # try: sends the HTTP request to the AI API and parses the JSON response
            # except Exception as exc: catches any network, timeout, or parsing errors
            #   and returns a friendly error message to display in the chat
            # ──────────────────────────────────────
            try:
                payload = json.dumps({
                    "model": AI_MODEL, "messages": api_msgs
                }).encode("utf-8")
                req = urllib.request.Request(
                    AI_API_URL, data=payload,
                    headers={
                        "Content-Type": "application/json",
                        "User-Agent": "AEMerchSystem/4.0"
                    })
                with urllib.request.urlopen(req, timeout=30) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                reply = data["choices"][0]["message"]["content"].strip()
                # Clean up markdown artifacts from the AI response
                reply = re.sub(r"<think>[\s\S]*?</think>", "",
                               reply, flags=re.IGNORECASE).strip()
                reply = re.sub(r"^#{1,6}\s+", "", reply, flags=re.MULTILINE)
                reply = re.sub(r"`{1,3}([^`]*)`{1,3}", r"\1", reply)
                reply = re.sub(r"^\s*[-]\s", "• ", reply, flags=re.MULTILINE)
                reply = re.sub(r"\n{3,}", "\n\n", reply).strip()
            except Exception as exc:
                # Returns an error message if the API call fails (e.g., no internet)
                reply = (f"Sorry, I couldn't connect to the AI service. "
                         f"Please check your internet.\n(⚠️ {exc})")
            self.after(0, lambda rep=reply: _finish(rep))

        def _finish(reply):
            # Replaces the "Thinking..." indicator with the actual AI reply
            self._ai_text.config(state="normal")
            self._ai_text.delete(think_mark, "end")
            self._ai_text.config(state="disabled")
            self._ai_append_msg("bot", reply)
            self._ai_send_btn.config(state="normal", text="Send ➤")
            # IF — restores the input placeholder if the field is still empty after sending
            if not self._ai_input.get("1.0", "end-1c").strip():
                self._ai_input.delete("1.0", "end")
                self._ai_input.insert("1.0", "Type your message…")
                self._ai_input.config(fg=C["gray"])
                self._ai_ph = True

        # Runs call_api() in a background thread so the GUI doesn't freeze while waiting
        threading.Thread(target=call_api, daemon=True).start()

# ══════════════════════════════════════════════
#  ENTRY POINT
# ══════════════════════════════════════════════
# NOTE: While loops are not present in this GUI application.
# In a tkinter app, the event loop (app.mainloop()) acts as the program's
# continuous loop — it keeps running and waiting for user events (clicks,
# key presses, etc.) until the window is closed. This replaces the need
# for explicit while loops that are typically used in console-based programs.
# Example of what mainloop() replaces conceptually:
#
#   while app_is_running:       ← this is handled internally by mainloop()
#       check_for_events()
#       process_events()
#       update_screen()

if __name__ == "__main__":
    app = App()
    # mainloop() starts the tkinter event loop — equivalent to a while loop
    # that keeps the window open and responsive until the user closes it
    app.mainloop()
