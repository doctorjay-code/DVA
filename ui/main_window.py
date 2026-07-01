import tkinter as tk
from ui.components.user_dashboard import UserDashboard
from ui.components.work_log import WorkLogPanel
from ui.components.seminar_panel import SeminarPanel
from ui.components.tooltip import ToolTip

class MainWindow:
    """
    메인 애플리케이션 창 레이아웃을 구성하는 프레임워크 클래스입니다.
    여러 UI 컴포넌트(UserDashboard, WorkLogPanel, SeminarPanel)를 조립합니다.
    """
    def __init__(self, root, callbacks, version=None):
        """
        :param root: tk.Tk 또는 tk.Toplevel 인스턴스
        :param callbacks: 버튼 클릭이나 이벤트 처리를 위한 딕셔너리
        :param version: 프로그램 버전 문자열 (옵션)
        """
        self.root = root
        self.callbacks = callbacks
        self.version = version
        
        import os
        account_name = os.environ.get('ACCOUNT_NAME', '')
        title_suffix = f" [{account_name}]" if account_name else ""
        self.root.title(f"닥터빌 자동화 프로그램 {self.version if self.version else ''}{title_suffix}")
        self.root.geometry("1000x800")
        
        self.setup_ui()

    def setup_ui(self):
        # root에 가중치 설정
        self.root.grid_columnconfigure(0, weight=1)
        self.root.grid_rowconfigure(0, weight=1)
        
        # 메인 프레임
        self.main_frame = tk.Frame(self.root, bg='#f0f0f0')
        self.main_frame.grid(row=0, column=0, sticky='nsew', padx=20, pady=20)
        
        # main_frame에 가중치 설정
        self.main_frame.grid_columnconfigure(0, weight=1)
        self.main_frame.grid_rowconfigure(4, weight=1)  # content_frame이 확장
        
        # 1. 제목과 설정 버튼 프레임
        self.title_frame = tk.Frame(self.main_frame, bg='#f0f0f0')
        self.title_frame.grid(row=0, column=0, sticky='ew', pady=(0, 20))
        
        import os
        account_name = os.environ.get('ACCOUNT_NAME', '')
        title_suffix = f" [{account_name}]" if account_name else ""
        display_title = f"닥터빌 자동화 프로그램 {self.version if self.version else ''}{title_suffix}"
        
        self.title_label = tk.Label(
            self.title_frame,
            text=display_title,
            font=("맑은 고딕", 24, "bold"),
            bg='#f0f0f0',
            fg='#2c3e50'
        )
        self.title_label.pack(side='left')
        
        self.settings_button = tk.Button(
            self.title_frame,
            text="⚙️",
            font=("맑은 고딕", 12),
            bg='#95a5a6',
            fg='white',
            activebackground='#7f8c8d',
            activeforeground='white',
            borderwidth=0,
            relief='flat',
            cursor='hand2',
            width=3,
            height=1,
            command=self.callbacks.get('on_settings', lambda: None)
        )
        self.settings_button.pack(side='right', padx=(10, 0))
        
        self.tray_button = tk.Button(
            self.title_frame,
            text="📥",
            font=("맑은 고딕", 12),
            bg='#3498db',
            fg='white',
            activebackground='#2980b9',
            activeforeground='white',
            borderwidth=0,
            relief='flat',
            cursor='hand2',
            width=3,
            height=1,
            command=self.callbacks.get('on_hide_to_tray', lambda: None)
        )
        self.tray_button.pack(side='right', padx=(10, 0))
        ToolTip(self.tray_button, "시스템 트레이로 최소화 (백그라운드 실행)", delay=500)
        
        # 2. 사용자 정보 대시보드 (컴포넌트 사용)
        self.info_panel = tk.Frame(self.main_frame, bg='#ffffff', relief='solid', borderwidth=1)
        self.info_panel.grid(row=2, column=0, sticky='ew', pady=(0, 20), padx=10)
        self.dashboard = UserDashboard(self.info_panel, bg='#ffffff')
        self.dashboard.pack(fill='both', expand=True)
        
        # 3. 상태 표시 프레임
        self.status_frame = tk.Frame(self.main_frame, bg='#f0f0f0')
        self.status_frame.grid(row=3, column=0, sticky='ew', pady=(0, 20))
        
        self.status_label = tk.Label(
            self.status_frame,
            text="상태: 대기 중",
            font=("맑은 고딕", 12),
            bg='#f0f0f0',
            fg='#7f8c8d'
        )
        self.status_label.pack()
        
        # 4. 좌우 분할 콘텐츠 프레임
        self.content_frame = tk.Frame(self.main_frame, bg='#f0f0f0')
        self.content_frame.grid(row=4, column=0, sticky='nsew')
        
        self.content_frame.grid_columnconfigure(0, weight=0)  # 왼쪽 메뉴
        self.content_frame.grid_columnconfigure(1, weight=1)  # 오른쪽 콘텐츠영역
        self.content_frame.grid_rowconfigure(0, weight=1)
        
        # 왼쪽 프레임 (버튼들)
        self.left_frame = tk.Frame(self.content_frame, bg='#f0f0f0')
        self.left_frame.grid(row=0, column=0, sticky='nsew', padx=(0, 20))
        
        # 오른쪽 프레임 (로그 및 정보 컴포넌트)
        self.right_frame = tk.Frame(self.content_frame, bg='#f0f0f0')
        self.right_frame.grid(row=0, column=1, sticky='nsew')
        
        # 5. 좌측 메뉴 버튼들 생성
        self.setup_sidebar_buttons()
        
        # 6. 우측 컴포넌트들 조립
        # 상단: 작업 로그
        self.right_top_frame = tk.Frame(self.right_frame, bg='#f0f0f0')
        self.right_top_frame.pack(fill='both', expand=True, pady=(0, 5))
        self.right_top_frame.pack_propagate(False)
        self.work_log = WorkLogPanel(self.right_top_frame, bg='#f0f0f0')
        self.work_log.pack(fill='both', expand=True)
        
        # 하단: 오늘의 세미나
        self.right_bottom_frame = tk.Frame(self.right_frame, bg='#f0f0f0')
        self.right_bottom_frame.pack(fill='both', expand=True, pady=(5, 0))
        self.right_bottom_frame.pack_propagate(False)
        self.seminar_panel = SeminarPanel(
            self.right_bottom_frame,
            bg='#f0f0f0',
            toggle_refresh_cmd=self.callbacks.get('on_seminar_refresh_toggle'),
            double_click_cmd=self.callbacks.get('on_seminar_double_click')
        )
        self.seminar_panel.pack(fill='both', expand=True)
        
    def setup_sidebar_buttons(self):
        button_style = {
            'font': ("맑은 고딕", 12, "bold"),
            'borderwidth': 0,
            'relief': 'flat',
            'cursor': 'hand2'
        }
        
        buttons_info = [
            ("✅ 출석 체크", '#27ae60', '#229954', 'on_attendance'),
            ("🧠 퀴즈 풀이", '#e74c3c', '#c0392b', 'on_quiz'),
            ("🧠 퀴즈 문제", '#e67e22', '#d35400', 'on_quiz_problem'),
            ("📺 세미나 목록", '#9b59b6', '#8e44ad', 'on_seminar_check'),
            ("📋 세미나 풀이", '#f39c12', '#e67e22', 'on_survey_open'),
            ("🎯 세미나 문제", '#3498db', '#2980b9', 'on_survey_problem'),
            ("💳 포인트 사용", '#27ae60', '#1e8449', 'on_baemin_purchase'),
            ("🚪 프로그램 종료", '#e67e22', '#d35400', 'on_exit')
        ]
        
        self.buttons = {}
        for index, (text, bg, active_bg, callback_key) in enumerate(buttons_info):
            btn = tk.Button(
                self.left_frame,
                text=text,
                bg=bg,
                fg='white',
                activebackground=active_bg,
                activeforeground='white',
                command=self.callbacks.get(callback_key, lambda: None),
                **button_style
            )
            # 패딩 로직: 첫 버튼과 마지막 버튼은 외부 패딩을 조금 더 줌
            pady = (10, 8) if index == 0 else ((8, 10) if index == len(buttons_info)-1 else 8)
            btn.pack(fill='x', padx=10, pady=pady)
            self.buttons[text] = btn
            
        self.setup_hover_effects()

    def setup_hover_effects(self):
        """버튼 호버 효과와 툴팁을 설정합니다."""
        hover_colors = {
            '✅ 출석 체크': '#229954',
            '🧠 퀴즈 풀이': '#c0392b',
            '🧠 퀴즈 문제': '#d35400',
            '📺 세미나 목록': '#8e44ad',
            '📋 세미나 풀이': '#e67e22',
            '🎯 세미나 문제': '#2471a3',
            '💳 포인트 사용': '#1e8449',
            '🚪 프로그램 종료': '#d35400'
        }
        
        original_colors = {
            '✅ 출석 체크': '#27ae60',
            '🧠 퀴즈 풀이': '#e74c3c',
            '🧠 퀴즈 문제': '#e67e22',
            '📺 세미나 목록': '#9b59b6',
            '📋 세미나 풀이': '#f39c12',
            '🎯 세미나 문제': '#3498db',
            '💳 포인트 사용': '#27ae60',
            '🚪 프로그램 종료': '#e67e22'
        }
        
        button_tooltips = {
            '✅ 출석 체크': '닥터빌 사이트에 자동으로 출석 체크합니다.\n매일 1회 자동 실행되며 포인트가 적립됩니다.',
            '🧠 퀴즈 풀이': '오늘의 일일 퀴즈를 풀고 정답을 자동 학습합니다.\n블로그 검색 기반으로 정답 후보를 찾아 자동 제출합니다.',
            '🧠 퀴즈 문제': '성공한 일일 퀴즈 정답들을 관리합니다.\n정답 번호 및 보기 텍스트를 수동으로 편집할 수 있습니다.',
            '📺 세미나 목록': '오늘 예정된 세미나 목록 정보를 조회하고 입장합니다.\n자동 신청, 자동 입장 및 입장 대기시간 설정이 가능합니다.',
            '📋 세미나 풀이': '강의 종료 후 세미나 설문을 자동으로 풀이하고 제출합니다.\n지연 풀기 대기열 및 Gemini AI 주관식 자동 완성을 지원합니다.',
            '🎯 세미나 문제': '세미나 설문 전용 문제와 정답 DB를 조회하고 관리합니다.\n카테고리별 정렬 및 선택지(보기 목록)를 제공합니다.',
            '💳 포인트 사용': '포인트를 소모해 배민 쿠폰 등을 구매합니다.\n기프티콘 정보 조회 및 수동/자동 포인트 결제를 지원합니다.',
            '🚪 프로그램 종료': '백그라운드 크롬 브라우저를 안전하게 정리하고 프로그램을 종료합니다.'
        }
        
        for text, btn in self.buttons.items():
            if text in hover_colors:
                hover_color = hover_colors[text]
                orig_color = original_colors.get(text, '#95a5a6')
                btn.bind('<Enter>', lambda e, b=btn, c=hover_color: b.config(bg=c))
                btn.bind('<Leave>', lambda e, b=btn, c=orig_color: b.config(bg=c))
            
            if text in button_tooltips:
                try:
                    ToolTip(btn, button_tooltips[text], delay=500)
                except Exception:
                    pass
                    
    def update_status(self, status):
        """메인 상태 라벨 업데이트"""
        self.status_label.config(text=f"상태: {status}")
        self.root.update_idletasks()
