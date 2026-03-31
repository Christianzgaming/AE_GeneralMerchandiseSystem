# AE General Merchandise System v4

A desktop-based **Bulk & Retail Purchase Tracking System** built with Python and Tkinter, developed as a **CC3 course project** at **Tarlac State University**.

---
## SHOW CASE GDdrive Link: https://drive.google.com/file/d/10LGlEiT2CYV-i0Y6hYkdI2hVlJToElnS/view?usp=drive_link

## 📌 Overview

The AE General Merchandise System is a local desktop application that allows a user to manage and track merchandise purchases. It supports two purchase types — **Retail** and **Bulk** — with automatic discount calculation, a live receipt preview, transaction history management, and an AI-powered chat assistant.

All data is stored locally using a **SQLite database**.

---

## ✨ Features

- **User Authentication** — Register and log in with secure SHA-256 password hashing
- **New Transaction** — Record purchases with item name, type, quantity, and unit price; live receipt preview updates in real time
- **Bulk Discount Logic** — Automatically applies a 15% discount for bulk orders exceeding 20 units
- **Transaction History** — View, search, sort, edit, and delete past transactions
- **Receipt Printing** — Preview and print or save receipts as `.txt` files
- **Account Settings** — Update full name and change password
- **AI Chat Assistant** — Ask questions about your transactions and spending (powered by Pollinations API)

---

## 🖥️ Tech Stack

| Technology | Purpose |
|---|---|
| Python 3 | Core programming language |
| Tkinter / ttk | GUI framework |
| SQLite3 | Local database storage |
| hashlib (SHA-256) | Password hashing |
| threading | Non-blocking AI API calls |
| urllib | HTTP requests to AI API |
| Pollinations API | Free AI chat backend |

---

## 📂 Project Structure

```
ae_merchandise_system/
│
├── AEGMSystem.py   # Main application file
└── ae_merchandise.db                 # Auto-generated SQLite database (on first run)
```

---

## 🚀 How to Run

1. Make sure **Python 3** is installed on your machine.
2. No additional packages are required — all libraries used are part of Python's standard library.
3. Run the application:

```bash
python AEGMSystem.py
```

4. Register an account on the login screen and start recording transactions.

---

## 🧠 Programming Concepts Used

This project demonstrates the following Python concepts:

- **If / Else** — Input validation, login checks, discount logic, UI state management
- **For Loop** — Building UI elements, populating tables, iterating transaction records
- **Try / Except** — Handling invalid inputs, database errors, and network failures gracefully
- **Casing Methods** — `.lower()` for usernames, `.upper()` for display labels, `.title()` for item and full names
- **Input Validation** — `.isalpha()`, `.isnumeric()`, `.isalnum()` for form field checks
- **Event Loop (mainloop)** — Tkinter's built-in loop replaces an explicit while loop in GUI applications

---

## 👨‍💻 Developer

**Christian Angel M. Geronimo**
Student — Tarlac State University
CC3 Project

---

## 📄 License

This project was created for academic purposes as part of a course requirement at Tarlac State University.
