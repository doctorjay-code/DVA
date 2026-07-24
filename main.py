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
from ui.dialogs.point_use_dialog import (
    show_point_use_loading_dialog,
    show_coupon_select_dialog,
    show_coupon_purchase_dialog
)
from ui.dialogs.settings_dialog import SettingsDialog
from ui.dialogs.seminar_dialog import show_seminar_info_dialog

VERSION = "v3.9.3"

class DoctorBillApp:
    def __init__(self, root):
        self.root = root
        
        # 공통 설정 및 사용자 정보 상태 관리
        base_dir = os.path.dirname(os.path.abspath(__file__))
        account_name = os.environ.get('ACCOUNT_NAME', '').strip()
        if account_name:
            self.settings_file = os.path.join(base_dir, "data", f"settings_{account_name}.json")
        else:
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
            'auto_quiz_min': 1,
            'auto_survey': True,
            'auto_survey_submit': True,
            'gemini_api_key': "",
            'gemini_prompt_template': (
                "의학 세미나 설문조사 주관식 질문입니다. 의사 또는 의료 전문가 관점에서 신뢰감 있고 전문적으로 답변해 주세요.\n\n"
                "답변을 작성할 때 반드시 다음 규칙을 지켜주세요:\n"
                "1. 큰따옴표(\"\"), 작은따옴표(''), 대괄호([]), 소괄호(()) 등의 모든 따옴표와 괄호 기호를 절대로 사용하지 마세요.\n"
                "2. 사람이 직접 손으로 타이핑한 것 같이 자연스러운 존댓말 형태로 작성해 주세요.\n"
                "3. 줄바꿈을 하지 말고 하나의 완성된 문단(단일 paragraph)으로만 답변을 작성해 주세요.\n"
                "4. 답변 외에 다른 군더더기 메타 설명(예: '답변:', '작성된 의견:', '최소 글자 수를 만족하는 답변입니다')은 절대 포함하지 마세요.\n\n"
                "{length_condition}\n\n"
                "질문: {question}"
            ),
            'auto_seminar_refresh': True,
            'auto_seminar_join': True,      # 자동 세미나 신청 활성화
            'auto_seminar_enter': True,     # 자동 세미나 입장 활성화
            'seminar_enter_delay': 1,
            'auto_seminar_close': True,    # 자동 세미나 퇴장 활성화
            'seminar_close_delay': 1,
            'seminar_refresh_interval': 60,
            'browser_headless': False,      # 크롬 창 보이게 설정
            'kakao_notify_enabled': False,  # 카카오톡 알림 비활성화
            'notify_attendance': True,
            'notify_quiz': True,
            'notify_survey': True,
            'notify_subjective_answer': True,
            'notify_seminar_join': True,
            'notify_seminar_enter': True,
            'notify_baemin': True,
            'notify_startup_summary': True,
            'notify_error': True,
            'baemin_phone': "",
            'auto_point_payment': False,
            'settings_window_width': 520,
            'settings_window_height': 950,
            'use_active_time_range': False,
            'active_start_h': 9,
            'active_start_m': 0,
            'active_end_h': 21,
            'active_end_m': 0,
            'auto_update_check': True
        }
        
        # 1. 설정 로드
        self.settings = self.load_settings()
        
        # 2. 작업 관리자 초기화
        self.task_manager = TaskManager()
        
        # 3. UI 생성 및 이벤트 와이어링
        self.ui = MainWindow(self.root, self.get_callbacks(), version=VERSION)
        
        # 4. 로깅 설정 (내부 로거를 UI 창으로 연결)
        self.setup_logging()
        
        self.update_check_completed = False
        self.last_auto_update_check_time = datetime.now()

        # 5. 초기 작업 스케줄링 및 트레이 설정
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.setup_tray_icon()
        
        self.root.after(200, self.start_update_check)
        self.root.after(500, self.check_slack_ipc_commands)
        self.root.after(1000, self.check_scheduled_tasks)
        self.root.after(1500, lambda: self.task_manager.start_slack_listener(self.get_callbacks()))

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
                # 계정별 전용 셋팅 파일(예: settings_박주하.json)이 최초 생성될 때
                # 기존 settings.json 의 소중한 설정값(Gemini키, 카카오토큰, 휴대폰번호 등)을 그대로 계승하여 절대 날아가지 않도록 보존합니다.
                base_dir = os.path.dirname(os.path.abspath(__file__))
                base_settings_file = os.path.join(base_dir, "data", "settings.json")
                initial_settings = self.default_settings.copy()
                if os.path.exists(base_settings_file) and base_settings_file != self.settings_file:
                    try:
                        with open(base_settings_file, 'r', encoding='utf-8') as f:
                            base_settings = json.load(f)
                        initial_settings.update(base_settings)
                    except:
                        pass
                self.save_settings(initial_settings)
                return initial_settings.copy()
        except:
            return self.default_settings.copy()

    def save_settings(self, settings=None):
        if settings is None:
            settings = self.settings
        else:
            self.settings = settings
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
            'notify_kakao': lambda msg, cat="notify_startup_summary": self.task_manager.notifier.send_kakao_message(msg, category=cat),
            'gui_instance': self
        }

    # ================= UI Actions -> TaskManager =================
    def auto_login(self):
        self.gui_update_status("로그인 중...")
        self.task_manager.execute_login(self.get_callbacks())

    def complete_update_check_and_login(self):
        self.update_check_completed = True
        self.auto_login()

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
            self.log_message("세미나 문제 관리 창을 열고 있습니다...")
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

    def on_baemin_purchase(self, force_refresh=False):
        def reset_module_state():
            self.task_manager.state.current_module = 'baemin_refresh'
            
            # 다이얼로그가 완전히 닫히면 메인 탭으로 포커스를 복구하고 포인트를 비동기로 갱신
            def _restore_and_refresh():
                try:
                    with self.task_manager.browser_lock:
                        state = self.task_manager.state
                        if state.web_automation and state.web_automation.driver:
                            driver = state.web_automation.driver
                            # 메인 탭(첫 번째 탭)으로 전환
                            if len(driver.window_handles) > 0:
                                try:
                                    driver.switch_to.window(driver.window_handles[0])
                                    self.log_message("포인트 상태 확인을 위해 메인 탭으로 전환했습니다.")
                                except Exception as e_sw:
                                    self.log_message(f"⚠ 탭 전환 오류: {e_sw}")
                                
                            # 포인트 갱신 모듈 실행
                            from modules.points_check_module import PointsCheckModule
                            points_mod = PointsCheckModule(state.web_automation, self.task_manager.create_gui_logger(self.get_callbacks()))
                            points_mod.set_callbacks(self.get_callbacks())
                            points_mod.gui_instance = self
                            points_mod.execute()
                except Exception as e:
                    self.log_message(f"⚠ 후속 포인트 갱신 오류 (무시 가능): {e}")
                finally:
                    self.task_manager.state.current_module = None
                    
            import threading
            threading.Thread(target=_restore_and_refresh, daemon=True).start()

        try:
            base_dir = os.path.dirname(os.path.abspath(__file__))
            cache_path = os.path.join(base_dir, "data", "coupon_cache.json")
            
            # 1. 로컬 캐시가 존재하고 강제 새로고침이 아니라면, 브라우저 조회(1~2초 지연)를 건너뛰고 즉시 로드
            if not force_refresh and os.path.exists(cache_path):
                try:
                    with open(cache_path, 'r', encoding='utf-8') as f:
                        coupon_list = json.load(f)
                    if coupon_list:
                        # 대시보드 UI에 표시된 보유 포인트를 파싱하여 활용
                        raw_points = self.user_info.get('points', '0')
                        points_digits = "".join(c for c in str(raw_points) if c.isdigit())
                        points = int(points_digits) if points_digits else 0
                        
                        phone = self.get_setting('baemin_phone') or ""
                        
                        # 대화상자가 열려있는 동안 자동 스케줄러 간섭 방지 락 설정
                        self.task_manager.state.current_module = 'baemin'
                        
                        def on_coupon_selected(coupon_item):
                            account_name = os.environ.get('ACCOUNT_NAME', '')
                            
                            def on_purchase_confirmed(quantity, entered_phone, entered_name, item):
                                self.task_manager.execute_point_use_purchase(
                                    quantity, entered_phone, item, entered_name, self.get_callbacks()
                                )
                                
                            show_coupon_purchase_dialog(
                                self.root,
                                current_points=points,
                                coupon_item=coupon_item,
                                phone_number=phone,
                                sender_name=account_name,
                                on_confirm_callback=on_purchase_confirmed,
                                on_cancel_callback=reset_module_state
                            )
                            
                        favorites = self.get_setting('baemin_favorites') or []
                        
                        def on_toggle_favorite(guid):
                            favs = self.get_setting('baemin_favorites') or []
                            if guid in favs:
                                favs.remove(guid)
                                self.log_message(f"⭐ 즐겨찾기 해제: {guid}")
                            else:
                                favs.append(guid)
                                self.log_message(f"⭐ 즐겨찾기 등록: {guid}")
                            self.set_setting('baemin_favorites', favs)
                            
                        def on_refresh():
                            self.on_baemin_purchase(force_refresh=True)
                            
                        show_coupon_select_dialog(
                            self.root,
                            current_points=points,
                            coupon_list=coupon_list,
                            favorites_list=favorites,
                            on_select_callback=on_coupon_selected,
                            on_cancel_callback=reset_module_state,
                            on_toggle_favorite_callback=on_toggle_favorite,
                            on_refresh_callback=on_refresh
                        )
                        return # 즉시 띄웠으므로 함수 종료
                except Exception as ce:
                    self.log_message(f"⚠ 로컬 캐시 로드 실패, 실시간 조회를 진행합니다: {ce}")

            # 2. 로컬 캐시가 없거나 강제 새로고침인 경우: 기존처럼 로딩 창을 띄우고 브라우저 실시간 조회
            # 로딩 팝업 표시
            loading_win = show_point_use_loading_dialog(self.root)
            self.gui_update_status("상품 목록 조회 중...")
            
            # 백그라운드 스레드에서 get_point_use_info 실행
            def _fetch_info():
                try:
                    info = self.task_manager.get_point_use_info(self.get_callbacks(), force_refresh=force_refresh)
                    
                    # UI 조작은 메인 스레드에서 실행
                    def _show_select():
                        try:
                            loading_win.destroy()
                        except:
                            pass
                        self.gui_update_status("대기 중")
                        
                        points = info.get('points', 0)
                        phone = info.get('phone', '')
                        coupon_list = info.get('coupon_list', [])
                        
                        if not coupon_list:
                            self.log_message("❌ 상품 목록을 불러오지 못했습니다.")
                            return
                            
                        # 대화상자가 열려있는 동안 자동 스케줄러(세미나 갱신 등)가 끼어들지 못하도록 모듈 잠금 설정
                        self.task_manager.state.current_module = 'baemin'
                        
                        # 상품 선택 창 표시
                        def on_coupon_selected(coupon_item):
                            # 수량/번호 입력 창 표시
                            account_name = os.environ.get('ACCOUNT_NAME', '')
                            
                            def on_purchase_confirmed(quantity, entered_phone, entered_name, item):
                                # execute_point_use_purchase 호출
                                self.task_manager.execute_point_use_purchase(
                                    quantity, entered_phone, item, entered_name, self.get_callbacks()
                                )
                                
                            show_coupon_purchase_dialog(
                                self.root,
                                current_points=points,
                                coupon_item=coupon_item,
                                phone_number=phone,
                                sender_name=account_name,
                                on_confirm_callback=on_purchase_confirmed,
                                on_cancel_callback=reset_module_state
                            )
                            
                        favorites = self.get_setting('baemin_favorites') or []
                        
                        def on_toggle_favorite(guid):
                            favs = self.get_setting('baemin_favorites') or []
                            if guid in favs:
                                favs.remove(guid)
                                self.log_message(f"⭐ 즐겨찾기 해제: {guid}")
                            else:
                                favs.append(guid)
                                self.log_message(f"⭐ 즐겨찾기 등록: {guid}")
                            self.set_setting('baemin_favorites', favs)
                            
                        def on_refresh():
                            self.on_baemin_purchase(force_refresh=True)
                            
                        show_coupon_select_dialog(
                            self.root,
                            current_points=points,
                            coupon_list=coupon_list,
                            favorites_list=favorites,
                            on_select_callback=on_coupon_selected,
                            on_cancel_callback=reset_module_state,
                            on_toggle_favorite_callback=on_toggle_favorite,
                            on_refresh_callback=on_refresh
                        )
                    
                    self.root.after(0, _show_select)
                    
                except Exception as ex:
                    def _handle_err(err_msg=str(ex)):
                        try:
                            loading_win.destroy()
                        except:
                            pass
                        self.log_message(f"❌ 정보 조회 오류: {err_msg}")
                        self.gui_update_status("에러 발생")
                        self.task_manager.state.current_module = None
                    self.root.after(0, _handle_err)
            
            threading.Thread(target=_fetch_info, daemon=True).start()
            
        except Exception as e:
            self.log_message(f"❌ 포인트 사용 정보 조회 불가: {e}")
            self.gui_update_status("에러 발생")

    def on_seminar_refresh_toggle(self, btn):
        current_text = btn.cget('text')
        if "새로고침 중" in current_text or "작동 중" in current_text or "멈춤" in current_text:
            btn.config(text="🔴 일시 정지", bg="#e74c3c")
            self.task_manager.state.is_seminar_refresh_paused = True
            self.log_message("세미나 새로고침이 일시정지되었습니다.")
        else:
            btn.config(text="🟢 새로고침 중", bg="#27ae60")
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

    def start_kakao_auth_flow(self, settings_dialog, wizard_window=None):
        """카카오톡 자동 감지 인증 흐름을 실행합니다."""
        import threading
        import time
        import requests
        import os
        import json
        import tkinter as tk
        from tkinter import messagebox, simpledialog

        # 1. settings.json 로드
        self.settings = self.load_settings()
        settings = self.settings

        # 2. REST API Key 확인
        rest_api_key = settings.get('kakao_rest_api_key')
        if not rest_api_key:
            # 도움말 및 가이드 대화 상자를 직접 띄웁니다!
            from ui.dialogs.settings_dialog import KakaoWizardDialog
            KakaoWizardDialog(settings_dialog.settings_window, self.get_setting, self.save_settings, self.start_kakao_auth_flow, settings_dialog)
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

        parent_win = wizard_window.window if wizard_window else settings_dialog.settings_window

        # 5. 항상 기본 웹 브라우저(개인 크롬 등)로 연동을 진행합니다.
        import webbrowser
        webbrowser.open(auth_url)
        
        auth_code = simpledialog.askstring(
            "💬 카카오 인증 코드 입력",
            "1. 인터넷 창에서 로그인을 끝내고 '연결할 수 없음' 창이 뜨면,\n"
            "2. 주소창의 주소 전체(또는 code= 뒤의 값)를 복사해서 아래에 붙여넣어 주세요:",
            parent=parent_win
        )
        if not auth_code:
            return
        
        auth_code = auth_code.strip()
        if "code=" in auth_code:
            try: auth_code = auth_code.split("code=")[1].split("&")[0]
            except: pass
            
        success = self._exchange_and_save_kakao_token(auth_code, rest_api_key, redirect_uri, settings_dialog, parent_win)
        if success and wizard_window:
            wizard_window.window.destroy()
            wizard_window.canvas.unbind_all("<MouseWheel>")

    def _exchange_and_save_kakao_token(self, auth_code, rest_api_key, redirect_uri, settings_dialog, parent_win):
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
                
                messagebox.showinfo("✅ 인증 성공", "카카오톡 알림 인증이 성공적으로 완료되었습니다!", parent=parent_win)
                return True
            else:
                err_desc = result.get('error_description', result.get('error', '알 수 없는 오류'))
                messagebox.showerror("❌ 인증 실패", f"토큰 발급에 실패했습니다:\n{err_desc}", parent=parent_win)
                return False
        except Exception as e:
            messagebox.showerror("❌ 에러 발생", f"토큰 교환 중 에러 발생: {e}", parent=parent_win)
            return False

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
        # GUI 로그를 파일 로그에도 똑같이 기록합니다.
        logging.info(f"[GUI] {message}")

    def gui_update_status(self, status):
        # 다줄 문구인 경우(상태 요약 등)는 1줄 메시지로 정리하여 상태 라벨 깨짐 방지
        clean_status = status
        if status and "\n" in str(status):
            clean_status = "포인트/상태 갱신 완료"
        self.root.after(0, lambda: self.ui.update_status(clean_status))

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

    def start_update_check(self):
        """백그라운드 스레드에서 업데이트 검사 시작"""
        self.remove_deprecated_files_locally()
        threading.Thread(target=self.check_for_updates, daemon=True).start()

    def remove_deprecated_files_locally(self):
        """더 이상 사용되지 않는 옛날 파일 정리 (예: 업데이트.bat)"""
        base_dir = os.path.dirname(os.path.abspath(__file__))
        deprecated_files = ['업데이트.bat']
        for file_name in deprecated_files:
            file_path = os.path.join(base_dir, file_name)
            if os.path.exists(file_path):
                try:
                    os.remove(file_path)
                except Exception:
                    pass

    def check_for_updates(self, is_auto=False):
        """업데이트 확인 로직 (백그라운드 스레드)"""
        base_dir = os.path.dirname(os.path.abspath(__file__))
        
        # 💡 개발자 모드 감지 (.git 폴더가 존재할 경우 업데이트 체크 생략)
        if os.path.exists(os.path.join(base_dir, ".git")):
            if not is_auto:
                self.root.after(0, lambda: self.log_message("[시스템] 개발자 모드 감지: 업데이트 검사를 생략합니다."))
                self.root.after(0, self.complete_update_check_and_login)
            return
            
        version_file = os.path.join(base_dir, "data", "version.json")
        github_repo_url = "https://api.github.com/repos/doctorjay-code/DVA"
        
        # 1. GitHub API로 최신 커밋 SHA 가져오기
        remote_sha = None
        try:
            import requests
            headers = {"User-Agent": "DVA-Updater"}
            # API 제한 및 타임아웃 고려하여 3초 설정
            response = requests.get(f"{github_repo_url}/commits/main", headers=headers, timeout=3)
            if response.status_code == 200:
                remote_sha = response.json().get("sha")
        except Exception as e:
            # 네트워크 오류, 타임아웃 등
            if not is_auto:
                self.root.after(0, lambda: self.log_message(f"[시스템] 업데이트 확인 실패 (오프라인 모드 / {str(e)})"))
                self.root.after(0, self.complete_update_check_and_login)
            return

        if not remote_sha:
            if not is_auto:
                self.root.after(0, lambda: self.log_message("[시스템] 업데이트 확인 실패 (원격 정보를 받아올 수 없습니다.)"))
                self.root.after(0, self.complete_update_check_and_login)
            return

        # 2. 로컬 SHA 가져오기
        local_sha = None
        if os.path.exists(version_file):
            try:
                with open(version_file, "r", encoding="utf-8") as f:
                    local_data = json.load(f)
                    local_sha = local_data.get("latest_commit_sha")
            except Exception:
                pass

        # 3. 버전 비교 및 후속 조치
        if not local_sha:
            # 로컬 파일이 없으면 최초 실행으로 가정, 현재 원격 SHA를 파일에 저장하여 최신 상태로 등록
            try:
                os.makedirs(os.path.dirname(version_file), exist_ok=True)
                with open(version_file, "w", encoding="utf-8") as f:
                    json.dump({"latest_commit_sha": remote_sha}, f, indent=4)
                if not is_auto:
                    self.root.after(0, lambda: self.log_message(f"[시스템] 초기 버전 정보 등록 완료: 최신 버전({VERSION})을 사용 중입니다."))
            except Exception:
                pass
            self.root.after(0, self.complete_update_check_and_login)
        elif local_sha == remote_sha:
            # 최신 버전
            if not is_auto:
                self.root.after(0, lambda: self.log_message(f"[시스템] 업데이트 확인 완료: 최신 버전({VERSION})을 사용 중입니다."))
            self.root.after(0, self.complete_update_check_and_login)
        else:
            # 업데이트 필요
            if is_auto:
                self.root.after(0, lambda: self.execute_silent_update(remote_sha))
            else:
                self.root.after(0, lambda: self.prompt_update_execution(remote_sha))

    def execute_silent_update(self, remote_sha):
        """1시간 주기 스캔에서 업데이트 발견 시, 사용자 팝업 없이 즉시 자동 업데이트 및 재기동 수행"""
        import subprocess
        import sys
        
        # 🚨 [2차 안전 가드] 그 사이에 다른 백그라운드 작업이 시작되었는지 더블 체크
        if self.task_manager.state.current_module is not None:
            self.log_message(f"[시스템] 업데이트가 감지되었으나 현재 백그라운드 작업('{self.task_manager.state.current_module}')이 진행 중이므로 업데이트를 10분 후로 연기합니다.")
            from datetime import timedelta
            self.last_auto_update_check_time = datetime.now() - timedelta(seconds=3000) # 10분 후 재검사
            return

        self.log_message("[시스템] 새로운 업데이트가 감지되어 프로그램을 자동 종료하고 업데이트를 실행합니다...")
        try:
            # scripts/update_program.py --auto 실행
            base_dir = os.path.dirname(os.path.abspath(__file__))
            script_path = os.path.join(base_dir, "scripts", "update_program.py")
            
            # detached process로 실행하여 부모 프로세스 종료 시에도 독립적으로 살아있게 함
            subprocess.Popen(
                [sys.executable, script_path, "--auto"],
                creationflags=subprocess.DETACHED_PROCESS if os.name == 'nt' else 0,
                close_fds=True
            )
            # 현재 메인 윈도우 안전하게 종료
            self.on_closing()
        except Exception as e:
            self.log_message(f"[시스템] 자동 업데이트 스크립트 실행 실패: {e}")

    def prompt_update_execution(self, remote_sha):
        """메인 스레드에서 사용자에게 업데이트 의사를 물어보고 실행"""
        from tkinter import messagebox
        import subprocess
        import sys
        
        answer = messagebox.askyesno(
            "새로운 업데이트 발견",
            "새로운 업데이트 버전이 존재합니다.\n지금 프로그램을 종료하고 업데이트를 진행하시겠습니까?"
        )
        if answer:
            # 🚨 [2차 안전 가드] 사용자 응답을 대기하는 동안 백그라운드 작업이 실행되었는지 더블 체크
            if self.task_manager.state.current_module is not None:
                messagebox.showwarning(
                    "업데이트 연기",
                    f"현재 백그라운드 작업('{self.task_manager.state.current_module}')이 수행 중입니다.\n작업이 모두 끝난 후 다시 시도해 주세요."
                )
                self.complete_update_check_and_login()
                return

            self.log_message("[시스템] 프로그램을 종료하고 업데이트를 시작합니다...")
            try:
                # scripts/update_program.py --auto 실행
                base_dir = os.path.dirname(os.path.abspath(__file__))
                script_path = os.path.join(base_dir, "scripts", "update_program.py")
                
                # detached process로 실행하여 부모 프로세스 종료 시에도 독립적으로 살아있게 함
                subprocess.Popen(
                    [sys.executable, script_path, "--auto"],
                    creationflags=subprocess.DETACHED_PROCESS if os.name == 'nt' else 0,
                    close_fds=True
                )
                # 현재 메인 윈도우 안전하게 종료
                self.on_closing()
            except Exception as e:
                messagebox.showerror("오류", f"업데이트 스크립트 실행 실패: {e}")
                self.complete_update_check_and_login()
        else:
            self.log_message("[시스템] 업데이트가 취소되었습니다. 현재 버전으로 계속 실행합니다.")
            self.complete_update_check_and_login()

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

    def check_slack_ipc_commands(self):
        """Slack 원격 명령 IPC 수신기: 동시에 실행 중인 박주하/박범준 앱에 실시간 명령 전파"""
        try:
            base_dir = os.path.dirname(os.path.abspath(__file__))
            dispatch_file = os.path.join(base_dir, "data", "slack_cmd_dispatch.json")
            if os.path.exists(dispatch_file):
                with open(dispatch_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                
                cmd_id = data.get("cmd_id")
                timestamp = data.get("timestamp", 0)
                
                import time
                if time.time() - timestamp < 15 and cmd_id != getattr(self, '_last_processed_slack_cmd_id', None):
                    self._last_processed_slack_cmd_id = cmd_id
                    
                    raw_text = data.get("raw_text", "")
                    my_account = os.environ.get("ACCOUNT_NAME", "").strip()
                    
                    is_target = True
                    if my_account and raw_text:
                        import re
                        clean_text = re.sub(r'<@.*?>', '', raw_text).strip()
                        my_names = [my_account]
                        if len(my_account) >= 2:
                            my_names.append(my_account[1:])  # 예: '박주하' -> '주하'
                        
                        # 1. 내 계정 이름이 포함되어 있으면 무조건 내 타겟
                        if any(n in clean_text for n in my_names if n):
                            is_target = True
                        else:
                            # 2. 다른 사람 계정 이름이 콕 집어 언급되어 있는지만 검사
                            all_known_accounts = ["박주하", "주하", "박범준", "범준"]
                            other_target_mentioned = False
                            for acc in all_known_accounts:
                                if acc not in my_names and acc in clean_text:
                                    other_target_mentioned = True
                                    break
                            
                            if other_target_mentioned:
                                is_target = False
                            else:
                                is_target = True
                        
                    if is_target:
                        task_name = data.get("task_name")
                        task_desc_map = {
                            'attendance': '📅 출석 체크',
                            'quiz': '🧠 일일 퀴즈 풀이',
                            'points': '💰 포인트/상태 갱신',
                            'seminar': '📢 세미나 목록',
                            'survey': '📋 세미나 설문',
                            'baemin': '🛵 포인트 사용 / 쿠폰 구매'
                        }
                        task_desc = task_desc_map.get(task_name, task_name)
                        self.log_message(f"📱 [Slack 원격 요청] {task_desc} 실행 요청 수신")
                        
                        gui_callbacks = self.get_callbacks()
                        if task_name == 'attendance':
                            self.on_attendance()
                        elif task_name == 'quiz':
                            self.on_quiz()
                        elif task_name == 'seminar':
                            self.on_seminar_check()
                        elif task_name == 'survey':
                            self.on_survey_open()
                        elif task_name == 'points':
                            self.task_manager.execute_module_by_config('points', gui_callbacks)
                        elif task_name == 'baemin':
                            p_kw = data.get('product_keyword', '배달의민족')
                            qty = data.get('quantity', 1)
                            self.on_baemin_remote_purchase(product_keyword=p_kw, quantity=qty)
                        elif task_name == 'answer_registration':
                            answer_val = data.get('answer_val') or data.get('product_keyword') or ''
                            answer_queue = data.get('answer_queue') or []
                            from modules.survey_module import SurveyModule
                            from modules.survey_problem import SurveyProblemManager
                            
                            if answer_queue:
                                SurveyModule.pending_answer_queue = answer_queue
                                
                            pending = getattr(SurveyModule, 'current_pending_quiz', None)
                            if pending and pending.get('question'):
                                pm = SurveyProblemManager()
                                pm.add_quiz(pending['question'], answer_val, category=pending.get('category', ''))
                                queue_str = f" (대기열: {', '.join(answer_queue)})" if answer_queue else ""
                                self.log_message(f"✅ [Slack 원격 정답 등록] 정답 '{answer_val}'{queue_str} 등록 완료 (풀이 자동 재개)")
        except Exception as ipc_err:
            self.log_message(f"⚠ Slack IPC 명령 처리 오류: {ipc_err}")
        finally:
            self.root.after(500, self.check_slack_ipc_commands)

    def on_baemin_remote_purchase(self, product_keyword='배달의민족', quantity=1):
        """Slack 원격 요청을 받아 GUI 팝업 없이 지정된 상품과 수량으로 백그라운드 자동 결제 진행"""
        def _run_remote_purchase():
            try:
                base_dir = os.path.dirname(os.path.abspath(__file__))
                cache_path = os.path.join(base_dir, "data", "coupon_cache.json")
                coupon_list = []
                
                # 1. 로컬 캐시에서 쿠폰 목록 읽기 시도
                if os.path.exists(cache_path):
                    try:
                        with open(cache_path, 'r', encoding='utf-8') as f:
                            coupon_list = json.load(f)
                    except Exception:
                        coupon_list = []
                        
                # 2. 캐시에 없으면 실시간 크롤링 시도
                if not coupon_list:
                    from modules.baemin_module import BaeminModule
                    with self.task_manager.browser_lock:
                        web_auto = self.task_manager.ensure_web_automation_alive(self.get_callbacks())
                        if web_auto:
                            baemin = BaeminModule(web_auto, self.task_manager.create_gui_logger(self.get_callbacks()))
                            coupon_list = baemin.scrape_coupon_list()
                            
                # 3. 매칭되는 쿠폰 검색
                target_coupon = None
                if coupon_list:
                    alias_map = {
                        "네이버": ["네이버", "N페이", "네페"],
                        "배달의민족": ["배달의민족", "배민"],
                        "카카오": ["카카오", "카카오페이"],
                        "스타벅스": ["스타벅스", "스벅"]
                    }
                    search_keywords = alias_map.get(product_keyword, [product_keyword])

                    for item in coupon_list:
                        name = item.get('name', '')
                        if any(kw in name for kw in search_keywords):
                            target_coupon = item
                            break
                            
                    if not target_coupon:
                        for item in coupon_list:
                            if "배달의민족" in item.get('name', ''):
                                target_coupon = item
                                break
                        if not target_coupon:
                            target_coupon = coupon_list[0]
                            
                # Fallback 기본 쿠폰
                if not target_coupon:
                    target_coupon = {
                        'name': '배달의민족 10,000원',
                        'price': 9700,
                        'value': 10000,
                        'guid': '14152303',
                        'purchase_type': 'bulk'
                    }
                    
                phone = self.get_setting('baemin_phone') or ""
                account_name = os.environ.get('ACCOUNT_NAME', '')
                
                self.log_message(f"🛵 [Slack 원격 결제 실행] {target_coupon.get('name')} {quantity}개 (수신번호: {phone or '기본'})")
                
                # force_auto_pay=True 로 GUI 팝업 없이 백그라운드 결제까지 완결
                self.task_manager.execute_point_use_purchase(
                    quantity=quantity,
                    phone=phone,
                    coupon_item=target_coupon,
                    sender_name=account_name,
                    gui_callbacks=self.get_callbacks(),
                    force_auto_pay=True
                )
            except Exception as e:
                self.log_message(f"❌ Slack 원격 구매 처리 중 오류: {e}")
                
        import threading
        threading.Thread(target=_run_remote_purchase, daemon=True).start()

    def check_scheduled_tasks(self):
        # 만약 업데이트 검사가 완료되지 않았다면, 다른 자동 스케줄 및 로그인 작업을 대기합니다.
        if not getattr(self, 'update_check_completed', False):
            self.root.after(1000, self.check_scheduled_tasks)
            return
            
        # 1시간 주기 자동 업데이트 검사
        now = datetime.now()
        if self.settings.get('auto_update_check', True) and (now - self.last_auto_update_check_time).total_seconds() >= 3600:
            # 현재 아무런 모듈도 실행 중이지 않을 때만 자동 업데이트 스캔 진행 (충돌 방지)
            if self.task_manager.state.current_module is None:
                self.last_auto_update_check_time = now
                self.log_message("[시스템] 1시간 주기 자동 업데이트 검사를 백그라운드에서 시작합니다.")
                threading.Thread(target=self.check_for_updates, kwargs={'is_auto': True}, daemon=True).start()
            
        self.task_manager.check_scheduled_tasks(self.settings, self.get_callbacks())
        # 반복 실행 (1초 간격으로 검사하여 딜레이 최소화)
        self.root.after(1000, self.check_scheduled_tasks)


def main():
    root = tk.Tk()
    
    # 창 제목에 버전 및 계정 이름 표시
    account_name = os.environ.get('ACCOUNT_NAME', '')
    title_suffix = f" [{account_name}]" if account_name else ""
    root.title(f"닥터빌 자동화 프로그램 {VERSION}{title_suffix}")
    
    app = DoctorBillApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()
