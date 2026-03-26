# -*- coding: utf-8 -*-
"""
Tkinter GUI：选择最多3个数据库文件、选择输出目录、运行分析、显示日志。
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


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title('期刊数据库交集分析工具')
        self.resizable(True, True)
        self.minsize(720, 560)
        self._file_vars = []   # StringVar for each file slot
        self._out_var = tk.StringVar()
        self._running = False
        self._build_ui()
        self._setup_logging()

    # ------------------------------------------------------------------ UI --
    def _build_ui(self):
        self.columnconfigure(0, weight=1)
        self.rowconfigure(3, weight=1)

        # ---- 文件选择区域 ----
        file_frame = ttk.LabelFrame(self, text='选择数据库文件（最多3个）', padding=10)
        file_frame.grid(row=0, column=0, sticky='ew', padx=12, pady=(12, 4))
        file_frame.columnconfigure(1, weight=1)

        labels = ['文件 1（北大核心 xlsx）', '文件 2（CSSCI xlsx）', '文件 3（CSCD PDF）']
        for i, lbl_text in enumerate(labels):
            ttk.Label(file_frame, text=lbl_text).grid(row=i, column=0, sticky='w', pady=3)
            var = tk.StringVar()
            self._file_vars.append(var)
            entry = ttk.Entry(file_frame, textvariable=var, width=55)
            entry.grid(row=i, column=1, sticky='ew', padx=(6, 4), pady=3)
            btn = ttk.Button(file_frame, text='浏览…',
                             command=lambda v=var: self._browse_file(v))
            btn.grid(row=i, column=2, pady=3)

        # ---- 输出目录区域 ----
        out_frame = ttk.LabelFrame(self, text='输出设置', padding=10)
        out_frame.grid(row=1, column=0, sticky='ew', padx=12, pady=4)
        out_frame.columnconfigure(1, weight=1)

        ttk.Label(out_frame, text='输出目录').grid(row=0, column=0, sticky='w')
        ttk.Entry(out_frame, textvariable=self._out_var, width=55).grid(
            row=0, column=1, sticky='ew', padx=(6, 4))
        ttk.Button(out_frame, text='浏览…', command=self._browse_outdir).grid(row=0, column=2)

        # ---- 按钮 ----
        btn_frame = ttk.Frame(self)
        btn_frame.grid(row=2, column=0, sticky='e', padx=12, pady=6)

        self._run_btn = ttk.Button(btn_frame, text='开始分析', command=self._on_run)
        self._run_btn.pack(side='right', padx=(6, 0))
        ttk.Button(btn_frame, text='清空日志', command=self._clear_log).pack(side='right')

        # ---- 日志区域 ----
        log_frame = ttk.LabelFrame(self, text='运行日志', padding=6)
        log_frame.grid(row=3, column=0, sticky='nsew', padx=12, pady=(4, 12))
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
            row=4, column=0, sticky='ew', padx=0, pady=0)

    # --------------------------------------------------------------- 日志 --
    def _setup_logging(self):
        log_dir = os.path.join(_BASE_DIR, 'logs')
        logger_setup.setup(log_dir=log_dir, callback=self._append_log)

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

    def _clear_log(self):
        self._log_text.config(state='normal')
        self._log_text.delete('1.0', 'end')
        self._log_text.config(state='disabled')

    # ------------------------------------------------------------ 文件浏览 --
    def _browse_file(self, var: tk.StringVar):
        path = filedialog.askopenfilename(
            title='选择数据库文件',
            filetypes=[
                ('支持的文件', '*.xlsx *.xls *.pdf'),
                ('Excel 文件', '*.xlsx *.xls'),
                ('PDF 文件', '*.pdf'),
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

        files = [v.get().strip() for v in self._file_vars if v.get().strip()]
        if not files:
            messagebox.showwarning('提示', '请至少选择一个数据库文件')
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
            args=(files, output_path),
            daemon=True
        )
        thread.start()

    def _run_task(self, files, output_path):
        try:
            import main as main_module
            # 重置日志 handlers 避免重复（GUI 已在 setup 中注册 callback）
            main_module.run(files, output_path)
            self.after(0, self._on_done, output_path, None)
        except Exception as e:
            self.after(0, self._on_done, output_path, str(e))

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
