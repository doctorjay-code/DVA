# -*- coding: utf-8 -*-
"""
모듈 베이스 클래스
모든 모듈이 공통으로 사용하는 기능들을 제공합니다.
"""

import logging

# 상수들을 직접 정의하여 순환 import 방지
STATUS_ATTENDANCE_COMPLETE = "출석체크 완료"
STATUS_ATTENDANCE_INCOMPLETE = "출석체크 미완료"
STATUS_QUIZ_COMPLETE = "퀴즈 참여 완료"
STATUS_QUIZ_INCOMPLETE = "퀴즈 참여 미완료"

# 상태 키 상수 정의 (PointsCheckModule과 일관성 유지)
STATUS_KEY_ATTENDANCE = 'attendance_status'
STATUS_KEY_QUIZ = 'quiz_status'

# 로그 메시지 상수 정의
LOG_POINTS_CHECK_SUCCESS = "🎯 {activity_type} 완료 후 최종 포인트: {points}P"
LOG_POINTS_CHECK_ERROR = "포인트 확인 중 오류"

class BaseModule:
    def __init__(self, web_automation, gui_logger=None):
        self.web_automation = web_automation
        self.gui_logger = gui_logger
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # GUI 콜백 함수들
        self.gui_logger = gui_logger
        
        # 로거 설정
        if not hasattr(self, 'logger'):
            self.logger = logging.getLogger(self.__class__.__name__)
    
    def set_callbacks(self, gui_callbacks):
        """GUI 콜백 함수들을 설정합니다."""
        # 필요한 콜백만 설정
        if 'log_message' in gui_callbacks:
            self.gui_logger = gui_callbacks['log_message']
        
        # gui_callbacks 자체도 저장 (PointsCheckModule에서 사용)
        self.gui_callbacks = gui_callbacks
    
    def log_info(self, message):
        """
        정보 로깅 - 파일 로그에는 기록하고, GUI에는 이모티콘 있을 때만 직접 노출
        """
        # 1. 시스템 파일 로그에는 무조건 기록 (디버깅용)
        # INFO 레벨 이상이 GUI와 연결되어 있을 가능성이 높으므로, 
        # GUI 노출을 원치 않는 것은 DEBUG 레벨로 기록합니다.
        UI_EMOJIS = ("✅", "🔐", "📅", "📝", "💰", "🔍", "🔄", "⚠️", "🚨", "🎉", "🚪", "🛵", "🔎", "💡", "📊", "🎯")
        
        is_important = message.strip().startswith(UI_EMOJIS)
        
        if is_important:
            self.logger.info(message)
            if self.gui_logger:
                # GUI 콜백을 직접 호출 (시스템 로거를 통하지 않음)
                self.gui_logger(message)
        else:
            # 이모티콘 없는 자질구레한 로그는 DEBUG 레벨로 숨김 (파일에는 남음)
            self.logger.debug(message)

    def log_success(self, message):
        """성공 로깅 (GUI 노출 보장)"""
        # 이미 이모티콘이 있을 수 있으니 체크
        if not message.startswith("✅"):
            message = f"✅ {message}"
        
        self.logger.info(message)
        if self.gui_logger:
            self.gui_logger(message)

    def log_error(self, message):
        """에러 로깅 (GUI 노출 보장)"""
        if not message.startswith("❌"):
            message = f"❌ {message}"
            
        self.logger.error(message)
        if self.gui_logger:
            self.gui_logger(message)

    def log_warning(self, message):
        """경고 로깅 (GUI 노출 보장)"""
        if not message.startswith("⚠️"):
            message = f"⚠️ {message}"
            
        self.logger.warning(message)
        if self.gui_logger:
            self.gui_logger(message)
    
    def log_and_update(self, message, status=None):
        """로깅과 상태 업데이트를 한 번에 처리합니다."""
        if self.gui_logger:
            self.gui_logger(message)
        # 상태 업데이트는 각 모듈에서 구현
    
    def find_element_safe(self, by, value, timeout=10, retries=3):
        """StaleElementReferenceException을 방지하며 요소를 안전하게 찾습니다."""
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC
        from selenium.common.exceptions import StaleElementReferenceException, TimeoutException
        import time

        last_exception = None
        for i in range(retries):
            try:
                element = WebDriverWait(self.web_automation.driver, timeout).until(
                    EC.presence_of_element_located((by, value))
                )
                # 요소가 화면에 보일 때까지 대기
                WebDriverWait(self.web_automation.driver, 5).until(EC.visibility_of(element))
                return element
            except StaleElementReferenceException as e:
                self.log_warning(f"요소 만료 감지 (Stale), 재시도 중... ({i+1}/{retries})")
                last_exception = e
                time.sleep(0.5)
            except TimeoutException as e:
                # 타임아웃 발생 시 last_exception을 설정하지만 재시도하지 않음
                last_exception = e
                break 
            except Exception as e:
                last_exception = e
                time.sleep(0.5)
        
        # 호출한 곳에서 처리할 수 있도록 원래의 예외를 발생시킴
        if last_exception:
            raise last_exception
        raise Exception(f"요소를 찾을 수 없음: {value}")

    def find_elements_safe(self, by, value, timeout=10, retries=3):
        """여러 요소를 안전하게 찾습니다."""
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC
        from selenium.common.exceptions import StaleElementReferenceException
        import time

        for i in range(retries):
            try:
                elements = WebDriverWait(self.web_automation.driver, timeout).until(
                    EC.presence_of_all_elements_located((by, value))
                )
                return elements
            except (StaleElementReferenceException, TimeoutException) as e:
                if isinstance(e, StaleElementReferenceException):
                    self.log_warning(f"요소 리스트 만료 감지, 재시도 중... ({i+1}/{retries})")
                time.sleep(0.5)
        return []

    def wait_for_condition_safe(self, condition_func, timeout=10, retries=3):
        """특정 조건이 충족될 때까지 안전하게 대기합니다."""
        from selenium.common.exceptions import StaleElementReferenceException
        import time

        for i in range(retries):
            try:
                start_time = time.time()
                while time.time() - start_time < timeout:
                    if condition_func():
                        return True
                    time.sleep(0.5)
                return False
            except StaleElementReferenceException:
                self.log_warning(f"조건 검사 중 요소 만료 감지, 재시도 중... ({i+1}/{retries})")
                time.sleep(0.5)
        return False

    def handle_error(self, error_type, error_message, recovery_suggestion=None):
        """일관된 에러 처리 - 사용자 친화적 메시지 생성"""
        try:
            # 에러 타입별 사용자 친화적 메시지
            user_friendly_messages = {
                'network': f"네트워크 연결 문제: {error_message}",
                'webpage': f"웹페이지 로딩 문제: {error_message}",
                'element': f"페이지 요소를 찾을 수 없음: {error_message}",
                'timeout': f"시간 초과: {error_message}",
                'login': f"로그인 문제: {error_message}",
                'data': f"데이터 수집 문제: {error_message}",
                'unknown': f"알 수 없는 오류: {error_message}"
            }
            
            # 에러 메시지 생성
            error_msg = user_friendly_messages.get(error_type, user_friendly_messages['unknown'])
            
            # 복구 방법 제시
            if recovery_suggestion:
                error_msg += f"\n💡 해결 방법: {recovery_suggestion}"
            else:
                # 기본 복구 방법
                default_suggestions = {
                    'network': "인터넷 연결을 확인하고 다시 시도해주세요.",
                    'webpage': "페이지를 새로고침하고 다시 시도해주세요.",
                    'element': "웹사이트가 변경되었을 수 있습니다. 관리자에게 문의하세요.",
                    'timeout': "잠시 후 다시 시도해주세요.",
                    'login': "아이디와 비밀번호를 확인하고 다시 시도해주세요.",
                    'data': "데이터를 다시 수집해보세요.",
                    'unknown': "프로그램을 재시작하고 다시 시도해주세요."
                }
                error_msg += f"\n💡 해결 방법: {default_suggestions.get(error_type, default_suggestions['unknown'])}"
            
            # 로그 기록
            self.log_error(error_msg)
            
            return error_msg
            
        except Exception as e:
            # 에러 처리 중 오류 발생 시 기본 메시지
            fallback_msg = f"오류 발생: {error_message}"
            self.log_error(fallback_msg)
            return fallback_msg
    

    
    def execute(self):
        """모든 모듈이 구현해야 할 메서드"""
        raise NotImplementedError("execute 메서드를 구현해야 합니다.")
    
    def cleanup(self):
        """모듈 정리 메서드 - 필요시 오버라이드"""
        pass
    
    def create_result(self, success, message="", data=None):
        """
        작업 결과를 일관된 구조로 생성합니다.
        
        Args:
            success (bool): 성공 여부
            message (str): 결과 요약 메시지
            data (dict, optional): 추가 데이터 페이로드
            
        Returns:
            dict: {"success": bool, "message": str, "data": dict}
        """
        return {
            "success": success,
            "message": message,
            "data": data or {}
        }
    
    def check_points_after_activity(self):
        """활동 완료 후 포인트 확인 (공통 메서드)"""
        try:
            self.log_info("포인트 상태를 확인합니다...")
            
            from modules.points_check_module import PointsCheckModule
            points_module = PointsCheckModule(self.web_automation, self.gui_logger)
            
            # PointsCheckModule에 콜백 설정
            if hasattr(self, 'gui_callbacks'):
                points_module.set_callbacks(self.gui_callbacks)
            
            result = points_module.get_user_info_summary()
            
            # 결과 처리 (표준화된 dict 또는 기존 dict 대응)
            data = result.get('data', result) if isinstance(result, dict) else {}
            
            if data:
                self.log_info(f"현재 포인트: {data.get('points', '0')}P")
                self.log_info("포인트 상태 확인 완료!")
            else:
                self.log_info("포인트 상태 확인 실패")
                
            return result
                
        except Exception as e:
            self.log_info(f"포인트 상태 확인 중 오류: {str(e)}")
            return None