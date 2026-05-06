import datetime
import json
import os
import shutil
import sqlite3
import threading
import traceback
import uuid
import webbrowser

try:
    import tkinter as tk
    from tkinter import filedialog, messagebox, ttk
except ImportError:
    raise SystemExit("Tkinter is required to run this tool.")


APP_TITLE = "Codex Provider 恢复工具"
DEFAULT_CODEX_HOME = os.path.join(os.path.expanduser("~"), ".codex")


def get_backup_root():
    return os.path.join(os.path.abspath(os.getcwd()), "备份")


class ProviderRepairApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(APP_TITLE)
        self.geometry("1180x860")
        self.minsize(1020, 740)

        self.codex_home_var = tk.StringVar(value=DEFAULT_CODEX_HOME)
        self.current_provider_var = tk.StringVar(value="-")
        self.current_vendor_var = tk.StringVar(value="-")
        self.vendor_url_var = tk.StringVar(value="-")
        self.codex_url_var = tk.StringVar(value="-")
        self.total_memory_var = tk.StringVar(value="0 B")
        self.active_count_var = tk.StringVar(value="0")
        self.archived_count_var = tk.StringVar(value="0")
        self.synced_count_var = tk.StringVar(value="0")
        self.status_var = tk.StringVar(value="就绪")

        self.backup_dir = None
        self.last_scan = None
        self.worker = None
        self.checked_thread_ids = set()
        self.active_tree = None
        self.archived_tree = None

        self._build_ui()
        self.after(200, self.scan)

    def _build_ui(self):
        root = ttk.Frame(self, padding=14)
        root.pack(fill=tk.BOTH, expand=True)
        root.columnconfigure(0, weight=1)
        root.rowconfigure(4, weight=1)

        header = ttk.Frame(root)
        header.grid(row=0, column=0, sticky="ew")
        header.columnconfigure(0, weight=1)
        ttk.Label(header, text=APP_TITLE, font=("Microsoft YaHei UI", 15, "bold")).grid(row=0, column=0, sticky="w")
        ttk.Label(header, textvariable=self.status_var).grid(row=0, column=1, sticky="e")

        path_row = ttk.Frame(root)
        path_row.grid(row=1, column=0, sticky="ew", pady=(12, 8))
        path_row.columnconfigure(1, weight=1)
        ttk.Label(path_row, text="Codex 目录").grid(row=0, column=0, sticky="w", padx=(0, 8))
        ttk.Entry(path_row, textvariable=self.codex_home_var).grid(row=0, column=1, sticky="ew", padx=(0, 8))
        ttk.Button(path_row, text="选择", command=self.choose_codex_home).grid(row=0, column=2, sticky="e")

        info_card = ttk.LabelFrame(root, text="当前配置")
        info_card.grid(row=2, column=0, sticky="ew")
        info_card.columnconfigure(1, weight=1)

        ttk.Label(info_card, text="当前 Provider").grid(row=0, column=0, sticky="w", padx=10, pady=(10, 6))
        ttk.Label(info_card, textvariable=self.current_provider_var, font=("Consolas", 11, "bold")).grid(
            row=0, column=1, sticky="w", padx=(0, 10), pady=(10, 6)
        )

        ttk.Label(info_card, text="当前供货商").grid(row=1, column=0, sticky="w", padx=10, pady=6)
        ttk.Label(info_card, textvariable=self.current_vendor_var, wraplength=860).grid(
            row=1, column=1, sticky="w", padx=(0, 10), pady=6
        )

        self._build_link_row(info_card, 2, "当前使用的供货商链接", self.vendor_url_var)
        self._build_link_row(info_card, 3, "Codex 配置当前使用的链接", self.codex_url_var)

        counts = ttk.Frame(info_card)
        counts.grid(row=4, column=0, columnspan=2, sticky="ew", padx=10, pady=(8, 10))
        counts.columnconfigure(1, weight=1)
        counts.columnconfigure(3, weight=1)
        counts.columnconfigure(5, weight=1)
        counts.columnconfigure(7, weight=1)

        ttk.Label(counts, text="聊天窗口").grid(row=0, column=0, sticky="w")
        ttk.Label(counts, textvariable=self.active_count_var, font=("Consolas", 11, "bold")).grid(row=0, column=1, sticky="w")
        ttk.Label(counts, text="归档对话").grid(row=0, column=2, sticky="w", padx=(18, 0))
        ttk.Label(counts, textvariable=self.archived_count_var, font=("Consolas", 11, "bold")).grid(row=0, column=3, sticky="w")
        ttk.Label(counts, text="已同步").grid(row=0, column=4, sticky="w", padx=(18, 0))
        ttk.Label(counts, textvariable=self.synced_count_var, font=("Consolas", 11, "bold")).grid(row=0, column=5, sticky="w")
        ttk.Label(counts, text="总聊天记录内存").grid(row=0, column=6, sticky="w", padx=(18, 0))
        ttk.Label(counts, textvariable=self.total_memory_var, font=("Consolas", 11, "bold")).grid(row=0, column=7, sticky="w")

        actions = ttk.Frame(root)
        actions.grid(row=3, column=0, sticky="ew", pady=(10, 8))
        ttk.Button(actions, text="扫描", command=self.scan).pack(side=tk.LEFT, padx=(0, 8))
        ttk.Button(actions, text="刷新列表", command=self.refresh_thread_list_only).pack(side=tk.LEFT, padx=(0, 8))
        ttk.Button(actions, text="全选", command=self.select_all_threads).pack(side=tk.LEFT, padx=(0, 8))
        ttk.Button(actions, text="清空勾选", command=self.clear_thread_checks).pack(side=tk.LEFT, padx=(0, 8))
        ttk.Button(actions, text="删除勾选", command=self.delete_checked_threads).pack(side=tk.LEFT, padx=(0, 18))
        ttk.Button(actions, text="备份并修复配置", command=self.repair).pack(side=tk.LEFT, padx=(0, 8))
        ttk.Button(actions, text="高级：重写历史", command=self.rewrite_history).pack(side=tk.LEFT, padx=(0, 8))
        ttk.Button(actions, text="打开备份目录", command=self.open_backup_dir).pack(side=tk.LEFT)

        main_panes = ttk.Panedwindow(root, orient=tk.VERTICAL)
        main_panes.grid(row=4, column=0, sticky="nsew")

        thread_box = ttk.LabelFrame(main_panes, text="聊天列表")
        thread_box.columnconfigure(0, weight=1)
        thread_box.rowconfigure(0, weight=1)

        self.thread_tabs = ttk.Notebook(thread_box)
        self.thread_tabs.grid(row=0, column=0, sticky="nsew", padx=8, pady=8)

        active_tab = ttk.Frame(self.thread_tabs)
        active_tab.columnconfigure(0, weight=1)
        active_tab.rowconfigure(0, weight=1)
        self.active_tree = self._build_thread_tree(active_tab)
        self.thread_tabs.add(active_tab, text="聊天窗口")

        archived_tab = ttk.Frame(self.thread_tabs)
        archived_tab.columnconfigure(0, weight=1)
        archived_tab.rowconfigure(0, weight=1)
        self.archived_tree = self._build_thread_tree(archived_tab)
        self.thread_tabs.add(archived_tab, text="归档对话")

        main_panes.add(thread_box, weight=3)

        log_frame = ttk.LabelFrame(main_panes, text="日志")
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(0, weight=1)
        self.log = tk.Text(log_frame, height=8, wrap=tk.WORD, state=tk.DISABLED)
        log_scroll = ttk.Scrollbar(log_frame, command=self.log.yview)
        self.log.configure(yscrollcommand=log_scroll.set)
        self.log.grid(row=0, column=0, sticky="nsew", padx=(8, 0), pady=8)
        log_scroll.grid(row=0, column=1, sticky="ns", padx=(0, 8), pady=8)
        main_panes.add(log_frame, weight=1)

    def _build_link_row(self, parent, row_index, label_text, variable):
        ttk.Label(parent, text=label_text).grid(row=row_index, column=0, sticky="w", padx=10, pady=6)
        ttk.Entry(parent, textvariable=variable, state="readonly").grid(
            row=row_index, column=1, sticky="ew", padx=(0, 8), pady=6
        )
        buttons = ttk.Frame(parent)
        buttons.grid(row=row_index, column=2, sticky="e", padx=(0, 10), pady=6)
        ttk.Button(buttons, text="复制", command=lambda: self.copy_text(variable.get())).pack(side=tk.LEFT, padx=(0, 6))
        ttk.Button(buttons, text="打开", command=lambda: self.open_url(variable.get())).pack(side=tk.LEFT)

    def _build_thread_tree(self, parent):
        wrap = ttk.Frame(parent)
        wrap.grid(row=0, column=0, sticky="nsew")
        wrap.columnconfigure(0, weight=1)
        wrap.rowconfigure(0, weight=1)

        columns = ("checked", "title", "provider", "size", "updated", "thread_id")
        tree = ttk.Treeview(wrap, columns=columns, show="headings", height=12)
        tree.heading("checked", text="勾选")
        tree.heading("title", text="标题")
        tree.heading("provider", text="Provider")
        tree.heading("size", text="内存")
        tree.heading("updated", text="更新时间")
        tree.heading("thread_id", text="线程 ID")
        tree.column("checked", width=58, anchor="center", stretch=False)
        tree.column("title", width=430, anchor="w")
        tree.column("provider", width=100, anchor="center", stretch=False)
        tree.column("size", width=90, anchor="e", stretch=False)
        tree.column("updated", width=140, anchor="center", stretch=False)
        tree.column("thread_id", width=250, anchor="w")
        tree.grid(row=0, column=0, sticky="nsew")
        tree.bind("<Button-1>", self.on_thread_tree_click)
        tree.bind("<Double-1>", self.on_thread_tree_double_click)

        scroll = ttk.Scrollbar(wrap, command=tree.yview)
        tree.configure(yscrollcommand=scroll.set)
        scroll.grid(row=0, column=1, sticky="ns")
        return tree

    def choose_codex_home(self):
        path = filedialog.askdirectory(initialdir=self.codex_home_var.get() or os.path.expanduser("~"))
        if path:
            self.codex_home_var.set(path)
            self.scan()

    def copy_text(self, text):
        if not text or text == "-":
            return
        self.clipboard_clear()
        self.clipboard_append(text)
        self.status_var.set("已复制链接")

    def open_url(self, text):
        if not text or text == "-" or "://" not in text:
            messagebox.showinfo(APP_TITLE, "当前没有可打开的链接。")
            return
        webbrowser.open(text)

    def set_busy(self, busy):
        state = tk.DISABLED if busy else tk.NORMAL
        for widget in self.winfo_children():
            pass

    def run_worker(self, label, func):
        if self.worker and self.worker.is_alive():
            messagebox.showinfo(APP_TITLE, "已有任务正在运行，请稍等。")
            return

        self.status_var.set(label)

        def target():
            try:
                result = func()
                self.after(0, lambda: self.on_worker_done(result, None))
            except Exception as exc:
                detail = traceback.format_exc()
                self.after(0, lambda: self.on_worker_done(None, (exc, detail)))

        self.worker = threading.Thread(target=target, daemon=True)
        self.worker.start()

    def on_worker_done(self, result, error):
        if error:
            exc, detail = error
            self.status_var.set("失败")
            self.append_log("执行失败：%s\n%s" % (exc, detail))
            messagebox.showerror(APP_TITLE, "执行失败：\n%s" % exc)
            return

        self.status_var.set("完成")
        if result:
            self.apply_result(result)

    def scan(self):
        self.run_worker("扫描中...", lambda: scan_codex_home(self.codex_home_var.get()))

    def verify(self):
        self.run_worker("验证中...", lambda: scan_codex_home(self.codex_home_var.get(), verify_only=True))

    def refresh_thread_list_only(self):
        self.run_worker("刷新列表中...", lambda: scan_codex_home(self.codex_home_var.get(), verify_only=True))

    def repair(self):
        codex_home = self.codex_home_var.get()
        scan = scan_codex_home(codex_home)
        provider = scan["current_provider"]

        if not provider:
            messagebox.showerror(APP_TITLE, "无法从 config.toml 读取 model_provider。")
            self.apply_result(scan)
            return

        if not scan.get("provider_defined"):
            defined = ", ".join(scan.get("provider_defined_names", [])) or "(无)"
            messagebox.showerror(
                APP_TITLE,
                "config.toml 当前指向的 provider '%s' 没有对应的配置段。\n\n已定义的 provider：%s"
                % (provider, defined),
            )
            self.apply_result(scan)
            return

        missing = scan.get("missing_history_providers", [])
        if not missing:
            messagebox.showinfo(APP_TITLE, "没有发现缺失的历史 provider，当前配置已经兼容。")
            self.apply_result(scan)
            return

        vendor_url = scan.get("active_vendor_url") or "-"
        msg = (
            "将先备份 config.toml，然后为这些历史 provider 名称补充兼容别名：\n\n"
            "%s\n\n"
            "这些别名都会指向当前使用的供货商链接：\n%s\n\n"
            "是否继续？"
        ) % (", ".join(missing), vendor_url)
        if not messagebox.askyesno(APP_TITLE, msg):
            self.apply_result(scan)
            return

        self.run_worker("修复配置中...", lambda: repair_codex_home(codex_home, scan))

    def rewrite_history(self):
        codex_home = self.codex_home_var.get()
        scan = scan_codex_home(codex_home)
        provider = scan["current_provider"]

        if not provider:
            messagebox.showerror(APP_TITLE, "无法从 config.toml 读取 model_provider。")
            self.apply_result(scan)
            return

        if not scan.get("provider_defined"):
            defined = ", ".join(scan.get("provider_defined_names", [])) or "(无)"
            messagebox.showerror(
                APP_TITLE,
                "config.toml 当前指向的 provider '%s' 没有对应的配置段。\n\n已定义的 provider：%s"
                % (provider, defined),
            )
            self.apply_result(scan)
            return

        if scan["db_non_current"] == 0 and scan["jsonl_non_current"] == 0:
            messagebox.showinfo(APP_TITLE, "历史记录已经和当前 provider 一致。")
            self.apply_result(scan)
            return

        msg = (
            "高级模式会把 %s 条数据库记录和 %s 个会话文件重写为 provider '%s'。\n\n"
            "是否继续？"
        ) % (scan["db_non_current"], scan["jsonl_non_current"], provider)
        if not messagebox.askyesno(APP_TITLE, msg):
            self.apply_result(scan)
            return

        self.run_worker("重写历史中...", lambda: rewrite_history_to_current_provider(codex_home, scan))

    def select_all_threads(self):
        if not self.last_scan:
            return
        self.checked_thread_ids = {item["id"] for item in self.last_scan.get("thread_list", [])}
        self.render_thread_list(self.last_scan.get("thread_list", []))

    def clear_thread_checks(self):
        self.checked_thread_ids.clear()
        if self.last_scan:
            self.render_thread_list(self.last_scan.get("thread_list", []))

    def delete_checked_threads(self):
        if not self.checked_thread_ids:
            messagebox.showinfo(APP_TITLE, "请先勾选要删除的聊天。")
            return

        if not self.last_scan:
            return

        selected = [item for item in self.last_scan.get("thread_list", []) if item["id"] in self.checked_thread_ids]
        count = len(selected)
        preview = "\n".join("- %s" % item["title_short"] for item in selected[:8])
        if count > 8:
            preview += "\n- ..."

        msg = (
            "将删除 %s 个聊天记录。\n\n"
            "这些聊天会从列表中移除，并删除对应数据库记录、session_index 记录和会话文件。\n\n"
            "%s\n\n"
            "删除前会自动备份。是否继续？"
        ) % (count, preview)
        if not messagebox.askyesno(APP_TITLE, msg):
            return

        selected_ids = sorted(self.checked_thread_ids)
        self.run_worker("删除聊天中...", lambda: delete_threads_from_codex_home(self.codex_home_var.get(), selected_ids))

    def on_thread_tree_click(self, event):
        tree = event.widget
        if tree not in (self.active_tree, self.archived_tree):
            return None
        region = tree.identify("region", event.x, event.y)
        column = tree.identify_column(event.x)
        item_id = tree.identify_row(event.y)
        if region == "cell" and column == "#1" and item_id:
            self.toggle_thread_check(item_id)
            return "break"
        return None

    def on_thread_tree_double_click(self, event):
        tree = event.widget
        item_id = tree.identify_row(event.y)
        if item_id:
            self.toggle_thread_check(item_id)
            return "break"
        return None

    def toggle_thread_check(self, thread_id):
        if thread_id in self.checked_thread_ids:
            self.checked_thread_ids.remove(thread_id)
        else:
            self.checked_thread_ids.add(thread_id)
        if self.last_scan:
            self.render_thread_list(self.last_scan.get("thread_list", []))

    def open_backup_dir(self):
        path = self.backup_dir or get_backup_root()
        if os.path.isdir(path):
            os.startfile(path)
        else:
            messagebox.showinfo(APP_TITLE, "备份目录暂时还不存在。")

    def apply_result(self, result):
        self.last_scan = result
        self.backup_dir = result.get("backup_dir") or self.backup_dir
        self.current_provider_var.set(result.get("current_provider") or "-")
        self.current_vendor_var.set(result.get("current_vendor_name") or "-")
        self.vendor_url_var.set(result.get("active_vendor_url") or "-")
        self.codex_url_var.set(result.get("codex_current_url") or "-")

        thread_list = result.get("thread_list", [])
        active_threads = [item for item in thread_list if not item["archived"]]
        archived_threads = [item for item in thread_list if item["archived"]]
        self.active_count_var.set(str(len(active_threads)))
        self.archived_count_var.set(str(len(archived_threads)))
        self.synced_count_var.set(str(result.get("jsonl_files_scanned", 0)))
        self.total_memory_var.set(format_bytes(sum(item.get("size_bytes", 0) for item in thread_list)))

        current_ids = {item["id"] for item in thread_list}
        self.checked_thread_ids.intersection_update(current_ids)

        self.render_thread_list(thread_list)
        self.append_log(format_log(result))

    def render_thread_list(self, thread_list):
        self.active_tree.delete(*self.active_tree.get_children())
        self.archived_tree.delete(*self.archived_tree.get_children())

        active_threads = [item for item in thread_list if not item["archived"]]
        archived_threads = [item for item in thread_list if item["archived"]]

        for tree, items in ((self.active_tree, active_threads), (self.archived_tree, archived_threads)):
            for item in items:
                checked = "☑" if item["id"] in self.checked_thread_ids else "☐"
                tree.insert(
                    "",
                    "end",
                    iid=item["id"],
                    values=(
                        checked,
                        item["title_short"],
                        item["provider"] or "",
                        item.get("size_label", "0 B"),
                        item["updated_label"],
                        item["id"],
                    ),
                )

    def append_log(self, text):
        stamp = datetime.datetime.now().strftime("%H:%M:%S")
        self.log.configure(state=tk.NORMAL)
        self.log.insert(tk.END, "[%s] %s\n\n" % (stamp, text.rstrip()))
        self.log.see(tk.END)
        self.log.configure(state=tk.DISABLED)


def read_text(path):
    with open(path, "r", encoding="utf-8", errors="replace", newline="") as f:
        return f.read()


def write_text(path, text):
    with open(path, "w", encoding="utf-8", newline="") as f:
        f.write(text)


def parse_simple_toml_kv(line):
    parts = line.split("=", 1)
    if len(parts) != 2:
        return None, None
    key = parts[0].strip()
    value = parts[1].strip()
    if value.startswith('"') and value.endswith('"'):
        value = value[1:-1]
    elif value.startswith("'") and value.endswith("'"):
        value = value[1:-1]
    return key, value


def read_current_provider(codex_home):
    config_path = os.path.join(codex_home, "config.toml")
    if not os.path.isfile(config_path):
        return None
    for line in read_text(config_path).splitlines():
        stripped = line.strip()
        if stripped.startswith("model_provider"):
            _, value = parse_simple_toml_kv(stripped)
            return value
    return None


def read_model_provider_profiles(codex_home):
    config_path = os.path.join(codex_home, "config.toml")
    profiles = {}
    if not os.path.isfile(config_path):
        return profiles

    current_name = None
    current_values = None
    prefix = "[model_providers."

    for line in read_text(config_path).splitlines():
        stripped = line.strip()
        if stripped.startswith(prefix) and stripped.endswith("]"):
            name = stripped[len(prefix):-1].strip()
            if name.startswith('"') and name.endswith('"'):
                name = name[1:-1]
            elif name.startswith("'") and name.endswith("'"):
                name = name[1:-1]
            current_name = name or None
            current_values = {}
            if current_name:
                profiles[current_name] = current_values
            continue

        if current_name and stripped and not stripped.startswith("["):
            key, value = parse_simple_toml_kv(stripped)
            if key:
                current_values[key] = value
    return profiles


def read_defined_model_providers(codex_home):
    return set(read_model_provider_profiles(codex_home).keys())


def extract_host(url):
    if not url:
        return ""
    if "://" in url:
        return url.split("://", 1)[1].split("/", 1)[0]
    return url.split("/", 1)[0]


def infer_vendor_name(profile_name, profile):
    profile = profile or {}
    base_url = profile.get("base_url", "")
    host = extract_host(base_url)
    if profile_name and host:
        return "%s (%s)" % (profile_name, host)
    if profile_name:
        return profile_name
    if host:
        return host
    return None


def choose_repair_source_provider(current_provider, defined_profiles):
    if current_provider and current_provider in defined_profiles:
        return current_provider
    if len(defined_profiles) == 1:
        return sorted(defined_profiles.keys())[0]
    return None


def list_jsonl_files(codex_home):
    result = []
    for name in ("sessions", "archived_sessions"):
        root = os.path.join(codex_home, name)
        if not os.path.isdir(root):
            continue
        for dirpath, _, filenames in os.walk(root):
            for filename in filenames:
                if filename.endswith(".jsonl"):
                    result.append(os.path.join(dirpath, filename))
    result.sort()
    return result


def read_session_meta_provider(path):
    with open(path, "r", encoding="utf-8", errors="surrogateescape", newline="") as f:
        first = f.readline()
    if not first:
        return None
    obj = json.loads(first.rstrip("\r\n"))
    if not isinstance(obj, dict) or obj.get("type") != "session_meta":
        return None
    payload = obj.get("payload")
    if not isinstance(payload, dict):
        return None
    return payload.get("model_provider")


def format_timestamp_ms(value):
    if not value:
        return ""
    try:
        dt = datetime.datetime.fromtimestamp(int(value) / 1000.0)
        return dt.strftime("%Y-%m-%d %H:%M")
    except Exception:
        return str(value)


def normalize_rollout_path(path):
    if not path:
        return ""
    if path.startswith("\\\\?\\"):
        return path[4:]
    return path


def format_bytes(size):
    try:
        value = float(size or 0)
    except (TypeError, ValueError):
        value = 0.0

    units = ("B", "KB", "MB", "GB", "TB")
    for unit in units:
        if value < 1024 or unit == units[-1]:
            if unit == "B":
                return "%d %s" % (int(value), unit)
            return "%.2f %s" % (value, unit)
        value /= 1024.0


def shorten_text(text, limit=60):
    text = (text or "").replace("\r", " ").replace("\n", " ").strip()
    if len(text) <= limit:
        return text
    return text[: limit - 1] + "…"


def load_threads(codex_home):
    state_db = os.path.join(codex_home, "state_5.sqlite")
    if not os.path.isfile(state_db):
        return []

    con = sqlite3.connect("file:%s?mode=ro" % state_db, uri=True)
    try:
        rows = con.execute(
            """
            select id, title, model_provider, updated_at_ms, archived, rollout_path
            from threads
            order by coalesce(updated_at_ms, 0) desc, coalesce(updated_at, 0) desc
            """
        ).fetchall()
    finally:
        con.close()

    result = []
    for thread_id, title, provider, updated_at_ms, archived, rollout_path in rows:
        rollout_path = normalize_rollout_path(rollout_path)
        size_bytes = os.path.getsize(rollout_path) if rollout_path and os.path.isfile(rollout_path) else 0
        result.append(
            {
                "id": thread_id,
                "title": title or "",
                "title_short": shorten_text(title or "(无标题)"),
                "provider": provider or "",
                "size_bytes": size_bytes,
                "size_label": format_bytes(size_bytes),
                "updated_at_ms": updated_at_ms or 0,
                "updated_label": format_timestamp_ms(updated_at_ms),
                "archived": bool(archived),
                "rollout_path": rollout_path,
            }
        )
    return result


def scan_codex_home(codex_home, verify_only=False):
    codex_home = os.path.abspath(os.path.expanduser(codex_home))
    provider = read_current_provider(codex_home)
    defined_profiles = read_model_provider_profiles(codex_home)
    defined_providers = set(defined_profiles.keys())
    repair_source_provider = choose_repair_source_provider(provider, defined_profiles)

    current_profile = defined_profiles.get(provider) if provider else None
    active_profile = defined_profiles.get(repair_source_provider) if repair_source_provider else None

    codex_current_url = (current_profile or {}).get("base_url")
    active_vendor_url = (active_profile or {}).get("base_url")
    current_vendor_name = infer_vendor_name(repair_source_provider, active_profile)
    state_db = os.path.join(codex_home, "state_5.sqlite")

    result = {
        "action": "验证" if verify_only else "扫描",
        "codex_home": codex_home,
        "current_provider": provider,
        "provider_defined": bool(provider and provider in defined_providers),
        "provider_defined_names": sorted(defined_providers),
        "repair_source_provider": repair_source_provider,
        "current_vendor_name": current_vendor_name,
        "active_vendor_url": active_vendor_url,
        "codex_current_url": codex_current_url,
        "db_counts": {},
        "db_total": 0,
        "db_non_current": 0,
        "jsonl_counts": {},
        "jsonl_total": 0,
        "jsonl_non_current": 0,
        "jsonl_files_scanned": 0,
        "thread_list": [],
        "missing_history_providers": [],
        "errors": [],
    }

    history_providers = set()

    if os.path.isfile(state_db):
        try:
            con = sqlite3.connect("file:%s?mode=ro" % state_db, uri=True)
            rows = con.execute("select model_provider, count(*) from threads group by model_provider").fetchall()
            con.close()
            for key, count in rows:
                key = key or ""
                result["db_counts"][key] = count
                result["db_total"] += count
                if key:
                    history_providers.add(key)
                if provider and key != provider:
                    result["db_non_current"] += count
        except Exception as exc:
            result["errors"].append("读取数据库失败：%s" % exc)
    else:
        result["errors"].append("未找到数据库：%s" % state_db)

    files = list_jsonl_files(codex_home)
    result["jsonl_files_scanned"] = len(files)
    for path in files:
        try:
            entry = read_session_meta_provider(path)
            value = entry if entry is not None else ""
            result["jsonl_counts"][value] = result["jsonl_counts"].get(value, 0) + 1
            result["jsonl_total"] += 1
            if value:
                history_providers.add(value)
            if provider and value != provider:
                result["jsonl_non_current"] += 1
        except Exception as exc:
            result["errors"].append("读取会话文件失败 %s：%s" % (path, exc))

    try:
        result["thread_list"] = load_threads(codex_home)
    except Exception as exc:
        result["errors"].append("读取聊天列表失败：%s" % exc)

    result["missing_history_providers"] = sorted(
        name for name in history_providers if name and name not in defined_providers
    )
    return result


def create_backup_dir(codex_home):
    backup_root = get_backup_root()
    if not os.path.isdir(backup_root):
        os.makedirs(backup_root)
    backup_dir = os.path.join(
        backup_root,
        datetime.datetime.now().strftime("%Y%m%d_%H%M%S") + "_" + uuid.uuid4().hex[:6],
    )
    os.makedirs(backup_dir)
    return backup_dir


def backup_config_file(codex_home, backup_dir):
    config_path = os.path.join(codex_home, "config.toml")
    if os.path.isfile(config_path):
        shutil.copy2(config_path, os.path.join(backup_dir, "config.toml.backup"))


def extract_provider_block(text, provider_name):
    header = "[model_providers.%s]" % provider_name
    quoted_headers = (
        '[model_providers."%s"]' % provider_name,
        "[model_providers.'%s']" % provider_name,
    )
    lines = text.splitlines()
    start = None

    for index, line in enumerate(lines):
        stripped = line.strip()
        if stripped == header or stripped in quoted_headers:
            start = index
            break
    if start is None:
        return None

    end = len(lines)
    for index in range(start + 1, len(lines)):
        stripped = lines[index].strip()
        if stripped.startswith("[") and stripped.endswith("]"):
            end = index
            break
    return "\n".join(lines[start:end]).rstrip()


def build_alias_block(source_block, alias_name):
    lines = source_block.splitlines()
    header = "[model_providers.%s]" % alias_name
    rebuilt = [header]
    replaced_name = False

    for line in lines[1:]:
        stripped = line.strip()
        if stripped.startswith("name"):
            prefix = line[: len(line) - len(line.lstrip())]
            rebuilt.append('%sname = "%s"' % (prefix, alias_name))
            replaced_name = True
        else:
            rebuilt.append(line)
    if not replaced_name:
        rebuilt.insert(1, 'name = "%s"' % alias_name)
    return "\n".join(rebuilt).rstrip()


def add_provider_aliases_to_config(codex_home, source_provider, aliases, backup_dir):
    config_path = os.path.join(codex_home, "config.toml")
    text = read_text(config_path)
    backup_config_file(codex_home, backup_dir)

    source_block = extract_provider_block(text, source_provider)
    if not source_block:
        raise RuntimeError("在 config.toml 中找不到 provider '%s' 对应的配置段。" % source_provider)

    added = []
    new_text = text.rstrip()
    for alias in aliases:
        if extract_provider_block(new_text, alias):
            continue
        new_text += "\n\n" + build_alias_block(source_block, alias)
        added.append(alias)
    new_text += "\n"

    if added:
        write_text(config_path, new_text)
    return added


def repair_codex_home(codex_home, scan):
    codex_home = os.path.abspath(os.path.expanduser(codex_home))
    provider = scan["current_provider"]
    source_provider = scan.get("repair_source_provider")

    if not provider:
        raise RuntimeError("在 config.toml 中没有找到当前 provider。")
    if not source_provider:
        raise RuntimeError("无法确定应当使用哪个已配置的供货商配置来修复。")
    if source_provider not in read_defined_model_providers(codex_home):
        raise RuntimeError("config.toml 未定义该 model provider：%s" % source_provider)

    missing = scan.get("missing_history_providers", [])
    if not missing:
        result = scan_codex_home(codex_home, verify_only=True)
        result["action"] = "修复配置"
        result["aliases_added"] = []
        result["config_changed"] = False
        result["db_changed"] = 0
        result["jsonl_changed"] = 0
        return result

    backup_dir = create_backup_dir(codex_home)
    added = add_provider_aliases_to_config(codex_home, source_provider, missing, backup_dir)

    result = scan_codex_home(codex_home, verify_only=True)
    result["action"] = "修复配置"
    result["backup_dir"] = backup_dir
    result["aliases_added"] = added
    result["config_changed"] = bool(added)
    result["db_changed"] = 0
    result["jsonl_changed"] = 0
    return result


def repair_database(codex_home, provider, backup_dir):
    state_db = os.path.join(codex_home, "state_5.sqlite")
    if not os.path.isfile(state_db):
        return 0

    backup_db = os.path.join(backup_dir, "state_5.sqlite.backup")
    con = sqlite3.connect(state_db, timeout=30)
    try:
        con.execute("pragma busy_timeout=30000")
        try:
            con.execute("pragma wal_checkpoint(full)")
        except sqlite3.Error:
            pass

        shutil.copy2(state_db, backup_db)
        for suffix in ("-wal", "-shm"):
            sidecar = state_db + suffix
            if os.path.exists(sidecar):
                shutil.copy2(sidecar, os.path.join(backup_dir, os.path.basename(sidecar)))

        rowcount = con.execute(
            "update threads set model_provider = ? where model_provider is null or model_provider <> ?",
            (provider, provider),
        ).rowcount
        con.commit()
        return rowcount
    finally:
        con.close()


def update_jsonl_first_line(path, provider, codex_home, backup_dir):
    with open(path, "rb") as src:
        first = src.readline()
        if not first:
            return False

        newline = b"\r\n" if first.endswith(b"\r\n") else b"\n" if first.endswith(b"\n") else b""
        body = first[:-2] if first.endswith(b"\r\n") else first[:-1] if first.endswith(b"\n") else first
        try:
            obj = json.loads(body.decode("utf-8", errors="surrogateescape"))
        except Exception:
            return False

        payload = obj.get("payload") if isinstance(obj, dict) else None
        if obj.get("type") != "session_meta" or not isinstance(payload, dict):
            return False
        if payload.get("model_provider") == provider:
            return False

        rel = os.path.relpath(path, codex_home)
        backup_path = os.path.join(backup_dir, rel)
        os.makedirs(os.path.dirname(backup_path), exist_ok=True)
        shutil.copy2(path, backup_path)

        payload["model_provider"] = provider
        new_first = json.dumps(obj, ensure_ascii=False, separators=(",", ":")).encode(
            "utf-8", errors="surrogateescape"
        ) + newline

        tmp_path = path + ".tmp-provider-repair"
        try:
            with open(tmp_path, "wb") as dst:
                dst.write(new_first)
                shutil.copyfileobj(src, dst, length=1024 * 1024)
        except Exception:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
            raise
    os.replace(tmp_path, path)
    return True


def repair_jsonl_files(codex_home, provider, backup_dir):
    changed = 0
    for path in list_jsonl_files(codex_home):
        if update_jsonl_first_line(path, provider, codex_home, backup_dir):
            changed += 1
    return changed


def rewrite_history_to_current_provider(codex_home, scan):
    codex_home = os.path.abspath(os.path.expanduser(codex_home))
    provider = scan["current_provider"]
    if not provider:
        raise RuntimeError("在 config.toml 中没有找到当前 provider。")
    if provider not in read_defined_model_providers(codex_home):
        raise RuntimeError("config.toml 未定义该 model provider：%s" % provider)

    backup_dir = create_backup_dir(codex_home)
    backup_config_file(codex_home, backup_dir)
    db_changed = repair_database(codex_home, provider, backup_dir)
    jsonl_changed = repair_jsonl_files(codex_home, provider, backup_dir)

    result = scan_codex_home(codex_home, verify_only=True)
    result["action"] = "重写历史"
    result["backup_dir"] = backup_dir
    result["aliases_added"] = []
    result["config_changed"] = False
    result["db_changed"] = db_changed
    result["jsonl_changed"] = jsonl_changed
    return result


def backup_file_if_exists(src_path, backup_path):
    if src_path and os.path.isfile(src_path):
        os.makedirs(os.path.dirname(backup_path), exist_ok=True)
        shutil.copy2(src_path, backup_path)


def prune_empty_parent_dirs(start_path, stop_dir):
    current = os.path.dirname(start_path)
    stop_dir = os.path.abspath(stop_dir)
    while current and os.path.abspath(current).startswith(stop_dir):
        if not os.path.isdir(current):
            break
        try:
            os.rmdir(current)
        except OSError:
            break
        if os.path.abspath(current) == stop_dir:
            break
        current = os.path.dirname(current)


def rewrite_session_index(codex_home, deleted_ids, backup_dir):
    path = os.path.join(codex_home, "session_index.jsonl")
    if not os.path.isfile(path):
        return 0

    backup_file_if_exists(path, os.path.join(backup_dir, "session_index.jsonl.backup"))

    kept = []
    removed = 0
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        for line in f:
            try:
                obj = json.loads(line)
            except Exception:
                kept.append(line)
                continue
            if obj.get("id") in deleted_ids:
                removed += 1
            else:
                kept.append(line)

    with open(path, "w", encoding="utf-8", newline="") as f:
        for line in kept:
            f.write(line)
    return removed


def delete_threads_from_codex_home(codex_home, thread_ids):
    codex_home = os.path.abspath(os.path.expanduser(codex_home))
    thread_ids = sorted(set(thread_ids))
    if not thread_ids:
        raise RuntimeError("没有提供要删除的线程。")

    state_db = os.path.join(codex_home, "state_5.sqlite")
    if not os.path.isfile(state_db):
        raise RuntimeError("未找到数据库：%s" % state_db)

    backup_dir = create_backup_dir(codex_home)
    backup_config_file(codex_home, backup_dir)

    con = sqlite3.connect(state_db, timeout=30)
    try:
        con.execute("pragma busy_timeout=30000")
        try:
            con.execute("pragma wal_checkpoint(full)")
        except sqlite3.Error:
            pass

        backup_file_if_exists(state_db, os.path.join(backup_dir, "state_5.sqlite.backup"))
        for suffix in ("-wal", "-shm"):
            backup_file_if_exists(state_db + suffix, os.path.join(backup_dir, os.path.basename(state_db + suffix)))

        placeholders = ",".join("?" for _ in thread_ids)
        rows = con.execute(
            "select id, title, rollout_path from threads where id in (%s)" % placeholders,
            thread_ids,
        ).fetchall()

        found_ids = {row[0] for row in rows}
        missing_ids = [thread_id for thread_id in thread_ids if thread_id not in found_ids]
        if missing_ids:
            raise RuntimeError("这些线程在数据库中不存在：%s" % ", ".join(missing_ids))

        deleted_titles = []
        for thread_id, title, rollout_path in rows:
            deleted_titles.append(shorten_text(title or thread_id, 80))
            rollout_path = normalize_rollout_path(rollout_path)
            if rollout_path and os.path.isfile(rollout_path):
                rel = os.path.relpath(rollout_path, codex_home)
                backup_file_if_exists(rollout_path, os.path.join(backup_dir, "deleted_rollouts", rel))

        con.execute("delete from thread_goals where thread_id in (%s)" % placeholders, thread_ids)
        con.execute("delete from thread_dynamic_tools where thread_id in (%s)" % placeholders, thread_ids)
        con.execute(
            "delete from thread_spawn_edges where parent_thread_id in (%s) or child_thread_id in (%s)" % (placeholders, placeholders),
            thread_ids + thread_ids,
        )
        deleted_count = con.execute("delete from threads where id in (%s)" % placeholders, thread_ids).rowcount
        con.commit()
    finally:
        con.close()

    session_index_removed = rewrite_session_index(codex_home, set(thread_ids), backup_dir)

    deleted_rollouts = 0
    for _, _, rollout_path in rows:
        rollout_path = normalize_rollout_path(rollout_path)
        if rollout_path and os.path.isfile(rollout_path):
            try:
                os.remove(rollout_path)
                deleted_rollouts += 1
                sessions_root = os.path.join(codex_home, "sessions")
                archived_root = os.path.join(codex_home, "archived_sessions")
                if os.path.abspath(rollout_path).startswith(os.path.abspath(sessions_root)):
                    prune_empty_parent_dirs(rollout_path, sessions_root)
                elif os.path.abspath(rollout_path).startswith(os.path.abspath(archived_root)):
                    prune_empty_parent_dirs(rollout_path, archived_root)
            except OSError:
                pass

    result = scan_codex_home(codex_home, verify_only=True)
    result["action"] = "删除聊天"
    result["backup_dir"] = backup_dir
    result["deleted_count"] = deleted_count
    result["deleted_titles"] = deleted_titles
    result["deleted_rollouts"] = deleted_rollouts
    result["session_index_removed"] = session_index_removed
    return result


def format_log(result):
    action = result.get("action", "扫描")
    thread_list = result.get("thread_list", [])
    active_count = len([item for item in thread_list if not item["archived"]])
    archived_count = len([item for item in thread_list if item["archived"]])

    if action == "修复配置":
        return "配置修复完成。当前供货商链接：%s。" % (result.get("active_vendor_url") or "(无)")
    if action == "重写历史":
        return "历史重写完成。数据库修改：%s，会话文件修改：%s。" % (
            result.get("db_changed", 0),
            result.get("jsonl_changed", 0),
        )
    if action == "删除聊天":
        return "聊天删除完成。已删除聊天：%s，已删除会话文件：%s。" % (
            result.get("deleted_count", 0),
            result.get("deleted_rollouts", 0),
        )
    return "扫描完成。聊天窗口：%s，归档对话：%s，已同步：%s。" % (
        active_count,
        archived_count,
        result.get("jsonl_files_scanned", 0),
    )


if __name__ == "__main__":
    app = ProviderRepairApp()
    app.mainloop()
