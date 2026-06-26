# -*- coding: utf-8 -*-
"""
출석체크 모듈
닥터빌 출석체크 기능을 담당합니다.
"""

import logging
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from .base_module import BaseModule
from .messages import MSG_ATTENDANCE_START, MSG_ATTENDANCE_SUCCESS, MSG_ATTENDANCE_ALREADY

# URL 상수 정의
ATTENDANCE_PAGE_URL = "https://www.doctorville.co.kr/event/attend"

# CSS 선택자 상수 정의
ATTEND_BUTTON_CLASS = "point_down"
SUCCESS_POPUP_ID = "popSuccessArea"

# 대기 시간 상수 정의
DEFAULT_IMPLICIT_WAIT = 5

# 에러 메시지 상수 정의
ERROR_WEBDRIVER_NOT_INITIALIZED = "웹드라이버가 초기화되지 않았습니다."
ERROR_ATTENDANCE_PAGE_NAVIGATION = "출석체크 페이지 이동 실패"
ERROR_ATTEND_BUTTON_CLICK = "출석하기 버튼 클릭 실패"
ERROR_ATTENDANCE_EXECUTION = "출석체크 실행 중 오류 발생"

class AttendanceModule(BaseModule):
    def __init__(self, web_automation, gui_logger=None):
        super().__init__(web_automation, gui_logger)
    
    def execute(self):
        """출석체크 페이지로 이동하고 포인트 받기 버튼 클릭"""
        """출석체크 작업 실행"""
        is_success = False
        result_msg = ""
        
        try:
            self.log_info(MSG_ATTENDANCE_START)
            
            # 출석체크 페이지로 이동
            self._navigate_to_attendance_page()
            
            # 출석 버튼 클릭 시도
            if self.click_attend_button():
                is_success = True
                result_msg = MSG_ATTENDANCE_SUCCESS
            else:
                is_success = True
                result_msg = MSG_ATTENDANCE_ALREADY
                self.log_info(result_msg)
            
        except Exception as e:
            is_success = False
            result_msg = f"출석체크 실행 중 오류 발생: {str(e)}"
            self.log_error(result_msg)
            
        return self.create_result(is_success, result_msg)
    
    def _navigate_to_attendance_page(self):
        """출석체크 페이지로 이동"""
        try:
            self.web_automation.driver.get(ATTENDANCE_PAGE_URL)
            self.web_automation.wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))
            self.log_info("출석체크 페이지 로딩 완료")
            return True
        except Exception as e:
            self.log_error(f"{ERROR_ATTENDANCE_PAGE_NAVIGATION}: {str(e)}")
            return False
    
    def click_attend_button(self):
        """출석하기 버튼 클릭 또는 이미 완료된 경우 확인"""
        try:
            self.log_info("출석하기 버튼 찾는 중...")
            
            # 암시적 대기를 일시적으로 0으로 설정 (즉시 검색)
            self.web_automation.driver.implicitly_wait(0)
            
            try:
                # 출석하기 버튼을 즉시 탐색 (이미 출석한 경우를 위해 0초 대기)
                # find_elements는 숨겨진 요소도 포함하므로 가시성 체크가 필요함
                all_buttons = self.web_automation.driver.find_elements(By.CLASS_NAME, ATTEND_BUTTON_CLASS)
                
                # 실제로 화면에 보이는 버튼만 필터링
                visible_buttons = [btn for btn in all_buttons if btn.is_displayed()]
                
                if visible_buttons:
                    button = visible_buttons[0]
                    self.log_info("출석하기 버튼 발견")
                    
                    # 버튼 클릭
                    button.click()
                    self.log_info("출석하기 버튼 클릭 완료")
                    
                    # 성공 팝업 확인
                    self._check_success_popup()
                else:
                    self.log_info("출석하기 버튼이 없거나 이미 숨겨져 있습니다. (출석 완료 상태)")
                
                return True
                
            except Exception as e:
                # 버튼을 찾는 과정이 아닌 클릭 등 다른 과정에서 오류가 발생한 경우
                self.log_error(f"출석 작업 중 오류: {str(e)}")
                return True # 포인트 확인으로 넘어가기 위해 True 반환
            finally:
                # 원래 암시적 대기 시간으로 복원
                self.web_automation.driver.implicitly_wait(DEFAULT_IMPLICIT_WAIT)
            
        except Exception as e:
            self.log_error(f"{ERROR_ATTEND_BUTTON_CLICK}: {str(e)}")
            return False
    
    def _check_success_popup(self):
        """성공 팝업 확인"""
        try:
            self.find_element_safe(By.ID, SUCCESS_POPUP_ID, timeout=5)
            self.log_info("출석체크 성공! 포인트가 적립되었습니다.")
        except Exception:
            self.log_info("출석체크 완료 (성공 팝업 확인 불가)")
    
    def _check_points_after_attendance(self):
        """출석체크 후 포인트 상태 확인 - BaseModule의 공통 메서드 사용"""
        self.check_points_after_activity()
    
    # 중복된 _log 메서드 제거 - BaseModule의 log_info 사용
