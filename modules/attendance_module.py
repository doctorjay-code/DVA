# -*- coding: utf-8 -*-
"""
출석 체크 모듈
닥터빌 출석 체크 기능을 담당합니다.
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
BUTTON_WAIT_TIMEOUT = 10  # 버튼 렌더링 대기 (JS 로딩 고려)
POPUP_WAIT_TIMEOUT = 5    # 성공 팝업 대기

# 에러 메시지 상수 정의
ERROR_WEBDRIVER_NOT_INITIALIZED = "웹드라이버가 초기화되지 않았습니다."
ERROR_ATTENDANCE_PAGE_NAVIGATION = "출석 체크 페이지 이동 실패"
ERROR_ATTEND_BUTTON_CLICK = "출석하기 버튼 클릭 실패"
ERROR_ATTENDANCE_EXECUTION = "출석 체크 실행 중 오류 발생"

class AttendanceModule(BaseModule):
    def __init__(self, web_automation, gui_logger=None):
        super().__init__(web_automation, gui_logger)
    
    def execute(self):
        """출석 체크 페이지로 이동하고 포인트 받기 버튼 클릭"""
        is_success = False
        result_msg = ""
        
        try:
            self.log_info(MSG_ATTENDANCE_START)
            
            # 출석 체크 페이지로 이동
            self._navigate_to_attendance_page()
            
            # 출석 버튼 클릭 시도
            # True  = 버튼을 찾아서 클릭 성공
            # None  = 버튼 없음 (이미 출석 완료 상태)
            # False = 클릭 중 오류
            clicked = self.click_attend_button()
            
            if clicked is True:
                is_success = True
                result_msg = MSG_ATTENDANCE_SUCCESS
            elif clicked is None:
                # 버튼이 없음 = 이미 출석 완료 상태
                is_success = True
                result_msg = MSG_ATTENDANCE_ALREADY
                self.log_info(result_msg)
            else:
                # False = 클릭 중 오류 발생
                is_success = False
                result_msg = "출석 체크 버튼 클릭 실패"
                self.log_error(result_msg)
            
        except Exception as e:
            is_success = False
            result_msg = f"출석 체크 실행 중 오류 발생: {str(e)}"
            self.log_error(result_msg)
            
        return self.create_result(is_success, result_msg)
    
    def _navigate_to_attendance_page(self):
        """출석 체크 페이지로 이동"""
        try:
            self.web_automation.driver.get(ATTENDANCE_PAGE_URL)
            # body 태그 대기 (기본 로딩 확인)
            self.web_automation.wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))
            self.log_info("출석 체크 페이지 로딩 완료")
            return True
        except Exception as e:
            self.log_error(f"{ERROR_ATTENDANCE_PAGE_NAVIGATION}: {str(e)}")
            return False
    
    def click_attend_button(self):
        """출석하기 버튼 클릭.
        
        Returns:
            True  : 버튼을 찾아 클릭 성공
            None  : 버튼 없음 (이미 출석 완료 상태)
            False : 예외 발생으로 실패
        """
        try:
            self.log_info("출석하기 버튼 찾는 중...")
            
            # [수정] implicitly_wait(0)+find_elements 제거
            # → EC.element_to_be_clickable으로 명시적 대기
            # 버튼은 JS로 렌더링되므로 body만 기다리면 아직 없을 수 있음
            try:
                button = WebDriverWait(self.web_automation.driver, BUTTON_WAIT_TIMEOUT).until(
                    EC.element_to_be_clickable((By.CLASS_NAME, ATTEND_BUTTON_CLASS))
                )
                self.log_info("출석하기 버튼 발견")
                
                # 버튼 클릭
                button.click()
                self.log_info("출석하기 버튼 클릭 완료")
                
                # 성공 팝업 확인
                self._check_success_popup()
                return True  # 클릭 성공
                
            except TimeoutException:
                # 10초 내 버튼이 나타나지 않음 = 이미 출석 완료 상태로 판단
                self.log_info("출석하기 버튼이 나타나지 않았습니다. (이미 출석 완료 상태)")
                return None  # 버튼 없음 (이미 완료)
            
        except Exception as e:
            self.log_error(f"{ERROR_ATTEND_BUTTON_CLICK}: {str(e)}")
            return False  # 예외 발생 = 실패
    
    def _check_success_popup(self):
        """성공 팝업 확인 - presence_of_element_located만 사용하여 빠르게 확인"""
        try:
            WebDriverWait(self.web_automation.driver, POPUP_WAIT_TIMEOUT).until(
                EC.presence_of_element_located((By.ID, SUCCESS_POPUP_ID))
            )
            self.log_info("출석 체크 성공! 포인트가 적립되었습니다.")
        except TimeoutException:
            self.log_info("출석 체크 완료 (성공 팝업 미감지 - 이미 완료 상태일 수 있음)")
        except Exception:
            self.log_info("출석 체크 완료 (성공 팝업 확인 불가)")
    
    def _check_points_after_attendance(self):
        """출석 체크 후 포인트 상태 확인 - BaseModule의 공통 메서드 사용"""
        self.check_points_after_activity()
    
    # 중복된 _log 메서드 제거 - BaseModule의 log_info 사용
