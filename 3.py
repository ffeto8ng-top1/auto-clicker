
import tkinter as tk
from tkinter import ttk, messagebox
from pynput.mouse import Button, Controller

from threading import Thread
import time, json, os
from datetime import datetime

CFG_FILE = "autoclicker_cfg.json"
LOG_FILE = "clicker_log.txt"

class AutoClicker:
    def __init__(self, root):
        self.root = root
        self.root.title("Автокликер PRO")
        self.root.geometry("420x520")
        self.root.resizable(False, False)

        # Цвета
        bg, fg, acc, ok = "#f0f2f5", "#333333", "#3b8ed0", "#2e7d32"
        self.colors = {"bg": bg, "fg": fg, "acc": acc, "ok": ok}
        self.root.configure(bg=bg)

        self.mouse = Controller()
        self.running = False
        self.target_x = self.target_y = None

        # Переменные
        cfg = self.load_config()
        self.interval_var = tk.StringVar(value=cfg.get("interval", "1.0"))
        self.count_var   = tk.StringVar(value=str(cfg.get("max_clicks", 0)))
        self.button_var  = tk.StringVar(value=cfg.get("button", "left"))
        self.mode_var    = tk.StringVar(value=cfg.get("mode", "none"))
        self.threshold_var = tk.StringVar(value=str(cfg.get("threshold", 20)))

        style = ttk.Style()
        style.theme_use("clam")
        style.configure("TLabel", background=bg, foreground=fg)
        style.configure("TLabelframe", background="#ffffff", foreground=fg)
        style.configure("TLabelframe.Label", font=("Segoe UI", 10, "bold"), background="#ffffff")
        style.configure("TButton", padding=6, font=("Segoe UI", 10))
        style.map("TButton", background=[("active", acc)])

        # Заголовок
        tk.Label(root, text="Автокликер PRO", font=("Segoe UI", 18, "bold"),
                 bg=bg, fg=fg).grid(row=0, column=0, columnspan=3, pady=(20,15), sticky="ew")

        # Настройки
        frm = ttk.LabelFrame(root, text="Настройки", padding=15)
        frm.grid(row=1, column=0, columnspan=3, padx=15, pady=5, sticky="ew")
        r = 0
        def add_row(label, var, width=10):
            nonlocal r
            ttk.Label(frm, text=label).grid(row=r, column=0, sticky="w", pady=6)
            ttk.Entry(frm, textvariable=var, width=width).grid(row=r, column=1, pady=6, padx=8, sticky="w")
            r += 1

        add_row("Интервал (сек):", self.interval_var)
        add_row("Макс. кликов (0=без лимита):", self.count_var)

        ttk.Label(frm, text="Кнопка:").grid(row=r, column=0, sticky="w", pady=6)
        cb_btn = ttk.Combobox(frm, textvariable=self.button_var,
                              values=["left","right","middle"], width=9, state="readonly")
        cb_btn.grid(row=r, column=1, pady=6, padx=8, sticky="w"); r += 1

        ttk.Label(frm, text="Режим возврата:").grid(row=r, column=0, sticky="w", pady=6)
        cb_mode = ttk.Combobox(frm, textvariable=self.mode_var,
                               values=["не возвращать","всегда возвращать","возвращать при уходе > порога"],
                               width=28, state="readonly")
        cb_mode.grid(row=r, column=1, pady=6, padx=8, sticky="w"); r += 1
        cb_mode.bind("<<ComboboxSelected>>", self.on_mode_change)

        self.lbl_thresh = ttk.Label(frm, text="Порог (px):")
        self.lbl_thresh.grid(row=r, column=0, sticky="w", pady=6)
        ttk.Entry(frm, textvariable=self.threshold_var, width=10).grid(row=r, column=1, pady=6, padx=8, sticky="w"); r+=1
        self.on_mode_change(None)

        # Позиция
        frm_pos = ttk.LabelFrame(root, text="Позиция клика", padding=12)
        frm_pos.grid(row=2, column=0, columnspan=3, padx=15, pady=10, sticky="ew")
        ttk.Button(frm_pos, text="Выбрать позицию (F10)", command=self.pick_position).pack(pady=4)
        self.pos_label = tk.Label(frm_pos, text="(позиция не задана)", font=("Consolas",10),
                                  bg="#ffffff", fg="#666666", anchor="w")
        self.pos_label.pack(fill="x", pady=(4,0))

        # Статус
        self.status_label = tk.Label(root, text="Статус: остановлен",
                                     font=("Segoe UI",11,"bold"), bg=bg, fg="#666666")
        self.status_label.grid(row=3, column=0, columnspan=3, pady=10)

        # Кнопки управления
        btn_frame = tk.Frame(root, bg=bg)
        btn_frame.grid(row=4, column=0, columnspan=3, pady=10)
        self.btn_start = ttk.Button(btn_frame, text="Старт (F9)", command=self.start_clicker)
        self.btn_start.pack(side="left", padx=8)
        self.btn_stop = ttk.Button(btn_frame, text="Стоп", command=self.stop_clicker, state="disabled")
        self.btn_stop.pack(side="left", padx=8)

        tk.Label(root, text="(3 сек задержка после старта)", font=("Segoe UI",9),
                 bg=bg, fg="#888888").grid(row=5, column=0, columnspan=3, pady=(0,5))

        # Инструменты
        tools = tk.Frame(root, bg=bg)
        tools.grid(row=6, column=0, columnspan=3, padx=15, pady=5, sticky="ew")
        ttk.Button(tools, text="Сохранить профиль", command=self.save_profile).pack(side="left", padx=(0,8))
        ttk.Button(tools, text="Загрузить профиль", command=self.load_profile).pack(side="left", padx=(0,8))

        logs = tk.Frame(root, bg=bg)
        logs.grid(row=7, column=0, columnspan=3, padx=15, pady=10, sticky="ew")
        ttk.Button(logs, text="Открыть лог", command=self.open_log).pack(side="left", padx=(0,8))
        ttk.Button(logs, text="Очистить лог", command=self.clear_log).pack(side="left")

        # Горячие клавиши
        root.bind("<F9>", lambda e: self.toggle_start())
        root.bind("<F10>", lambda e: self.pick_position())

    # --- Логика горячих клавиш ---
    def toggle_start(self):
        if self.running:
            self.stop_clicker()
        else:
            self.start_clicker()

    def on_mode_change(self, event):
        mode = self.mode_var.get()
        state = "normal" if mode == "возвращать при уходе > порога" else "disabled"
        self.lbl_thresh.config(state=state)

    # --- Выбор позиции ---
    def pick_position(self):
        self.status_label.config(text="Статус: выберите точку на экране", fg=self.colors["acc"])
        self.root.update()
        def on_click(x, y, b, p):
            if p:
                self.target_x, self.target_y = x, y
                self.pos_label.config(text=f"Позиция: x={x}, y={y}", fg=self.colors["ok"])
                self.status_label.config(text="Статус: остановлен", fg="#666666")
                return False
        with Listener(on_click=on_click) as listener:
            listener.join()

    # --- Рабочий цикл ---
    def click_loop(self):
        try:
            max_count = int(self.count_var.get())
            if max_count < 0:
                max_count = 0
        except ValueError:
            max_count = 0

        clicked = 0
        btn_map = {"left": Button.left, "right": Button.right, "middle": Button.middle}
        btn = btn_map.get(self.button_var.get(), Button.left)
        mode = self.mode_var.get()

        try:
            threshold = int(self.threshold_var.get())
            if threshold < 0:
                threshold = 0
        except ValueError:
            threshold = 20

        while self.running:
            if max_count > 0 and clicked >= max_count:
                self.running = False
                break

            try:
                interval = float(self.interval_var.get())
                if interval <= 0:
                    interval = 0.1
            except ValueError:
                interval = 1.0

            if self.target_x is not None and self.target_y is not None:
                cx, cy = self.mouse.position
                dx, dy = abs(cx - self.target_x), abs(cy - self.target_y)

                should_move = False
                if mode == "всегда возвращать":
                    should_move = True
                elif mode == "возвращать при уходе > порога":
                    if dx > threshold or dy > threshold:
                        should_move = True

                if should_move:
                    self.mouse.position = (self.target_x, self.target_y)
                    time.sleep(0.01)

                self.mouse.click(btn, 1)
                lx, ly = self.target_x, self.target_y
            else:
                self.mouse.click(btn, 1)
                lx, ly = self.mouse.position

            self.log_click(lx, ly, self.button_var.get())
            clicked += 1
            time.sleep(interval)

        self.root.after(0, lambda: self.status_label.config(text="Статус: остановлен", fg="#666666"))

    # --- Управление ---
    def start_clicker(self):
        if self.running:
            return
        self.running = True
        self.btn_start.config(state="disabled")
        self.btn_stop.config(state="normal")
        self.status_label.config(text="Статус: ожидание (3 сек)", fg="#666666")

        def starter():
            time.sleep(3)
            if not self.running:
                return
            self.status_label.config(text="Статус: работает", fg=self.colors["ok"])
            Thread(target=self.click_loop, daemon=True).start()

        Thread(target=starter, daemon=True).start()

    def stop_clicker(self):
        self.running = False
        self.btn_start.config(state="normal")
        self.btn_stop.config(state="disabled")

    # --- Лог ---
    def log_click(self, x, y, button):
        line = f"{datetime.now().isoformat()} | click | {button} | x={x}, y={y}\n"
        try:
            with open(LOG_FILE, "a", encoding="utf-8") as f:
                f.write(line)
        except Exception:
            pass

    def open_log(self):
        if not os.path.exists(LOG_FILE):
            messagebox.showinfo("Инфо", "Лог-файл ещё не создан.")
            return

        if os.name == "nt":
            os.startfile(LOG_FILE)
        elif os.name == "darwin":
            os.system(f"open {LOG_FILE}")
        else:
            os.system(f"xdg-open {LOG_FILE}")

    def clear_log(self):
        if not os.path.exists(LOG_FILE):
            messagebox.showinfo("Инфо", "Лог-файла ещё нет.")
            return

        try:
            with open(LOG_FILE, "w", encoding="utf-8") as f:
                f.write("")
            messagebox.showinfo("Успех", "Лог очищен.")
        except Exception as e:
            messagebox.showerror("Ошибка", str(e))

    # --- Профили ---
    def load_config(self):
        try:
            with open(CFG_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return {}

    def save_config(self, data):
        try:
            with open(CFG_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def save_profile(self):
        data = {
            "interval": self.interval_var.get(),
            "max_clicks": self.count_var.get(),
            "button": self.button_var.get(),
            "mode": self.mode_var.get(),
            "threshold": self.threshold_var.get(),
        }
        self.save_config(data)
        messagebox.showinfo("Успех", "Профиль сохранён.")

    def load_profile(self):
        cfg = self.load_config()
        if not cfg:
            messagebox.showwarning("Внимание", "Нет сохранённого профиля.")
            return

        self.interval_var.set(cfg.get("interval", "1.0"))
        self.count_var.set(str(cfg.get("max_clicks", 0)))
        self.button_var.set(cfg.get("button", "left"))
        self.mode_var.set(cfg.get("mode", "none"))
        self.threshold_var.set(str(cfg.get("threshold", 20)))
        self.on_mode_change(None)
        messagebox.showinfo("Успех", "Профиль загружен.")

if __name__ == "__main__":
    root = tk.Tk()
    app = AutoClicker(root)
    root.mainloop()
