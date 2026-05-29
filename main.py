import tkinter as tk
from tkinter import messagebox
import json
import os
import threading
import logging
import time
import pystray
from datetime import datetime
from pystray import MenuItem as item
from PIL import Image

from main_task_manager import TaskManager
from ui.main_window import MainWindow
from ui.dialogs.baemin_dialog import show_baemin_purchase_dialog
from ui.dialogs.settings_dialog import SettingsDialog
from ui.dialogs.seminar_dialog import show_seminar_info_dialog

class DoctorBillApp:
    def __init__(self, root):
        self.root = root
        
        # 공통 설정 및 사용자 정보 상태 관리
        base_dir = os.path.dirname(os.path.abspath(__file__))
        self.settings_file = os.path.join(base_dir, "data", "settings.json")
        self.user_info = {
            'name': '로그인 대기',
            'points': '0 P',
            'attendance': '대기',
            'quiz': '대기'
        }
        
        self.default_settings = {
            'auto_attendance': True,
            'auto_attendance_hour': 9,
            'auto_attendance_min': 0,
            'auto_quiz': True,
            'auto_quiz_hour': 9,
            'auto_quiz_min': 5,
            'auto_survey': True,
            'auto_seminar_refresh': True,
            'auto_seminar_join': True,      # 자동 세미나 신청 활성화
            'auto_seminar_enter': True,     # 자동 세미나 입장 활성화
            'seminar_enter_delay': 5,
            'seminar_refresh_interval': 5,
            'browser_headless': False,      # 크롬 창 보이게 설정
            'kakao_notify_enabled': False,  # 카카오톡 알림 비활성화
            'notify_attendance': True,
            'notify_quiz': True,
            'notify_survey': True,
            'notify_seminar_join': True,
            'notify_seminar_enter': True,
            'notify_baemin': True,
            'notify_startup_summary': True,
            'notify_error': True,
            'settings_window_width': 520,
            'settings_window_height': 850
        }
        
        # 1. 설정 로드
        self.settings = self.load_settings()
        
        # 2. 작업 관리자 초기화
        self.task_manager = TaskManager()
        
        # 3. UI 생성 및 이벤트 와이어링
        self.ui = MainWindow(self.root, self.get_callbacks())
        
        # 4. 로깅 설정 (내부 로거를 UI 창으로 연결)
        self.setup_logging()
        
        # 5. 초기 작업 스케줄링 및 트레이 설정
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.setup_tray_icon()
        
        self.root.after(200, self.auto_login)
        self.root.after(1000, self.check_scheduled_tasks)

        self.ui.work_log.log_message("프로그램이 시작되었습니다.")

    # ================= Settings =================
    def load_settings(self):
        try:
            if os.path.exists(self.settings_file):
                with open(self.settings_file, 'r', encoding='utf-8') as f:
                    settings = json.load(f)
                merged = self.default_settings.copy()
                merged.update(settings)
                return merged
            else:
                self.save_settings(self.default_settings)
                return self.default_settings.copy()
        except:
            return self.default_settings.copy()

    def save_settings(self, settings=None):
        if settings is None:
            settings = self.settings
        try:
            with open(self.settings_file, 'w', encoding='utf-8') as f:
                json.dump(settings, f, ensure_ascii=False, indent=2)
        except Exception as e:
            self.log_message(f"❌ 설정 저장 실패: {e}")

    def get_setting(self, key):
        return self.settings.get(key, self.default_settings.get(key, False))

    def set_setting(self, key, value):
        self.settings[key] = value
        self.save_settings()

    # ================= Callbacks Registration =================
    def get_callbacks(self):
        """UI와 TaskManager가 통신할 콜백 모음집입니다."""
        return {
            # UI Actions (UI -> App -> TaskManager)
            'on_attendance': self.on_attendance,
            'on_quiz': self.on_quiz,
            'on_seminar_check': self.on_seminar_check,
            'on_survey_open': self.on_survey_open,
            'on_survey_problem': self.on_survey_problem,
            'on_quiz_problem': self.on_quiz_problem,
            'on_baemin_purchase': self.on_baemin_purchase,
            'on_settings': self.open_settings,
            'on_hide_to_tray': self.hide_window,
            'on_exit': self.on_closing,
            'on_seminar_refresh_toggle': self.on_seminar_refresh_toggle,
            'on_seminar_double_click': self.on_seminar_double_click,
            
            # Application Actions (TaskManager -> App -> UI)
            'log_message': self.log_message,
            'log_info': lambda m: self.log_message(f"ℹ {m}"),
            'log_error': lambda m: self.log_message(f"❌ {m}"),
            'log_success': lambda m: self.log_message(f"✅ {m}"),
            'log_warning': lambda m: self.log_message(f"⚠ {m}"),
            'update_status': self.gui_update_status,
            'update_user_info': self.gui_update_user_info,
            'update_display': self.gui_update_display,
            'log_and_update_status': self.log_and_update_status,
            'show_seminar_dialog': self.show_seminar_dialog,
            'update_seminar_dialog': self.update_seminar_dialog,
            'gui_instance': self
        }

    # ================= UI Actions -> TaskManager =================
    def auto_login(self):
        self.gui_update_status("로그인 중...")
        self.task_manager.execute_login(self.get_callbacks())

    def on_attendance(self):
        self.task_manager.execute_attendance(self.get_callbacks())

    def on_quiz(self):
        self.task_manager.execute_quiz(self.get_callbacks())

    def on_seminar_check(self):
        self.task_manager.execute_seminar(self.get_callbacks())

    def on_survey_open(self):
        self.task_manager.execute_survey(self.get_callbacks())

    def on_survey_problem(self, initial_question=None, initial_category=None, image_path=None):
        self.open_survey_problem(initial_question, initial_category, image_path)
        
    def open_survey_problem(self, initial_question=None, initial_category=None, image_path=None):
        try:
            from ui.dialogs.survey_problem_dialog import open_survey_problem_manager
            if image_path:
                paths = image_path if isinstance(image_path, list) else [image_path]
                for p in paths:
                    if os.path.exists(p):
                        try: os.startfile(p)
                        except: pass
            self.log_message("설문 문제 관리 창을 열고 있습니다...")
            open_survey_problem_manager(self.root, self.log_message, initial_question, initial_category)
        except Exception as e:
            self.log_message(f"❌ 설문 관리자를 열 수 없습니다: {e}")

    def on_quiz_problem(self, initial_question=None, initial_category=None, image_path=None):
        self.open_daily_quiz(initial_question, initial_category, image_path)

    def open_daily_quiz(self, initial_question=None, initial_category=None, image_path=None):
        try:
            from ui.dialogs.quiz_dialog import open_quiz_manager
            if image_path:
                paths = image_path if isinstance(image_path, list) else [image_path]
                for p in paths:
                    if os.path.exists(p):
                        try: os.startfile(p)
                        except: pass
            self.log_message("퀴즈 문제 관리 창을 열고 있습니다...")
            open_quiz_manager(self.root, self.log_message, initial_question, initial_category)
        except Exception as e:
            self.log_message(f"❌ 퀴즈 관리자를 열 수 없습니다: {e}")

    def on_baemin_purchase(self):
        try:
            self.gui_update_status("정보 조회 중...")
            # Thread에서 조회하도록 하는게 좋지만, 일단 간단히 실행
            info = self.task_manager.get_baemin_info(self.get_callbacks())
            self.gui_update_status("대기 중")
            
            def handle_purchase(quantity, phone, total_cost=None):
                self.task_manager.execute_baemin_purchase(quantity, phone, self.get_callbacks())
                
            show_baemin_purchase_dialog(
                self.root, 
                current_points=info.get('points', 0), 
                max_coupons=info.get('max_coupons', 0), 
                phone_number=info.get('phone', ''), 
                on_confirm_callback=handle_purchase,
                on_cancel_callback=lambda: None
            )
        except Exception as e:
            self.log_message(f"❌ 배민 정보 조회 불가: {e}")
            self.gui_update_status("에러 발생")

    def on_seminar_refresh_toggle(self, btn):
        current_text = btn.cget('text')
        if "멈춤" in current_text:
            btn.config(text="▶ 재개", bg="#27ae60")
            self.task_manager.state.is_seminar_refresh_paused = True
            self.log_message("세미나 새로고침이 일시정지되었습니다.")
        else:
            btn.config(text="⏸ 멈춤", bg="#e74c3c")
            self.task_manager.state.is_seminar_refresh_paused = False
            self.log_message("세미나 새로고침이 재개되었습니다.")

    def on_seminar_double_click(self, event):
        selection = self.ui.seminar_panel.seminar_tree.selection()
        if not selection: return
        item = selection[0]
        tags = self.ui.seminar_panel.seminar_tree.item(item, "tags")
        if 'date_separator' in tags: return
        
        detail_link = tags[0] if len(tags) > 0 else ""
        if not detail_link: return
        
        status_tag = tags[1] if len(tags) > 1 else None
        
        # 제목 추출 (4번째 컬럼)
        values = self.ui.seminar_panel.seminar_tree.item(item, "values")
        title = values[3] if len(values) > 3 else "알 수 없는 세미나"
        
        self.log_message(f"세미나 상세 요청을 처리중입니다: {title}")
        if detail_link.startswith('/'):
            detail_link = "https://www.doctorville.co.kr" + detail_link
        
        # TaskManager로 전달하여 처리
        self.task_manager._handle_seminar_single_action(detail_link, status_tag, self.get_callbacks(), title=title)
        self.ui.seminar_panel.seminar_tree.selection_remove(item)

    def start_kakao_auth_flow(self, settings_dialog):
        """카카오톡 자동 감지 인증 흐름을 실행합니다."""
        import threading
        import time
        import requests
        import os
        import json
        import tkinter as tk
        from tkinter import messagebox, simpledialog

        # 1. settings.json 로드
        settings_path = "data/settings.json"
        settings = self.load_settings()

        # 2. REST API Key 확인
        rest_api_key = settings.get('kakao_rest_api_key')
        if not rest_api_key:
            # 도움말 및 가이드 대화 상자를 직접 띄웁니다!
            from ui.dialogs.settings_dialog import KakaoWizardDialog
            KakaoWizardDialog(settings_dialog.settings_window, self.get_setting, self.save_settings, self.start_kakao_auth_flow)
            return

        # 3. Redirect URI
        redirect_uri = settings.get('kakao_redirect_uri', "http://localhost")

        # 4. 인증 URL 생성
        auth_url = (
            f"https://kauth.kakao.com/oauth/authorize?"
            f"client_id={rest_api_key}&"
            f"redirect_uri={redirect_uri}&"
            f"response_type=code&"
            f"scope=talk_message"
        )

        # 5. 자동화 크롬이 실행 중인지 확인
        state = self.task_manager.state
        driver = None
        if state and state.web_automation and state.web_automation.driver:
            driver = state.web_automation.driver

        if not driver:
            # 자동화 크롬이 없는 경우, 기존처럼 팝업 입력식으로 진행 (백업 장치)
            import webbrowser
            webbrowser.open(auth_url)
            
            auth_code = simpledialog.askstring(
                "💬 카카오 인증 코드 입력",
                "카카오 자동화 크롬이 실행 중이 아닙니다.\n"
                "1. 열린 일반 웹 브라우저에서 로그인을 완료하세요.\n"
                "2. 주소창 전체 또는 'code=' 뒤의 코드를 복사하여 아래에 입력하세요:",
                parent=settings_dialog.settings_window
            )
            if not auth_code:
                return
            
            auth_code = auth_code.strip()
            if "code=" in auth_code:
                try: auth_code = auth_code.split("code=")[1].split("&")[0]
                except: pass
                
            self._exchange_and_save_kakao_token(auth_code, rest_api_key, redirect_uri, settings_dialog)
            return

        # 6. 자동화 크롬이 실행 중인 경우 -> 초간편 자동 감지 모드 실행!
        try:
            # 메인 탭 핸들 기억
            main_tab_handle = driver.current_window_handle
            
            # 새 탭 열기
            driver.execute_script("window.open(arguments[0], '_blank');", auth_url)
            auth_tab_handle = driver.window_handles[-1]
            driver.switch_to.window(auth_tab_handle)
            
            # 비차단형 안내 메세지 창 띄우기
            status_window = tk.Toplevel(settings_dialog.settings_window)
            status_window.title("💬 카카오 인증 진행 중")
            status_window.geometry("450x180")
            status_window.resizable(False, False)
            status_window.configure(bg='#ffffff')
            status_window.transient(settings_dialog.settings_window)
            status_window.grab_set()
            
            # 윈도우 센터링
            status_window.update_idletasks()
            w = status_window.winfo_width()
            h = status_window.winfo_height()
            x = settings_dialog.settings_window.winfo_x() + (settings_dialog.settings_window.winfo_width() // 2) - (w // 2)
            y = settings_dialog.settings_window.winfo_y() + (settings_dialog.settings_window.winfo_height() // 2) - (h // 2)
            status_window.geometry(f"+{x}+{y}")
            
            tk.Label(
                status_window, text="💬 카카오 로그인 자동 감지 중...",
                font=("맑은 고딕", 14, "bold"), bg='#ffffff', fg='#2c3e50'
            ).pack(pady=(20, 10))
            
            tk.Label(
                status_window, text="새로 열린 크롬 탭에서 로그인을 완료해 주세요.\n로그인이 완료되면 탭이 자동으로 닫히고 인증이 등록됩니다.",
                font=("맑은 고딕", 10), bg='#ffffff', fg='#7f8c8d', justify='center'
            ).pack(pady=5)
            
            # 모니터링 정지 플래그
            is_cancelled = [False]
            
            def on_cancel():
                is_cancelled[0] = True
                status_window.destroy()
                # 탭 닫기 시도
                try:
                    if auth_tab_handle in driver.window_handles:
                        driver.switch_to.window(auth_tab_handle)
                        driver.close()
                except:
                    pass
                try:
                    driver.switch_to.window(main_tab_handle)
                except:
                    pass
                messagebox.showwarning("취소", "카카오톡 인증이 취소되었습니다.", parent=settings_dialog.settings_window)
                
            cancel_btn = tk.Button(
                status_window, text="취소", font=("맑은 고딕", 10, "bold"),
                bg='#e74c3c', fg='white', relief='flat', padx=15, pady=5,
                command=on_cancel, cursor='hand2'
            )
            cancel_btn.pack(pady=10)
            
            status_window.protocol("WM_DELETE_WINDOW", on_cancel)

            # 백그라운드에서 URL 감시 스레드 가동
            def monitor_url_loop():
                auth_code = None
                try:
                    # 10분간 감시 (1200회 * 0.5초)
                    for _ in range(1200):
                        if is_cancelled[0]:
                            return
                            
                        # 브라우저 상태 체크
                        if auth_tab_handle not in driver.window_handles:
                            # 사용자가 탭을 수동으로 닫았음
                            self.root.after(0, lambda: self._on_auth_failed("사용자가 로그인 탭을 수동으로 닫았습니다.", status_window, settings_dialog))
                            return
                            
                        # 현재 URL 체크 (포커스 변경 없이 감지)
                        current_url = driver.current_url
                        
                        if "code=" in current_url and "kauth.kakao.com" not in current_url:
                            # 코드 감지 성공!
                            try:
                                auth_code = current_url.split("code=")[1].split("&")[0]
                            except Exception as parse_err:
                                self.root.after(0, lambda: self._on_auth_failed(f"인증 코드 파싱 실패: {parse_err}", status_window, settings_dialog))
                                return
                            break
                            
                        time.sleep(0.5)
                        
                    if not auth_code:
                        self.root.after(0, lambda: self._on_auth_failed("인증 대기 시간이 초과되었습니다.", status_window, settings_dialog))
                        return
                        
                    # 성공 처리
                    self.root.after(0, lambda: self._on_auth_success(auth_code, rest_api_key, redirect_uri, auth_tab_handle, main_tab_handle, status_window, settings_dialog))
                    
                except Exception as monitor_err:
                    self.root.after(0, lambda: self._on_auth_failed(f"모니터링 중 에러 발생: {monitor_err}", status_window, settings_dialog))
            
            threading.Thread(target=monitor_url_loop, daemon=True).start()
            
        except Exception as e:
            messagebox.showerror("❌ 에러 발생", f"자동 감지 시스템 작동 실패: {str(e)}", parent=settings_dialog.settings_window)

    def _exchange_and_save_kakao_token(self, auth_code, rest_api_key, redirect_uri, settings_dialog):
        """수동 입력받은 코드로 토큰 교환 및 저장"""
        import requests
        from tkinter import messagebox
        token_url = "https://kauth.kakao.com/oauth/token"
        data = {
            "grant_type": "authorization_code",
            "client_id": rest_api_key,
            "redirect_uri": redirect_uri,
            "code": auth_code
        }
        try:
            response = requests.post(token_url, data=data)
            result = response.json()
            if response.status_code == 200:
                settings = self.load_settings()
                settings['kakao_access_token'] = result.get('access_token')
                settings['kakao_refresh_token'] = result.get('refresh_token')
                settings['kakao_notify_enabled'] = True
                self.save_settings(settings)
                
                # GUI 동기화
                settings_dialog.setting_vars['kakao_notify_enabled'].set(True)
                for w in settings_dialog._notify_sub_widgets:
                    try: w.configure(state='normal')
                    except: pass
                
                messagebox.showinfo("✅ 인증 성공", "카카오톡 알림 인증이 성공적으로 완료되었습니다!", parent=settings_dialog.settings_window)
            else:
                err_desc = result.get('error_description', result.get('error', '알 수 없는 오류'))
                messagebox.showerror("❌ 인증 실패", f"토큰 발급에 실패했습니다:\n{err_desc}", parent=settings_dialog.settings_window)
        except Exception as e:
            messagebox.showerror("❌ 에러 발생", f"토큰 교환 중 에러 발생: {e}", parent=settings_dialog.settings_window)

    def _on_auth_success(self, auth_code, rest_api_key, redirect_uri, auth_tab_handle, main_tab_handle, status_window, settings_dialog):
        """자동 감지 성공 시 처리"""
        # 1. 탭 닫기 및 메인 탭 복귀
        try:
            state = self.task_manager.state
            if state and state.web_automation and state.web_automation.driver:
                driver = state.web_automation.driver
                if auth_tab_handle in driver.window_handles:
                    driver.switch_to.window(auth_tab_handle)
                    driver.close()
                driver.switch_to.window(main_tab_handle)
        except:
            pass
            
        # 2. 상태 창 닫기
        try: status_window.destroy()
        except: pass
        
        # 3. 토큰 교환 및 저장
        self._exchange_and_save_kakao_token(auth_code, rest_api_key, redirect_uri, settings_dialog)

    def _on_auth_failed(self, reason, status_window, settings_dialog):
        """자동 감지 실패 시 처리"""
        from tkinter import messagebox
        try: status_window.destroy()
        except: pass
        messagebox.showerror("❌ 인증 실패", f"카카오 자동 인증에 실패했습니다:\n{reason}", parent=settings_dialog.settings_window)

    def open_settings(self):
        # 설정 창을 열기 직전 파일에서 최신 정보를 다시 불러와 동기화합니다.
        self.settings = self.load_settings()
        
        def on_save(new_set):
            # 모든 설정을 저장 (기존의 렉 유발 요인인 재시작 로직 제거)
            for k, v in new_set.items(): 
                self.set_setting(k, v)
            
            # 현재 실행 중인 자동화 객체가 있다면 headless 설정값을 업데이트
            if self.task_manager.state.web_automation:
                self.task_manager.state.web_automation.headless = new_set.get('browser_headless', True)
                
            messagebox.showinfo("저장", "설정이 저장되었습니다.")
                
        def on_close(dims):
            if dims:
                self.set_setting('settings_window_width', dims.get('width', 520))
                self.set_setting('settings_window_height', dims.get('height', 850))

        SettingsDialog(self.root, self.get_setting, on_save, on_close, self.start_kakao_auth_flow)

    # ================= Tray Icon & Window Control =================
    def setup_tray_icon(self):
        """시스템 트레이 아이콘을 설정하고 별도 스레드에서 실행합니다."""
        try:
            icon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "icon.png")
            image = Image.open(icon_path) if os.path.exists(icon_path) else Image.new('RGB', (64, 64), color=(39, 174, 96))
            
            account_name = os.environ.get('ACCOUNT_NAME', '')
            title_text = f"닥터빌 자동화 [{account_name}]" if account_name else "닥터빌 자동화"
            
            # 1. 초기 메뉴 구성 (정보 포함)
            name_info = f"👤 {self.user_info['name']} ({self.user_info['points']})"
            status_info = f"✅ 출석: {self.user_info['attendance']} | 🧠 퀴즈: {self.user_info['quiz']}"
            
            menu_content = pystray.Menu(
                item(name_info, lambda: None, enabled=False),
                item(status_info, lambda: None, enabled=False),
                pystray.Menu.SEPARATOR,
                item('🔓 열기', lambda icon, item: self.root.after(0, self.show_window), default=True),
                item('⚙️ 설정', lambda icon, item: self.root.after(0, self.open_settings)),
                pystray.Menu.SEPARATOR,
                item('❌ 완전 종료', lambda icon, item: self.root.after(0, self.on_closing))
            )
            
            # 2. 아이콘 객체 생성 및 스레드 시작
            self.tray_icon = pystray.Icon("doctor_ville_auto", image, title_text, menu_content)
            threading.Thread(target=self.tray_icon.run, daemon=True).start()
            
        except Exception as e:
            self.log_message(f"⚠ 트레이 아이콘 생성 실패: {e}")

    def refresh_tray_menu(self):
        """사용자 정보를 포함하여 트레이 메뉴를 최신화합니다."""
        if not hasattr(self, 'tray_icon'):
            return

        # 정보 메뉴 텍스트 재구성 (enabled=True로 설정하여 회색 현상 해결)
        name_info = f"👤 {self.user_info['name']} ({self.user_info['points']})"
        status_info = f"✅ 출석: {self.user_info['attendance']} | 🧠 퀴즈: {self.user_info['quiz']}"
        
        menu_content = pystray.Menu(
            item(name_info, lambda: None), # 클릭 동작 없음 (정보 열람용)
            item(status_info, lambda: None),
            pystray.Menu.SEPARATOR,
            item('🔓 열기', lambda icon, item: self.root.after(0, self.show_window), default=True),
            item('⚙️ 설정', lambda icon, item: self.root.after(0, self.open_settings)),
            pystray.Menu.SEPARATOR,
            item('❌ 완전 종료', lambda icon, item: self.root.after(0, self.on_closing))
        )
        self.tray_icon.menu = menu_content

    def hide_window(self):
        """창을 숨기고 트레이로 최소화한 것처럼 보이게 합니다."""
        self.root.withdraw()
        
        # 💡 브라우저 창도 같이 숨김 (설정이 '창 보이기' 상태일 때만 의미 있음)
        self.task_manager.set_browser_visibility(False)
        
        if hasattr(self, 'tray_icon'):
            # 현재 상태를 다시 한번 메뉴에 반영
            self.refresh_tray_menu()
            self.tray_icon.notify("프로그램이 시스템 트레이로 최소화되었습니다.", "알림")

    def show_window(self, icon=None, item=None):
        """트레이에서 창을 다시 화면으로 불러옵니다."""
        self.root.after(0, self.root.deiconify)
        self.root.after(0, self.root.lift)
        self.root.after(0, lambda: self.root.state('normal'))
        
        # 💡 브라우저 창도 같이 다시 표시
        self.task_manager.set_browser_visibility(True)

    def on_closing(self, icon=None, item=None):
        self.log_message("프로그램을 종료합니다...")
        
        # 1. 화면 창을 즉시 숨깁니다 (사용자 입장에서는 꺼진 것처럼 보임)
        self.root.withdraw()
        
        # 트레이 아이콘이 있으면 종료
        if hasattr(self, 'tray_icon'):
            try:
                self.tray_icon.stop()
            except:
                pass
        
        # 2. 백그라운드에서 크롬을 안전하게 끄고 완전히 프로세스를 종료합니다
        def fast_exit():
            try:
                self.task_manager.cleanup() # 크롬 종료 대기 (1~2초 소요)
            except:
                pass
            import os
            os._exit(0) # 완벽한 종료
            
        threading.Thread(target=fast_exit, daemon=True).start()

    # ================= TaskManager -> UI Effects =================
    def log_message(self, message):
        self.root.after(0, lambda: self.ui.work_log.log_message(message))

    def gui_update_status(self, status):
        self.root.after(0, lambda: self.ui.update_status(status))

    def gui_update_user_info(self, user_name=None, account_type=None):
        if user_name:
            self.user_info['name'] = user_name
        self.root.after(0, lambda: self.ui.dashboard.update_user_info(user_name, account_type))
        self.root.after(0, self.refresh_tray_menu)

    def gui_update_display(self, display_type, value):
        # 작업 매니저에서 오는 다양한 키 값을 인지하도록 보강
        if display_type in ['points', 'user_points']: self.user_info['points'] = value
        elif display_type in ['attendance', 'attendance_status']: self.user_info['attendance'] = value
        elif display_type in ['quiz', 'quiz_status']: self.user_info['quiz'] = value
        
        self.root.after(0, lambda: self.ui.dashboard.update_display(display_type, value))
        self.root.after(0, self.refresh_tray_menu)

    def log_and_update_status(self, log_msg, status_msg):
        self.log_message(log_msg)
        self.gui_update_status(status_msg)
        
    def show_seminar_dialog(self, seminars, cb):
        self._seminar_dialog_window = show_seminar_info_dialog(self.root, seminars, cb)

    def update_seminar_dialog(self, seminars):
        self.root.after(0, lambda: self._update_main_seminar_tree(seminars))
        self.root.after(0, lambda: self._update_seminar_dialog_window(seminars))
        
    def _update_seminar_dialog_window(self, seminars):
        if hasattr(self, '_seminar_dialog_window') and self._seminar_dialog_window.winfo_exists():
            try:
                self._seminar_dialog_window.refresh_data(seminars)
            except:
                pass

    def _update_main_seminar_tree(self, seminars):
        self.ui.seminar_panel.clear_all()
        
        # 오늘 날짜 구하기 (ex: "2/27")
        import datetime
        today = datetime.datetime.now()
        today_str = f"{today.month}/{today.day}"
        
        # 오늘 세미나만 필터링
        today_seminars = [s for s in seminars if s.get('date', '') == today_str]
        
        if not today_seminars:
            self.ui.seminar_panel.insert_item(("", "", "", "오늘 예정된 세미나가 없습니다", "", "", ""))
            return
            
        current_date = None
        for s in today_seminars:
            if current_date != s.get('date', ''):
                current_date = s.get('date', '')
                if current_date:
                    self.ui.seminar_panel.insert_item((f"📅 {current_date} {s.get('day','')}", "", "", "", "", "", ""), tags=('date_separator',))
            from modules.utils import get_status_tag
            status_tag = get_status_tag(s.get('status',''))
            self.ui.seminar_panel.insert_item(
                (s.get('date',''), s.get('day',''), s.get('time',''), s.get('title',''), s.get('lecturer',''), s.get('person',''), s.get('status','')),
                tags=(s.get('detail_link',''), status_tag)
            )

    # ================= Utils =================
    def setup_logging(self):
        """
        로깅 설정 - 시스템 로그는 파일에만 남기고, GUI 로그는 명시적 콜백으로만 관리
        """
        # 로그 저장 폴더 생성
        log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs")
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)
            
        account_name = os.environ.get('ACCOUNT_NAME', 'default')
        log_file = os.path.join(log_dir, f"dva_{account_name}_{datetime.now().strftime('%Y%m%d')}.log")
        
        # 전체 로거 설정 (INFO 레벨)
        logger = logging.getLogger()
        logger.setLevel(logging.INFO)
        
        # 기존 핸들러 제거 (중복 방지)
        for handler in logger.handlers[:]:
            logger.removeHandler(handler)
            
        # 1. 파일 핸들러 (모든 상세 로그 저장)
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setFormatter(logging.Formatter('[%(asctime)s] [%(name)s] [%(levelname)s] %(message)s'))
        logger.addHandler(file_handler)
        
        # 💡 [중요] GUI 핸들러는 더 이상 Root Logger에 추가하지 않습니다.
        # 이렇게 함으로써 logger.info() 호출이 GUI 로그창을 더럽히는 것을 원천 봉쇄합니다.
        # GUI 로그는 오직 self.log_message() 호출을 통해서만 이루어집니다.

    def check_scheduled_tasks(self):
        self.task_manager.check_scheduled_tasks(self.settings, self.get_callbacks())
        # 반복 실행 (1초 간격으로 검사하여 딜레이 최소화)
        self.root.after(1000, self.check_scheduled_tasks)


def main():
    root = tk.Tk()
    
    # 창 제목에 계정 이름 표시
    account_name = os.environ.get('ACCOUNT_NAME', '')
    title_suffix = f" [{account_name}]" if account_name else ""
    root.title(f"닥터빌 자동화 프로그램{title_suffix}")
    
    app = DoctorBillApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()
