# -*- coding: utf-8 -*-
import tkinter as tk
from tkinter import ttk, messagebox
import subprocess
import sys
from ui.components.tooltip import ToolTip

class KakaoWizardDialog:
    def __init__(self, parent, get_setting_func, save_callback, start_auth_callback=None):
        self.parent = parent
        self.get_setting = get_setting_func
        self.save_callback = save_callback
        self.start_auth_callback = start_auth_callback
        
        self.window = tk.Toplevel(parent)
        self.window.title("💬 카카오 알림 연동 도우미")
        self.window.geometry("560x780")
        self.window.configure(bg='#ffffff')
        self.window.resizable(False, False)
        
        self.window.transient(parent)
        self.window.grab_set()
        self.window.lift()
        self.window.focus_force()
        
        # Center the window
        self.window.update_idletasks()
        w = self.window.winfo_width()
        h = self.window.winfo_height()
        x = parent.winfo_x() + (parent.winfo_width() // 2) - (w // 2)
        y = parent.winfo_y() + (parent.winfo_height() // 2) - (h // 2)
        self.window.geometry(f"+{x}+{y}")
        
        self._setup_ui()
        
    def _setup_ui(self):
        # 헤더 배너
        header = tk.Frame(self.window, bg='#fee500', height=85)
        header.pack(fill='x', side='top')
        header.pack_propagate(False)
        
        tk.Label(
            header, text="💬 카카오 알림 초간편 3분 연동 도우미",
            font=("맑은 고딕", 15, "bold"), bg='#fee500', fg='#3c1e1e'
        ).pack(pady=(15, 2))
        
        tk.Label(
            header, text="처음 설정하시는 분들도 아래 안내에 따라 차근차근 클릭하시면 3분 만에 끝납니다!",
            font=("맑은 고딕", 9), bg='#fee500', fg='#3c1e1e'
        ).pack()
        
        # 스크롤 가능한 본문 프레임
        main_container = tk.Frame(self.window, bg='#ffffff')
        main_container.pack(fill='both', expand=True, padx=25, pady=15)
        
        canvas = tk.Canvas(main_container, bg='#ffffff', highlightthickness=0)
        scrollbar = ttk.Scrollbar(main_container, orient="vertical", command=canvas.yview)
        
        self.scroll_frame = tk.Frame(canvas, bg='#ffffff')
        self.scroll_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas_frame = canvas.create_window((0, 0), window=self.scroll_frame, anchor="nw")
        
        def _configure_canvas(event):
            canvas.itemconfig(canvas_frame, width=event.width)
        canvas.bind("<Configure>", _configure_canvas)
        
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # 마우스 휠 지원
        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        canvas.bind_all("<MouseWheel>", _on_mousewheel)
        self.canvas = canvas
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # --- 단계별 카드식 UI ---
        
        # 1단계
        self._add_step_card(
            self.scroll_frame, "1단계: 카카오 개발자 콘솔 접속 & 로그인",
            "아래 버튼을 클릭해 카카오 개발자 사이트로 이동하신 후,\n평소 쓰시는 카카오 계정으로 로그인해 주세요.",
            btn_text="🌐 카카오 개발자 콘솔 바로가기",
            btn_cmd=lambda: self._open_url("https://developers.kakao.com/console/app")
        )
        
        # 2단계
        self._add_step_card(
            self.scroll_frame, "2단계: 애플리케이션 생성 (앱 추가)",
            "화면 우측 상단의 [➕ 앱 생성] 버튼을 클릭하신 후,\n다음 정보를 입력하고 [저장]을 눌러 앱을 만드세요.\n\n"
            "• 앱 이름: DVA 입력\n"
            "• 회사명: 개인 입력\n"
            "• 카테고리: 아무 카테고리나 선택 (예: IT/기술)\n"
            "• 약관 동의 체크박스 필수 체크!"
        )
        
        # 3단계
        self._add_step_card(
            self.scroll_frame, "3단계: 플랫폼 키에서 REST API 키 복사",
            "방금 만들어진 DVA 앱을 클릭해 들어가신 뒤,\n"
            "왼쪽 메뉴에서 [앱 설정] ➡️ [플랫폼 키]로 이동합니다.\n\n"
            "• 화면 첫 번째에 표시된 'REST API 키'의 복사(📋) 버튼을 클릭해 복사합니다."
        )
        
        # 4단계
        self._add_step_card(
            self.scroll_frame, "4단계: 카카오 로그인 활성화 및 주소 등록",
            "프로그램 연동을 위한 필수 보안 설정을 진행합니다.\n\n"
            "① 왼쪽 메뉴에서 [카카오 로그인] 클릭 ➡️ 활성화 상태를 [ON]으로 변경\n"
            "② 그 바로 아래 [Redirect URI 등록] 클릭 ➡️ http://localhost 입력 후 저장"
        )
        
        # 5단계
        self._add_step_card(
            self.scroll_frame, "5단계: 카카오톡 메시지 전송 권한 승인",
            "프로그램이 카톡을 보낼 수 있도록 동의해 주는 마지막 설정입니다.\n\n"
            "① 왼쪽 메뉴에서 [카카오 로그인] ➡️ [동의항목] 클릭\n"
            "② 맨 아래 [카카오톡 메시지 전송] 항목의 [설정] 클릭\n"
            "③ [이용자 동의] 체크박스 체크 후 저장 클릭"
        )
        
        # --- 입력 및 완료 영역 ---
        input_frame = tk.LabelFrame(
            self.scroll_frame, text="🔑 3단계에서 복사한 REST API 키를 등록하세요",
            font=("맑은 고딕", 11, "bold"), bg='#ffffff', fg='#2c3e50', padx=15, pady=15, relief='solid', borderwidth=1
        )
        input_frame.pack(fill='x', pady=(15, 10))
        
        self.key_entry = tk.Entry(
            input_frame, font=("Consolas", 12), justify='center',
            relief='solid', borderwidth=1, bg='#f8f9fa'
        )
        self.key_entry.pack(fill='x', ipady=6, pady=(0, 15))
        
        # 기존 키가 있다면 채워두기
        existing_key = self.get_setting('kakao_rest_api_key')
        if existing_key:
            self.key_entry.insert(0, existing_key)
            
        start_btn = tk.Button(
            input_frame, text="🚀 설정 완료 및 자동 로그인 연동 시작",
            font=("맑은 고딕", 12, "bold"), bg='#fee500', fg='#3c1e1e',
            activebackground='#edd000', activeforeground='#3c1e1e',
            relief='flat', cursor='hand2', padx=10, pady=10,
            command=self._on_confirm
        )
        start_btn.pack(fill='x')
        
    def _add_step_card(self, parent, title, desc, btn_text=None, btn_cmd=None):
        card = tk.Frame(parent, bg='#f8f9fa', padx=15, pady=12, relief='solid', borderwidth=1)
        card.pack(fill='x', pady=(0, 12))
        
        tk.Label(
            card, text=title, font=("맑은 고딕", 10, "bold"),
            bg='#f8f9fa', fg='#2c3e50', anchor='w'
        ).pack(fill='x', pady=(0, 5))
        
        tk.Label(
            card, text=desc, font=("맑은 고딕", 9),
            bg='#f8f9fa', fg='#555555', justify='left', anchor='w'
        ).pack(fill='x', pady=(0, 5))
        
        if btn_text and btn_cmd:
            btn = tk.Button(
                card, text=btn_text, font=("맑은 고딕", 9, "bold"),
                bg='#3498db', fg='white', relief='flat', cursor='hand2',
                padx=10, pady=4, command=btn_cmd
            )
            btn.pack(anchor='w', pady=(3, 0))
            
    def _open_url(self, url):
        import webbrowser
        webbrowser.open(url)
        
    def _on_confirm(self):
        key = self.key_entry.get().strip()
        if not key:
            messagebox.showwarning("입력 필요", "REST API 키를 입력해 주세요.", parent=self.window)
            return
            
        # 32자리 검사 등 간단 포맷 체크
        if len(key) != 32:
            if not messagebox.askyesno("확인", "일반적인 카카오 REST API 키는 32자리 글자입니다. 입력한 키가 정확한가요?", parent=self.window):
                return
                
        # settings.json에 저장
        settings_path = "data/settings.json"
        import os, json
        settings = {}
        if os.path.exists(settings_path):
            try:
                with open(settings_path, 'r', encoding='utf-8') as f:
                    settings = json.load(f)
            except:
                pass
                
        settings['kakao_rest_api_key'] = key
        
        os.makedirs(os.path.dirname(settings_path), exist_ok=True)
        with open(settings_path, 'w', encoding='utf-8') as f:
            json.dump(settings, f, indent=2, ensure_ascii=False)
            
        # 설정 변수 동기화
        self.save_callback(settings)
        
        self.window.destroy()
        self.canvas.unbind_all("<MouseWheel>")
        
        # 재인증 플로우 시작
        if self.start_auth_callback:
            # Toplevel의 destroy 딜레이를 고려하여 살짝 뒤에 실행
            self.parent.after(100, lambda: self.start_auth_callback(self.parent))


class SettingsDialog:
    def __init__(self, parent, get_setting_func, save_callback, close_callback, open_browser_func=None):
        self.parent = parent
        self.get_setting = get_setting_func
        self.save_callback = save_callback
        self.close_callback = close_callback
        self.open_browser_func = open_browser_func
        
        self.setting_vars = {}
        self._seminar_sub_widgets = []
        self._notify_sub_widgets = []
        
        self.settings_window = tk.Toplevel(parent)
        self.settings_window.title("⚙️ 설정")
        
        # 저장된 창 크기 불러오기
        width = self.get_setting('settings_window_width') or 600
        height = self.get_setting('settings_window_height') or 800
        self.settings_window.geometry(f"{width}x{height}")
        
        self.settings_window.configure(bg='#f0f0f0')
        self.settings_window.resizable(True, True)
        
        # 부모 창이 보일 때만 transient로 묶어줍니다 (트레이에 있을 때는 독립적으로 띄움)
        if parent.state() != 'withdrawn':
            self.settings_window.transient(parent)
        
        self.settings_window.grab_set()
        self.settings_window.lift()
        self.settings_window.focus_force()
        
        self._setup_ui()
        
        # 창이 닫힐 때 처리
        self.settings_window.protocol("WM_DELETE_WINDOW", self._on_closing)

    def _setup_ui(self):
        # 1. 하단 버튼 프레임
        bottom_frame = tk.Frame(self.settings_window, bg='#ffffff', pady=15, padx=20, relief='raised', borderwidth=1)
        bottom_frame.pack(side='bottom', fill='x')
        
        btn_container = tk.Frame(bottom_frame, bg='#ffffff')
        btn_container.pack()
        
        save_button = tk.Button(
            btn_container, text="💾 설정 저장", font=("맑은 고딕", 12, "bold"),
            bg='#27ae60', fg='white', activebackground='#229954', activeforeground='white',
            borderwidth=0, padx=20, pady=8, relief='flat', cursor='hand2',
            command=self._on_save
        )
        save_button.pack(side='left', padx=10)
        
        close_button = tk.Button(
            btn_container, text="❌ 닫기", font=("맑은 고딕", 12, "bold"),
            bg='#e74c3c', fg='white', activebackground='#c0392b', activeforeground='white',
            borderwidth=0, padx=20, pady=8, relief='flat', cursor='hand2',
            command=self._on_closing
        )
        close_button.pack(side='left', padx=10)
        
        # 2. 스크롤 가능한 영역
        container = tk.Frame(self.settings_window, bg='#f0f0f0')
        container.pack(side='top', fill='both', expand=True)
        
        canvas = tk.Canvas(container, bg='#f0f0f0', highlightthickness=0)
        scrollbar = ttk.Scrollbar(container, orient="vertical", command=canvas.yview)
        
        self.scrollable_frame = tk.Frame(canvas, bg='#f0f0f0')
        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas_frame = canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        
        def _configure_canvas(event):
            canvas.itemconfig(canvas_frame, width=event.width)
        canvas.bind("<Configure>", _configure_canvas)
        
        canvas.configure(yscrollcommand=scrollbar.set)
        
        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        canvas.bind_all("<MouseWheel>", _on_mousewheel)
        self.canvas = canvas # Store for unbinding
        
        canvas.pack(side="left", fill="both", expand=True, padx=(20, 0), pady=20)
        scrollbar.pack(side="right", fill="y", pady=20)
        
        # 3. 설정 내용 채우기
        tk.Label(
            self.scrollable_frame, text="⚙️ 프로그램 설정",
            font=("맑은 고딕", 18, "bold"), bg='#f0f0f0', fg='#2c3e50'
        ).pack(pady=(0, 20))
        
        self._setup_options(self.scrollable_frame)

    def _setup_options(self, parent):
        # 자동 실행 설정 섹션
        auto_frame = tk.LabelFrame(
            parent, text="🤖 자동 실행 설정", font=("맑은 고딕", 12, "bold"),
            bg='#f0f0f0', fg='#2c3e50', padx=10, pady=5
        )
        auto_frame.pack(fill='x', pady=(0, 10))
        
        # 1. 자동 출석체크
        self.setting_vars['auto_attendance'] = tk.BooleanVar(value=self.get_setting('auto_attendance'))
        attendance_check = tk.Checkbutton(
            auto_frame, text="✅ 자동 출석체크", variable=self.setting_vars['auto_attendance'],
            font=("맑은 고딕", 11), bg='#f0f0f0', fg='#2c3e50',
            activebackground='#f0f0f0', activeforeground='#2c3e50'
        )
        attendance_check.pack(anchor='w', pady=(2, 0))
        
        attendance_time_frame = tk.Frame(auto_frame, bg='#f0f0f0')
        attendance_time_frame.pack(anchor='w', pady=(0, 5), padx=25)
        
        attendance_widgets = []
        def _on_attendance_toggle():
            state = 'normal' if self.setting_vars['auto_attendance'].get() else 'disabled'
            for w in attendance_widgets:
                try: w.configure(state=state)
                except: pass
        
        lbl_time = tk.Label(attendance_time_frame, text="⏰ 실행 시간:", font=("맑은 고딕", 10), bg='#f0f0f0', fg='#2c3e50')
        lbl_time.pack(side='left')
        attendance_widgets.append(lbl_time)
        attendance_check.configure(command=_on_attendance_toggle)
        
        self.setting_vars['auto_attendance_hour'] = tk.StringVar(value=str(self.get_setting('auto_attendance_hour')))
        hour_spin = tk.Spinbox(attendance_time_frame, from_=0, to=23, textvariable=self.setting_vars['auto_attendance_hour'], width=3, font=("맑은 고딕", 10, "bold"), justify='center')
        hour_spin.pack(side='left', padx=2)
        attendance_widgets.append(hour_spin)
        
        tk.Label(attendance_time_frame, text="시", font=("맑은 고딕", 10), bg='#f0f0f0', fg='#2c3e50').pack(side='left')
        
        self.setting_vars['auto_attendance_min'] = tk.StringVar(value=str(self.get_setting('auto_attendance_min')))
        min_spin = tk.Spinbox(attendance_time_frame, from_=0, to=59, textvariable=self.setting_vars['auto_attendance_min'], width=3, font=("맑은 고딕", 10, "bold"), justify='center')
        min_spin.pack(side='left', padx=2)
        attendance_widgets.append(min_spin)
        
        tk.Label(attendance_time_frame, text="분", font=("맑은 고딕", 10), bg='#f0f0f0', fg='#2c3e50').pack(side='left')
        
        tk.Label(
            auto_frame, text="  └ 지정한 시간에 오늘의 출석체크를 자동으로 진행합니다.",
            font=("맑은 고딕", 9), bg='#f0f0f0', fg='#7f8c8d'
        ).pack(anchor='w', pady=(0, 5), padx=25)

        # 2. 자동 퀴즈풀기
        self.setting_vars['auto_quiz'] = tk.BooleanVar(value=self.get_setting('auto_quiz'))
        quiz_check = tk.Checkbutton(
            auto_frame, text="🧠 자동 퀴즈풀기", variable=self.setting_vars['auto_quiz'],
            font=("맑은 고딕", 11), bg='#f0f0f0', fg='#2c3e50',
            activebackground='#f0f0f0', activeforeground='#2c3e50'
        )
        quiz_check.pack(anchor='w', pady=(2, 0))
        
        quiz_time_frame = tk.Frame(auto_frame, bg='#f0f0f0')
        quiz_time_frame.pack(anchor='w', pady=(0, 5), padx=25)
        
        quiz_widgets = []
        def _on_quiz_toggle():
            state = 'normal' if self.setting_vars['auto_quiz'].get() else 'disabled'
            for w in quiz_widgets:
                try: w.configure(state=state)
                except: pass
        
        lbl_q_time = tk.Label(quiz_time_frame, text="⏰ 실행 시간:", font=("맑은 고딕", 10), bg='#f0f0f0', fg='#2c3e50')
        lbl_q_time.pack(side='left')
        quiz_widgets.append(lbl_q_time)
        quiz_check.configure(command=_on_quiz_toggle)
        
        self.setting_vars['auto_quiz_hour'] = tk.StringVar(value=str(self.get_setting('auto_quiz_hour')))
        q_hour_spin = tk.Spinbox(quiz_time_frame, from_=0, to=23, textvariable=self.setting_vars['auto_quiz_hour'], width=3, font=("맑은 고딕", 10, "bold"), justify='center')
        q_hour_spin.pack(side='left', padx=2)
        quiz_widgets.append(q_hour_spin)
        
        tk.Label(quiz_time_frame, text="시", font=("맑은 고딕", 10), bg='#f0f0f0', fg='#2c3e50').pack(side='left')
        
        self.setting_vars['auto_quiz_min'] = tk.StringVar(value=str(self.get_setting('auto_quiz_min')))
        q_min_spin = tk.Spinbox(quiz_time_frame, from_=0, to=59, textvariable=self.setting_vars['auto_quiz_min'], width=3, font=("맑은 고딕", 10, "bold"), justify='center')
        q_min_spin.pack(side='left', padx=2)
        quiz_widgets.append(q_min_spin)
        
        tk.Label(quiz_time_frame, text="분", font=("맑은 고딕", 10), bg='#f0f0f0', fg='#2c3e50').pack(side='left')
        
        tk.Label(
            auto_frame, text="  └ 지정한 시간에 미완료된 수강 퀴즈를 자동으로 풀이합니다.",
            font=("맑은 고딕", 9), bg='#f0f0f0', fg='#7f8c8d'
        ).pack(anchor='w', pady=(0, 5), padx=25)

        # 3. 자동 세미나 입장하기
        self.setting_vars['auto_seminar_enter'] = tk.BooleanVar(value=self.get_setting('auto_seminar_enter'))
        seminar_enter_check = tk.Checkbutton(
            auto_frame, text="🚪 자동 세미나 입장하기", variable=self.setting_vars['auto_seminar_enter'],
            font=("맑은 고딕", 11), bg='#f0f0f0', fg='#2c3e50',
            activebackground='#f0f0f0', activeforeground='#2c3e50'
        )
        seminar_enter_check.pack(anchor='w', pady=(2, 0))
        
        tk.Label(
            auto_frame, text="  └ 세미나 시작 시간 부근에 자동으로 시청 페이지에 입장합니다.",
            font=("맑은 고딕", 9), bg='#f0f0f0', fg='#7f8c8d'
        ).pack(anchor='w', pady=(0, 2), padx=25)
        
        enter_delay_frame = tk.Frame(auto_frame, bg='#f0f0f0')
        enter_delay_frame.pack(anchor='w', pady=(5, 10), padx=25)
        
        enter_widgets = []
        def _on_enter_toggle():
            state = 'normal' if self.setting_vars['auto_seminar_enter'].get() else 'disabled'
            for w in enter_widgets:
                try: w.configure(state=state)
                except: pass
        
        seminar_enter_check.configure(command=_on_enter_toggle)
        
        lbl_delay = tk.Label(enter_delay_frame, text="⏳ 입장 대기시간: 시작시간 +", font=("맑은 고딕", 10), bg='#f0f0f0', fg='#2c3e50')
        lbl_delay.pack(side='left')
        enter_widgets.append(lbl_delay)
        
        self.setting_vars['seminar_enter_delay'] = tk.StringVar(value=str(self.get_setting('seminar_enter_delay')))
        enter_delay_spinbox = tk.Spinbox(enter_delay_frame, from_=0, to=30, textvariable=self.setting_vars['seminar_enter_delay'], width=4, font=("맑은 고딕", 10, "bold"), justify='center')
        enter_delay_spinbox.pack(side='left', padx=5)
        enter_widgets.append(enter_delay_spinbox)
        
        tk.Label(enter_delay_frame, text="분 후 자동 입장", font=("맑은 고딕", 10), bg='#f0f0f0', fg='#7f8c8d').pack(side='left')

        # 4. 자동 세미나 새로고침
        self.setting_vars['auto_seminar_refresh'] = tk.BooleanVar(value=self.get_setting('auto_seminar_refresh'))
        
        def _on_refresh_toggle():
            is_enabled = self.setting_vars['auto_seminar_refresh'].get()
            state = 'normal' if is_enabled else 'disabled'
            for widget in self._seminar_sub_widgets:
                try: widget.configure(state=state)
                except: pass
            if not is_enabled:
                self.setting_vars['auto_seminar_join'].set(False)
                self.setting_vars['auto_survey'].set(False)
        
        refresh_check = tk.Checkbutton(
            auto_frame, text="🔄 자동 세미나 새로고침", variable=self.setting_vars['auto_seminar_refresh'],
            command=_on_refresh_toggle, font=("맑은 고딕", 11), bg='#f0f0f0', fg='#2c3e50',
            activebackground='#f0f0f0', activeforeground='#2c3e50'
        )
        refresh_check.pack(anchor='w', pady=(5, 0))
        
        tk.Label(
            auto_frame, text="  └ 세미나 목록을 설정한 간격을 주기로 새로고침합니다",
            font=("맑은 고딕", 9), bg='#f0f0f0', fg='#7f8c8d'
        ).pack(anchor='w', pady=(0, 2), padx=25)
        
        interval_frame = tk.Frame(auto_frame, bg='#f0f0f0')
        interval_frame.pack(anchor='w', pady=(2, 10), padx=25)
        
        refresh_label = tk.Label(interval_frame, text="⏱️ 세미나 새로고침 간격:", font=("맑은 고딕", 10), bg='#f0f0f0', fg='#2c3e50')
        refresh_label.pack(side='left')
        self._seminar_sub_widgets.append(refresh_label)
        
        self.setting_vars['seminar_refresh_interval'] = tk.StringVar(value=str(self.get_setting('seminar_refresh_interval')))
        interval_spin = tk.Spinbox(interval_frame, from_=1, to=3600, textvariable=self.setting_vars['seminar_refresh_interval'], width=5, font=("맑은 고딕", 10, "bold"), justify='center')
        interval_spin.pack(side='left', padx=2)
        self._seminar_sub_widgets.append(interval_spin)
        
        refresh_unit = tk.Label(interval_frame, text="초 (권장: 5초 이상)", font=("맑은 고딕", 10), bg='#f0f0f0', fg='#7f8c8d')
        refresh_unit.pack(side='left')
        self._seminar_sub_widgets.append(refresh_unit)

        # 5. 자동 세미나 신청
        self.setting_vars['auto_seminar_join'] = tk.BooleanVar(value=self.get_setting('auto_seminar_join'))
        seminar_join_check = tk.Checkbutton(
            auto_frame, text="📝 자동 세미나 신청", variable=self.setting_vars['auto_seminar_join'],
            font=("맑은 고딕", 11), bg='#f0f0f0', fg='#2c3e50',
            activebackground='#f0f0f0', activeforeground='#2c3e50'
        )
        seminar_join_check.pack(anchor='w', pady=(2, 0))
        self._seminar_sub_widgets.append(seminar_join_check)
        
        tk.Label(
            auto_frame, text="  └ 발견된 새로운 세미나를 자동으로 신청합니다.\n  └ 자동 세미나 새로고침 간격에 따릅니다 (활성화 필요)",
            font=("맑은 고딕", 9), bg='#f0f0f0', fg='#7f8c8d', justify='left'
        ).pack(anchor='w', pady=(0, 5), padx=25)
        
        # 6. 자동 설문참여
        self.setting_vars['auto_survey'] = tk.BooleanVar(value=self.get_setting('auto_survey'))
        survey_check = tk.Checkbutton(
            auto_frame, text="📋 자동 설문참여", variable=self.setting_vars['auto_survey'],
            font=("맑은 고딕", 11), bg='#f0f0f0', fg='#2c3e50',
            activebackground='#f0f0f0', activeforeground='#2c3e50'
        )
        survey_check.pack(anchor='w', pady=(2, 0))
        self._seminar_sub_widgets.append(survey_check)
        
        tk.Label(
            auto_frame, text="  └ 강의 종료 후 출력되는 설문조사에 자동으로 응답합니다.\n  └ 자동 세미나 새로고침 간격에 따릅니다 (활성화 필요)",
            font=("맑은 고딕", 9), bg='#f0f0f0', fg='#7f8c8d', justify='left'
        ).pack(anchor='w', pady=(0, 5), padx=25)

        # 브라우저 설정 섹션
        browser_frame = tk.LabelFrame(
            parent, text="🌐 브라우저 설정", font=("맑은 고딕", 12, "bold"),
            bg='#f0f0f0', fg='#2c3e50', padx=10, pady=5
        )
        browser_frame.pack(fill='x', pady=(0, 10))

        # 크롬 창 숨기기
        self.setting_vars['browser_headless'] = tk.BooleanVar(value=self.get_setting('browser_headless'))
        headless_check = tk.Checkbutton(
            browser_frame, text="🛡️ 크롬 창 숨기기 (백그라운드 실행)", variable=self.setting_vars['browser_headless'],
            font=("맑은 고딕", 11), bg='#f0f0f0', fg='#2c3e50',
            activebackground='#f0f0f0', activeforeground='#2c3e50'
        )
        headless_check.pack(anchor='w', pady=(2, 0))
        
        tk.Label(
            browser_frame, text="  └ 브라우저 화면을 숨기고 백그라운드에서 조용히 실행합니다.",
            font=("맑은 고딕", 9), bg='#f0f0f0', fg='#7f8c8d'
        ).pack(anchor='w', pady=(0, 5), padx=25)
        
        ToolTip(headless_check, "크롬 창을 띄우지 않고 백그라운드에서 작업을 수행합니다.\n체크하면 작업 중 컴퓨터 사용이 더 편리해집니다.", delay=500)

        ToolTip(headless_check, "크롬 창을 띄우지 않고 백그라운드에서 작업을 수행합니다.\n체크하면 작업 중 컴퓨터 사용이 더 편리해집니다.", delay=500)

        # 4. 알림 설정 섹션
        notify_frame = tk.LabelFrame(
            parent, text="🔔 알림 설정", font=("맑은 고딕", 12, "bold"),
            bg='#f0f0f0', fg='#2c3e50', padx=10, pady=5
        )
        notify_frame.pack(fill='x', pady=(0, 10))

        # 카카오톡 알림 사용
        self.setting_vars['kakao_notify_enabled'] = tk.BooleanVar(value=self.get_setting('kakao_notify_enabled'))
        
        def _on_kakao_toggle():
            state = 'normal' if self.setting_vars['kakao_notify_enabled'].get() else 'disabled'
            for w in self._notify_sub_widgets:
                try: w.configure(state=state)
                except: pass
        
        kakao_header_frame = tk.Frame(notify_frame, bg='#f0f0f0')
        kakao_header_frame.pack(fill='x')

        kakao_check = tk.Checkbutton(
            kakao_header_frame, text="💬 카카오톡 알림 받기", variable=self.setting_vars['kakao_notify_enabled'],
            command=_on_kakao_toggle, font=("맑은 고딕", 11), bg='#f0f0f0', fg='#2c3e50',
            activebackground='#f0f0f0', activeforeground='#2c3e50'
        )
        kakao_check.pack(side='left', pady=(2, 0))

        # 도움말 버튼 추가
        help_btn = tk.Button(
            kakao_header_frame, text="❓ 도움말", font=("맑은 고딕", 9, "bold"),
            bg='#f0f0f0', fg='#3498db', relief='flat', cursor='hand2',
            command=self._show_kakao_help, activebackground='#f0f0f0'
        )
        help_btn.pack(side='left', padx=5, pady=(4, 0))
        ToolTip(help_btn, "카카오톡 알림 설정 방법을 확인합니다.")
        
        tk.Label(
            notify_frame, text="  └ 설정한 주요 작업 완료 및 오류 발생 시 카카오톡으로 알림을 보냅니다.",
            font=("맑은 고딕", 9), bg='#f0f0f0', fg='#7f8c8d'
        ).pack(anchor='w', pady=(0, 5), padx=25)

        # 세부 알림 설정 프레임
        notify_grid = tk.Frame(notify_frame, bg='#f0f0f0')
        notify_grid.pack(fill='x', padx=25, pady=5)
        
        # 개별 알림 설정 항목들
        notify_items = [
            ('notify_attendance', "📅 출석체크"),
            ('notify_quiz', "🧠 퀴즈풀기"),
            ('notify_survey', "📋 설문참여"),
            ('notify_seminar_join', "📢 세미나 자동신청"),
            ('notify_seminar_enter', "📅 세미나 입장"),
            ('notify_baemin', "🛵 배민 쿠폰구매"),
            ('notify_startup_summary', "🏠 초기 상태 요약"),
            ('notify_error', "⚠️ 모든 오류 알림")
        ]
        
        for i, (key, text) in enumerate(notify_items):
            # 기본값 True로 설정 (명시적으로 False인 경우 제외)
            current_val = self.get_setting(key)
            if current_val is None: current_val = True
            
            self.setting_vars[key] = tk.BooleanVar(value=current_val)
            cb = tk.Checkbutton(
                notify_grid, text=text, variable=self.setting_vars[key],
                font=("맑은 고딕", 9), bg='#f0f0f0', activebackground='#f0f0f0'
            )
            cb.grid(row=i//2, column=i%2, sticky='w', pady=2, padx=(0, 20))
            self._notify_sub_widgets.append(cb)

        # 인증 버튼
        auth_btn = tk.Button(
            notify_frame, text="🔑 카카오톡 알림 도달 확인 및 재인증", font=("맑은 고딕", 9),
            bg='#fee500', fg='#3c1e1e', relief='flat', cursor='hand2',
            padx=10, pady=5, command=self._on_kakao_auth
        )
        auth_btn.pack(anchor='w', pady=(5, 10), padx=25)
        self._notify_sub_widgets.append(auth_btn)
        
        ToolTip(auth_btn, "최초 1회 인증이 필요하거나, 토큰이 만료되어 알림이 오지 않을 때 클릭하세요.", delay=500)

        # 초기 상태 업데이트
        _on_attendance_toggle()
        _on_quiz_toggle()
        _on_enter_toggle()
        _on_refresh_toggle()
        _on_kakao_toggle()

    def _show_kakao_help(self):
        """카카오톡 알림 설정 도움말 표시 (대화형 비주얼 위저드 창)"""
        KakaoWizardDialog(self.settings_window, self.get_setting, self.save_callback, self.open_browser_func)

    def _on_save(self):
        new_settings = {}
        for key, var in self.setting_vars.items():
            val = var.get()
            if isinstance(val, str) and val.isdigit():
                try: new_settings[key] = int(val, 10)
                except: new_settings[key] = val
            else:
                new_settings[key] = val
        
        # 창 크기 정보 추가
        width = self.settings_window.winfo_width()
        height = self.settings_window.winfo_height()
        if width > 100 and height > 100:
            new_settings['settings_window_width'] = width
            new_settings['settings_window_height'] = height
            
        self.save_callback(new_settings)

    def _on_closing(self):
        # 마우스 휠 바인딩 해제
        self.canvas.unbind_all("<MouseWheel>")
        
        # 창 크기 정보 수집
        dimensions = {}
        width = self.settings_window.winfo_width()
        height = self.settings_window.winfo_height()
        if width > 100 and height > 100:
            dimensions['width'] = width
            dimensions['height'] = height
            
        self.settings_window.destroy()
        self.close_callback(dimensions)

    def _on_kakao_auth(self):
        """GUI 기반 카카오톡 인증 프로세스 진행"""
        if self.open_browser_func:
            self.open_browser_func(self)
            return
            
        import webbrowser
        import requests
        import json
        import os
        from tkinter import simpledialog
        
        try:
            # 1. settings.json 로드
            settings_path = "data/settings.json"
            settings = {}
            if os.path.exists(settings_path):
                with open(settings_path, 'r', encoding='utf-8') as f:
                    settings = json.load(f)
            
            # 2. REST API Key 확인
            rest_api_key = settings.get('kakao_rest_api_key')
            if not rest_api_key:
                rest_api_key = simpledialog.askstring(
                    "🔑 REST API 키 입력", 
                    "카카오 개발자 센터에서 발급받은 'REST API 키'를 입력해주세요:",
                    parent=self.settings_window
                )
                if not rest_api_key:
                    return
                rest_api_key = rest_api_key.strip()
                settings['kakao_rest_api_key'] = rest_api_key
            
            # 3. Redirect URI
            redirect_uri = settings.get('kakao_redirect_uri', "http://localhost")
            settings['kakao_redirect_uri'] = redirect_uri
            
            # 4. 인증 URL 생성 및 브라우저 열기
            auth_url = (
                f"https://kauth.kakao.com/oauth/authorize?"
                f"client_id={rest_api_key}&"
                f"redirect_uri={redirect_uri}&"
                f"response_type=code&"
                f"scope=talk_message"
            )
            
            if self.open_browser_func:
                self.open_browser_func(auth_url)
            else:
                webbrowser.open(auth_url)
            
            # 5. 인가 코드 입력 받기 (GUI 팝업창)
            auth_code = simpledialog.askstring(
                "💬 카카오 인증 코드 입력",
                "1. 열린 웹 브라우저에서 카카오 로그인을 진행하세요.\n"
                "2. '사이트에 연결할 수 없음' 화면이 뜨면 정상입니다.\n"
                "3. 상단 주소창의 'code=' 뒤에 있는 문자열 전체를 복사하여 아래에 입력하세요:",
                parent=self.settings_window
            )
            
            if not auth_code:
                messagebox.showwarning("취소", "인증 코드가 입력되지 않아 인증이 취소되었습니다.", parent=self.settings_window)
                return
            
            auth_code = auth_code.strip()
            
            # 주소 전체를 붙여넣었을 경우 대비해서 code= 파싱 처리 (사용자 실수 방지)
            if "code=" in auth_code:
                try:
                    auth_code = auth_code.split("code=")[1].split("&")[0]
                except:
                    pass
            
            # 6. 토큰 발급 요청
            token_url = "https://kauth.kakao.com/oauth/token"
            data = {
                "grant_type": "authorization_code",
                "client_id": rest_api_key,
                "redirect_uri": redirect_uri,
                "code": auth_code
            }
            
            response = requests.post(token_url, data=data)
            result = response.json()
            
            if response.status_code == 200:
                # 7. 토큰 저장 및 활성화
                settings['kakao_access_token'] = result.get('access_token')
                settings['kakao_refresh_token'] = result.get('refresh_token')
                settings['kakao_notify_enabled'] = True
                
                # 설정 파일 저장
                os.makedirs(os.path.dirname(settings_path), exist_ok=True)
                with open(settings_path, 'w', encoding='utf-8') as f:
                    json.dump(settings, f, indent=2, ensure_ascii=False)
                
                # GUI 변수 동기화
                if 'kakao_notify_enabled' in self.setting_vars:
                    self.setting_vars['kakao_notify_enabled'].set(True)
                    # 하위 위젯 활성화 트리거
                    for w in self._notify_sub_widgets:
                        try: w.configure(state='normal')
                        except: pass
                
                # 저장 완료 알림 콜백 호출로 설정 메모리 갱신
                self.save_callback(settings)
                
                messagebox.showinfo("✅ 인증 성공", "카카오톡 알림 인증이 성공적으로 완료되었습니다!\n이제 프로그램 알림이 카카오톡으로 전송됩니다.", parent=self.settings_window)
            else:
                err_desc = result.get('error_description', result.get('error', '알 수 없는 오류'))
                messagebox.showerror("❌ 인증 실패", f"토큰 발급에 실패했습니다:\n{err_desc}", parent=self.settings_window)
                
        except Exception as e:
            messagebox.showerror("❌ 에러 발생", f"인증 진행 중 예외 발생: {str(e)}", parent=self.settings_window)
