import tkinter as tk
from datetime import datetime

class WorkLogPanel(tk.Frame):
    """
    프로그램 작업 로그를 표시하는 UI 컴포넌트입니다.
    텍스트 영역과 스크롤바, 로그 지우기 버튼으로 구성됩니다.
    """
    def __init__(self, parent, bg='#f0f0f0', **kwargs):
        super().__init__(parent, bg=bg, **kwargs)
        self.setup_ui()

    def setup_ui(self):
        # 로그 제목
        self.log_title = tk.Label(
            self,
            text="📝 작업 로그",
            font=("맑은 고딕", 14, "bold"),
            bg=self.cget("bg"),
            fg='#2c3e50'
        )
        self.log_title.pack(anchor='w', pady=(0, 10))
        
        # 로그 텍스트 영역
        self.log_text = tk.Text(
            self,
            height=15,
            width=60,
            font=("맑은 고딕", 10),
            bg='#ffffff',
            fg='#2c3e50',
            relief='solid',
            borderwidth=1,
            wrap='word'
        )
        self.log_text.pack(fill='both', expand=True)
        
        # 스크롤바
        log_scrollbar = tk.Scrollbar(self, orient='vertical', command=self.log_text.yview)
        log_scrollbar.pack(side='right', fill='y')
        self.log_text.config(yscrollcommand=log_scrollbar.set)
        
        # 로그 지우기 버튼
        clear_log_button = tk.Button(
            self,
            text="🗑️ 로그 지우기",
            font=("맑은 고딕", 10),
            bg='#95a5a6',
            fg='white',
            activebackground='#7f8c8d',
            activeforeground='white',
            borderwidth=0,
            relief='flat',
            cursor='hand2',
            command=self.clear_log
        )
        clear_log_button.pack(pady=(10, 0))

    def log_message(self, message):
        """로그 메시지를 추가합니다."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_entry = f"[{timestamp}] {message}\n"
        
        # Thread-safe 하도록 after 호출이 필요할 수 있으나, 일반적으로는 caller 쪽에서 보장하거나 여기서 묶습니다.
        # GUI의 메서드로 뺄 수도 있습니다.
        self._add_log_entry(log_entry)

    def _add_log_entry(self, log_entry):
        try:
            self.log_text.insert(tk.END, log_entry)
            self.log_text.see(tk.END)
            
            # 로그가 너무 많아지면 오래된 것 삭제
            if int(self.log_text.index('end-1c').split('.')[0]) > 1000:
                self.log_text.delete('1.0', '100.0')
        except Exception as e:
            print(f"로그 엔트리 추가 실패: {e}")

    def clear_log(self):
        """로그를 지웁니다."""
        try:
            self.log_text.delete('1.0', tk.END)
            self.log_message("로그가 지워졌습니다.")
        except Exception as e:
            print(f"로그 지우기 실패: {e}")
