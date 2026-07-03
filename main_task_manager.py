# -*- coding: utf-8 -*-
"""
닥터빌 자동화 프로그램 - Task Manager
기능 실행 로직을 담당합니다.
"""

import threading
import logging
import time
import os
from datetime import datetime
from web_automation import WebAutomation
from modules.base_module import (
    BaseModule,
    STATUS_ATTENDANCE_COMPLETE, 
    STATUS_ATTENDANCE_INCOMPLETE,
    STATUS_QUIZ_COMPLETE, 
    STATUS_QUIZ_INCOMPLETE,
    STATUS_KEY_ATTENDANCE, 
    STATUS_KEY_QUIZ
)
from modules.messages import (
    MSG_SEMINAR_REFRESH, MSG_SEMINAR_AUTO_APPLY_START, MSG_SEMINAR_APPLY_SUCCESS, 
    MSG_SEMINAR_APPLY_NONE, MSG_SEMINAR_AUTO_ENTER, MSG_POINTS_SUMMARY
)
from modules.notification_manager import NotificationManager

class TaskManagerState:
    """TaskManager 상태를 체계적으로 관리하는 클래스"""
    
    def __init__(self):
        self._web_automation = None
        self._is_logging_in = False
        self._current_module = None
        self._module_queue = []
        self._last_activity = None
        self._logger = logging.getLogger(__name__)
        
        # 스케줄러 상태
        self._last_auto_attendance_date = None
        self._last_auto_quiz_date = None
        self._last_seminar_refresh_time = None
        self._is_seminar_refresh_paused = False
        self._previous_seminar_titles = set()
        self._previous_seminar_urls = {} # 세미나 제목 대 상세 URL 매핑
        self._entered_seminar_links = set() # 자동 입장 완료된 링크 저장
        self._entered_seminar_windows = [] # 자동 입장 완료된 창 정보 (handle, enter_time, title, link)
        self._survey_retry_queue = [] # 설문 1분 주기 재시도 대기열
        self._recently_ended_seminars = set() # 최근에 종료 감지된 세미나 제목 목록
        self._permanently_closed_seminar_urls = set() # 이미 여러 번 시도했으나 설문 버튼이 없는 확정 종료 URL (이후 전체 스캔 시 건너맜)
        self._last_vod_scan_time = None # 마지막 VOD 자동 스캔 시간 기록 변수
        self._startup_time = datetime.now()
        self._is_sleeping = False
        self._prev_active_time_config = None
    
    @property
    def is_seminar_refresh_paused(self):
        return self._is_seminar_refresh_paused
        
    @is_seminar_refresh_paused.setter
    def is_seminar_refresh_paused(self, value):
        self._is_seminar_refresh_paused = value

    @property
    def last_seminar_refresh_time(self):
        return self._last_seminar_refresh_time
        
    @last_seminar_refresh_time.setter
    def last_seminar_refresh_time(self, value):
        self._last_seminar_refresh_time = value

    @property
    def last_auto_attendance_date(self):
        return self._last_auto_attendance_date
    
    @last_auto_attendance_date.setter
    def last_auto_attendance_date(self, value):
        self._last_auto_attendance_date = value

    @property
    def last_auto_quiz_date(self):
        return self._last_auto_quiz_date
    
    @last_auto_quiz_date.setter
    def last_auto_quiz_date(self, value):
        self._last_auto_quiz_date = value

    @property
    def startup_time(self):
        return self._startup_time
    
    @property
    def web_automation(self):
        """웹 자동화 상태 반환"""
        return self._web_automation
    
    @web_automation.setter
    def web_automation(self, value):
        """웹 자동화 상태 설정"""
        old_value = self._web_automation
        self._web_automation = value
        self._last_activity = datetime.now()
        
        if old_value != value:
            if value:
                self._logger.info("웹 자동화 초기화됨")
            else:
                self._logger.info("웹 자동화 정리됨")
    
    @property
    def is_logging_in(self):
        """로그인 상태 반환"""
        return self._is_logging_in
    
    @is_logging_in.setter
    def is_logging_in(self, value):
        """로그인 상태 설정 - 관련 상태도 함께 관리"""
        old_value = self._is_logging_in
        self._is_logging_in = value
        
        # 로그인 상태 변경 시 관련 상태도 함께 관리
        if old_value != value:
            if value:  # 로그인 시작
                self._current_module = 'login'
                self._last_activity = datetime.now()
                self._logger.debug("로그인 상태: 시작됨")
            else:  # 로그인 종료
                self._current_module = None
                self._last_activity = datetime.now()
                self._logger.debug("로그인 상태: 종료됨")
    
    @property
    def current_module(self):
        """현재 실행 중인 모듈 반환"""
        return self._current_module
    
    @current_module.setter
    def current_module(self, value):
        """현재 실행 중인 모듈 설정"""
        old_value = self._current_module
        self._current_module = value
        self._last_activity = datetime.now()
        
        if old_value != value:
            if value:
                self._logger.debug(f"현재 모듈: {value} 시작")
            else:
                self._logger.debug("모듈 실행 완료")
    
    def add_module_to_queue(self, module_name):
        """모듈을 큐에 추가"""
        if module_name not in self._module_queue:
            self._module_queue.append(module_name)
            self._logger.debug(f"모듈 큐에 추가: {module_name}")
    
    def remove_module_from_queue(self, module_name):
        """모듈을 큐에서 제거"""
        if module_name in self._module_queue:
            self._module_queue.remove(module_name)
            self._logger.debug(f"모듈 큐에서 제거: {module_name}")
    
    def get_status_summary(self):
        """현재 상태 요약 반환"""
        return {
            'web_automation_active': self._web_automation is not None,
            'is_logging_in': self._is_logging_in,
            'current_module': self._current_module,
            'queued_modules': self._module_queue.copy(),
            'last_activity': self._last_activity.isoformat() if self._last_activity else None
        }
    
    def cleanup(self):
        """상태 정리"""
        self._web_automation = None
        self._is_logging_in = False
        self._current_module = None
        self._module_queue.clear()
        self._last_activity = None
        self._logger.info("상태 정리 완료")

class ModuleFactory:
    """모듈을 만드는 공장 - 모듈 생성 로직 통합"""
    
    # 모듈 정보를 딕셔너리로 관리
    MODULE_INFO = {
        'login': ('modules.login_module', 'LoginModule'),
        'attendance': ('modules.attendance_module', 'AttendanceModule'),
        'quiz': ('modules.quiz_module', 'QuizModule'),
        'survey': ('modules.survey_module', 'SurveyModule'),
        'seminar': ('modules.seminar_module', 'SeminarModule'),
        'baemin': ('modules.baemin_module', 'BaeminModule'),
        'points': ('modules.points_check_module', 'PointsCheckModule')
    }
    
    # 간단한 모듈 설정 - 로그인 체크 필요 여부만 관리
    MODULES_REQUIRE_LOGIN = {
        'attendance', 'quiz', 'survey', 'seminar'
    }
    
    @classmethod
    def create_module_class(cls, module_type):
        """모듈 타입에 따라 모듈 클래스 반환"""
        if module_type in cls.MODULE_INFO:
            module_path, module_name = cls.MODULE_INFO[module_type]
            try:
                # 동적으로 모듈 import
                module_class = getattr(__import__(module_path, fromlist=[module_name]), module_name)
                return module_class
            except (ImportError, AttributeError) as e:
                raise ValueError(f"모듈 '{module_type}' 로드 실패: {str(e)}")
        else:
            raise ValueError(f"알 수 없는 모듈 타입: {module_type}")

class TaskManager:
    def __init__(self):
        self.state = TaskManagerState()  # 상태 관리 클래스 사용
        self.logger = logging.getLogger(__name__)
        self._module_cache = {}  # 모듈 클래스 캐시
        self.browser_lock = threading.RLock()  # 브라우저 전역 잠금 (재진입 가능)
        self.notifier = NotificationManager() # 카카오 알림 매니저 초기화
    
    def initialize_web_automation(self, gui_callbacks=None):
        """웹드라이버가 없으면 초기화"""
        if not self.state.web_automation:
            # 설정에서 브라우저 헤드리스 모드 여부 확인
            headless = None
            if gui_callbacks and 'gui_instance' in gui_callbacks and gui_callbacks['gui_instance']:
                try:
                    headless = gui_callbacks['gui_instance'].get_setting('browser_headless')
                except:
                    pass
            
            self.state.web_automation = WebAutomation(headless=headless)
        return self.state.web_automation
    
    def ensure_web_automation_alive(self, gui_callbacks):
        """브라우저가 열려있는지 확인하고 닫혔으면 재로그인 수행"""
        web_auto = self.state.web_automation or self.initialize_web_automation(gui_callbacks)
        
        if not web_auto.is_alive():
            self.logger.info("브라우저가 닫혀있음을 감지했습니다. 자동 복구(재로그인)를 시도합니다.")
            if gui_callbacks and 'log_message' in gui_callbacks:
                gui_callbacks['log_message']("⚠ 브라우저가 닫혀있습니다. 자동 복구(재로그인)를 시도합니다...")
            
            # 현재 어떤 모듈이 실행 중인지 잠시 기억했다가 복구 후 진행
            original_module = self.state.current_module
            
            # 로그인 모듈 실행 (동기 방식)
            try:
                login_class = self.get_module_class('login')
                login_module = login_class(web_auto, self.create_gui_logger(gui_callbacks))
                login_module.set_callbacks(gui_callbacks)
                login_result = login_module.execute()
                
                # 상태 원복
                self.state.current_module = original_module
                
                is_success = login_result.get('success', False) if isinstance(login_result, dict) else bool(login_result)
                if not is_success:
                    self.logger.error("브라우저 자동 복구 실패")
                    return None
            except Exception as e:
                self.logger.error(f"브라우저 자동 복구 중 오류: {str(e)}")
                self.state.current_module = original_module
                return None
                
        return web_auto
    
    def create_gui_logger(self, gui_callbacks):
        """통일된 GUI 로거 생성 - 단순화"""
        def gui_log(message):
            # 모듈의 로그를 GUI에 표시
            if 'log_message' in gui_callbacks:
                gui_callbacks['log_message'](message)
        
        return gui_log

    def check_login_status(self, gui_callbacks):
        """로그인 상태 체크 공통 로직"""
        if self.state.is_logging_in:
            gui_callbacks['log_message']("로그인 중입니다. 잠시 기다려주세요...")
            self.logger.info("로그인 상태 체크: 이미 로그인 중")
            return False
        return True
    
    def execute_module_in_thread(self, module_class, module_name, gui_callbacks, *args, **kwargs):
        """모듈을 스레드에서 실행하는 공통 메서드"""
        def module_task():
            self.execute_module_safely(module_class, module_name, gui_callbacks, *args, **kwargs)
        
        threading.Thread(target=module_task, daemon=True).start()
        return True
    
    def execute_module_by_config(self, module_type, gui_callbacks, *args, **kwargs):
        """설정 기반으로 모듈 실행 - 단순화"""
        # 유효한 모듈 타입인지 확인
        if module_type not in ModuleFactory.MODULE_INFO:
            self.logger.error(f"알 수 없는 모듈 타입: {module_type}")
            return False
        
        # 현재 실행 중인 다른 작업이 있다면 중복 실행 방지 (브라우저 락 대기열 누적 차단)
        # 로그인(login)은 execute_login()에서 별도로 is_logging_in 가드가 있으므로 제외
        if self.state.current_module is not None and module_type != 'login':
            self.logger.info(f"작업 요청 거부: 현재 다른 모듈({self.state.current_module})이 실행 중입니다. (요청 모듈: {module_type})")
            return False
        
        # 로그인이 필요한 모듈인지 확인
        if module_type in ModuleFactory.MODULES_REQUIRE_LOGIN and not self.check_login_status(gui_callbacks):
            return False
        
        # 모듈 클래스 가져오기
        try:
            module_class = self.get_module_class(module_type)
        except ValueError as e:
            self.logger.error(f"모듈 클래스 생성 실패: {str(e)}")
            return False
        
        # 간단한 디스플레이 이름 매핑
        display_names = {
            'login': '로그인',
            'attendance': '출석 체크', 
            'quiz': '퀴즈 풀이',
            'survey': '세미나 풀이',
            'seminar': '세미나 목록',
            'points': '포인트'
        }
        
        # 모듈 실행 (모든 모듈에 동일한 설정 적용)
        return self.execute_module_in_thread(
            module_class, 
            display_names.get(module_type, module_type), 
            gui_callbacks,
            *args, **kwargs
        )
    
    def execute_module_safely(self, module_class, module_name, gui_callbacks, *args, **kwargs):
        """모듈 실행 공통 로직 - 전역 브라우저 잠금 적용"""
        try:
            # 브라우저 확보 및 생존 확인
            with self.browser_lock:
                if module_name == "로그인":
                    web_auto = self.state.web_automation or self.initialize_web_automation(gui_callbacks)
                else:
                    web_auto = self.ensure_web_automation_alive(gui_callbacks)
                    
                if not web_auto:
                    self.log_error(module_name, "브라우저를 초기화할 수 없습니다.", gui_callbacks)
                    return
 
                gui_logger = self.create_gui_logger(gui_callbacks)
                
                # 모듈에서 직접 개별 결과를 알림으로 보낼 수 있도록 콜백 추가
                mod_callbacks = gui_callbacks.copy()
                mod_callbacks['notify_kakao'] = lambda msg, cat="notify_survey": self.notifier.send_kakao_message(msg, category=cat)
                mod_callbacks['notify_success'] = lambda msg: self.notifier.send_kakao_message(msg, category="notify_survey")
                
                # 현재 모듈 상태 업데이트 (시스템 로그에만 기록)
                self.state.current_module = module_name
                self.logger.info(f"--- [ {module_name} ] 모듈 실행 시작 ---")
                
                # 모듈 생성
                module = module_class(web_auto, gui_logger)
                
                # BaseModule을 상속받은 모듈은 자동으로 set_callbacks 사용 가능
                if isinstance(module, BaseModule):
                    module.set_callbacks(mod_callbacks)
                    # 새로운 콜백 방식을 위한 속성 설정
                    module.gui_callbacks = mod_callbacks
                    
                    # gui_instance가 있으면 모듈에 설정 (로그인과 대시보드 모듈)
                    if module_name in ["로그인", "대시보드"] and 'gui_instance' in gui_callbacks and gui_callbacks['gui_instance']:
                        module.gui_instance = gui_callbacks['gui_instance']
                        
                elif hasattr(module, 'set_callbacks'):
                    # 기존 방식 지원 (하위 호환성)
                    module.set_callbacks(gui_callbacks)
                    
                    # gui_instance가 있으면 모듈에 설정
                    if 'gui_instance' in gui_callbacks and gui_callbacks['gui_instance']:
                        module.gui_instance = gui_callbacks['gui_instance']
                
                # 모듈 실행
                result = module.execute(*args, **kwargs)
                
                # 결과 해석 (딕셔너리 또는 불리언 대응)
                is_success = False
                message = ""
                if isinstance(result, dict):
                    is_success = result.get('success', False)
                    message = result.get('message', '')
                    if message:
                        self.logger.info(f"[{module_name}] {message}")
                else:
                    is_success = bool(result)
                
                if is_success:
                    # '세미나 풀이'는 개별 항목별로 이미 알림을 보냈으므로 최종 요약 알림은 건너뜀
                    skip = (module_name == "세미나 풀이")
                    self.log_success(module_name, gui_callbacks, message, skip_notify=skip)
                    self.handle_special_actions(module_name, 'success')
                else:
                    self.log_failure(module_name, gui_callbacks, message)
                    self.handle_special_actions(module_name, 'failure')

                # [추가] 세미나 풀이 모듈인 경우 미오픈 설문에 대한 1분 재시도 대기열 업데이트
                if module_name == "세미나 풀이" and isinstance(result, dict) and result.get('success'):
                    data = result.get('data', {})
                    targets = data.get('targets', [])
                    for t in targets:
                        title = t.get('title')
                        url = t.get('url')
                        
                        if t.get('success'):
                            # 성공했으므로 재시도 대기열 및 최근 종료 목록에서 제거
                            if hasattr(self.state, '_survey_retry_queue') and self.state._survey_retry_queue:
                                before_len = len(self.state._survey_retry_queue)
                                self.state._survey_retry_queue = [
                                    item for item in self.state._survey_retry_queue
                                    if item.get('url') != url and item.get('title') != title
                                ]
                                if len(self.state._survey_retry_queue) < before_len:
                                    gui_callbacks['log_message'](f"✅ 설문 완료로 재시도 대기열에서 제거되었습니다: {title}")
                            # 지연 대기열(파일)에서도 제거
                            try:
                                surveys = self._load_pending_surveys()
                                if surveys:
                                    new_surveys = [s for s in surveys if s.get('url') != url and s.get('title') != title]
                                    if len(new_surveys) < len(surveys):
                                        self._save_pending_surveys(new_surveys)
                                        gui_callbacks['log_message'](f"✅ 설문 완료로 지연 대기열에서 제거되었습니다: {title}")
                            except Exception as pe_err:
                                self.logger.error(f"지연 대기열 제거 중 오류: {pe_err}")
                            # _recently_ended_seminars, _permanently_closed_seminar_urls 에서도 제거
                            if hasattr(self.state, '_recently_ended_seminars'):
                                self.state._recently_ended_seminars.discard(title)
                            if hasattr(self.state, '_permanently_closed_seminar_urls') and url:
                                self.state._permanently_closed_seminar_urls.discard(url)
                        else:
                            # 실패/스킵인 경우 중 재입장 버튼이 없는 경우(미오픈)에만 처리
                            if t.get('reason') == 'no_reenter_button':
                                is_recently_ended = hasattr(self.state, '_recently_ended_seminars') and title in self.state._recently_ended_seminars
                                is_target = (kwargs.get('target_title') == title or kwargs.get('target_url') == url)
                                
                                if is_recently_ended or is_target:
                                    # 최근 종료 세미나 or 명시 대상 → 재시도 대기열에 추가
                                    if hasattr(self.state, '_survey_retry_queue'):
                                        existing = any(item.get('url') == url for item in self.state._survey_retry_queue)
                                        if not existing:
                                            self.state._survey_retry_queue.append({
                                                'title': title,
                                                'url': url,
                                                'retry_count': 0,
                                                'last_try_time': datetime.now()
                                            })
                                            gui_callbacks['log_message'](f"🔄 설문 미오픈 감지: 1분 뒤 재시도를 위해 대기열에 추가합니다. ({title})")
                                else:
                                    # 최근 종료도 아니고 명시 대상도 아님 → 이미 완료됐거나 영구 종료된 세미나
                                    # 이후 전체 스캔(버튼 클릭) 시 건너뛰도록 등록
                                    if hasattr(self.state, '_permanently_closed_seminar_urls') and url:
                                        self.state._permanently_closed_seminar_urls.add(url)
                                        self.logger.info(f"확정 종료 세미나로 등록 (이후 전체 스캔 제외): {title}")


                # [중요] 특정 모듈(로그인, 출석 체크, 퀴즈 풀이, 세미나 풀이) 완료 후에는 자동으로 포인트 체크 수행
                # 단, '세미나 풀이'의 경우 실제로 1건 이상의 설문을 성공적으로 처리했을 때만 후속 포인트 체크를 실행합니다. (5분 주기 자동 스캔 시 알림 도배 방지)
                should_check_points = False
                if module_name in ["로그인", "출석 체크", "퀴즈 풀이"]:
                    should_check_points = True
                elif module_name == "세미나 풀이":
                    success_count = 0
                    if isinstance(result, dict):
                        success_count = result.get('data', {}).get('success_count', 0)
                    
                    if success_count > 0:
                        should_check_points = True
                    else:
                        self.logger.info("세미나 풀이 성공 건수가 0건이므로 후속 포인트 체크를 생략합니다.")
                
                if should_check_points:
                    try:
                        self.logger.info(f"{module_name} 완료 후 포인트 상태 확인 시작...")
                        points_class = self.get_module_class('points')
                        points_mod = points_class(web_auto, gui_logger)
                        points_mod.gui_callbacks = mod_callbacks
                        points_mod.execute()
                    except Exception as pe:
                        self.logger.error(f"후속 포인트 체크 중 오류: {str(pe)}")
                        
                # [추가] '세미나 풀이' 모듈이 최종 완료된 후에는 UI 세미나 목록과 상태 동기화를 위해 즉시 세미나 목록 새로고침 수행
                if module_name == "세미나 풀이":
                    try:
                        self.logger.info("세미나 풀이 완료 후 세미나 목록 새로고침 트리거...")
                        self._handle_seminar_refresh(gui_callbacks)
                    except Exception as re:
                        self.logger.error(f"세미나 풀이 완료 후 새로고침 중 오류: {str(re)}")
                
                return is_success
                
        except Exception as e:
            self.log_error(module_name, str(e), gui_callbacks)
            self.handle_special_actions(module_name, 'error')
            return False
        finally:
            # 모듈 실행 완료 후 상태 정리
            self.state.current_module = None
    
    def cleanup_web_automation(self):
        """웹드라이버 정리"""
        if self.state.web_automation:
            self.state.web_automation.close_driver()
            self.state.web_automation = None
    
    def execute_login(self, gui_callbacks):
        """로그인 실행"""
        if self.state.is_logging_in:
            gui_callbacks['log_message']("이미 로그인 중입니다. 잠시 기다려주세요...")
            self.logger.info("로그인 실행 시도: 이미 로그인 중")
            return False
        
        self.state.is_logging_in = True
        self.logger.debug("로그인 실행 시작")
        
        # 모듈을 큐에 추가
        self.state.add_module_to_queue('login')
        
        # 설정 기반으로 모듈 실행 (하드코딩 제거)
        result = self.execute_module_by_config('login', gui_callbacks)
        
        # 실행 완료 후 큐에서 제거
        if result:
            self.state.remove_module_from_queue('login')
        
        return result
    
    def execute_attendance(self, gui_callbacks):
        """출석 체크 실행"""
        # 설정 기반으로 모듈 실행 (하드코딩 제거)
        return self.execute_module_by_config('attendance', gui_callbacks)
    
    def execute_quiz(self, gui_callbacks):
        """퀴즈 풀기 실행"""
        # 설정 기반으로 모듈 실행 (하드코딩 제거)
        return self.execute_module_by_config('quiz', gui_callbacks)

    def execute_attendance_then_quiz(self, gui_callbacks):
        """출석체크 완료 후 퀴즈 풀기를 순차적으로 실행합니다.
        출석체크와 퀴즈 예약 시간이 같을 때 경쟁 조건을 방지하기 위해 사용합니다."""
        def _sequential_task():
            try:
                # 1단계: 출석 체크 동기 실행
                attendance_class = self.get_module_class('attendance')
                self.execute_module_safely(attendance_class, '출석 체크', gui_callbacks)
            except Exception as e:
                self.logger.error(f"순차 실행 중 출석체크 오류: {e}")
            finally:
                # 2단계: 퀴즈 풀기 동기 실행 (출석체크 성공 여부와 관계없이)
                try:
                    quiz_class = self.get_module_class('quiz')
                    self.execute_module_safely(quiz_class, '퀴즈 풀이', gui_callbacks)
                except Exception as e:
                    self.logger.error(f"순차 실행 중 퀴즈 오류: {e}")

        threading.Thread(target=_sequential_task, daemon=True).start()
        return True
    
    def execute_survey(self, gui_callbacks, target_url=None, target_title=None):
        """세미나 풀이 실행"""
        # 전체 스캔(target_url 없음) 시, 이미 확정 종료된 세미나 URL은 건너맜
        skip_urls = None
        if target_url is None and hasattr(self.state, '_permanently_closed_seminar_urls') and self.state._permanently_closed_seminar_urls:
            skip_urls = set(self.state._permanently_closed_seminar_urls)  # 복사본 전달
        return self.execute_module_by_config('survey', gui_callbacks, target_url=target_url, target_title=target_title, skip_urls=skip_urls)
    
    def execute_seminar(self, gui_callbacks):
        """라이브 세미나 정보를 확인하고 다이얼로그를 표시합니다."""
        def _run():
            try:
                self.state.current_module = 'seminar_view'
                web_auto = self.ensure_web_automation_alive(gui_callbacks)
                if not web_auto: return

                module_class = self.get_module_class('seminar')
                gui_logger = self.create_gui_logger(gui_callbacks)
                
                seminar = module_class(web_auto, gui_logger)
                seminar.set_callbacks(gui_callbacks)
                
                gui_callbacks['log_message']("🚀 세미나 목록 정보 수집을 시작합니다...")
                gui_callbacks['update_status']("세미나 정보 수집 중...")
                
                seminars_res = seminar.get_seminar_list()
                if isinstance(seminars_res, dict):
                    seminars = seminars_res.get('data', [])
                else:
                    seminars = seminars_res
                
                if not seminars:
                    gui_callbacks['log_message']("⚠ 세미나 정보를 찾을 수 없습니다.")
                    return

                # UI 스레드에서 다이얼로그 띄우기
                if 'show_seminar_dialog' in gui_callbacks:
                    dialog_callbacks = {
                        'on_apply': lambda checked: self._handle_seminar_batch_action(checked, 'apply', gui_callbacks),
                        'on_cancel': lambda checked: self._handle_seminar_batch_action(checked, 'cancel', gui_callbacks),
                        'on_refresh': lambda: self._handle_seminar_refresh(gui_callbacks),
                        'on_action': lambda link, status: self._handle_seminar_single_action(link, status, gui_callbacks),
                        'log_message': gui_callbacks['log_message']
                    }
                    gui_callbacks['show_seminar_dialog'](seminars, dialog_callbacks)
                
            except Exception as e:
                self.logger.error(f"세미나 확인 오류: {str(e)}")
                if 'log_error' in gui_callbacks:
                    gui_callbacks['log_error'](f"세미나 확인 중 오류: {str(e)}")
            finally:
                self.state.current_module = None
                gui_callbacks['update_status']("대기 중")

        threading.Thread(target=_run, daemon=True).start()
        return True

    def _handle_seminar_batch_action(self, checked_list, action_type, gui_callbacks):
        """세미나 일괄 처리 (신청/취소)"""
        if not checked_list:
            gui_callbacks['log_message']("⚠ 선택된 세미나가 없습니다.")
            return

        def _run():
            try:
                with self.browser_lock:
                    web_auto = self.ensure_web_automation_alive(gui_callbacks)
                    if not web_auto: return

                    module_class = self.get_module_class('seminar')
                    gui_logger = self.create_gui_logger(gui_callbacks)
                    seminar = module_class(web_auto, gui_logger)
                    seminar.set_callbacks(gui_callbacks)

                    success_count = 0
                    for i, item in enumerate(checked_list, 1):
                        title = item['title']
                        gui_callbacks['log_message'](f"[{i}/{len(checked_list)}] {title} {action_type} 중...")
                        
                        status_to_send = '신청완료' if action_type == 'cancel' else '신청가능'
                        result = seminar.handle_seminar_action(item['detail_link'], status_to_send)
                        success = result.get('success', False) if isinstance(result, dict) else bool(result)
                        
                        if success:
                            success_count += 1
                            gui_callbacks['log_message'](f"✅ {title} 완료")
                        else:
                            msg = result.get('message', '실패') if isinstance(result, dict) else '실패'
                            gui_callbacks['log_message'](f"❌ {title} {msg}")
                        time.sleep(0.5)

                    gui_callbacks['log_message'](f"🎉 일괄 처리 완료! 성공: {success_count}개")
                    self._handle_seminar_refresh(gui_callbacks)
            except Exception as e:
                gui_callbacks['log_error'](f"일괄 처리 중 오류: {str(e)}")

        threading.Thread(target=_run, daemon=True).start()

    def _handle_seminar_single_action(self, link, status, gui_callbacks, title=None):
        """개별 세미나 액션 처리 (더블클릭)"""
        def _run():
            try:
                with self.browser_lock:
                    web_auto = self.ensure_web_automation_alive(gui_callbacks)
                    if not web_auto: return

                    module_class = self.get_module_class('seminar')
                    gui_logger = self.create_gui_logger(gui_callbacks)
                    seminar = module_class(web_auto, gui_logger)
                    seminar.set_callbacks(gui_callbacks)

                    result = seminar.handle_seminar_action(link, status)
                success = result.get('success', False) if isinstance(result, dict) else bool(result)
                message = result.get('message', '') if isinstance(result, dict) else ''
                
                if success:
                    # '입장하기' 상태인 경우 세미나 입장 알림 전송
                    if status == '입장하기':
                        display_title = title if title else "세미나"
                        self.log_success("세미나 입장", gui_callbacks, f"세미나 입장 완료: {display_title}")
                    else:
                        gui_callbacks['log_message']("✅ 작업 완료")
                    self._handle_seminar_refresh(gui_callbacks)
                else:
                    msg = message if message else '작업 실패'
                    gui_callbacks['log_message'](f"❌ {msg}")
            except Exception as e:
                gui_callbacks['log_error'](f"세미나 작업 중 오류: {str(e)}")

        threading.Thread(target=_run, daemon=True).start()

    def _handle_seminar_refresh(self, gui_callbacks, settings=None):
        """세미나 목록 새로고침 및 종료 감지 기반 자동 설문 트리거"""
        def _run():
            try:
                self.state.current_module = 'seminar_refresh'
                
                # settings가 전달되지 않은 경우 (수동 새로고침 등), 로컬 settings.json을 로드하여 대처
                active_settings = settings
                if active_settings is None:
                    try:
                        import os
                        import json
                        base_dir = os.path.dirname(os.path.abspath(__file__))
                        settings_path = os.path.join(base_dir, "data", "settings.json")
                        if os.path.exists(settings_path):
                            with open(settings_path, 'r', encoding='utf-8') as f:
                                active_settings = json.load(f)
                    except Exception as e:
                        self.logger.warning(f"새로고침 중 설정 로드 실패: {e}")

                with self.browser_lock:
                    web_auto = self.ensure_web_automation_alive(gui_callbacks)
                    if not web_auto: return

                    module_class = self.get_module_class('seminar')
                    gui_logger = self.create_gui_logger(gui_callbacks)
                    seminar = module_class(web_auto, gui_logger)
                    seminar.set_callbacks(gui_callbacks)
    
                    gui_callbacks['log_message'](MSG_SEMINAR_REFRESH)
                    seminars_res = seminar.get_seminar_list()
                    
                    if seminars_res is None:
                        self.logger.warning("세미나 목록 수집 실패로 인해 종료 감지 로직을 건너뜁니다.")
                        gui_callbacks['log_message']("⚠️ 세미나 목록 수집 실패 (네트워크/타임아웃 오류). 종료 감지를 생략합니다.")
                        return
                    
                    # 결과 목록 추출
                    current_seminars = seminars_res.get('data', []) if isinstance(seminars_res, dict) else seminars_res
                    
                    from modules.utils import get_status_tag
                    current_titles = set()
                    for s in current_seminars:
                        title = s.get('title', '')
                        status = s.get('status', '')
                        if title:
                            tag = get_status_tag(status)
                            status_lower = status.lower()
                            # 설문참여, 종료, 결과확인, 상세보기 등 이미 방송이 종료된 상태는 제외 (이들을 종료로 감지하기 위함)
                            is_ended = (tag == '기타') or any(kw in status_lower for kw in ['설문', '종료', '결과', '상세'])
                            if not is_ended:
                                current_titles.add(title)
    
                    # [추가] 자동 설문 트리거 로직: 세미나 종료 감지
                    if active_settings and active_settings.get('auto_survey'):
                        # 이전 목록이 있고 (첫 실행 제외), 이전에 있던 제목이 현재 없으면 종료로 간주
                        if self.state._previous_seminar_titles:
                            ended_seminars = self.state._previous_seminar_titles - current_titles
                            if ended_seminars:
                                self.logger.info(f"세미나 종료 감지: {ended_seminars}")
                                msg = f"📢 세미나 종료 감지: {list(ended_seminars)[0]} 외 {len(ended_seminars)-1}건" if len(ended_seminars) > 1 else f"📢 세미나 종료 감지: {list(ended_seminars)[0]}"
                                gui_callbacks['log_message'](msg)
                                self.notifier.send_kakao_message(msg, category="notify_survey")
                                
                                # 최근 종료 세미나 목록 업데이트
                                if hasattr(self.state, '_recently_ended_seminars'):
                                    self.state._recently_ended_seminars.update(ended_seminars)
                                
                                # 지연 설정 활성화 시 대기열에 추가
                                if active_settings.get('auto_survey_delay'):
                                    for title in ended_seminars:
                                        url = self.state._previous_seminar_urls.get(title)
                                        self._add_pending_survey(title, url)
                                else:
                                    # [VOD 미업데이트 안전망] 종료 감지된 세미나를 1분 재시도 대기열에 직접 추가
                                    # VOD 페이지가 아직 업데이트 안 됐었어도 1분 후 재시도 함으로써 누락 방지
                                    for title in ended_seminars:
                                        raw_url = self.state._previous_seminar_urls.get(title)
                                        if raw_url:
                                            full_url = ("https://www.doctorville.co.kr" + raw_url) if raw_url.startswith('/') else raw_url
                                            if hasattr(self.state, '_survey_retry_queue'):
                                                existing = any(item.get('url') == full_url for item in self.state._survey_retry_queue)
                                                if not existing:
                                                    self.state._survey_retry_queue.append({
                                                        'title': title,
                                                        'url': full_url,
                                                        'retry_count': 0,
                                                        'last_try_time': datetime.now()  # 1분 후 첫 시도
                                                    })
                                                    gui_callbacks['log_message'](f"📌 1분 후 설문 참여를 시도합니다. ({title})")

                                    # 현재 여유가 있으면 즉시 시도도 병행 (점급 설문 참여)
                                    if self.state.current_module is None:
                                        gui_callbacks['log_message']("📝 자동 세미나 풀이를 시작합니다...")
                                        self.execute_survey(gui_callbacks)
                    
                    # [추가] 자동 세미나 입장 로직: 시작 시간 기반
                    if active_settings and active_settings.get('auto_seminar_enter'):
                        try:
                            delay_min = int(active_settings.get('seminar_enter_delay', 5))
                        except:
                            delay_min = 5
                            
                        now = datetime.now()
                        today_str = f"{now.month}/{now.day}"
                        
                        # 입장 대상 수집
                        targets = []
                        for s in current_seminars:
                            title = s.get('title', '')
                            link = s.get('detail_link', '')
                            time_str = s.get('time', '')
                            date_str = s.get('date', '')
                            
                            from modules.utils import get_status_tag
                            if date_str == today_str and get_status_tag(s.get('status', '')) == '입장하기' and link not in self.state._entered_seminar_links:
                                try:
                                    start_time_part = time_str.split('~')[0].strip()
                                    start_h, start_m = map(int, start_time_part.split(':'))
                                    start_dt = now.replace(hour=start_h, minute=start_m, second=0, microsecond=0)
                                    
                                    from datetime import timedelta
                                    enter_time = start_dt + timedelta(minutes=delay_min)
                                    
                                    # 1. 예약된 시간이 지났고
                                    # 2. 그 예약 시각이 '프로그램 시작 시각' 이후인 경우에만 실행 (재시작 시 중복 방지)
                                    if now >= enter_time and enter_time >= self.state.startup_time:
                                        targets.append((link, title))
                                        self.state._entered_seminar_links.add(link) # 중복 방지
                                except: continue
    
                        # 수집된 대상이 있으면 순차적으로 실행
                        if targets:
                            def _sequential_enter(entry_list):
                                for link, title in entry_list:
                                    gui_callbacks['log_message'](f"🚪 세미나 자동 입장을 시작합니다: {title}")
                                    self.auto_enter_seminar(link, title, gui_callbacks)
                                    time.sleep(5) # 브라우저 안정화를 위해 5초 대기 후 다음 입장 진행
                            
                            threading.Thread(target=_sequential_enter, args=(targets,), daemon=True).start()
    
                    # 이전 목록 갱신 (설정 여부와 상관없이 항상 최신 상태 유지)
                    self.state._previous_seminar_titles = current_titles
                    self.state._previous_seminar_urls = {s.get('title', ''): s.get('detail_link', '') for s in current_seminars if s.get('title')}
    
                    if 'update_seminar_dialog' in gui_callbacks:
                        gui_callbacks['update_seminar_dialog'](current_seminars)
                    
            except Exception as e:
                gui_callbacks['log_error'](f"새로고침 중 오류: {str(e)}")
            finally:
                self.state.current_module = None
                gui_callbacks['update_status']("대기 중")
                
                # 자동 설문 옵션이 켜져 있고 세미나 새로고침이 완료된 후, 5분(300초) 주기로 VOD 자동 스캔
                if active_settings and active_settings.get('auto_survey'):
                    now = datetime.now()
                    if (self.state._last_vod_scan_time is None or 
                        (now - self.state._last_vod_scan_time).total_seconds() >= 300):
                        self.state._last_vod_scan_time = now
                        gui_callbacks['log_message']("📝 [스케줄러] 5분 주기 VOD 목록 자동 스캔을 시작합니다...")
                        self.execute_survey(gui_callbacks)

        threading.Thread(target=_run, daemon=True).start()

    def _handle_auto_seminar_join(self, gui_callbacks):
        """자동 세미나 신청 처리"""
        def _run():
            try:
                self.state.current_module = 'seminar_auto_apply'
                with self.browser_lock:
                    web_auto = self.ensure_web_automation_alive(gui_callbacks)
                    if not web_auto: return

                    module_class = self.get_module_class('seminar')
                    gui_logger = self.create_gui_logger(gui_callbacks)
                    seminar = module_class(web_auto, gui_logger)
                    seminar.set_callbacks(gui_callbacks)
    
                    result = seminar.auto_apply_available_seminars()
                    stats = result.get('data', {}) if isinstance(result, dict) else {}
                    
                    total = stats.get('total', 0)
                    success = stats.get('success', 0)
                    closed = stats.get('closed', 0)
                    applied_already = stats.get('applied', 0)
                    applied_titles = stats.get('applied_titles', [])
                    
                    # 1. 신규 신청 성공 건이 있을 때만 상세 보고
                    if success > 0:
                        # 원래 있던 성공 로그 복구
                        msg_original = MSG_SEMINAR_APPLY_SUCCESS.format(count=success)
                        gui_callbacks['log_message'](msg_original)
                        
                        # 📊 요약 메시지 구성
                        final_applied = applied_already + success
                        summary_msg = f"📊 [세미나 요약] 전체: {total}건, 신청완료: {final_applied}건, 신청마감: {closed}건"
                        gui_callbacks['log_message'](summary_msg)
                        
                        # 카톡 알림 구성
                        titles_str = "\n".join([f"- {t}" for t in applied_titles])
                        kakao_msg = f"{summary_msg}\n\n✅ 이번 자동 신청 ({success}건):\n{titles_str}"
                        
                        try:
                            self.notifier.send_kakao_message(kakao_msg, category="notify_seminar_join")
                        except Exception as ne:
                            self.logger.error(f"세미나 신청 알림 전송 실패: {ne}")
                        
                        # 🔥 신규 신청이 있었으므로 즉시 UI 갱신
                        self._handle_seminar_refresh(gui_callbacks)
                    else:
                        # 새로운 신청이 없으면 조용히 종료 (로그 도배 방지)
                        # 단, UI 목록은 최신 정보를 유지하기 위해 필요시 갱신 (이미 룬 메드 루틴에서 처리됨)
                        pass
            except Exception as e:
                self.logger.error(f"자동 세미나 신청 오류: {str(e)}")
            finally:
                self.state.current_module = None
                gui_callbacks['update_status']("대기 중")

        threading.Thread(target=_run, daemon=True).start()
    
    def get_point_use_info(self, gui_callbacks, force_refresh=False):
        """포인트 사용(빌마켓 쿠폰 구매)을 위한 초기 정보(포인트, 번호, 상품 목록)를 가져옵니다."""
        try:
            self.state.current_module = 'baemin'
            with self.browser_lock:
                base_dir = os.path.dirname(os.path.abspath(__file__))
                cache_path = os.path.join(base_dir, "data", "coupon_cache.json")
                coupon_list = []
                
                if not force_refresh and os.path.exists(cache_path):
                    try:
                        import json
                        with open(cache_path, 'r', encoding='utf-8') as f:
                            coupon_list = json.load(f)
                        if coupon_list:
                            self.logger.info("상품 목록을 로컬 캐시에서 불러왔습니다.")
                    except Exception as ce:
                        self.logger.warning(f"로컬 캐시 로드 실패 (크롤링 진행): {ce}")

                web_auto = self.ensure_web_automation_alive(gui_callbacks)
                if not web_auto: return {'points': 0, 'phone': '', 'coupon_list': []}

                module_class = self.get_module_class('baemin')
                gui_logger = self.create_gui_logger(gui_callbacks)
                
                baemin = module_class(web_auto, gui_logger)
                baemin.set_callbacks(gui_callbacks)
                
                points_res = baemin.get_current_points()
                if isinstance(points_res, dict):
                    points = points_res.get('data', 0)
                else:
                    points = points_res
                    
                phone_res = baemin.get_phone_number()
                if isinstance(phone_res, dict):
                    phone = phone_res.get('data', '')
                else:
                    phone = phone_res or ''
                    
                if not coupon_list:
                    coupon_list = baemin.scrape_coupon_list()
                    if coupon_list:
                        try:
                            import json
                            data_dir = os.path.dirname(cache_path)
                            if not os.path.exists(data_dir):
                                os.makedirs(data_dir)
                            with open(cache_path, 'w', encoding='utf-8') as f:
                                json.dump(coupon_list, f, ensure_ascii=False, indent=2)
                            self.logger.info("새로 수집한 상품 목록을 로컬 캐시에 저장했습니다.")
                        except Exception as se:
                            self.logger.warning(f"로컬 캐시 저장 실패: {se}")
                
                return {
                    'points': points,
                    'phone': phone,
                    'coupon_list': coupon_list
                }
        except Exception as e:
            self.logger.error(f"포인트 사용 정보 조회 오류: {str(e)}")
            raise
        finally:
            self.state.current_module = None

    def execute_point_use_purchase(self, quantity, phone, coupon_item, sender_name, gui_callbacks):
        """선택된 상품 쿠폰 구매를 실행합니다."""
        def _run():
            try:
                self.state.current_module = 'baemin'
                product_name = coupon_item.get('name', '쿠폰')
                with self.browser_lock:
                    web_auto = self.ensure_web_automation_alive(gui_callbacks)
                    if not web_auto: return

                    module_class = self.get_module_class('baemin')
                    gui_logger = self.create_gui_logger(gui_callbacks)
                    
                    baemin = module_class(web_auto, gui_logger)
                    baemin.set_callbacks(gui_callbacks)
                    
                    result = baemin.execute(quantity=quantity, phone_number=phone, coupon_item=coupon_item, sender_name=sender_name)
                    
                    is_success = False
                    message = ""
                    if isinstance(result, dict):
                        is_success = result.get('success', False)
                        message = result.get('message', '')
                    else:
                        is_success = bool(result)
                        
                    if is_success:
                        self.log_success(f"{product_name} 구매", gui_callbacks, message)
                    else:
                        self.log_failure(f"{product_name} 구매", gui_callbacks, message)
            except Exception as e:
                self.log_error(f"{coupon_item.get('name', '쿠폰')} 구매", str(e), gui_callbacks)
            finally:
                # 락 해제(current_module = None)는 사용자가 대화상자를 닫을 때 reset_module_state 콜백을 통해 수행하므로 여기서는 유지합니다.
                pass
        
        threading.Thread(target=_run, daemon=True).start()

    def get_seminar_list(self, gui_callbacks):
        """최신 세미나 목록을 수집하여 반환합니다."""
        try:
            self.state.current_module = 'seminar_collect'
            with self.browser_lock:
                web_auto = self.ensure_web_automation_alive(gui_callbacks)
                if not web_auto: return []

                module_class = self.get_module_class('seminar')
                gui_logger = self.create_gui_logger(gui_callbacks)
                
                seminar = module_class(web_auto, gui_logger)
                seminar.set_callbacks(gui_callbacks)
                
                result = seminar.collect_seminar_info_only()
                if isinstance(result, dict):
                    return result.get('data', [])
                return result
        except Exception as e:
            self.logger.error(f"세미나 목록 수집 오류: {str(e)}")
            return []
        finally:
            self.state.current_module = None

    def auto_apply_and_refresh_seminars(self, gui_callbacks):
        """세미나 자동 신청 및 목록 새로고침을 수행합니다."""
        try:
            # 이 작업은 백그라운드 스레드에서 실행되므로 직접 클래스 생성
            with self.browser_lock:
                web_auto = self.ensure_web_automation_alive(gui_callbacks)
                if not web_auto: return 0, []

                module_class = self.get_module_class('seminar')
                gui_logger = self.create_gui_logger(gui_callbacks)
                
                seminar = module_class(web_auto, gui_logger)
                seminar.set_callbacks(gui_callbacks)
                
                result = seminar.auto_apply_available_seminars()
                # auto_apply_available_seminars가 튜플 (count, list)을 반환하는지, dict를 반환하는지 처리
                if isinstance(result, dict):
                    data = result.get('data', {})
                    return data.get('count', 0), data.get('seminars', [])
                return result
        except Exception as e:
            self.logger.error(f"세미나 자동 신청/새로고침 오류: {str(e)}")
            return 0, []

    def auto_enter_seminar(self, link, title, gui_callbacks):
        """특정 세미나에 자동으로 입장합니다."""
        try:
            self.state.current_module = 'auto_enter'
            with self.browser_lock:
                web_auto = self.ensure_web_automation_alive(gui_callbacks)
                if not web_auto: return False

                module_class = self.get_module_class('seminar')
                gui_logger = self.create_gui_logger(gui_callbacks)
                
                # 상대 경로 처리
                full_link = link
                if link.startswith('/'):
                    full_link = "https://www.doctorville.co.kr" + link
                
                web_auto.driver.get(full_link)
                time.sleep(2)
                
                seminar = module_class(web_auto, gui_logger)
                seminar.set_callbacks(gui_callbacks)
                
                # 기존 window handles 수집
                prev_handles = web_auto.driver.window_handles
                
                result = seminar.enter_seminar()
                success = result.get('success', False) if isinstance(result, dict) else bool(result)
                message = result.get('message', '') if isinstance(result, dict) else ''
                
                if success:
                    self.log_success("세미나 입장", gui_callbacks, f"자동 세미나 입장 성공: {title}")
                    
                    # 새 창의 핸들 감지
                    time.sleep(2)
                    try:
                        current_handles = web_auto.driver.window_handles
                        new_handles = set(current_handles) - set(prev_handles)
                        if new_handles:
                            new_handle = list(new_handles)[0]
                            self.state._entered_seminar_windows.append({
                                'handle': new_handle,
                                'enter_time': datetime.now(),
                                'title': title,
                                'link': link
                            })
                            self.logger.info(f"세미나 창 [{title}] 핸들 저장 완료: {new_handle}")
                    except Exception as he:
                        self.logger.warning(f"새 세미나 창 핸들 감지 중 오류: {he}")
                    return True
                else:
                    self.log_failure("세미나 입장", gui_callbacks, f"자동 세미나 입장 실패: {title} ({message})")
                    return False
        except Exception as e:
            self.logger.error(f"세미나 자동 입장 오류: {str(e)}")
            return False
        finally:
            self.state.current_module = None
    
    def check_scheduled_tasks(self, settings, gui_callbacks):
        """설정된 시간에 맞춰 자동 작업을 실행합니다."""
        try:
            # 0. 특정 시간대 일시정지(대기) 모드 체크
            use_range = settings.get('use_active_time_range', False)
            try:
                start_h = int(settings.get('active_start_h', 9))
                start_m = int(settings.get('active_start_m', 0))
                end_h = int(settings.get('active_end_h', 21))
                end_m = int(settings.get('active_end_m', 0))
            except:
                start_h, start_m, end_h, end_m = 9, 0, 21, 0
                
            current_config = (use_range, start_h, start_m, end_h, end_m)
            
            # 설정 변경 여부를 감지하여 대기 모드 판정 플래그 초기화
            if getattr(self.state, '_prev_active_time_config', None) != current_config:
                self.state._prev_active_time_config = current_config
                self.state._is_sleeping = None  # None으로 변경해 즉시 재평가 유도
                
            if use_range:
                now_time = datetime.now().time()
                from datetime import time
                start_time = time(start_h, start_m)
                end_time = time(end_h, end_m)
                
                is_active = False
                if start_time <= end_time:
                    is_active = start_time <= now_time <= end_time
                else:
                    # 자정을 걸치는 경우 (예: 22:00 ~ 다음날 06:00)
                    is_active = now_time >= start_time or now_time <= end_time
                
                # 12시간제 출력 문자열 생성
                def format_12h(h, m):
                    ampm = "오후" if h >= 12 else "오전"
                    h12 = h % 12
                    h12 = 12 if h12 == 0 else h12
                    return f"{ampm} {h12}시 {m:02d}분"
                
                start_str = format_12h(start_h, start_m)
                end_str = format_12h(end_h, end_m)
                
                if not is_active:
                    # _is_sleeping이 True가 아니거나 브라우저 리소스가 켜져 있으면 비활성 모드 수행
                    if self.state._is_sleeping is not True or self.state.web_automation is not None:
                        self.state._is_sleeping = True
                        gui_callbacks['log_message'](f"💤 작동 시간(설정: {start_str} ~ {end_str}) 외 시각이므로 작업을 일시정지하고 대기 모드로 전환합니다.")
                        if self.state.web_automation:
                            self.logger.info("비활성 시간대 진입으로 웹브라우저를 안전하게 정리합니다.")
                            self.cleanup_web_automation()
                    return False
                else:
                    # _is_sleeping이 False가 아니거나 브라우저가 꺼져 있다면 활성 모드 복구 수행
                    if self.state._is_sleeping is not False or self.state.web_automation is None:
                        self.state._is_sleeping = False
                        gui_callbacks['log_message'](f"⏰ 작동 시간(설정: {start_str} ~ {end_str})이 되어 대기 모드를 해제하고 작업을 재개합니다.")
                        # 대기 모드가 해제되는 시점에 백그라운드 자동 로그인을 수행하여 브라우저 복구
                        self.execute_login(gui_callbacks)
            else:
                # 시간대 가드 비활성화 상태인 경우
                if self.state._is_sleeping is True or (self.state._is_sleeping is None and self.state.web_automation is None):
                    self.state._is_sleeping = False
                    gui_callbacks['log_message']("⏰ 시간 제한 설정이 비활성화되어 작업을 재개합니다.")
                    self.execute_login(gui_callbacks)

            # 브라우저가 준비되지 않았거나 다른 작업이 실행 중이면 건너뛰기
            if self.state.web_automation is None or self.state.current_module is not None:
                return False

            now = datetime.now()
            today = now.date()
            
            # 1. 자동 출석 체크 체크
            attendance_due = False
            quiz_due = False

            if settings.get('auto_attendance') and self.state.last_auto_attendance_date != today:
                att_hour = settings.get('auto_attendance_hour')
                att_min = settings.get('auto_attendance_min')
                att_scheduled = now.replace(hour=att_hour, minute=att_min, second=0, microsecond=0)
                if now >= att_scheduled and att_scheduled >= self.state.startup_time:
                    attendance_due = True

            # 2. 자동 퀴즈 풀이 체크
            if settings.get('auto_quiz') and self.state.last_auto_quiz_date != today:
                quiz_hour = settings.get('auto_quiz_hour')
                quiz_min = settings.get('auto_quiz_min')
                quiz_scheduled = now.replace(hour=quiz_hour, minute=quiz_min, second=0, microsecond=0)
                if now >= quiz_scheduled and quiz_scheduled >= self.state.startup_time:
                    quiz_due = True

            # 출석체크와 퀴즈가 동시에 예약된 경우 → 순차 실행 (경쟁 조건 방지)
            if attendance_due and quiz_due:
                gui_callbacks['log_message'](f"⏰ 예약된 자동 출석 체크를 시작합니다. (설정시간: {att_hour:02d}:{att_min:02d})")
                gui_callbacks['log_message'](f"⏰ 예약된 자동 퀴즈 풀이를 시작합니다. (설정시간: {quiz_hour:02d}:{quiz_min:02d})")
                gui_callbacks['update_status']("자동 출석 체크 → 퀴즈 풀이 순차 실행 중...")
                self.execute_attendance_then_quiz(gui_callbacks)
                self.state.last_auto_attendance_date = today
                self.state.last_auto_quiz_date = today
                return True

            # 출석체크만 예약된 경우
            if attendance_due:
                gui_callbacks['log_message'](f"⏰ 예약된 자동 출석 체크를 시작합니다. (설정시간: {att_hour:02d}:{att_min:02d})")
                gui_callbacks['update_status']("자동 출석 체크 중...")
                self.execute_attendance(gui_callbacks)
                self.state.last_auto_attendance_date = today
                return True

            # 퀴즈만 예약된 경우
            if quiz_due:
                gui_callbacks['log_message'](f"⏰ 예약된 자동 퀴즈 풀이를 시작합니다. (설정시간: {quiz_hour:02d}:{quiz_min:02d})")
                gui_callbacks['update_status']("자동 퀴즈 풀이 중...")
                self.execute_quiz(gui_callbacks)
                self.state.last_auto_quiz_date = today
                return True
            
            # 3. 자동 세미나 새로고침 체크
            if settings.get('auto_seminar_refresh') and not getattr(self.state, 'is_seminar_refresh_paused', False):
                try:
                    refresh_interval = int(settings.get('seminar_refresh_interval', 5))
                except (ValueError, TypeError):
                    refresh_interval = 5
                    
                if self.state.last_seminar_refresh_time is None or (now - self.state.last_seminar_refresh_time).total_seconds() >= refresh_interval:
                    self.state.last_seminar_refresh_time = now
                    gui_callbacks['update_status']("자동 세미나 수집 중...")
                    self._handle_seminar_refresh(gui_callbacks, settings)
                    return True

            # 3-1. 자동 설문 지연 처리 대기열 체크
            if settings.get('auto_survey') and settings.get('auto_survey_delay') and self.state.current_module is None:
                try:
                    delay_min = int(settings.get('auto_survey_delay_min', 10))
                except:
                    delay_min = 10
                    
                surveys = self._load_pending_surveys()
                if surveys:
                    executable_item = None
                    executable_index = -1
                    
                    for idx, item in enumerate(surveys):
                        try:
                            det_time = datetime.strptime(item['detected_time'], "%Y-%m-%d %H:%M:%S")
                            elapsed = (now - det_time).total_seconds() / 60.0
                            if elapsed >= delay_min:
                                executable_item = item
                                executable_index = idx
                                break
                        except Exception as te:
                            self.logger.error(f"대기열 데이터 시간 파싱 실패: {te}")
                            # 파싱 실패한 데이터는 롤백 방지용 삭제
                            surveys.pop(idx)
                            self._save_pending_surveys(surveys)
                            break
                            
                    if executable_item:
                        title = executable_item['title']
                        url = executable_item['url']
                        retry = executable_item.get('retry_count', 0)
                        
                        gui_callbacks['log_message'](f"⏱ 지연 대기 완료({delay_min}분 경과)로 자동 설문을 시작합니다: {title}")
                        
                        try:
                            # 상태 업데이트
                            self.state.current_module = '세미나 풀이'
                            module_class = self.get_module_class('survey')
                            
                            # 동기적으로 실행 (이미 백그라운드 스레드 상태임)
                            success = self.execute_module_safely(module_class, "세미나 풀이", gui_callbacks, target_url=url, target_title=title)
                            
                            # 결과 처리
                            surveys = self._load_pending_surveys() # 최신화 (실행 중 추가된 내역 반영)
                            # 현재 지웠는지 다시 인덱스 검색 (안전성)
                            current_index = -1
                            for c_idx, s_item in enumerate(surveys):
                                if s_item.get('url') == url:
                                    current_index = c_idx
                                    break
                                    
                            if success:
                                if current_index != -1:
                                    surveys.pop(current_index)
                                    self._save_pending_surveys(surveys)
                                self.logger.info(f"✅ 지연 설문 처리 완료 및 대기열 제거: {title}")
                            else:
                                if current_index != -1:
                                    surveys[current_index]['retry_count'] = retry + 1
                                    if surveys[current_index]['retry_count'] >= 3:
                                        surveys.pop(current_index)
                                        self._save_pending_surveys(surveys)
                                        self.logger.error(f"❌ 지연 설문 3회 실패로 대기열에서 제외 처리: {title}")
                                    else:
                                        self._save_pending_surveys(surveys)
                                        self.logger.warning(f"⚠️ 지연 설문 실패로 재시도 예정 (현재 재시도 횟수: {retry + 1}/3): {title}")
                        except Exception as ex:
                            self.logger.error(f"지연 설문 백그라운드 실행 오류: {ex}")

            # 3-2. 자동 설문 1분 주기 재시도 대기열 체크
            if settings.get('auto_survey') and hasattr(self.state, '_survey_retry_queue') and self.state._survey_retry_queue and self.state.current_module is None:
                executable_item = None
                executable_index = -1
                
                for idx, item in enumerate(self.state._survey_retry_queue):
                    last_try = item.get('last_try_time')
                    elapsed = (now - last_try).total_seconds()
                    if elapsed >= 60.0:  # 60초(1분) 경과 시 실행
                        executable_item = item
                        executable_index = idx
                        break
                
                if executable_item:
                    title = executable_item['title']
                    url = executable_item['url']
                    retry = executable_item.get('retry_count', 0)
                    
                    # 재시도 횟수 업데이트
                    executable_item['retry_count'] = retry + 1
                    executable_item['last_try_time'] = now
                    
                    if retry + 1 > 5:  # 최대 5회(5분) 시도 후 포기
                        self.state._survey_retry_queue.pop(executable_index)
                        gui_callbacks['log_message'](f"❌ 설문 재시도 5회 초과로 대기열에서 제외합니다 (설문 미오픈 확정): {title}")
                        self.logger.error(f"설문 재시도 5회 초과로 포기: {title}")
                        # _recently_ended_seminars에서도 제거하여 이후 스캔에서 재등록되는 것을 완전 차단
                        if hasattr(self.state, '_recently_ended_seminars'):
                            self.state._recently_ended_seminars.discard(title)
                    else:
                        gui_callbacks['log_message'](f"🔄 [재시도 {retry + 1}/5] 설문 참여를 다시 시도합니다: {title}")
                        self.execute_survey(gui_callbacks, target_url=url, target_title=title)
                        return True

            # 4. 자동 세미나 신청 체크 (새로고침 직후에만 실행되도록 설계)
            if settings.get('auto_seminar_join') and settings.get('auto_seminar_refresh'):
                # 새로고침이 방금 일어났고 (2초 이내), 현재 다른 작업이 없다면 신청 시도
                if (self.state.last_seminar_refresh_time is not None and 
                     (now - self.state.last_seminar_refresh_time).total_seconds() < 2 and
                     self.state.current_module is None):
                    self._handle_auto_seminar_join(gui_callbacks)
                    return True

            # 5. 자동 세미나 퇴장(닫기) 체크
            if settings.get('auto_seminar_close') and self.state._entered_seminar_windows:
                try:
                    close_delay_min = int(settings.get('seminar_close_delay', 10))
                except:
                    close_delay_min = 10
                    
                now = datetime.now()
                expired_windows = []
                remaining_windows = []
                
                for win_info in self.state._entered_seminar_windows:
                    elapsed = (now - win_info['enter_time']).total_seconds() / 60.0
                    if elapsed >= close_delay_min:
                        expired_windows.append(win_info)
                    else:
                        remaining_windows.append(win_info)
                        
                if expired_windows:
                    with self.browser_lock:
                        web_auto = self.state.web_automation
                        if web_auto and web_auto.is_alive():
                            try:
                                original_handle = web_auto.driver.current_window_handle
                            except:
                                original_handle = None
                                
                            for win_info in expired_windows:
                                handle = win_info['handle']
                                title = win_info['title']
                                try:
                                    if handle in web_auto.driver.window_handles:
                                        web_auto.driver.switch_to.window(handle)
                                        web_auto.driver.close()
                                        gui_callbacks['log_message'](f"🚪 세미나 시청 시간이 만료되어 창을 자동으로 닫았습니다: {title}")
                                        self.logger.info(f"세미나 창 [{title}] 자동 종료 완료")
                                    else:
                                        self.logger.debug(f"세미나 창 [{title}] 이미 닫혀 있음")
                                except Exception as ce:
                                    self.logger.warning(f"세미나 창 [{title}] 닫는 중 오류: {ce}")
                                    
                            # 원래 창으로 포커스 복원
                            if original_handle:
                                try:
                                    if original_handle in web_auto.driver.window_handles:
                                        web_auto.driver.switch_to.window(original_handle)
                                    else:
                                        web_auto.driver.switch_to.window(web_auto.driver.window_handles[0])
                                except:
                                    pass
                    self.state._entered_seminar_windows = remaining_windows
                    return True

            return False
            
        except Exception as e:
            if 'log_error' in gui_callbacks:
                gui_callbacks['log_error'](f"스케줄 작업 체크 중 오류: {str(e)}")
            return False
    
    def get_module_class(self, module_type):
        """모듈 클래스 캐시에서 가져오기 - 성능 최적화"""
        if module_type not in self._module_cache:
            # 캐시에 없으면 새로 생성하고 저장
            try:
                self._module_cache[module_type] = ModuleFactory.create_module_class(module_type)
                self.logger.debug(f"모듈 클래스 캐시에 추가: {module_type}")
            except ValueError as e:
                self.logger.error(f"모듈 클래스 생성 실패: {str(e)}")
                raise
        
        return self._module_cache[module_type]
    
    def _get_kakao_category(self, module_name):
        """모듈 이름을 카톡 알림 카테고리 키로 변환"""
        mapping = {
            "출석 체크": "notify_attendance",
            "퀴즈 풀이": "notify_quiz",
            "세미나 풀이": "notify_survey",
            "세미나 자동신청": "notify_seminar_join",
            "세미나 입장": "notify_seminar_enter",
            "배민 쿠폰 구매": "notify_baemin",
            "포인트": "notify_startup_summary",
            "로그인": "notify_startup_summary"
        }
        if "구매" in module_name:
            return "notify_baemin"
        return mapping.get(module_name)

    def log_success(self, module_name, gui_callbacks, custom_message="", skip_notify=False):
        """성공 로깅 - 일관된 방식"""
        message = custom_message if custom_message else f"{module_name} 완료"
        gui_callbacks['log_and_update_status'](message, message)
        self.logger.info(message)
        
        # 특정 성공 로그 시 카카오톡 전송
        if not skip_notify:
            category = self._get_kakao_category(module_name)
            if category:
                self.notifier.send_kakao_message(message, category=category)
    
    def log_failure(self, module_name, gui_callbacks, custom_message=""):
        """실패 로깅 - 일관된 방식"""
        message = custom_message if custom_message else f"{module_name} 실패"
        gui_callbacks['log_and_update_status'](message, message)
        self.logger.warning(message)
        
        # 특정 실패 로그 시 카카오톡 전송
        category = self._get_kakao_category(module_name)
        if category:
            self.notifier.send_kakao_message(message, category=category)
    
    def log_error(self, module_name, error_msg, gui_callbacks):
        """오류 로깅 - 일관된 방식"""
        message = f"{module_name} 오류: {error_msg}"
        gui_callbacks['log_and_update_status'](message, message)
        self.logger.error(f"모듈 실행 오류: {module_name} - {error_msg}")
        
        # 모든 오류는 중요하므로 알림 전송 (오류 알림 설정에 따름)
        self.notifier.send_kakao_message(message, category="notify_error")
    
    def handle_special_actions(self, module_name, action_type):
        """모듈별 특별 액션 처리 - 한 곳에서 관리"""
        if module_name == "로그인":
            if action_type == 'success':
                self.state.is_logging_in = False
                self.logger.info("로그인 성공 - 로그인 상태 해제")
            elif action_type == 'failure':
                self.cleanup_web_automation()
                self.state.is_logging_in = False
                self.logger.warning("로그인 실패 - 웹드라이버 정리 및 로그인 상태 해제")
            elif action_type == 'error':
                self.cleanup_web_automation()
                self.state.is_logging_in = False
                self.logger.error("로그인 오류 - 웹드라이버 정리 및 로그인 상태 해제")
    
    def cleanup(self):
        """프로그램 종료 시 정리 작업"""
        try:
            self.cleanup_web_automation()
            self.state.cleanup()  # 상태도 함께 정리
            
            # 캐시 정리
            self._module_cache.clear()
            
            self.logger.info("모든 캐시 정리 완료")
        except Exception as e:
            # 백그라운드 정리 중 오류는 무시
            pass
    
    def get_status_summary(self):
        """현재 상태 요약 반환"""
        return self.state.get_status_summary()
    
    def set_browser_visibility(self, visible):
        """브라우저 가시성 제어 요청 전달"""
        if self.state.web_automation:
            self.state.web_automation.set_visibility(visible)
    
    def get_cache_info(self):
        """캐시 정보 반환 - 성능 모니터링용"""
        return {
            'module_cache_size': len(self._module_cache),
            'cached_modules': list(self._module_cache.keys())
        }

    def _load_pending_surveys(self):
        """임시 설문 대기열 파일을 로드합니다. 파싱 실패 시 자동 복구를 포함합니다."""
        import os
        import json
        base_dir = os.path.dirname(os.path.abspath(__file__))
        path = os.path.join(base_dir, "data", "pending_surveys.json")
        if not os.path.exists(path):
            return []
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, list):
                    return data
                return []
        except Exception as e:
            self.logger.error(f"대기열 파일 로딩 실패(초기화 시도): {e}")
            try:
                with open(path, "w", encoding="utf-8") as f:
                    json.dump([], f, ensure_ascii=False, indent=2)
            except:
                pass
            return []

    def _save_pending_surveys(self, surveys):
        """임시 설문 대기열 파일에 데이터를 저장합니다."""
        import os
        import json
        base_dir = os.path.dirname(os.path.abspath(__file__))
        path = os.path.join(base_dir, "data", "pending_surveys.json")
        try:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                json.dump(surveys, f, ensure_ascii=False, indent=2)
        except Exception as e:
            self.logger.error(f"대기열 파일 저장 실패: {e}")

    def _add_pending_survey(self, title, url):
        """종료 감지된 세미나를 대기열 파일에 등록합니다. 중복 방지가 포함됩니다."""
        from datetime import datetime
        surveys = self._load_pending_surveys()
        if any(s.get('url') == url for s in surveys):
            return
        surveys.append({
            "title": title,
            "url": url,
            "detected_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "retry_count": 0
        })
        self._save_pending_surveys(surveys)
        self.logger.info(f"📝 자동 설문 대기열에 등록되었습니다: {title} (지연 시간 설정 적용)")
