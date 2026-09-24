import os
import sys
import json
import time
import threading
import tkinter as tk
from tkinter import ttk, messagebox
from urllib.parse import unquote, urlparse
from PIL import ImageGrab, Image, ImageDraw
from supabase import create_client, Client
import pystray
import winreg

APP_NAME = "AloptamaAutoScreenshot"

if getattr(sys, 'frozen', False):
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

CONFIG_FILE = os.path.join(BASE_DIR, "config.json")


def get_startup_command():
    if getattr(sys, 'frozen', False):
        return f'"{sys.executable}"'
    else:
        script_path = os.path.abspath(__file__)
        return f'"{sys.executable}" "{script_path}"'


def is_auto_startup_enabled():
    try:
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Run",
            0,
            winreg.KEY_READ
        )
        val, _ = winreg.QueryValueEx(key, APP_NAME)
        winreg.CloseKey(key)
        return bool(val)
    except FileNotFoundError:
        return False
    except Exception:
        return False


def set_auto_startup(enable: bool):
    try:
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Run",
            0,
            winreg.KEY_SET_VALUE
        )
        if enable:
            cmd = get_startup_command()
            winreg.SetValueEx(key, APP_NAME, 0, winreg.REG_SZ, cmd)
        else:
            try:
                winreg.DeleteValue(key, APP_NAME)
            except FileNotFoundError:
                pass
        winreg.CloseKey(key)
        return True
    except Exception as e:
        print(f"Error setting auto startup: {e}")
        return False




def storage_path_from_public_url(public_url, bucket_name):
    if not public_url:
        return None
    marker = f"/object/public/{bucket_name}/"
    path = unquote(urlparse(public_url).path)
    idx = path.find(marker)
    if idx == -1:
        return None
    return path[idx + len(marker):]


def cleanup_old_bucket_files(supabase, bucket_name, kode, keep_name, old_url, log):
    """Hapus screenshot lama perangkat ini, sisakan file yang baru diunggah."""
    to_delete = set()
    old_path = storage_path_from_public_url(old_url, bucket_name)
    if old_path and old_path != keep_name:
        to_delete.add(old_path)

    prefix = f"{kode}_"
    try:
        listed = supabase.storage.from_(bucket_name).list(
            "",
            {"limit": 100, "offset": 0, "search": kode},
        )
        for item in listed or []:
            name = item.get("name") if isinstance(item, dict) else None
            if name and name.startswith(prefix) and name != keep_name:
                to_delete.add(name)
    except Exception as e:
        log(f"Gagal list bucket: {e}")

    if not to_delete:
        return

    try:
        supabase.storage.from_(bucket_name).remove(list(to_delete))
        log(f"Membersihkan {len(to_delete)} file lama di bucket.")
    except Exception as e:
        log(f"Gagal hapus file bucket: {e}")

def create_image():
    # Menghasilkan gambar untuk ikon System Tray
    image = Image.new('RGB', (64, 64), color=(0, 102, 204))
    dc = ImageDraw.Draw(image)
    dc.text((12, 24), "ALOP", fill=(255, 255, 255))
    return image

class AppGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Aloptama Auto Screenshot")
        self.root.geometry("490x750")
        self.root.resizable(False, False)

        # Tangani tombol X di sudut kanan atas
        self.root.protocol('WM_DELETE_WINDOW', self.on_closing)

        self.running = False
        self.thread = None
        self.config = {}
        self.tray_icon = None

        self.load_config()
        self.build_ui()

        # Otomatisasi saat aplikasi pertama kali terbuka
        if self.config.get("AUTO_START_CAPTURE", False):
            self.root.after(1000, self.start_capture)

        if self.config.get("START_MINIMIZED", False):
            self.root.after(600, self.hide_window)

    def load_config(self):
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, 'r') as f:
                    self.config = json.load(f)
            except Exception as e:
                print(f"Error reading config: {e}")
                self.set_default_config()
        else:
            self.set_default_config()

    def set_default_config(self):
        self.config = {
            "SUPABASE_URL": "",
            "SUPABASE_KEY": "",
            "BUCKET_NAME": "aloptama-images",
            "TABLE_NAME": "aloptama",
            "INTERVAL_DETIK": 60,
            "AUTO_START_CAPTURE": False,
            "START_MINIMIZED": False,
            "PERANGKAT": {
                "kode": "PPN",
                "jenis": "Display",
                "bujur": "0.0",
                "lintang": "0.0",
                "status": "green"
            }
        }

    def save_config(self):
        with open(CONFIG_FILE, 'w') as f:
            json.dump(self.config, f, indent=4)

    def build_ui(self):
        # Gaya Tampilan agar lebih rapih (Clean UI)
        style = ttk.Style()
        try:
            style.theme_use('clam')
        except:
            pass
            
        style.configure("TFrame", background="#f4f6f9")
        style.configure("TLabel", background="#f4f6f9", font=("Segoe UI", 10))
        style.configure("TLabelframe", background="#f4f6f9")
        style.configure("TLabelframe.Label", background="#f4f6f9", font=("Segoe UI", 10, "bold"), foreground="#333333")
        style.configure("TButton", font=("Segoe UI", 10), padding=5)
        style.configure("TNotebook", background="#e9ecef")

        self.root.configure(bg="#f4f6f9")

        notebook = ttk.Notebook(self.root)
        notebook.pack(pady=10, padx=10, expand=True, fill='both')

        control_frame = ttk.Frame(notebook)
        notebook.add(control_frame, text='   Kontrol   ')

        settings_frame = ttk.Frame(notebook)
        notebook.add(settings_frame, text='   Pengaturan   ')

        self.build_control_tab(control_frame)
        self.build_settings_tab(settings_frame)

    def build_control_tab(self, frame):
        # --- Bagian Status ---
        status_box = ttk.LabelFrame(frame, text="Status Aplikasi", padding=15)
        status_box.pack(fill="x", padx=20, pady=(20, 10))

        self.status_label = ttk.Label(status_box, text="BERHENTI", foreground="#d9534f", font=("Segoe UI", 16, "bold"))
        self.status_label.pack(pady=5)

        ttk.Label(status_box, text="Interval Screenshot (Detik):").pack(pady=(10, 5))
        self.interval_var = tk.StringVar(value=str(self.config.get("INTERVAL_DETIK", 60)))
        interval_entry = ttk.Entry(status_box, textvariable=self.interval_var, justify='center', width=15, font=("Segoe UI", 12))
        interval_entry.pack()

        # --- Bagian Tombol ---
        btn_box = ttk.Frame(frame)
        btn_box.pack(fill="x", padx=20, pady=10)

        self.start_btn = ttk.Button(btn_box, text="▶ Start", command=self.start_capture, width=10)
        self.start_btn.pack(side=tk.LEFT, padx=5)

        self.stop_btn = ttk.Button(btn_box, text="■ Stop", command=self.stop_capture, state=tk.DISABLED, width=10)
        self.stop_btn.pack(side=tk.LEFT, padx=5)
        
        # Tombol tray
        self.tray_btn = ttk.Button(btn_box, text="⬇ Ke Tray", command=self.hide_window, width=12)
        self.tray_btn.pack(side=tk.RIGHT, padx=5)

        # --- Bagian Log ---
        log_box = ttk.LabelFrame(frame, text="Log Aktivitas", padding=10)
        log_box.pack(fill="both", expand=True, padx=20, pady=(10, 20))
        
        self.log_text = tk.Text(log_box, height=12, state='disabled', bg="#ffffff", font=("Consolas", 9), relief="flat")
        self.log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        scrollbar = ttk.Scrollbar(log_box, command=self.log_text.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.log_text.config(yscrollcommand=scrollbar.set)

    def build_settings_tab(self, frame):
        # Variables
        self.supabase_url_var = tk.StringVar(value=self.config.get("SUPABASE_URL", ""))
        self.supabase_key_var = tk.StringVar(value=self.config.get("SUPABASE_KEY", ""))
        self.kode_var = tk.StringVar(value=self.config.get("PERANGKAT", {}).get("kode", ""))
        self.jenis_var = tk.StringVar(value=self.config.get("PERANGKAT", {}).get("jenis", ""))
        self.bujur_var = tk.StringVar(value=self.config.get("PERANGKAT", {}).get("bujur", ""))
        self.lintang_var = tk.StringVar(value=self.config.get("PERANGKAT", {}).get("lintang", ""))
        self.status_var = tk.StringVar(value=self.config.get("PERANGKAT", {}).get("status", "green"))
        
        self.auto_startup_var = tk.BooleanVar(value=is_auto_startup_enabled())
        self.auto_start_capture_var = tk.BooleanVar(value=self.config.get("AUTO_START_CAPTURE", False))
        self.start_minimized_var = tk.BooleanVar(value=self.config.get("START_MINIMIZED", False))
        
        # --- Grup Database ---
        db_box = ttk.LabelFrame(frame, text="Database Supabase", padding=15)
        db_box.pack(fill="x", padx=20, pady=(15, 8))

        ttk.Label(db_box, text="Supabase URL:").pack(anchor=tk.W, pady=(0, 2))
        ttk.Entry(db_box, textvariable=self.supabase_url_var, width=50).pack(fill="x", pady=(0, 8))

        ttk.Label(db_box, text="Supabase Key:").pack(anchor=tk.W, pady=(0, 2))
        ttk.Entry(db_box, textvariable=self.supabase_key_var, show="*", width=50).pack(fill="x", pady=(0, 4))

        # --- Grup Perangkat ---
        dev_box = ttk.LabelFrame(frame, text="Data Perangkat", padding=15)
        dev_box.pack(fill="x", padx=20, pady=8)

        grid_frame = ttk.Frame(dev_box)
        grid_frame.pack(fill="x")

        ttk.Label(grid_frame, text="Kode:").grid(row=0, column=0, sticky=tk.W, pady=4, padx=(0, 10))
        ttk.Entry(grid_frame, textvariable=self.kode_var, width=15).grid(row=0, column=1, sticky=tk.W, pady=4)

        ttk.Label(grid_frame, text="Jenis:").grid(row=0, column=2, sticky=tk.W, pady=4, padx=(15, 10))
        ttk.Entry(grid_frame, textvariable=self.jenis_var, width=15).grid(row=0, column=3, sticky=tk.W, pady=4)

        ttk.Label(grid_frame, text="Bujur:").grid(row=1, column=0, sticky=tk.W, pady=4, padx=(0, 10))
        ttk.Entry(grid_frame, textvariable=self.bujur_var, width=15).grid(row=1, column=1, sticky=tk.W, pady=4)

        ttk.Label(grid_frame, text="Lintang:").grid(row=1, column=2, sticky=tk.W, pady=4, padx=(15, 10))
        ttk.Entry(grid_frame, textvariable=self.lintang_var, width=15).grid(row=1, column=3, sticky=tk.W, pady=4)
        
        ttk.Label(grid_frame, text="Status Awal:").grid(row=2, column=0, sticky=tk.W, pady=4, padx=(0, 10))
        status_combo = ttk.Combobox(grid_frame, textvariable=self.status_var, values=["green", "yellow", "red"], width=13)
        status_combo.grid(row=2, column=1, sticky=tk.W, pady=4)

        # --- Grup Startup & Otomasi ---
        startup_box = ttk.LabelFrame(frame, text="Startup & Otomasi Windows", padding=12)
        startup_box.pack(fill="x", padx=20, pady=8)

        ttk.Checkbutton(
            startup_box,
            text="Jalankan otomatis saat Windows booting (Auto Startup)",
            variable=self.auto_startup_var
        ).pack(anchor=tk.W, pady=(0, 4))

        ttk.Checkbutton(
            startup_box,
            text="Otomatis mulai capture saat aplikasi dibuka",
            variable=self.auto_start_capture_var
        ).pack(anchor=tk.W, pady=(0, 4))

        ttk.Checkbutton(
            startup_box,
            text="Mulai langsung di System Tray (Background)",
            variable=self.start_minimized_var
        ).pack(anchor=tk.W, pady=(0, 2))

        # Tombol Save
        save_btn = ttk.Button(frame, text="Simpan Pengaturan", command=self.save_settings, width=20)
        save_btn.pack(pady=12)

    # --- FUNGSI TRAY ---
    def hide_window(self):
        # Sembunyikan window tkinter
        self.root.withdraw()
        
        image = create_image()
        menu = (
            pystray.MenuItem('Show', self.show_window, default=True),
            pystray.MenuItem('Exit', self.quit_app)
        )
        self.tray_icon = pystray.Icon("Aloptama", image, "Aloptama Screenshot", menu)
        
        # Jalankan pystray di thread berbeda agar tidak memblokir tkinter loop sepenuhnya
        # (pystray.run() bersifat memblokir)
        threading.Thread(target=self.tray_icon.run, daemon=True).start()

    def show_window(self, icon, item):
        self.tray_icon.stop()
        self.root.after(0, self.root.deiconify)

    def quit_app(self, icon=None, item=None):
        if self.tray_icon:
            self.tray_icon.stop()
        self.running = False
        self.root.destroy()
        os._exit(0) # Paksa keluar karena mungkin ada thread

    def on_closing(self):
        # Ketika tombol X diklik, minimize ke tray saja
        if messagebox.askyesno("Perhatian", "Aplikasi akan disembunyikan ke System Tray.\nPilih 'No' jika ingin mematikan aplikasi sepenuhnya."):
            self.hide_window()
        else:
            self.quit_app()

    # --- FUNGSI UTAMA ---
    def save_settings(self):
        self.config["SUPABASE_URL"] = self.supabase_url_var.get()
        self.config["SUPABASE_KEY"] = self.supabase_key_var.get()
        if "PERANGKAT" not in self.config:
            self.config["PERANGKAT"] = {}
        self.config["PERANGKAT"]["kode"] = self.kode_var.get()
        self.config["PERANGKAT"]["jenis"] = self.jenis_var.get()
        self.config["PERANGKAT"]["bujur"] = self.bujur_var.get()
        self.config["PERANGKAT"]["lintang"] = self.lintang_var.get()
        self.config["PERANGKAT"]["status"] = self.status_var.get()
        try:
            self.config["INTERVAL_DETIK"] = int(self.interval_var.get())
        except ValueError:
            messagebox.showerror("Error", "Interval harus berupa angka")
            return

        self.config["AUTO_START_CAPTURE"] = self.auto_start_capture_var.get()
        self.config["START_MINIMIZED"] = self.start_minimized_var.get()

        startup_success = set_auto_startup(self.auto_startup_var.get())
        if not startup_success:
            self.log("Peringatan: Gagal memperbarui registry Windows Auto Startup.")

        self.save_config()
        messagebox.showinfo("Success", "Settings saved successfully")


    def log(self, message):
        def _log():
            try:
                self.log_text.config(state='normal')
                time_str = time.strftime('%H:%M:%S')
                self.log_text.insert(tk.END, f"[{time_str}] {message}\n")
                self.log_text.see(tk.END)
                self.log_text.config(state='disabled')
            except:
                pass
        self.root.after(0, _log)

    def start_capture(self):
        try:
            interval_val = int(self.interval_var.get())
            if interval_val < 1:
                raise ValueError
            self.config["INTERVAL_DETIK"] = interval_val
            self.save_config()
        except ValueError:
            messagebox.showerror("Error", "Interval harus berupa angka positif.")
            return

        if not self.config.get("SUPABASE_URL") or not self.config.get("SUPABASE_KEY"):
            messagebox.showerror("Error", "Harap isi Supabase URL dan Key di tab Settings terlebih dahulu.")
            return

        self.running = True
        self.start_btn.config(state=tk.DISABLED)
        self.stop_btn.config(state=tk.NORMAL)
        self.status_label.config(text="BERJALAN", foreground="#5cb85c")
        self.log("Proses dimulai...")

        self.thread = threading.Thread(target=self.capture_loop, daemon=True)
        self.thread.start()

    def stop_capture(self):
        self.running = False
        self.start_btn.config(state=tk.NORMAL)
        self.stop_btn.config(state=tk.DISABLED)
        self.status_label.config(text="BERHENTI", foreground="#d9534f")
        self.log("Proses dihentikan.")

    def capture_loop(self):
        try:
            supabase: Client = create_client(self.config["SUPABASE_URL"], self.config["SUPABASE_KEY"])
        except Exception as e:
            self.log(f"Gagal koneksi Supabase: {e}")
            self.root.after(0, self.stop_capture)
            return

        interval = self.config["INTERVAL_DETIK"]
        bucket_name = self.config["BUCKET_NAME"]
        table_name = self.config["TABLE_NAME"]
        perangkat = self.config["PERANGKAT"]

        while self.running:
            try:
                self.log("Mengambil screenshot...")
                screenshot = ImageGrab.grab()
                
                kode = perangkat.get("kode", "UNKNOWN")
                timestamp = int(time.time())
                file_name = f"{kode}_{timestamp}.jpg"
                file_path = os.path.join(BASE_DIR, file_name)
                
                screenshot.save(file_path, "JPEG", quality=70)
                self.log(f"Mengupload {file_name}...")
                
                with open(file_path, "rb") as f:
                    supabase.storage.from_(bucket_name).upload(
                        file=f,
                        path=file_name,
                        file_options={"content-type": "image/jpeg"}
                    )
                
                public_url = supabase.storage.from_(bucket_name).get_public_url(file_name)
                self.log("Update database...")
                
                db_data = {
                    "kode": kode,
                    "gambar_url": public_url,
                    "jenis": perangkat.get("jenis", ""),
                    "bujur": float(perangkat.get("bujur", 0.0)),
                    "lintang": float(perangkat.get("lintang", 0.0)),
                    "status": perangkat.get("status", "green"),
                    "timestamp": time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())
                }
                
                check_res = supabase.table(table_name).select('id, gambar_url').eq('kode', kode).execute()
                old_url = None

                if len(check_res.data) > 0:
                    row_id = check_res.data[0]['id']
                    old_url = check_res.data[0].get('gambar_url')
                    supabase.table(table_name).update(db_data).eq('id', row_id).execute()
                else:
                    supabase.table(table_name).insert(db_data).execute()

                cleanup_old_bucket_files(
                    supabase, bucket_name, kode, file_name, old_url, self.log
                )
                
                self.log("Berhasil! Menghapus gambar lokal...")
                try:
                    os.remove(file_path)
                except Exception as del_err:
                    self.log(f"Gagal menghapus gambar lokal: {del_err}")

            except Exception as e:
                self.log(f"Error: {str(e)}")
            
            for _ in range(interval * 10):
                if not self.running:
                    break
                time.sleep(0.1)

if __name__ == "__main__":
    root = tk.Tk()
    app = AppGUI(root)
    root.mainloop()
