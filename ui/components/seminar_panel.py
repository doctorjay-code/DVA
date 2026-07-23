import tkinter as tk
from tkinter import ttk

class SeminarPanel(tk.Frame):
    """
    오늘의 세미나 목록을 보여주는 표(Treeview) UI 컴포넌트입니다.
    """
    def __init__(self, parent, bg='#f0f0f0', toggle_refresh_cmd=None, double_click_cmd=None, **kwargs):
        super().__init__(parent, bg=bg, **kwargs)
        self.toggle_refresh_cmd = toggle_refresh_cmd
        self.double_click_cmd = double_click_cmd
        self.setup_ui()

    def setup_ui(self):
        # 세미나 제목 + 멈춤 버튼 프레임
        seminar_header_frame = tk.Frame(self, bg=self.cget("bg"))
        seminar_header_frame.pack(fill='x', pady=(0, 10))
        
        self.seminar_title = tk.Label(
            seminar_header_frame,
            text="📺 오늘의 세미나",
            font=("맑은 고딕", 14, "bold"),
            bg=self.cget("bg"),
            fg='#2c3e50'
        )
        self.seminar_title.pack(side='left')
        
        # 새로고침 멈춤/재개 버튼
        self.seminar_refresh_btn = tk.Button(
            seminar_header_frame,
            text="🟢 새로고침 중",
            font=("맑은 고딕", 9, "bold"),
            bg='#27ae60',
            fg='white',
            relief='flat',
            cursor='hand2',
            padx=5,
            command=self._on_toggle_refresh
        )
        self.seminar_refresh_btn.pack(side='right', padx=(0, 10))
        
        # 세미나 정보 표시 영역
        self.seminar_info_frame = tk.Frame(self, bg='#ffffff', relief='solid', borderwidth=1)
        self.seminar_info_frame.pack(fill='both', expand=True, padx=10)
        
        # 트리뷰 생성
        columns = ('날짜', '요일', '시간', '강의명', '강의자', '신청인원', '신청상태')
        self.seminar_tree = ttk.Treeview(self.seminar_info_frame, columns=columns, show='headings', height=8)
        
        # 컬럼 설정
        for col in columns:
            self.seminar_tree.heading(col, text=col)
            
        # 컬럼 너비 설정
        self.seminar_tree.column('날짜', width=70, anchor='center')
        self.seminar_tree.column('요일', width=50, anchor='center')
        self.seminar_tree.column('시간', width=80, anchor='center')
        self.seminar_tree.column('강의명', width=200, anchor='w')
        self.seminar_tree.column('강의자', width=120, anchor='w')
        self.seminar_tree.column('신청인원', width=70, anchor='center')
        self.seminar_tree.column('신청상태', width=80, anchor='center')
        
        # 스크롤바 추가
        seminar_scrollbar = ttk.Scrollbar(self.seminar_info_frame, orient=tk.VERTICAL, command=self.seminar_tree.yview)
        self.seminar_tree.configure(yscrollcommand=seminar_scrollbar.set)
        
        # 트리뷰와 스크롤바 배치
        self.seminar_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(10, 0), pady=10)
        seminar_scrollbar.pack(side=tk.RIGHT, fill=tk.Y, pady=10)
        
        # 초기 메시지 표시
        self.seminar_tree.insert('', 'end', values=("", "", "", "자동 로그인 후 세미나 정보가 자동으로 수집됩니다", "", "", ""))
        
        # 상태별 색상 설정
        self.seminar_tree.tag_configure('신청가능', background='#d5f4e6', foreground='#2e7d32')
        self.seminar_tree.tag_configure('신청완료', background='#fef9e7', foreground='#f39c12')
        self.seminar_tree.tag_configure('신청마감', background='#fadbd8', foreground='#e74c3c')
        self.seminar_tree.tag_configure('입장하기', background='#d6eaf8', foreground='#3498db')
        self.seminar_tree.tag_configure('대기중', background='#f8f9fa', foreground='#6c757d')
        self.seminar_tree.tag_configure('기타', background='#f4f6f6', foreground='#34495e')
        
        # 더블클릭 이벤트
        if self.double_click_cmd:
            self.seminar_tree.bind('<Double-1>', self.double_click_cmd)
            
    def _on_toggle_refresh(self):
        if self.toggle_refresh_cmd:
            self.toggle_refresh_cmd(self.seminar_refresh_btn)
            
    def clear_all(self):
        """트리뷰의 모든 항목을 지웁니다."""
        for item in self.seminar_tree.get_children():
            self.seminar_tree.delete(item)
            
    def insert_item(self, values, tags=()):
        """트리뷰에 세미나 항목을 추가합니다."""
        self.seminar_tree.insert('', 'end', values=values, tags=tags)
