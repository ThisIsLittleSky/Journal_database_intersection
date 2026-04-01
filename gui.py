# -*- coding: utf-8 -*-
"""
Tkinter GUI：支持动态选择 2-10 个数据库文件、选择输出目录、运行分析、显示日志。
"""
import os
import sys
import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

# 确保 main.py 所在目录在 sys.path 中
_BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if _BASE_DIR not in sys.path:
    sys.path.insert(0, _BASE_DIR)

import logger_setup
from core import config as app_config


class App(tk.Tk):
    MIN_FILES = 2
    MAX_FILES = 10

    def __init__(self):
        super().__init__()
        self.title('期刊数据库交集分析工具')
        self.resizable(True, True)
        self.minsize(820, 620)
        self._file_vars = []
        self._out_var = tk.StringVar()
        self._export_mode_var = tk.StringVar(value='简洁模式')
        self._api_key_var = tk.StringVar()
        self._running = False
        self._load_saved_config()
        self._build_ui()
        self._setup_logging()
        self.protocol('WM_DELETE_WINDOW', self._on_close)

    # ------------------------------------------------------------------ UI --
    def _build_ui(self):
        self.columnconfigure(0, weight=1)
        self.rowconfigure(4, weight=1)

        file_frame = ttk.LabelFrame(self, text='选择数据库文件（2-10个）', padding=10)
        file_frame.grid(row=0, column=0, sticky='ew', padx=12, pady=(12, 4))
        file_frame.columnconfigure(1, weight=1)
        self._file_frame = file_frame

        action_frame = ttk.Frame(file_frame)
        action_frame.grid(row=0, column=0, columnspan=3, sticky='ew', pady=(0, 8))
        action_frame.columnconfigure(0, weight=1)
        ttk.Label(
            action_frame,
            text='支持格式：xlsx、xls、csv、txt、pdf、docx、doc、html'
        ).grid(row=0, column=0, sticky='w')
        ttk.Button(action_frame, text='添加文件', command=self._add_file_row).grid(
            row=0, column=1, padx=(4, 4))
        ttk.Button(action_frame, text='删除最后一个', command=self._remove_file_row).grid(
            row=0, column=2)

        self._file_list_frame = ttk.Frame(file_frame)
        self._file_list_frame.grid(row=1, column=0, columnspan=3, sticky='ew')
        self._file_list_frame.columnconfigure(1, weight=1)

        for _ in range(self.MIN_FILES):
            self._file_vars.append(tk.StringVar())
        self._refresh_file_rows()

        # ---- 输出目录区域 ----
        out_frame = ttk.LabelFrame(self, text='输出设置', padding=10)
        out_frame.grid(row=1, column=0, sticky='ew', padx=12, pady=4)
        out_frame.columnconfigure(1, weight=1)

        ttk.Label(out_frame, text='输出目录').grid(row=0, column=0, sticky='w')
        ttk.Entry(out_frame, textvariable=self._out_var, width=55).grid(
            row=0, column=1, sticky='ew', padx=(6, 4))
        ttk.Button(out_frame, text='浏览…', command=self._browse_outdir).grid(row=0, column=2)
        ttk.Label(out_frame, text='导出模式').grid(row=1, column=0, sticky='w', pady=(8, 0))
        ttk.Combobox(
            out_frame,
            textvariable=self._export_mode_var,
            state='readonly',
            values=('简洁模式', '完整模式'),
            width=12
        ).grid(row=1, column=1, sticky='w', padx=(6, 4), pady=(8, 0))

        llm_frame = ttk.LabelFrame(self, text='LLM 配置', padding=10)
        llm_frame.grid(row=2, column=0, sticky='ew', padx=12, pady=4)
        llm_frame.columnconfigure(1, weight=1)
        ttk.Label(llm_frame, text='DeepSeek API Key').grid(row=0, column=0, sticky='w')
        api_entry = ttk.Entry(llm_frame, textvariable=self._api_key_var, show='*', width=55)
        api_entry.grid(row=0, column=1, sticky='ew', padx=(6, 4))
        api_entry.bind('<FocusOut>', lambda _event: self._save_config())
        ttk.Label(
            llm_frame,
            text='填写后将保存到 conf_Journal_database_intersection.conf（与 exe 同目录）'
        ).grid(row=1, column=0, columnspan=3, sticky='w', pady=(6, 0))

        # ---- 按钮 ----
        btn_frame = ttk.Frame(self)
        btn_frame.grid(row=3, column=0, sticky='e', padx=12, pady=6)

        self._run_btn = ttk.Button(btn_frame, text='开始分析', command=self._on_run)
        self._run_btn.pack(side='right', padx=(6, 0))
        ttk.Button(btn_frame, text='清空日志', command=self._clear_log).pack(side='right')

        # ---- 日志区域 ----
        log_frame = ttk.LabelFrame(self, text='运行日志', padding=6)
        log_frame.grid(row=4, column=0, sticky='nsew', padx=12, pady=(4, 12))
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(0, weight=1)

        self._log_text = tk.Text(log_frame, wrap='word', state='disabled',
                                  bg='#1E1E1E', fg='#D4D4D4',
                                  font=('Consolas', 9), relief='flat')
        self._log_text.grid(row=0, column=0, sticky='nsew')

        sb = ttk.Scrollbar(log_frame, orient='vertical', command=self._log_text.yview)
        sb.grid(row=0, column=1, sticky='ns')
        self._log_text['yscrollcommand'] = sb.set

        # 日志颜色标签
        self._log_text.tag_config('INFO', foreground='#9CDCFE')
        self._log_text.tag_config('ERROR', foreground='#F44747')
        self._log_text.tag_config('WARNING', foreground='#CE9178')

        # ---- 状态栏 ----
        self._status_var = tk.StringVar(value='就绪')
        ttk.Label(self, textvariable=self._status_var,
                  relief='sunken', anchor='w').grid(
            row=5, column=0, sticky='ew', padx=0, pady=0)

    # --------------------------------------------------------------- 日志 --
    def _setup_logging(self):
        log_dir = os.path.join(_BASE_DIR, 'logs')
        logger_setup.setup(log_dir=log_dir, callback=self._append_log)

    def _load_saved_config(self):
        saved = app_config.load_app_config()
        self._api_key_var.set(saved.get('llm_api_key', ''))

    def _save_config(self):
        api_key = self._api_key_var.get().strip()
        app_config.save_app_config({
            'llm_enabled': bool(api_key),
            'llm_api_key': api_key,
            'llm_base_url': app_config.DEFAULT_BASE_URL,
            'llm_model': app_config.DEFAULT_MODEL,
        })

    def _append_log(self, msg: str):
        """线程安全地向日志文本框追加消息。"""
        self.after(0, self._do_append_log, msg)

    def _do_append_log(self, msg: str):
        self._log_text.config(state='normal')
        tag = 'INFO'
        if '[ERROR]' in msg:
            tag = 'ERROR'
        elif '[WARNING]' in msg:
            tag = 'WARNING'
        self._log_text.insert('end', msg + '\n', tag)
        self._log_text.see('end')
        self._log_text.config(state='disabled')

    def _refresh_file_rows(self):
        for child in self._file_list_frame.winfo_children():
            child.destroy()

        for idx, var in enumerate(self._file_vars, 1):
            ttk.Label(self._file_list_frame, text=f'文件 {idx}').grid(
                row=idx - 1, column=0, sticky='w', pady=3)
            ttk.Entry(self._file_list_frame, textvariable=var, width=68).grid(
                row=idx - 1, column=1, sticky='ew', padx=(6, 4), pady=3)
            ttk.Button(
                self._file_list_frame,
                text='浏览…',
                command=lambda current_var=var: self._browse_file(current_var)
            ).grid(row=idx - 1, column=2, pady=3)

    def _add_file_row(self):
        if len(self._file_vars) >= self.MAX_FILES:
            messagebox.showinfo('提示', f'最多支持 {self.MAX_FILES} 个文件')
            return
        self._file_vars.append(tk.StringVar())
        self._refresh_file_rows()

    def _remove_file_row(self):
        if len(self._file_vars) <= self.MIN_FILES:
            messagebox.showinfo('提示', f'至少保留 {self.MIN_FILES} 个文件')
            return
        self._file_vars.pop()
        self._refresh_file_rows()

    def _clear_log(self):
        self._log_text.config(state='normal')
        self._log_text.delete('1.0', 'end')
        self._log_text.config(state='disabled')

    # ------------------------------------------------------------ 文件浏览 --
    def _browse_file(self, var: tk.StringVar):
        path = filedialog.askopenfilename(
            title='选择数据库文件',
            filetypes=[
                ('支持的文件', '*.xlsx *.xls *.csv *.txt *.pdf *.docx *.doc *.rtf *.html *.htm'),
                ('Excel 文件', '*.xlsx *.xls'),
                ('CSV 文件', '*.csv'),
                ('文本文件', '*.txt'),
                ('PDF 文件', '*.pdf'),
                ('Word 文件', '*.docx *.doc *.rtf'),
                ('HTML 文件', '*.html *.htm'),
                ('所有文件', '*.*'),
            ]
        )
        if path:
            var.set(path)

    def _browse_outdir(self):
        path = filedialog.askdirectory(title='选择输出目录')
        if path:
            self._out_var.set(path)

    # --------------------------------------------------------------- 运行 --
    def _on_run(self):
        if self._running:
            return

        self._save_config()

        files = [v.get().strip() for v in self._file_vars if v.get().strip()]
        if len(files) < self.MIN_FILES:
            messagebox.showwarning('提示', f'请至少选择 {self.MIN_FILES} 个数据库文件')
            return
        if len(files) > self.MAX_FILES:
            messagebox.showwarning('提示', f'最多只能选择 {self.MAX_FILES} 个数据库文件')
            return

        out_dir = self._out_var.get().strip()
        if not out_dir:
            out_dir = os.path.dirname(files[0])
            self._out_var.set(out_dir)

        for fp in files:
            if not os.path.exists(fp):
                messagebox.showerror('错误', f'文件不存在：{fp}')
                return

        from datetime import datetime
        ts = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_path = os.path.join(out_dir, f'期刊交集分析_{ts}.xlsx')

        self._running = True
        self._run_btn.config(state='disabled', text='分析中…')
        self._status_var.set('分析中，请稍候…')

        thread = threading.Thread(
            target=self._run_task,
            args=(files, output_path, self._get_export_mode(), self._build_llm_config()),
            daemon=True
        )
        thread.start()

    def _get_export_mode(self):
        return 'full' if self._export_mode_var.get() == '完整模式' else 'compact'

    def _build_llm_config(self):
        return app_config.build_llm_config({
            'llm_enabled': bool(self._api_key_var.get().strip()),
            'llm_api_key': self._api_key_var.get().strip(),
            'llm_base_url': app_config.DEFAULT_BASE_URL,
            'llm_model': app_config.DEFAULT_MODEL,
        })

    def _run_task(self, files, output_path, export_mode, llm_config):
        try:
            import main as main_module
            main_module.run(
                files,
                output_path,
                export_mode=export_mode,
                llm_config=llm_config,
            )
            self.after(0, self._on_done, output_path, None)
        except Exception as e:
            self.after(0, self._on_done, output_path, str(e))

    def _on_close(self):
        self._save_config()
        self.destroy()

    def _on_done(self, output_path, error):
        self._running = False
        self._run_btn.config(state='normal', text='开始分析')
        if error:
            self._status_var.set(f'分析失败：{error}')
            messagebox.showerror('分析失败', f'发生错误：\n{error}')
        else:
            self._status_var.set(f'完成！输出：{output_path}')
            if messagebox.askyesno('完成', f'分析完成！\n结果已保存至：\n{output_path}\n\n是否打开文件所在目录？'):
                import subprocess
                subprocess.Popen(f'explorer /select,"{output_path}"')


def main():
    app = App()
    app.mainloop()


if __name__ == '__main__':
    main()
