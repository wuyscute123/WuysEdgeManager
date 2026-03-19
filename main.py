import os
import json
import subprocess
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
from datetime import datetime, date, timedelta
import time as time_module
import threading
import re
import shutil
import sys

class WuysEdgeManager:
    def __init__(self, root):
        self.root = root
        self.root.title("Wuys Edge Manager")
        self.root.geometry("1400x800")
        
        # Cấu hình giao diện đen
        self.root.configure(bg='#1e1e1e')
        
        # Đường dẫn
        if getattr(sys, 'frozen', False):
            self.application_path = os.path.dirname(sys.executable)
        else:
            self.application_path = os.path.dirname(os.path.abspath(__file__))
        
        self.edge_profile_path = os.path.join(
            os.environ.get('LOCALAPPDATA'),
            'Microsoft', 'Edge', 'User Data'
        )
        
        self.data_file = os.path.join(self.application_path, 'wuys_data.json')
        self.MAX_POINTS_PER_PROFILE = 6750
        
        # Dữ liệu
        self.data = {'profiles': {}, 'daily_status': {}}
        self.current_date = date.today().isoformat()
        self.load_data()
        
        self.selected_item = None
        self.context_item = None
        
        self.setup_ui()
        self.setup_context_menu()
        self.load_profiles()
        self.start_date_check()
    
    def detect_profile_type(self, profile_name):
        name_lower = profile_name.lower()
        if re.search(r'roblox', name_lower):
            return "roblox"
        if re.search(r'chô\s*li|choli', name_lower):
            return "choli"
        return "other"
    
    def extract_number(self, profile_name, patterns):
        if not profile_name:
            return float('inf')
        profile_lower = profile_name.lower()
        for pattern in patterns:
            match = re.search(pattern, profile_lower)
            if match:
                try:
                    return int(match.group(1))
                except:
                    pass
        numbers = re.findall(r'\d+', profile_name)
        if numbers:
            try:
                return int(numbers[0])
            except:
                pass
        return float('inf')
    
    def extract_roblox_number(self, profile_name):
        patterns = [r'roblox\s*(\d+)', r'Roblox\s*(\d+)', r'\((\d+)\)', r'\[(\d+)\]']
        return self.extract_number(profile_name, patterns)
    
    def extract_choli_number(self, profile_name):
        patterns = [r'chô\s*li\s*bi\s*(\d+)', r'choli\s*bi\s*(\d+)', 
                   r'chô\s*li\s*(\d+)', r'choli\s*(\d+)', r'\((\d+)\)', r'\[(\d+)\]']
        return self.extract_number(profile_name, patterns)
    
    def get_sort_number(self, profile_name, profile_type):
        if profile_type == "roblox":
            return self.extract_roblox_number(profile_name)
        elif profile_type == "choli":
            return self.extract_choli_number(profile_name)
        return float('inf')
    
    def get_sort_display(self, profile_name, profile_type):
        if profile_type == "other":
            return "-"
        number = self.get_sort_number(profile_name, profile_type)
        return str(number) if number != float('inf') else "-"
    
    def sort_profiles(self, profiles_list):
        type_priority = {"roblox": 1, "choli": 2, "other": 3}
        def sort_key(p):
            return (type_priority.get(p['type'], 3), p['sort_num'], p['name'])
        return sorted(profiles_list, key=sort_key)
    
    def setup_context_menu(self):
        self.context_menu = tk.Menu(self.root, tearoff=0, 
                                    bg='#2d2d2d', fg='white',
                                    activebackground='#3d3d3d', 
                                    activeforeground='white',
                                    font=('Segoe UI', 10))
        
        self.context_menu.add_command(label="➕ Cộng điểm", 
                                      command=self.show_add_points_dialog)
        self.context_menu.add_command(label="✏️ Chỉnh sửa điểm", 
                                      command=self.show_set_points_dialog)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="📋 Copy Profile", 
                                      command=self.copy_selected_profile)
        
        self.tree.bind('<Button-3>', self.show_context_menu)
    
    def show_context_menu(self, event):
        item = self.tree.identify_row(event.y)
        if item:
            self.tree.selection_set(item)
            self.context_item = item
            self.context_menu.post(event.x_root, event.y_root)
    
    def get_total_points(self, profile_path):
        total = 0
        for date_str, daily_data in self.data['daily_status'].items():
            if profile_path in daily_data:
                if isinstance(daily_data[profile_path], dict):
                    total += daily_data[profile_path].get('daily_points', 0)
                else:
                    total += daily_data[profile_path] if isinstance(daily_data[profile_path], (int, float)) else 0
        return total
    
    def show_add_points_dialog(self):
        if not self.context_item:
            return
        
        values = self.tree.item(self.context_item, 'values')
        if not values or len(values) < 7:
            return
        
        profile_name = values[0]
        profile_path = values[3]
        
        total_points = self.get_total_points(profile_path)
        
        daily_points = 0
        if (self.current_date in self.data['daily_status'] and 
            profile_path in self.data['daily_status'][self.current_date]):
            daily_data = self.data['daily_status'][self.current_date][profile_path]
            if isinstance(daily_data, dict):
                daily_points = daily_data.get('daily_points', 0)
            else:
                daily_points = daily_data if isinstance(daily_data, (int, float)) else 0
        
        dialog = tk.Toplevel(self.root)
        dialog.title("Cộng điểm")
        dialog.geometry("450x320")
        dialog.configure(bg='#1e1e1e')
        dialog.transient(self.root)
        dialog.grab_set()
        
        main_frame = tk.Frame(dialog, bg='#1e1e1e')
        main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # Tiêu đề
        tk.Label(main_frame, text=f"Profile: {profile_name}", 
                bg='#1e1e1e', fg='white', font=('Segoe UI', 12, 'bold')).pack(pady=(0, 15))
        
        # Thông tin
        info_frame = tk.Frame(main_frame, bg='#1e1e1e')
        info_frame.pack(fill=tk.X, pady=5)
        
        tk.Label(info_frame, text=f"Tổng điểm: {total_points}", 
                bg='#1e1e1e', fg='#4CAF50', font=('Segoe UI', 11)).pack(anchor='w')
        tk.Label(info_frame, text=f"Điểm hôm nay: {daily_points}", 
                bg='#1e1e1e', fg='#FF9800', font=('Segoe UI', 11)).pack(anchor='w', pady=5)
        
        remaining = self.MAX_POINTS_PER_PROFILE - total_points
        tk.Label(info_frame, text=f"Còn có thể thêm: {remaining}", 
                bg='#1e1e1e', fg='#888888', font=('Segoe UI', 10)).pack(anchor='w')
        
        # Nhập điểm
        input_frame = tk.Frame(main_frame, bg='#1e1e1e')
        input_frame.pack(fill=tk.X, pady=15)
        
        tk.Label(input_frame, text="Số điểm thêm:", 
                bg='#1e1e1e', fg='white', font=('Segoe UI', 11)).pack(side=tk.LEFT, padx=5)
        
        points_var = tk.StringVar(value="0")
        entry = tk.Entry(input_frame, textvariable=points_var, width=10, 
                        font=('Segoe UI', 11), bg='#2d2d2d', fg='white',
                        insertbackground='white', bd=0, relief=tk.FLAT)
        entry.pack(side=tk.LEFT, padx=5)
        entry.focus()
        
        error_label = tk.Label(main_frame, text="", bg='#1e1e1e', fg='red', font=('Segoe UI', 9))
        error_label.pack(pady=5)
        
        # Nút bấm
        button_frame = tk.Frame(main_frame, bg='#1e1e1e')
        button_frame.pack(pady=15)
        
        def on_confirm():
            try:
                points = int(points_var.get().strip())
                new_daily = daily_points + points
                new_total = total_points + points
                
                if points < 0:
                    error_label.config(text="Không thể thêm điểm âm!")
                    return
                if new_total > self.MAX_POINTS_PER_PROFILE:
                    error_label.config(text=f"Không thể vượt quá {self.MAX_POINTS_PER_PROFILE}!")
                    return
                
                if messagebox.askyesno("Xác nhận", f"Thêm {points} điểm cho '{profile_name}'?"):
                    self.save_daily_points(self.context_item, new_daily, new_total, points)
                    dialog.destroy()
                
            except ValueError:
                error_label.config(text="Vui lòng nhập số hợp lệ!")
        
        tk.Button(button_frame, text="Xác nhận", command=on_confirm,
                 bg='#4CAF50', fg='white', font=('Segoe UI', 10, 'bold'),
                 width=12, height=1, bd=0, cursor='hand2').pack(side=tk.LEFT, padx=5)
        tk.Button(button_frame, text="Hủy", command=dialog.destroy,
                 bg='#f44336', fg='white', font=('Segoe UI', 10, 'bold'),
                 width=12, height=1, bd=0, cursor='hand2').pack(side=tk.LEFT, padx=5)
    
    def show_set_points_dialog(self):
        if not self.context_item:
            return
        
        values = self.tree.item(self.context_item, 'values')
        if not values or len(values) < 7:
            return
        
        profile_name = values[0]
        profile_path = values[3]
        total_points = self.get_total_points(profile_path)
        
        dialog = tk.Toplevel(self.root)
        dialog.title("Chỉnh sửa điểm")
        dialog.geometry("450x280")
        dialog.configure(bg='#1e1e1e')
        dialog.transient(self.root)
        dialog.grab_set()
        
        main_frame = tk.Frame(dialog, bg='#1e1e1e')
        main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        tk.Label(main_frame, text=f"Profile: {profile_name}", 
                bg='#1e1e1e', fg='white', font=('Segoe UI', 12, 'bold')).pack(pady=(0, 15))
        
        tk.Label(main_frame, text=f"Tổng điểm hiện tại: {total_points}", 
                bg='#1e1e1e', fg='#FF9800', font=('Segoe UI', 11)).pack(anchor='w', pady=5)
        
        input_frame = tk.Frame(main_frame, bg='#1e1e1e')
        input_frame.pack(fill=tk.X, pady=15)
        
        tk.Label(input_frame, text="Tổng điểm mới:", 
                bg='#1e1e1e', fg='white', font=('Segoe UI', 11)).pack(side=tk.LEFT, padx=5)
        
        points_var = tk.StringVar(value=str(total_points))
        entry = tk.Entry(input_frame, textvariable=points_var, width=10,
                        font=('Segoe UI', 11), bg='#2d2d2d', fg='white',
                        insertbackground='white', bd=0, relief=tk.FLAT)
        entry.pack(side=tk.LEFT, padx=5)
        entry.focus()
        
        error_label = tk.Label(main_frame, text="", bg='#1e1e1e', fg='red', font=('Segoe UI', 9))
        error_label.pack(pady=5)
        
        button_frame = tk.Frame(main_frame, bg='#1e1e1e')
        button_frame.pack(pady=15)
        
        def on_confirm():
            try:
                new_total = int(points_var.get().strip())
                
                if new_total < 0:
                    error_label.config(text="Điểm không thể âm!")
                    return
                if new_total > self.MAX_POINTS_PER_PROFILE:
                    error_label.config(text=f"Không thể vượt quá {self.MAX_POINTS_PER_PROFILE}!")
                    return
                
                if messagebox.askyesno("Xác nhận", f"Chỉnh sửa điểm '{profile_name}'?\n{total_points} → {new_total}"):
                    self.set_total_points(self.context_item, new_total)
                    dialog.destroy()
                
            except ValueError:
                error_label.config(text="Vui lòng nhập số hợp lệ!")
        
        tk.Button(button_frame, text="Xác nhận", command=on_confirm,
                 bg='#4CAF50', fg='white', font=('Segoe UI', 10, 'bold'),
                 width=12, height=1, bd=0, cursor='hand2').pack(side=tk.LEFT, padx=5)
        tk.Button(button_frame, text="Hủy", command=dialog.destroy,
                 bg='#f44336', fg='white', font=('Segoe UI', 10, 'bold'),
                 width=12, height=1, bd=0, cursor='hand2').pack(side=tk.LEFT, padx=5)
    
    def save_daily_points(self, item, new_daily, new_total, added=0):
        try:
            values = self.tree.item(item, 'values')
            if not values:
                return
            
            profile_path = values[3]
            profile_name = values[0]
            
            is_worked = (new_daily > 0)
            status = "Đã làm việc" if is_worked else "Chưa làm việc"
            icon = '✓' if is_worked else '○'
            
            if self.current_date not in self.data['daily_status']:
                self.data['daily_status'][self.current_date] = {}
            
            self.data['daily_status'][self.current_date][profile_path] = {
                'worked': is_worked,
                'daily_points': new_daily
            }
            
            self.save_data()
            
            self.tree.item(item, values=(
                profile_name, values[1], values[2], profile_path,
                status, str(new_daily) if new_daily > 0 else "",
                str(new_total) if new_total > 0 else ""
            ))
            self.tree.item(item, text=icon)
            
            self.update_statistics()
            
            remaining = self.MAX_POINTS_PER_PROFILE - new_total
            self.save_status_label.config(
                text=f"✅ Đã thêm {added} điểm (tổng: {new_total}) | Còn: {remaining}")
            self.root.after(3000, lambda: self.save_status_label.config(text=""))
            
        except Exception as e:
            print(f"Lỗi: {e}")
    
    def set_total_points(self, item, new_total):
        try:
            values = self.tree.item(item, 'values')
            if not values:
                return
            
            profile_path = values[3]
            profile_name = values[0]
            
            # Tính điểm hiện tại
            current_daily = 0
            if (self.current_date in self.data['daily_status'] and 
                profile_path in self.data['daily_status'][self.current_date]):
                data = self.data['daily_status'][self.current_date][profile_path]
                if isinstance(data, dict):
                    current_daily = data.get('daily_points', 0)
                else:
                    current_daily = data if isinstance(data, (int, float)) else 0
            
            old_total = self.get_total_points(profile_path)
            diff = new_total - old_total
            new_daily = current_daily + diff
            
            if new_daily < 0:
                messagebox.showerror("Lỗi", "Không thể set điểm thấp hơn điểm đã có!")
                return
            
            is_worked = (new_daily > 0)
            status = "Đã làm việc" if is_worked else "Chưa làm việc"
            icon = '✓' if is_worked else '○'
            
            if self.current_date not in self.data['daily_status']:
                self.data['daily_status'][self.current_date] = {}
            
            self.data['daily_status'][self.current_date][profile_path] = {
                'worked': is_worked,
                'daily_points': new_daily
            }
            
            self.save_data()
            
            self.tree.item(item, values=(
                profile_name, values[1], values[2], profile_path,
                status, str(new_daily) if new_daily > 0 else "",
                str(new_total) if new_total > 0 else ""
            ))
            self.tree.item(item, text=icon)
            
            self.update_statistics()
            
            remaining = self.MAX_POINTS_PER_PROFILE - new_total
            self.save_status_label.config(
                text=f"✅ Đã chỉnh sửa: tổng {new_total} | Còn: {remaining}")
            self.root.after(3000, lambda: self.save_status_label.config(text=""))
            
        except Exception as e:
            print(f"Lỗi: {e}")
    
    def copy_selected_profile(self):
        if not self.context_item:
            messagebox.showwarning("Cảnh báo", "Vui lòng chọn profile để copy!")
            return
        
        values = self.tree.item(self.context_item, 'values')
        if not values or values[0].startswith('==='):
            messagebox.showwarning("Cảnh báo", "Vui lòng chọn profile!")
            return
        
        source_path = values[3]
        source_name = values[0].strip()
        
        if not os.path.exists(source_path):
            messagebox.showerror("Lỗi", "Không tìm thấy profile nguồn!")
            return
        
        new_name = simpledialog.askstring("Copy Profile", 
            f"Nhập tên cho profile mới (copy từ '{source_name}'):", parent=self.root)
        
        if not new_name:
            return
        
        try:
            # Tìm số profile tiếp theo
            next_num = 1
            existing = []
            if os.path.exists(self.edge_profile_path):
                for item in os.listdir(self.edge_profile_path):
                    if item.startswith("Profile "):
                        try:
                            existing.append(int(item.split(" ")[1]))
                        except:
                            pass
            if existing:
                next_num = max(existing) + 1
            
            dir_name = f"Profile {next_num}"
            new_path = os.path.join(self.edge_profile_path, dir_name)
            
            shutil.copytree(source_path, new_path)
            
            # Cập nhật Preferences
            pref_file = os.path.join(new_path, 'Preferences')
            if os.path.exists(pref_file):
                try:
                    with open(pref_file, 'r', encoding='utf-8') as f:
                        pref = json.load(f)
                    pref['profile'] = pref.get('profile', {})
                    pref['profile']['name'] = new_name
                    pref['profile_name'] = new_name
                    with open(pref_file, 'w', encoding='utf-8') as f:
                        json.dump(pref, f, ensure_ascii=False, indent=2)
                except:
                    pass
            
            ptype = self.detect_profile_type(new_name)
            self.data['profiles'][new_path] = {
                'name': new_name, 'created_date': datetime.now().isoformat(),
                'folder_name': dir_name, 'type': ptype
            }
            
            self.save_data()
            self.load_profiles()
            messagebox.showinfo("Thành công", f"✅ Đã copy profile: {new_name}")
            
        except Exception as e:
            messagebox.showerror("Lỗi", f"Không thể copy: {str(e)}")
    
    def load_data(self):
        try:
            if os.path.exists(self.data_file):
                with open(self.data_file, 'r', encoding='utf-8') as f:
                    loaded = json.load(f)
                    self.data['profiles'] = loaded.get('profiles', {})
                    self.data['daily_status'] = loaded.get('daily_status', {})
                    self.cleanup_old_data()
        except Exception as e:
            print(f"Lỗi đọc file: {e}")
    
    def save_data(self):
        try:
            with open(self.data_file, 'w', encoding='utf-8') as f:
                json.dump(self.data, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            print(f"Lỗi lưu file: {e}")
            return False
    
    def cleanup_old_data(self):
        thirty_days_ago = (date.today() - timedelta(days=30)).isoformat()
        self.data['daily_status'] = {
            day: status for day, status in self.data['daily_status'].items() 
            if day >= thirty_days_ago
        }
    
    def check_new_day(self):
        new_date = date.today().isoformat()
        if new_date != self.current_date:
            self.current_date = new_date
            if self.current_date not in self.data['daily_status']:
                self.data['daily_status'][self.current_date] = {}
            self.save_data()
            self.root.after(0, self.load_profiles)
            return True
        return False
    
    def start_date_check(self):
        def check():
            while True:
                try:
                    self.check_new_day()
                    time_module.sleep(60)
                except:
                    pass
        thread = threading.Thread(target=check, daemon=True)
        thread.start()
    
    def setup_ui(self):
        # Frame chính
        main_frame = tk.Frame(self.root, bg='#1e1e1e')
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Tiêu đề
        title = tk.Label(main_frame, text="Wuys Edge Manager", 
                        bg='#1e1e1e', fg='white', font=('Segoe UI', 20, 'bold'))
        title.pack(pady=5)
        
        # Thời gian
        time_frame = tk.Frame(main_frame, bg='#1e1e1e')
        time_frame.pack(fill=tk.X, pady=5)
        
        self.time_label = tk.Label(time_frame, text="", bg='#1e1e1e', fg='white', 
                                   font=('Segoe UI', 11))
        self.time_label.pack(side=tk.LEFT)
        
        self.date_label = tk.Label(time_frame, text="", bg='#1e1e1e', fg='#4CAF50',
                                   font=('Segoe UI', 11, 'bold'))
        self.date_label.pack(side=tk.LEFT, padx=20)
        
        self.update_time()
        
        # Treeview
        tree_frame = tk.Frame(main_frame, bg='#1e1e1e')
        tree_frame.pack(fill=tk.BOTH, expand=True, pady=10)
        
        # Scrollbar
        scrollbar = tk.Scrollbar(tree_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Treeview với style
        style = ttk.Style()
        style.theme_use('clam')
        style.configure('Treeview', 
                       background='#2d2d2d',
                       foreground='white',
                       fieldbackground='#2d2d2d',
                       rowheight=25,
                       font=('Segoe UI', 10))
        style.configure('Treeview.Heading', 
                       background='#3d3d3d',
                       foreground='white',
                       font=('Segoe UI', 10, 'bold'))
        style.map('Treeview',
                 background=[('selected', '#4d4d4d')])
        
        self.tree = ttk.Treeview(tree_frame, 
                                 columns=('Tên Profile', 'Loại', 'Số', 'Đường Dẫn', 'Trạng Thái', 'Hôm nay', 'Tổng'),
                                 show='tree headings',
                                 yscrollcommand=scrollbar.set,
                                 height=14)
        
        # Định nghĩa cột
        self.tree.heading('#0', text='', anchor='center')
        self.tree.heading('Tên Profile', text='Tên Profile')
        self.tree.heading('Loại', text='Loại')
        self.tree.heading('Số', text='Số')
        self.tree.heading('Đường Dẫn', text='Đường Dẫn')
        self.tree.heading('Trạng Thái', text='Trạng Thái')
        self.tree.heading('Hôm nay', text='Điểm hôm nay')
        self.tree.heading('Tổng', text='Tổng điểm')
        
        # Độ rộng cột
        self.tree.column('#0', width=40, anchor='center')
        self.tree.column('Tên Profile', width=220)
        self.tree.column('Loại', width=80, anchor='center')
        self.tree.column('Số', width=50, anchor='center')
        self.tree.column('Đường Dẫn', width=450)
        self.tree.column('Trạng Thái', width=100, anchor='center')
        self.tree.column('Hôm nay', width=100, anchor='center')
        self.tree.column('Tổng', width=100, anchor='center')
        
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.tree.yview)
        
        # Bind events
        self.tree.bind('<Button-1>', self.on_click)
        self.tree.bind('<Double-Button-1>', self.on_double_click)
        self.tree.bind('<<TreeviewSelect>>', self.on_select)
        
        # Frame nút bấm
        button_frame = tk.Frame(main_frame, bg='#1e1e1e')
        button_frame.pack(fill=tk.X, pady=10)
        
        buttons = [
            ("▶ Mở Profile", self.open_selected_profile, '#4CAF50'),
            ("➕ Tạo Mới", self.create_new_profile, '#2196F3'),
            ("📋 Copy Profile", self.copy_profile_button, '#FF9800'),
            ("🔄 Làm Mới", self.load_profiles, '#9C27B0'),
            ("📊 Lịch Sử", self.view_history, '#00BCD4'),
            ("✕ Thoát", self.root.quit, '#f44336')
        ]
        
        for text, cmd, color in buttons:
            btn = tk.Button(button_frame, text=text, command=cmd,
                           bg=color, fg='white', font=('Segoe UI', 11, 'bold'),
                           width=14, height=1, bd=0, cursor='hand2')
            btn.pack(side=tk.LEFT, padx=3)
            # Hover effect
            btn.bind('<Enter>', lambda e, b=btn, c=color: b.config(bg=self.lighten_color(c)))
            btn.bind('<Leave>', lambda e, b=btn, c=color: b.config(bg=c))
        
        # Frame thống kê
        stats_frame = tk.Frame(main_frame, bg='#1e1e1e')
        stats_frame.pack(fill=tk.X, pady=5)
        
        self.stats_labels = {}
        stats = [('total', 'Tổng số:', 'white'),
                ('worked', 'Đã làm việc:', '#4CAF50'),
                ('daily_points', 'Điểm hôm nay:', '#FF9800'),
                ('total_points', 'Tổng điểm:', '#2196F3')]
        
        for i, (key, text, color) in enumerate(stats):
            frame = tk.Frame(stats_frame, bg='#1e1e1e')
            frame.pack(side=tk.LEFT, padx=20)
            
            tk.Label(frame, text=text, bg='#1e1e1e', fg='white',
                    font=('Segoe UI', 11)).pack(side=tk.LEFT)
            label = tk.Label(frame, text='0', bg='#1e1e1e', fg=color,
                            font=('Segoe UI', 11, 'bold'))
            label.pack(side=tk.LEFT, padx=5)
            self.stats_labels[key] = label
        
        # Label thông báo
        self.save_status_label = tk.Label(main_frame, text="", bg='#1e1e1e',
                                          fg='#4CAF50', font=('Segoe UI', 10))
        self.save_status_label.pack(pady=5)
    
    def lighten_color(self, color):
        # Làm sáng màu cho hover effect
        r, g, b = int(color[1:3], 16), int(color[3:5], 16), int(color[5:7], 16)
        r, g, b = min(255, r + 30), min(255, g + 30), min(255, b + 30)
        return f'#{r:02x}{g:02x}{b:02x}'
    
    def copy_profile_button(self):
        if not self.selected_item:
            messagebox.showwarning("Cảnh báo", "Vui lòng chọn profile để copy!")
            return
        self.context_item = self.selected_item
        self.copy_selected_profile()
    
    def update_time(self):
        try:
            now = datetime.now()
            self.time_label.config(text=f"Thời gian: {now.strftime('%H:%M:%S')}")
            self.date_label.config(text=f"Ngày: {now.strftime('%d/%m/%Y')}")
            self.check_new_day()
        except:
            pass
        self.root.after(1000, self.update_time)
    
    def on_click(self, event):
        region = self.tree.identify_region(event.x, event.y)
        if region == "cell":
            col = self.tree.identify_column(event.x)
            item = self.tree.identify_row(event.y)
            if item and col == '#1':
                self.tree.selection_set(item)
                return "break"
    
    def on_double_click(self, event):
        self.open_selected_profile()
    
    def on_select(self, event):
        sel = self.tree.selection()
        if sel:
            self.selected_item = sel[0]
    
    def get_profile_name(self, path):
        try:
            pref = os.path.join(path, 'Preferences')
            if os.path.exists(pref):
                with open(pref, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    name = data.get('profile', {}).get('name')
                    if not name:
                        name = data.get('profile_name')
                    if not name:
                        name = os.path.basename(path)
                    return name
        except:
            pass
        return os.path.basename(path)
    
    def load_profiles(self):
        try:
            # Clear tree
            for item in self.tree.get_children():
                self.tree.delete(item)
            
            profiles = []
            type_counts = {"roblox": 0, "choli": 0, "other": 0}
            total_worked = total_daily = total_all = 0
            
            if os.path.exists(self.edge_profile_path):
                for item in os.listdir(self.edge_profile_path):
                    path = os.path.join(self.edge_profile_path, item)
                    if not os.path.isdir(path):
                        continue
                    
                    # Kiểm tra profile
                    is_profile = False
                    name = item
                    
                    if item == "Default":
                        is_profile = True
                        name = "Default"
                    elif item.startswith("Profile "):
                        is_profile = True
                        name = self.get_profile_name(path)
                    
                    if not is_profile and os.path.exists(os.path.join(path, 'Preferences')):
                        is_profile = True
                        name = self.get_profile_name(path)
                    
                    if not is_profile:
                        continue
                    
                    # Thêm vào data nếu chưa có
                    if path not in self.data['profiles']:
                        self.data['profiles'][path] = {
                            'name': name, 'created_date': datetime.now().isoformat(),
                            'folder_name': item
                        }
                    
                    # Lấy điểm
                    daily = 0
                    worked = False
                    if self.current_date in self.data['daily_status']:
                        data = self.data['daily_status'][self.current_date].get(path, {})
                        if isinstance(data, dict):
                            worked = data.get('worked', False)
                            daily = data.get('daily_points', 0)
                        else:
                            worked = bool(data)
                            daily = data if isinstance(data, (int, float)) else 0
                    
                    total = self.get_total_points(path)
                    
                    # Phân loại
                    ptype = self.detect_profile_type(name)
                    type_counts[ptype] += 1
                    
                    type_display = {"roblox": "Roblox", "choli": "Chô li bi", "other": "Khác"}[ptype]
                    sort_num = self.get_sort_number(name, ptype)
                    sort_disp = self.get_sort_display(name, ptype)
                    
                    profiles.append({
                        'name': name, 'type': ptype, 'type_display': type_display,
                        'sort_num': sort_num, 'sort_disp': sort_disp, 'path': path,
                        'worked': worked, 'daily': daily, 'total': total,
                        'icon': '✓' if worked else '○',
                        'status': "Đã làm việc" if worked else "Chưa làm việc"
                    })
                    
                    if worked:
                        total_worked += 1
                    total_daily += daily
                    total_all += total
            
            # Sắp xếp
            profiles.sort(key=lambda p: (
                {"roblox": 1, "choli": 2, "other": 3}[p['type']],
                p['sort_num'] if p['sort_num'] != float('inf') else float('inf'),
                p['name']
            ))
            
            # Hiển thị
            current_type = None
            for p in profiles:
                if p['type'] != current_type:
                    current_type = p['type']
                    title = {
                        "roblox": f"=== ROBLOX PROFILES ({type_counts['roblox']}) ===",
                        "choli": f"=== CHÔ LI BI PROFILES ({type_counts['choli']}) ===",
                        "other": f"=== OTHER PROFILES ({type_counts['other']}) ==="
                    }[current_type]
                    
                    self.tree.insert('', tk.END, values=(title, "", "", "", "", "", ""),
                                    tags=('header',))
                
                self.tree.insert('', tk.END,
                               text=p['icon'],
                               values=(
                                   f"  {p['name']}", p['type_display'], p['sort_disp'],
                                   p['path'], p['status'],
                                   str(p['daily']) if p['daily'] > 0 else "",
                                   str(p['total']) if p['total'] > 0 else ""
                               ))
            
            self.tree.tag_configure('header', background='#3d3d3d', foreground='#FF9800', font=('Segoe UI', 10, 'bold'))
            
            self.update_statistics(len(profiles), total_worked, total_daily, total_all)
            
            if len(profiles) == 0:
                messagebox.showinfo("Thông báo", "Không tìm thấy profile Edge nào!")
            
        except Exception as e:
            print(f"Lỗi load: {e}")
            messagebox.showerror("Lỗi", f"Lỗi khi tải profiles: {str(e)}")
    
    def update_statistics(self, total=None, worked=None, daily=None, total_pts=None):
        if total is not None:
            self.stats_labels['total'].config(text=str(total))
            self.stats_labels['worked'].config(text=str(worked))
            self.stats_labels['daily_points'].config(text=str(daily))
            self.stats_labels['total_points'].config(text=str(total_pts))
    
    def open_selected_profile(self):
        if not self.selected_item:
            messagebox.showwarning("Cảnh báo", "Vui lòng chọn profile!")
            return
        
        values = self.tree.item(self.selected_item, 'values')
        if not values or values[0].startswith('==='):
            messagebox.showwarning("Cảnh báo", "Vui lòng chọn profile!")
            return
        
        path = values[3]
        name = values[0].strip()
        
        info = self.data['profiles'].get(path, {})
        folder = info.get('folder_name', os.path.basename(path))
        
        # Tìm Edge
        edge_paths = [
            os.path.join(os.environ.get('PROGRAMFILES', 'C:\\Program Files'),
                        'Microsoft', 'Edge', 'Application', 'msedge.exe'),
            os.path.join(os.environ.get('PROGRAMFILES(X86)', 'C:\\Program Files (x86)'),
                        'Microsoft', 'Edge', 'Application', 'msedge.exe')
        ]
        
        edge_exe = None
        for ep in edge_paths:
            if os.path.exists(ep):
                edge_exe = ep
                break
        
        if edge_exe:
            subprocess.Popen([edge_exe, f'--profile-directory={folder}'])
            self.save_status_label.config(text=f"✅ Đang mở: {name}")
            self.root.after(2000, lambda: self.save_status_label.config(text=""))
        else:
            messagebox.showerror("Lỗi", "Không tìm thấy Microsoft Edge!")
    
    def create_new_profile(self):
        name = simpledialog.askstring("Tạo Profile Mới", "Nhập tên cho profile mới:", parent=self.root)
        if not name:
            return
        
        try:
            # Tìm số tiếp theo
            next_num = 1
            existing = []
            if os.path.exists(self.edge_profile_path):
                for item in os.listdir(self.edge_profile_path):
                    if item.startswith("Profile "):
                        try:
                            existing.append(int(item.split(" ")[1]))
                        except:
                            pass
            if existing:
                next_num = max(existing) + 1
            
            folder = f"Profile {next_num}"
            new_path = os.path.join(self.edge_profile_path, folder)
            os.makedirs(new_path, exist_ok=True)
            
            # Tạo Preferences
            pref = {
                "profile": {"name": name},
                "profile_name": name
            }
            with open(os.path.join(new_path, 'Preferences'), 'w', encoding='utf-8') as f:
                json.dump(pref, f, ensure_ascii=False, indent=2)
            
            ptype = self.detect_profile_type(name)
            self.data['profiles'][new_path] = {
                'name': name, 'created_date': datetime.now().isoformat(),
                'folder_name': folder, 'type': ptype
            }
            self.save_data()
            self.load_profiles()
            messagebox.showinfo("Thành công", f"✅ Đã tạo: {name}")
            
        except Exception as e:
            messagebox.showerror("Lỗi", f"Không thể tạo: {str(e)}")
    
    def view_history(self):
        win = tk.Toplevel(self.root)
        win.title("Lịch Sử")
        win.geometry("850x500")
        win.configure(bg='#1e1e1e')
        
        main = tk.Frame(win, bg='#1e1e1e')
        main.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        tk.Label(main, text="Lịch Sử Theo Ngày", bg='#1e1e1e', fg='white',
                font=('Segoe UI', 16, 'bold')).pack(pady=5)
        
        # Treeview
        frame = tk.Frame(main, bg='#1e1e1e')
        frame.pack(fill=tk.BOTH, expand=True)
        
        scroll = tk.Scrollbar(frame)
        scroll.pack(side=tk.RIGHT, fill=tk.Y)
        
        cols = ('Ngày', 'Tổng', 'Đã LV', 'Điểm', 'Roblox', 'Chô li bi', 'Khác')
        tree = ttk.Treeview(frame, columns=cols, show='headings',
                            yscrollcommand=scroll.set, height=15)
        
        for col, width in zip(cols, [120, 70, 70, 100, 80, 80, 70]):
            tree.heading(col, text=col)
            tree.column(col, width=width, anchor='center')
        
        tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scroll.config(command=tree.yview)
        
        # Dữ liệu
        for date_str in sorted(self.data['daily_status'].keys(), reverse=True)[:30]:
            data = self.data['daily_status'][date_str]
            counts = {"roblox": 0, "choli": 0, "other": 0}
            worked = pts = 0
            
            for path, pdata in data.items():
                info = self.data['profiles'].get(path, {})
                ptype = self.detect_profile_type(info.get('name', ''))
                counts[ptype] += 1
                
                if isinstance(pdata, dict):
                    if pdata.get('worked'):
                        worked += 1
                    pts += pdata.get('daily_points', 0)
                else:
                    if pdata:
                        worked += 1
                    pts += pdata if isinstance(pdata, (int, float)) else 0
            
            try:
                d = datetime.fromisoformat(date_str).strftime('%d/%m/%Y')
            except:
                d = date_str
            
            tree.insert('', tk.END, values=(
                d, len(data), worked, pts,
                counts['roblox'], counts['choli'], counts['other']
            ))
        
        tk.Button(main, text="Đóng", command=win.destroy,
                 bg='#f44336', fg='white', font=('Segoe UI', 11, 'bold'),
                 width=12, bd=0, cursor='hand2').pack(pady=10)

def main():
    root = tk.Tk()
    app = WuysEdgeManager(root)
    root.mainloop()

if __name__ == "__main__":
    main()