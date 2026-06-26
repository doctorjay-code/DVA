import tkinter as tk

class UserDashboard(tk.Frame):
    """
    유저 정보를 표시하는 대시보드 UI 컴포넌트입니다.
    사용자 이름, 포인트, 출석/퀴즈 진행 상태 등을 표시합니다.
    """
    def __init__(self, parent, bg='#ffffff', relief='solid', borderwidth=1, **kwargs):
        super().__init__(parent, bg=bg, relief=relief, borderwidth=borderwidth, **kwargs)
        self.setup_ui()

    def setup_ui(self):
        # 정보 패널 제목
        self.info_title = tk.Label(
            self,
            text="📊 사용자 정보 대시보드",
            font=("맑은 고딕", 12, "bold"),
            bg='#ffffff',
            fg='#2c3e50'
        )
        self.info_title.pack(pady=(10, 5))
        
        # 사용자 정보 프레임 생성
        self.user_info_frame = tk.Frame(self, bg='#ffffff')
        self.user_info_frame.pack(fill='x', padx=20, pady=10)
        
        # grid 레이아웃을 위한 설정
        self.user_info_frame.grid_columnconfigure(0, weight=1)
        self.user_info_frame.grid_columnconfigure(1, weight=1)
        self.user_info_frame.grid_columnconfigure(2, weight=1)
        self.user_info_frame.grid_columnconfigure(3, weight=1)
        
        # 사용자 이름
        self.user_name_label = tk.Label(
            self.user_info_frame,
            text="사용자: 로그인 필요",
            font=("맑은 고딕", 14, "bold"),
            bg='#ffffff',
            fg='#7f8c8d'
        )
        self.user_name_label.grid(row=0, column=0, columnspan=4, pady=(10, 15), sticky='ew')
        
        # 포인트 정보
        self.points_label = tk.Label(
            self.user_info_frame,
            text="포인트: 0",
            font=("맑은 고딕", 12),
            bg='#ffffff',
            fg='#2c3e50'
        )
        self.points_label.grid(row=1, column=0, pady=(0, 10), padx=(0, 20), sticky='ew')
        
        # 출석 체크 상태
        self.attendance_label = tk.Label(
            self.user_info_frame,
            text="출석 체크: 미완료",
            font=("맑은 고딕", 12),
            bg='#ffffff',
            fg='#e74c3c'
        )
        self.attendance_label.grid(row=1, column=1, pady=(0, 10), padx=(20, 20), sticky='ew')
        
        # 퀴즈 참여 상태
        self.quiz_label = tk.Label(
            self.user_info_frame,
            text="퀴즈참여: 미완료",
            font=("맑은 고딕", 12),
            bg='#ffffff',
            fg='#e74c3c'
        )
        self.quiz_label.grid(row=1, column=2, pady=(0, 10), padx=(20, 0), sticky='ew')

    def update_user_info(self, user_name=None, account_type=None):
        """사용자 이름을 업데이트합니다."""
        if user_name is not None:
            display_name = user_name if user_name != "사용자" else "로그인 필요"
            self.user_name_label.config(
                text=f"사용자: {display_name}",
                fg='#27ae60'
            )

    def update_display(self, display_type, value):
        """포인트, 출석, 퀴즈 상태를 업데이트합니다."""
        # 상태에 따른 접두어나 색상을 매핑하는 로직은 유연하게 처리
        if display_type == 'points':
            self.points_label.config(text=f"포인트: {value}", fg='#f39c12')
        elif display_type in ("attendance", "attendance_status"):
            is_done = str(value) == "True" or ("완료" in str(value) and "미완료" not in str(value))
            text_val = "완료" if is_done else "미완료"
            color_val = "#27ae60" if is_done else "#e74c3c"
            self.attendance_label.config(text=f"출석 체크: {text_val}", fg=color_val)
        elif display_type in ("quiz", "quiz_status"):
            is_done = str(value) == "True" or ("완료" in str(value) and "미완료" not in str(value))
            text_val = "완료" if is_done else "미완료"
            color_val = "#27ae60" if is_done else "#e74c3c"
            self.quiz_label.config(text=f"퀴즈참여: {text_val}", fg=color_val)
