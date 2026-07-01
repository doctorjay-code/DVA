# -*- coding: utf-8 -*-
import tkinter as tk
from tkinter import ttk, messagebox
import subprocess
import sys
from tkinter import scrolledtext
from ui.components.tooltip import ToolTip

class KakaoWizardDialog:
    def __init__(self, parent, get_setting_func, save_callback, start_auth_callback=None, settings_dialog=None):
        self.parent = parent
        self.settings_dialog = settings_dialog
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
            self.scroll_frame, "3단계: 로그인 활성화 및 권한 설정",
            "프로그램 연동을 위한 필수 로그인 및 권한 설정을 진행합니다.\n\n"
            "① 왼쪽 메뉴에서 [카카오 로그인] ➡️ [일반]으로 이동하여 사용 설정을 [ON]으로 변경합니다.\n"
            "② 왼쪽 메뉴에서 [카카오 로그인] ➡️ [동의항목]으로 이동하여 맨 아래 [카카오톡 메시지 전송]의 [설정]을 클릭합니다.\n"
            "   - 동의 단계를 [선택 동의]로 선택하고, 동의 목적에 '카카오톡 메시지 전송하기 위함'을 적은 뒤 저장합니다."
        )

        # 4단계
        self._add_step_card(
            self.scroll_frame, "4단계: 주소 등록 및 보안(시크릿) 설정",
            "리다이렉트 주소 등록 및 보안 설정을 변경합니다.\n\n"
            "① 왼쪽 메뉴에서 [앱] ➡️ [플랫폼 키]로 이동하여 [Default Rest API Key] 우측 상단의 더보기(⋮) 아이콘 ➡️ [수정]을 클릭합니다.\n"
            "② [카카오 로그인 리다이렉트 URI] 칸에 'http://localhost'를 입력하고 '+' 버튼을 클릭합니다.\n"
            "③ [클라이언트 시크릿] ➡️ [카카오 로그인] 아래에 있는 활성화 스위치를 클릭해 [OFF]로 꺼줍니다. (파란색 ON ➡️ 회색 OFF)\n"
            "④ 화면 맨 아래로 스크롤을 내려 [저장] 버튼을 클릭합니다."
        )

        # 5단계
        self._add_step_card(
            self.scroll_frame, "5단계: REST API 키 복사",
            "저장 완료 후 다시 나타난 [플랫폼 키] 화면에서, 방금 설정한 [Default Rest API Key] 카드에 표시된 32자리 문자열 우측의 복사(📋) 아이콘을 클릭하여 복사합니다."
        )

        # 6단계
        self._add_step_card(
            self.scroll_frame, "6단계: 로그인 연동 및 인증 완료",
            "최종적으로 프로그램과 카카오톡을 연동하고 연동 결과를 등록합니다.\n\n"
            "① 복사한 REST API 키를 하단의 입력창에 붙여넣고 노란색 [설정 완료 및 자동 로그인 연동 시작] 버튼을 누릅니다.\n"
            "② 인터넷 브라우저 창이 열리면 [서비스 접근권한 동의 - 카카오톡 메시지 전송] 항목에 체크한 뒤, 아래 노란색 [확인하고 계속하기] 버튼을 클릭합니다. (⚠️ 맞춤형 광고 동의 항목은 체크하지 않아도 됩니다.)\n"
            "③ 그 후 '사이트에 연결할 수 없음' 에러 페이지가 뜨면 정상입니다. 주소창의 주소 전체를 그대로 복사하여 프로그램의 코드 입력창에 붙여넣어 연동을 완료합니다."
        )
        
        # --- 입력 및 완료 영역 ---
        input_frame = tk.LabelFrame(
            self.scroll_frame, text="🔑 5단계에서 복사한 REST API 키를 등록하세요",
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
        
        lbl_title = tk.Label(
            card, text=title, font=("맑은 고딕", 10, "bold"),
            bg='#f8f9fa', fg='#2c3e50', justify='left', anchor='w'
        )
        lbl_title.pack(fill='x', pady=(0, 5))
        
        lbl_desc = tk.Label(
            card, text=desc, font=("맑은 고딕", 9),
            bg='#f8f9fa', fg='#555555', justify='left', anchor='w'
        )
        lbl_desc.pack(fill='x', pady=(0, 5))
        
        def _on_card_configure(event, lt=lbl_title, ld=lbl_desc):
            # 카드의 내부 패딩을 고려하여 줄바꿈 너비(wraplength) 동적 설정
            wrap_w = event.width - 40
            if wrap_w > 50:
                lt.configure(wraplength=wrap_w)
                ld.configure(wraplength=wrap_w)
                
        card.bind("<Configure>", _on_card_configure)
        
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
        
        # 재인증 플로우 시작
        if self.start_auth_callback:
            # Toplevel을 파괴하지 않고 콜백에 SettingsDialog 인스턴스를 전달하여 후속 처리를 진행하도록 함
            target_dialog = self.settings_dialog if self.settings_dialog else self.parent
            self.parent.after(100, lambda: self.start_auth_callback(target_dialog, wizard_window=self))
        else:
            self.window.destroy()
            self.canvas.unbind_all("<MouseWheel>")


class GeminiWizardDialog:
    def __init__(self, parent):
        self.parent = parent
        
        self.window = tk.Toplevel(parent)
        self.window.title("🔑 Gemini API 키 발급 가이드")
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
        header = tk.Frame(self.window, bg='#3498db', height=85)
        header.pack(fill='x', side='top')
        header.pack_propagate(False)
        
        tk.Label(
            header, text="🧠 Gemini API 키 발급 및 연동 가이드",
            font=("맑은 고딕", 15, "bold"), bg='#3498db', fg='#ffffff'
        ).pack(pady=(15, 2))
        
        tk.Label(
            header, text="구글의 100% 무료 AI API 키를 발급받는 간단한 순서입니다.",
            font=("맑은 고딕", 9), bg='#3498db', fg='#ffffff'
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
        
        self._add_step_card(
            self.scroll_frame, "1단계: Google AI Studio 접속 & 로그인",
            "아래 바로가기 버튼을 눌러 Google AI Studio 사이트로 이동한 후, 구글 계정으로 로그인해 주세요. (무료 사용이며 결제 카드 등록이 전혀 필요하지 않습니다.)",
            btn_text="🌐 Google AI Studio 바로가기",
            btn_cmd=lambda: self._open_url("https://aistudio.google.com/")
        )
        
        self._add_step_card(
            self.scroll_frame, "2단계: 최초 동의 및 가입 완료",
            "처음 접속하신 경우 서비스 사용을 위한 동의 창이 뜹니다. 약관 체크박스에 동의한 후 [Continue]를 클릭하여 메인 화면으로 진입하세요."
        )
        
        self._add_step_card(
            self.scroll_frame, "3단계: API 키 생성 메뉴 진입",
            "왼쪽 메뉴바 최상단에 있는 파란색 [🔑 Get API key] 또는 화면 중앙에 있는 [Create API Key] 버튼을 클릭하세요."
        )
        
        self._add_step_card(
            self.scroll_frame, "4단계: 새 프로젝트에서 키 발급받기",
            "팝업 창이 열리면 노란색 또는 파란색 버튼인 [➕ Create API key in new project] (새 프로젝트에서 API 키 만들기) 버튼을 클릭하세요. 자동으로 구글 클라우드에 새 임시 프로젝트가 개설되며 API 키가 발급됩니다."
        )
        
        self._add_step_card(
            self.scroll_frame, "5단계: 생성된 API Key 복사",
            "화면에 발급된 영어와 숫자로 이루어진 API 키 문자열이 나타납니다. 우측의 [Copy] 버튼 또는 복사 아이콘을 눌러 클립보드에 키를 복사해 주세요."
        )
        
        self._add_step_card(
            self.scroll_frame, "6단계: DVA 프로그램에 연동 완료",
            "DVA 프로그램 설정 창의 '🧠 AI 주관식 자동화 설정' 아래에 있는 'Gemini API Key' 입력칸에 복사한 키를 붙여넣기(Ctrl+V) 한 뒤, 하단의 [💾 설정 저장] 버튼을 누르면 연동이 끝납니다."
        )
        
        # 닫기 버튼 영역
        btn_frame = tk.Frame(self.scroll_frame, bg='#ffffff')
        btn_frame.pack(fill='x', pady=(15, 10))
        
        close_btn = tk.Button(
            btn_frame, text="✅ 확인 완료 (닫기)",
            font=("맑은 고딕", 12, "bold"), bg='#3498db', fg='white',
            activebackground='#2980b9', activeforeground='white',
            relief='flat', cursor='hand2', padx=10, pady=8,
            command=self._on_close
        )
        close_btn.pack(fill='x')
        
    def _add_step_card(self, parent, title, desc, btn_text=None, btn_cmd=None):
        card = tk.Frame(parent, bg='#f8f9fa', padx=15, pady=12, relief='solid', borderwidth=1)
        card.pack(fill='x', pady=(0, 12))
        
        lbl_title = tk.Label(
            card, text=title, font=("맑은 고딕", 10, "bold"),
            bg='#f8f9fa', fg='#2c3e50', justify='left', anchor='w'
        )
        lbl_title.pack(fill='x', pady=(0, 5))
        
        lbl_desc = tk.Label(
            card, text=desc, font=("맑은 고딕", 9),
            bg='#f8f9fa', fg='#555555', justify='left', anchor='w'
        )
        lbl_desc.pack(fill='x', pady=(0, 5))
        
        def _on_card_configure(event, lt=lbl_title, ld=lbl_desc):
            wrap_w = event.width - 40
            if wrap_w > 50:
                lt.configure(wraplength=wrap_w)
                ld.configure(wraplength=wrap_w)
                
        card.bind("<Configure>", _on_card_configure)
        
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
        
    def _on_close(self):
        self.canvas.unbind_all("<MouseWheel>")
        self.window.destroy()


class SettingsDialog:
    # Gemini API 프롬프트 기본값 상수 정의
    DEFAULT_PROMPT_TEMPLATE = (
        "의학 세미나 설문조사 주관식 질문입니다. 의사 또는 의료 전문가 관점에서 신뢰감 있고 전문적으로 답변해 주세요.\n\n"
        "답변을 작성할 때 반드시 다음 규칙을 지켜주세요:\n"
        "1. 큰따옴표(\"\"), 작은따옴표(''), 대괄호([]), 소괄호(()) 등의 모든 따옴표와 괄호 기호를 절대로 사용하지 마세요.\n"
        "2. 사람이 직접 손으로 타이핑한 것 같이 자연스러운 존댓말 형태로 작성해 주세요.\n"
        "3. 줄바꿈을 하지 말고 하나의 완성된 문단(단일 paragraph)으로만 답변을 작성해 주세요.\n"
        "4. 답변 외에 다른 군더더기 메타 설명(예: '답변:', '작성된 의견:', '최소 글자 수를 만족하는 답변입니다')은 절대 포함하지 마세요.\n\n"
        "{length_condition}\n\n"
        "질문: {question}"
    )

    DEFAULT_MIN_LIMIT = "답변의 길이는 공백을 포함하여 반드시 {min_limit}자 이상 {min_plus_100}자 이하로 넉넉하게 작성해 주세요."
    DEFAULT_MAX_LIMIT = "답변의 길이는 공백을 포함하여 반드시 {max_safe_min}자 이상 {max_safe_max}자 이하로 작성해 주세요. (절대 {max_limit}자를 넘으면 안 됩니다.)"
    DEFAULT_NO_LIMIT = "답변의 길이는 공백을 포함하여 40자 내외로 간결하게 작성해 주세요."

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
        self.scrollable_frame.bind("<Configure>", self._on_frame_configure)
        
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
        # 활성 시간대 설정을 위한 변수 변환 및 할당
        start_h24 = self.get_setting('active_start_h')
        if start_h24 is None or start_h24 is False: start_h24 = 9
        else: start_h24 = int(start_h24)
        
        start_m = self.get_setting('active_start_m')
        if start_m is None or start_m is False: start_m = 0
        else: start_m = int(start_m)
        
        start_ampm_val = "오후" if start_h24 >= 12 else "오전"
        start_h12_val = start_h24 % 12
        if start_h12_val == 0: start_h12_val = 12
        
        end_h24 = self.get_setting('active_end_h')
        if end_h24 is None or end_h24 is False: end_h24 = 21
        else: end_h24 = int(end_h24)
        
        end_m = self.get_setting('active_end_m')
        if end_m is None or end_m is False: end_m = 0
        else: end_m = int(end_m)
        
        end_ampm_val = "오후" if end_h24 >= 12 else "오전"
        end_h12_val = end_h24 % 12
        if end_h12_val == 0: end_h12_val = 12

        self.setting_vars['active_start_ampm'] = tk.StringVar(value=start_ampm_val)
        self.setting_vars['active_start_h12'] = tk.StringVar(value=str(start_h12_val))
        self.setting_vars['active_start_m'] = tk.StringVar(value=str(start_m))
        
        self.setting_vars['active_end_ampm'] = tk.StringVar(value=end_ampm_val)
        self.setting_vars['active_end_h12'] = tk.StringVar(value=str(end_h12_val))
        self.setting_vars['active_end_m'] = tk.StringVar(value=str(end_m))

        # 자동 실행 설정 섹션
        auto_frame = tk.LabelFrame(
            parent, text="🤖 자동 실행 설정", font=("맑은 고딕", 12, "bold"),
            bg='#f0f0f0', fg='#2c3e50', padx=10, pady=5
        )
        auto_frame.pack(fill='x', pady=(0, 10))
        
        # 1. 자동 출석 체크
        self.setting_vars['auto_attendance'] = tk.BooleanVar(value=self.get_setting('auto_attendance'))
        attendance_check = tk.Checkbutton(
            auto_frame, text="✅ 자동 출석 체크", variable=self.setting_vars['auto_attendance'],
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
            auto_frame, text="  └ 지정한 시간에 오늘의 출석 체크를 자동으로 진행합니다.",
            font=("맑은 고딕", 9), bg='#f0f0f0', fg='#7f8c8d'
        ).pack(anchor='w', pady=(0, 5), padx=25)

        # 2. 자동 퀴즈 풀이
        self.setting_vars['auto_quiz'] = tk.BooleanVar(value=self.get_setting('auto_quiz'))
        quiz_check = tk.Checkbutton(
            auto_frame, text="🧠 자동 퀴즈 풀이", variable=self.setting_vars['auto_quiz'],
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

        # 3. 자동 세미나 새로고침
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

        # 4. 자동 세미나 신청
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

        # 5. 자동 세미나 입장하기
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

        # 5-1. 자동 세미나 퇴장하기
        self.setting_vars['auto_seminar_close'] = tk.BooleanVar(value=self.get_setting('auto_seminar_close'))
        seminar_close_check = tk.Checkbutton(
            auto_frame, text="🚪 자동 세미나 퇴장하기 (창 닫기)", variable=self.setting_vars['auto_seminar_close'],
            font=("맑은 고딕", 11), bg='#f0f0f0', fg='#2c3e50',
            activebackground='#f0f0f0', activeforeground='#2c3e50'
        )
        seminar_close_check.pack(anchor='w', pady=(2, 0))
        
        tk.Label(
            auto_frame, text="  └ 자동 입장한 세미나 창을 설정된 시간 이후 자동으로 닫습니다.",
            font=("맑은 고딕", 9), bg='#f0f0f0', fg='#7f8c8d'
        ).pack(anchor='w', pady=(0, 2), padx=25)
        
        close_delay_frame = tk.Frame(auto_frame, bg='#f0f0f0')
        close_delay_frame.pack(anchor='w', pady=(5, 10), padx=25)
        
        close_widgets = []
        def _on_close_toggle():
            state = 'normal' if self.setting_vars['auto_seminar_close'].get() else 'disabled'
            for w in close_widgets:
                try: w.configure(state=state)
                except: pass
                
        seminar_close_check.configure(command=_on_close_toggle)
        
        lbl_close_delay = tk.Label(close_delay_frame, text="⏳ 퇴장 대기시간: 입장 후", font=("맑은 고딕", 10), bg='#f0f0f0', fg='#2c3e50')
        lbl_close_delay.pack(side='left')
        close_widgets.append(lbl_close_delay)
        
        self.setting_vars['seminar_close_delay'] = tk.StringVar(value=str(self.get_setting('seminar_close_delay')))
        close_delay_spinbox = tk.Spinbox(close_delay_frame, from_=1, to=180, textvariable=self.setting_vars['seminar_close_delay'], width=4, font=("맑은 고딕", 10, "bold"), justify='center')
        close_delay_spinbox.pack(side='left', padx=5)
        close_widgets.append(close_delay_spinbox)
        
        tk.Label(close_delay_frame, text="분 후 자동 퇴장", font=("맑은 고딕", 10), bg='#f0f0f0', fg='#7f8c8d').pack(side='left')
        
        # 6. 자동 세미나 설문 풀이
        self.setting_vars['auto_survey'] = tk.BooleanVar(value=self.get_setting('auto_survey'))
        survey_check = tk.Checkbutton(
            auto_frame, text="📋 자동 세미나 설문 풀이", variable=self.setting_vars['auto_survey'],
            font=("맑은 고딕", 11), bg='#f0f0f0', fg='#2c3e50',
            activebackground='#f0f0f0', activeforeground='#2c3e50'
        )
        survey_check.pack(anchor='w', pady=(2, 0))
        self._seminar_sub_widgets.append(survey_check)
        
        tk.Label(
            auto_frame, text="  └ 강의 종료 후 출력되는 설문조사에 자동으로 응답합니다.\n  └ 자동 세미나 새로고침 간격에 따릅니다 (활성화 필요)",
            font=("맑은 고딕", 9), bg='#f0f0f0', fg='#7f8c8d', justify='left'
        ).pack(anchor='w', pady=(0, 2), padx=25)

        # 6-1. 자동 세미나 설문 지연 풀기
        self.setting_vars['auto_survey_delay'] = tk.BooleanVar(value=self.get_setting('auto_survey_delay'))
        
        # 지연 풀기 활성화 체크박스와 스핀박스를 담을 프레임
        delay_frame = tk.Frame(auto_frame, bg='#f0f0f0')
        delay_frame.pack(anchor='w', pady=(5, 10), padx=25)
        
        # 스핀박스 및 라벨 활성/비활성 제어를 위한 리스트
        delay_widgets = []
        
        def toggle_delay_widgets():
            state = 'normal' if self.setting_vars['auto_survey_delay'].get() else 'disabled'
            for widget in delay_widgets:
                try: widget.config(state=state)
                except: pass
                
        # 체크박스 자체 (체크박스 기호만 노출)
        survey_delay_check = tk.Checkbutton(
            delay_frame, text="", variable=self.setting_vars['auto_survey_delay'],
            bg='#f0f0f0', activebackground='#f0f0f0',
            command=toggle_delay_widgets
        )
        survey_delay_check.pack(side='left', padx=(0, 2))
        self._seminar_sub_widgets.append(survey_delay_check)
        
        # 지연 풀기 텍스트 라벨 (입장/퇴장 라벨 색상 fg='#2c3e50' 과 일치)
        lbl_delay_text = tk.Label(
            delay_frame, text="⏱ 설문 지연 풀기 적용: 종료 감지 후",
            font=("맑은 고딕", 10), bg='#f0f0f0', fg='#2c3e50'
        )
        lbl_delay_text.pack(side='left')
        delay_widgets.append(lbl_delay_text)
        self._seminar_sub_widgets.append(lbl_delay_text)
        
        self.setting_vars['auto_survey_delay_min'] = tk.StringVar(value=str(self.get_setting('auto_survey_delay_min') or 10))
        delay_spinbox = tk.Spinbox(
            delay_frame, from_=1, to=180,
            textvariable=self.setting_vars['auto_survey_delay_min'],
            width=4, font=("맑은 고딕", 10, "bold"), justify='center'
        )
        delay_spinbox.pack(side='left', padx=5)
        delay_widgets.append(delay_spinbox)
        self._seminar_sub_widgets.append(delay_spinbox)
        
        # 단위 텍스트 라벨 (입장/퇴장 단위 라벨 색상 fg='#7f8c8d' 와 일치)
        lbl_delay_unit = tk.Label(
            delay_frame, text="분 뒤 자동 설문 시작",
            font=("맑은 고딕", 10), bg='#f0f0f0', fg='#7f8c8d'
        )
        lbl_delay_unit.pack(side='left')
        delay_widgets.append(lbl_delay_unit)
        self._seminar_sub_widgets.append(lbl_delay_unit)
        
        # 초기 상태 토글 호출
        toggle_delay_widgets()

        # 7. 자동 세미나 설문 제출 (자동 세미나 풀이 여부와 무관하게 항상 독립적으로 설정 가능)
        self.setting_vars['auto_survey_submit'] = tk.BooleanVar(value=self.get_setting('auto_survey_submit'))
        survey_submit_check = tk.Checkbutton(
            auto_frame, text="📋 자동 세미나 설문 제출", variable=self.setting_vars['auto_survey_submit'],
            font=("맑은 고딕", 11), bg='#f0f0f0', fg='#2c3e50',
            activebackground='#f0f0f0', activeforeground='#2c3e50'
        )
        survey_submit_check.pack(anchor='w', pady=(2, 0))
        
        tk.Label(
            auto_frame, text="  └ 설문 작성 완료 후 최종 제출 버튼까지 자동으로 클릭합니다.\n  └ 체크 해제 시 설문 답변만 작성 후 대기하므로 직접 확인하고 제출할 수 있습니다.",
            font=("맑은 고딕", 9), bg='#f0f0f0', fg='#7f8c8d', justify='left'
        ).pack(anchor='w', pady=(0, 5), padx=25)

        # 8. 자동 포인트 결제
        self.setting_vars['auto_point_payment'] = tk.BooleanVar(value=self.get_setting('auto_point_payment'))
        auto_payment_check = tk.Checkbutton(
            auto_frame, text="🛵 자동 포인트 결제", variable=self.setting_vars['auto_point_payment'],
            font=("맑은 고딕", 11), bg='#f0f0f0', fg='#2c3e50',
            activebackground='#f0f0f0', activeforeground='#2c3e50'
        )
        auto_payment_check.pack(anchor='w', pady=(2, 0))
        
        tk.Label(
            auto_frame, text="  └ 체크 안 하면 결제하기 버튼 누르기 직전까지만 가고, 체크하면 결제까지 진행합니다.",
            font=("맑은 고딕", 9), bg='#f0f0f0', fg='#7f8c8d'
        ).pack(anchor='w', pady=(0, 5), padx=25)

        # 9. 특정 시간대 일시정지 설정
        self.setting_vars['use_active_time_range'] = tk.BooleanVar(value=self.get_setting('use_active_time_range'))
        
        time_range_widgets = []
        def _on_time_range_toggle():
            state = 'normal' if self.setting_vars['use_active_time_range'].get() else 'disabled'
            for w in time_range_widgets:
                try:
                    if isinstance(w, ttk.Combobox):
                        w.configure(state='readonly' if state == 'normal' else 'disabled')
                    else:
                        w.configure(state=state)
                except: pass
                
        time_range_check = tk.Checkbutton(
            auto_frame, text="🕒 특정 시간대에만 작동 (일시정지 설정)", variable=self.setting_vars['use_active_time_range'],
            command=_on_time_range_toggle, font=("맑은 고딕", 11), bg='#f0f0f0', fg='#2c3e50',
            activebackground='#f0f0f0', activeforeground='#2c3e50'
        )
        time_range_check.pack(anchor='w', pady=(2, 0))
        
        tk.Label(
            auto_frame, text="  └ 설정한 활성 시간대 외에는 브라우저를 닫고 대기 모드로 일시정지합니다.",
            font=("맑은 고딕", 9), bg='#f0f0f0', fg='#7f8c8d'
        ).pack(anchor='w', pady=(0, 2), padx=25)
        
        time_select_frame = tk.Frame(auto_frame, bg='#f0f0f0')
        time_select_frame.pack(anchor='w', pady=(2, 10), padx=25)
        
        lbl_start = tk.Label(time_select_frame, text="⏳ 시작: ", font=("맑은 고딕", 10), bg='#f0f0f0', fg='#2c3e50')
        lbl_start.pack(side='left')
        time_range_widgets.append(lbl_start)
        
        start_ampm_combo = ttk.Combobox(
            time_select_frame, textvariable=self.setting_vars['active_start_ampm'],
            values=["오전", "오후"], width=4, state="readonly", font=("맑은 고딕", 9, "bold")
        )
        start_ampm_combo.pack(side='left', padx=2)
        time_range_widgets.append(start_ampm_combo)
        
        start_h_spin = tk.Spinbox(
            time_select_frame, from_=1, to=12, textvariable=self.setting_vars['active_start_h12'],
            width=3, font=("맑은 고딕", 10, "bold"), justify='center'
        )
        start_h_spin.pack(side='left', padx=2)
        time_range_widgets.append(start_h_spin)
        
        lbl_start_h = tk.Label(time_select_frame, text="시", font=("맑은 고딕", 10), bg='#f0f0f0', fg='#2c3e50')
        lbl_start_h.pack(side='left')
        time_range_widgets.append(lbl_start_h)
        
        start_m_spin = tk.Spinbox(
            time_select_frame, from_=0, to=59, textvariable=self.setting_vars['active_start_m'],
            width=3, font=("맑은 고딕", 10, "bold"), justify='center', format="%02.0f"
        )
        start_m_spin.pack(side='left', padx=2)
        time_range_widgets.append(start_m_spin)
        
        lbl_start_m = tk.Label(time_select_frame, text="분  ~  종료: ", font=("맑은 고딕", 10), bg='#f0f0f0', fg='#2c3e50')
        lbl_start_m.pack(side='left')
        time_range_widgets.append(lbl_start_m)
        
        end_ampm_combo = ttk.Combobox(
            time_select_frame, textvariable=self.setting_vars['active_end_ampm'],
            values=["오전", "오후"], width=4, state="readonly", font=("맑은 고딕", 9, "bold")
        )
        end_ampm_combo.pack(side='left', padx=2)
        time_range_widgets.append(end_ampm_combo)
        
        end_h_spin = tk.Spinbox(
            time_select_frame, from_=1, to=12, textvariable=self.setting_vars['active_end_h12'],
            width=3, font=("맑은 고딕", 10, "bold"), justify='center'
        )
        end_h_spin.pack(side='left', padx=2)
        time_range_widgets.append(end_h_spin)
        
        lbl_end_h = tk.Label(time_select_frame, text="시", font=("맑은 고딕", 10), bg='#f0f0f0', fg='#2c3e50')
        lbl_end_h.pack(side='left')
        time_range_widgets.append(lbl_end_h)
        
        end_m_spin = tk.Spinbox(
            time_select_frame, from_=0, to=59, textvariable=self.setting_vars['active_end_m'],
            width=3, font=("맑은 고딕", 10, "bold"), justify='center', format="%02.0f"
        )
        end_m_spin.pack(side='left', padx=2)
        time_range_widgets.append(end_m_spin)
        
        lbl_end_m = tk.Label(time_select_frame, text="분", font=("맑은 고딕", 10), bg='#f0f0f0', fg='#2c3e50')
        lbl_end_m.pack(side='left')
        time_range_widgets.append(lbl_end_m)

        # AI 주관식 자동화 설정 섹션
        ai_frame = tk.LabelFrame(
            parent, text="🧠 AI 주관식 자동화 설정", font=("맑은 고딕", 12, "bold"),
            bg='#f0f0f0', fg='#2c3e50', padx=10, pady=5
        )
        ai_frame.pack(fill='x', pady=(0, 10))
        
        # 1. 안내 및 가이드 버튼 프레임 (윗줄)
        guide_button_container = tk.Frame(ai_frame, bg='#f0f0f0')
        guide_button_container.pack(fill='x', pady=(5, 2), padx=10)
        
        def _show_gemini_help():
            GeminiWizardDialog(self.settings_window)
            
        btn_gemini_help = tk.Button(
            guide_button_container, text="❓ 초간단 발급 가이드", font=("맑은 고딕", 9, "bold"),
            bg='#f0f0f0', fg='#3498db', relief='flat', cursor='hand2',
            command=_show_gemini_help, activebackground='#f0f0f0'
        )
        btn_gemini_help.pack(side='left')
        ToolTip(btn_gemini_help, "Gemini API 키를 어떻게 발급받는지 단계별로 설명해주는 도움말 가이드를 엽니다.", delay=500)
        
        # 2. API Key 입력 프레임 (아랫줄)
        api_key_container = tk.Frame(ai_frame, bg='#f0f0f0')
        api_key_container.pack(fill='x', pady=(2, 5), padx=10)
        
        lbl_api_key = tk.Label(api_key_container, text="🔑 Gemini API Key:", font=("맑은 고딕", 10), bg='#f0f0f0', fg='#2c3e50')
        lbl_api_key.pack(side='left')
        
        self.setting_vars['gemini_api_key'] = tk.StringVar(value=self.get_setting('gemini_api_key') or "")
        api_key_entry = tk.Entry(api_key_container, textvariable=self.setting_vars['gemini_api_key'], width=25, font=("맑은 고딕", 10), justify='center', show='*')
        api_key_entry.pack(side='left', padx=5)
        
        tk.Label(
            ai_frame, text="  └ API 키가 등록되면 설문조사의 주관식 및 글자수 제한 문항을 AI가 자동으로 작성합니다.\n  └ 키가 없거나 비어있는 경우 기존처럼 수동 입력 대기로 자동 전환됩니다.",
            font=("맑은 고딕", 9), bg='#f0f0f0', fg='#7f8c8d', justify='left'
        ).pack(anchor='w', pady=(0, 5), padx=25)

        # 3. AI 프롬프트 템플릿 설정 (텍스트 창)
        prompt_frame = tk.Frame(ai_frame, bg='#f0f0f0')
        prompt_frame.pack(fill='x', pady=(5, 5), padx=10)
        
        lbl_prompt = tk.Label(prompt_frame, text="📝 AI 답변 생성 프롬프트 템플릿:", font=("맑은 고딕", 10, "bold"), bg='#f0f0f0', fg='#2c3e50')
        lbl_prompt.pack(anchor='w', pady=(0, 2))
        
        tk.Label(
            prompt_frame, text="  └ {question}은 질문으로, {length_condition}은 글자수 조건 지시문으로 치환됩니다.",
            font=("맑은 고딕", 8), bg='#f0f0f0', fg='#e67e22', justify='left'
        ).pack(anchor='w', pady=(0, 5))

        # 3-2. 상황별 {length_condition} 세부 문구 설정
        limits_frame = tk.Frame(prompt_frame, bg='#f0f0f0')
        limits_frame.pack(fill='x', pady=(5, 5))
        
        tk.Label(
            limits_frame, text="📏 상황별 글자수 지시문 설정 (중괄호 내용으로 채워짐):",
            font=("맑은 고딕", 9, "bold"), bg='#f0f0f0', fg='#2c3e50'
        ).pack(anchor='w', pady=(0, 3))
        
        # 1) 최소 글자 조건 시
        min_cond_frame = tk.Frame(limits_frame, bg='#f0f0f0')
        min_cond_frame.pack(fill='x', pady=2)
        tk.Label(min_cond_frame, text=" • 최소 글자 조건 시:", font=("맑은 고딕", 9), bg='#f0f0f0', fg='#2c3e50', width=16, anchor='w').pack(side='left')
        self.setting_vars['gemini_prompt_min_limit'] = tk.StringVar(value=self.get_setting('gemini_prompt_min_limit') or SettingsDialog.DEFAULT_MIN_LIMIT)
        tk.Entry(min_cond_frame, textvariable=self.setting_vars['gemini_prompt_min_limit'], font=("맑은 고딕", 9), bg='#ffffff', relief='solid', borderwidth=1).pack(side='left', fill='x', expand=True, ipady=2)
        ToolTip(min_cond_frame, "최소 글자 수 제한만 감지되었을 때 적용되는 문장입니다.\n사용 가능 변수: {min_limit}, {min_plus_100}", delay=300)
        
        # 2) 최대 글자 조건 시
        max_cond_frame = tk.Frame(limits_frame, bg='#f0f0f0')
        max_cond_frame.pack(fill='x', pady=2)
        tk.Label(max_cond_frame, text=" • 최대 글자 조건 시:", font=("맑은 고딕", 9), bg='#f0f0f0', fg='#2c3e50', width=16, anchor='w').pack(side='left')
        self.setting_vars['gemini_prompt_max_limit'] = tk.StringVar(value=self.get_setting('gemini_prompt_max_limit') or SettingsDialog.DEFAULT_MAX_LIMIT)
        tk.Entry(max_cond_frame, textvariable=self.setting_vars['gemini_prompt_max_limit'], font=("맑은 고딕", 9), bg='#ffffff', relief='solid', borderwidth=1).pack(side='left', fill='x', expand=True, ipady=2)
        ToolTip(max_cond_frame, "최대 글자 수 제한만 감지되었거나, 최소/최대 제한이 모두 감지되었을 때 적용되는 문장입니다.\n사용 가능 변수: {max_limit}, {max_safe_min}, {max_safe_max}, {min_limit}", delay=300)
        
        # 3) 글자 제한 없을 시
        no_cond_frame = tk.Frame(limits_frame, bg='#f0f0f0')
        no_cond_frame.pack(fill='x', pady=2)
        tk.Label(no_cond_frame, text=" • 글자 제한 없을 시:", font=("맑은 고딕", 9), bg='#f0f0f0', fg='#2c3e50', width=16, anchor='w').pack(side='left')
        self.setting_vars['gemini_prompt_no_limit'] = tk.StringVar(value=self.get_setting('gemini_prompt_no_limit') or SettingsDialog.DEFAULT_NO_LIMIT)
        tk.Entry(no_cond_frame, textvariable=self.setting_vars['gemini_prompt_no_limit'], font=("맑은 고딕", 9), bg='#ffffff', relief='solid', borderwidth=1).pack(side='left', fill='x', expand=True, ipady=2)
        ToolTip(no_cond_frame, "글자 수 조건이 없을 때 적용되는 기본 문장입니다.", delay=300)
        
        # 3-3. 기본값 복원 버튼 콘테이너 (오른쪽 정렬)
        restore_btn_frame = tk.Frame(prompt_frame, bg='#f0f0f0')
        restore_btn_frame.pack(fill='x', pady=(5, 0))
        
        btn_restore = tk.Button(
            restore_btn_frame, text="🔄 AI 설정 기본값 복원", font=("맑은 고딕", 9, "bold"),
            bg='#f0f0f0', fg='#e74c3c', relief='flat', cursor='hand2',
            command=self._restore_gemini_defaults, activebackground='#f0f0f0'
        )
        btn_restore.pack(side='right', padx=5)
        ToolTip(btn_restore, "프롬프트 템플릿과 상황별 글자수 지시문 설정을 처음 설치 상태의 기본값으로 원상복구합니다.", delay=300)

        self.prompt_text = scrolledtext.ScrolledText(
            prompt_frame, width=40, height=8, font=("Consolas", 9),
            relief='solid', borderwidth=1, wrap='word'
        )
        self.prompt_text.pack(fill='x', pady=(0, 5))
        
        saved_prompt = self.get_setting('gemini_prompt_template') or SettingsDialog.DEFAULT_PROMPT_TEMPLATE
        self.prompt_text.insert('1.0', saved_prompt)

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
            ('notify_startup_summary', "🏠 상태 요약"),
            ('notify_attendance', "📅 출석 체크"),
            ('notify_quiz', "🧠 퀴즈 풀이"),
            ('notify_baemin', "🛵 포인트 사용"),
            ('notify_seminar_join', "📢 세미나 신청"),
            ('notify_seminar_enter', "📅 세미나 입장"),
            ('notify_survey', "📋 세미나 풀이"),
            ('notify_subjective_answer', "💬 세미나 주관식"),
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

        # 5. 포인트 사용 설정 섹션
        baemin_frame = tk.LabelFrame(
            parent, text="💰 포인트 사용 설정", font=("맑은 고딕", 12, "bold"),
            bg='#f0f0f0', fg='#2c3e50', padx=10, pady=5
        )
        baemin_frame.pack(fill='x', pady=(0, 10))
        
        phone_container = tk.Frame(baemin_frame, bg='#f0f0f0')
        phone_container.pack(anchor='w', pady=(5, 5), padx=25)
        
        lbl_phone = tk.Label(phone_container, text="📱 수신 휴대폰 번호:", font=("맑은 고딕", 10), bg='#f0f0f0', fg='#2c3e50')
        lbl_phone.pack(side='left')
        
        self.setting_vars['baemin_phone'] = tk.StringVar(value=str(self.get_setting('baemin_phone') or ""))
        phone_entry = tk.Entry(phone_container, textvariable=self.setting_vars['baemin_phone'], width=15, font=("맑은 고딕", 10, "bold"), justify='center')
        phone_entry.pack(side='left', padx=5)
        
        tk.Label(
            baemin_frame, text="  └ 쿠폰(배민/기프티콘 등) 자동 구매 시 쿠폰을 전송받을 기본 휴대폰 번호입니다.",
            font=("맑은 고딕", 9), bg='#f0f0f0', fg='#7f8c8d'
        ).pack(anchor='w', pady=(0, 5), padx=25)



        # 초기 상태 업데이트
        _on_attendance_toggle()
        _on_quiz_toggle()
        _on_enter_toggle()
        _on_close_toggle()
        _on_refresh_toggle()
        _on_kakao_toggle()
        _on_time_range_toggle()

    def _show_kakao_help(self):
        """카카오톡 알림 설정 도움말 표시 (대화형 비주얼 위저드 창)"""
        KakaoWizardDialog(self.settings_window, self.get_setting, self.save_callback, self.open_browser_func, self)

    def _on_save(self):
        new_settings = {}
        for key, var in self.setting_vars.items():
            if key in ['active_start_ampm', 'active_start_h12', 'active_end_ampm', 'active_end_h12']:
                continue
            val = var.get()
            if key in ['baemin_phone', 'gemini_api_key']:
                new_settings[key] = str(val).strip()
            elif key in ['active_start_m', 'active_end_m']:
                try: new_settings[key] = int(val)
                except: new_settings[key] = 0
            elif isinstance(val, str) and val.isdigit():
                try: new_settings[key] = int(val, 10)
                except: new_settings[key] = val
            else:
                new_settings[key] = val
        
        # 12시간제 UI 설정을 24시간제 정수값으로 환산해서 저장
        try:
            start_ampm = self.setting_vars['active_start_ampm'].get()
            start_h12 = int(self.setting_vars['active_start_h12'].get())
            start_h24 = start_h12 % 12
            if start_ampm == "오후":
                start_h24 += 12
            new_settings['active_start_h'] = start_h24
            
            end_ampm = self.setting_vars['active_end_ampm'].get()
            end_h12 = int(self.setting_vars['active_end_h12'].get())
            end_h24 = end_h12 % 12
            if end_ampm == "오후":
                end_h24 += 12
            new_settings['active_end_h'] = end_h24
        except Exception as e:
            # 실패 시 기본값 저장
            new_settings['active_start_h'] = 9
            new_settings['active_end_h'] = 21
        
        # 창 크기 정보 추가
        width = self.settings_window.winfo_width()
        height = self.settings_window.winfo_height()
        if width > 100 and height > 100:
            new_settings['settings_window_width'] = width
            new_settings['settings_window_height'] = height
            
        # 프롬프트 템플릿 저장 추가
        new_settings['gemini_prompt_template'] = self.prompt_text.get('1.0', 'end-1c').strip()
            
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

    def _on_frame_configure(self, event):
        # 1. 캔버스 스크롤 영역 갱신
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        
        # 2. 긴 설명용 Label들의 wraplength를 프레임 너비에 맞게 동적으로 조정 (자동 줄바꿈)
        # 패딩과 여백을 뺀 값으로 설정 (최소 100 픽셀 확보)
        new_width = event.width - 60
        if new_width < 100:
            return
            
        def _update_recursive(widget):
            if isinstance(widget, tk.Label):
                text = widget.cget("text")
                # 설명글 성격의 긴 텍스트(15자 이상)를 가진 라벨만 대상으로 줄바꿈 너비 지정
                if text and len(text) > 15:
                    widget.configure(wraplength=new_width, justify='left', anchor='w')
            
            for child in widget.winfo_children():
                _update_recursive(child)
                
        _update_recursive(self.scrollable_frame)

    def _restore_gemini_defaults(self):
        """AI 주관식 관련 프롬프트 및 지시문 설정을 초기 기본값으로 원상복구합니다."""
        if messagebox.askyesno(
            "기본값 복원",
            "AI 주관식 프롬프트 템플릿과 상황별 지시문 설정을 초기 기본값으로 원상복구하시겠습니까?\n"
            "(원상복구 후 '설정 저장' 버튼을 눌러야 최종 저장됩니다.)",
            parent=self.settings_window
        ):
            # 1. 마스터 프롬프트 복원
            self.prompt_text.delete('1.0', 'end')
            self.prompt_text.insert('1.0', SettingsDialog.DEFAULT_PROMPT_TEMPLATE)
            
            # 2. 상황별 지시문 복원
            self.setting_vars['gemini_prompt_min_limit'].set(SettingsDialog.DEFAULT_MIN_LIMIT)
            self.setting_vars['gemini_prompt_max_limit'].set(SettingsDialog.DEFAULT_MAX_LIMIT)
            self.setting_vars['gemini_prompt_no_limit'].set(SettingsDialog.DEFAULT_NO_LIMIT)
            
            messagebox.showinfo("복원 완료", "기본값으로 복원되었습니다.\n[💾 설정 저장] 버튼을 누르면 완전히 파일에 저장됩니다.", parent=self.settings_window)

    def _on_kakao_auth(self):
        """GUI 기반 카카오톡 인증 프로세스 진행 (도움말 위저드를 띄워 API 키 변경이 가능하도록 함)"""
        self._show_kakao_help()
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
