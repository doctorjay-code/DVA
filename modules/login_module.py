# -*- coding: utf-8 -*-
"""
닥터빌 자동 로그인 모듈
통합회원 로그인을 통해 자동으로 로그인을 수행합니다.
"""

import time
import os
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

# 오류 메시지 상수 정의
ERROR_DRIVER_NOT_INITIALIZED = "웹드라이버가 초기화되지 않았습니다."
ERROR_PAGE_LOAD_TIMEOUT = "페이지 로딩 시간 초과"
ERROR_ELEMENT_NOT_FOUND = "요소를 찾을 수 없습니다."
ERROR_LOGIN_FAILED = "로그인에 실패했습니다."
ERROR_USER_INFO_COLLECTION_FAILED = "사용자 정보 수집 중 오류"
ERROR_GUI_UPDATE_FAILED = "GUI 업데이트 실패"
ERROR_WEBDRIVER_NOT_INITIALIZED = "웹드라이버가 초기화되지 않았습니다. 먼저 로그인해주세요."

# URL 상수 정의
DOCTORVILLE_URLS = {
    'main': 'https://www.doctorville.co.kr',
    'login': 'https://www.doctorville.co.kr/login',
    'unified_login': 'https://www.doctorville.co.kr/login/unified'
}

# CSS 선택자 상수 정의
CSS_SELECTORS = {
    'unified_login_button': 'a.btn_join.union',
    'login_form_username': 'identifier',
    'login_form_password': 'password',
    'login_submit_button': 'button[type="submit"]',
    'user_info_element': '.myinfo .txt_blue',
    'myinfo_container': '.myinfo'
}

# 대기 시간 상수 정의
WAIT_TIMES = {
    'page_load': 10,
    'form_load': 10,
    'after_login': 2,
    'after_click': 1
}

from modules.base_module import BaseModule
from modules.messages import (
    MSG_LOGIN_START, MSG_LOGIN_SUCCESS, MSG_LOGIN_STEP_SETUP,
    MSG_LOGIN_STEP_NAVIGATE, MSG_LOGIN_STEP_CLICK_UNIFIED,
    MSG_LOGIN_STEP_WAIT_FORM, MSG_LOGIN_STEP_PERFORM, MSG_LOGIN_STEP_CHECK
)

class LoginModule(BaseModule):
    def __init__(self, web_automation, gui_logger=None):
        super().__init__(web_automation, gui_logger)
    
    
    def execute(self):
        """완전한 로그인 프로세스 실행"""
        try:
            self.log_info(MSG_LOGIN_START)
            
            # 단계별 로그인 프로세스 실행
            if not self._execute_login_steps():
                return self.create_result(False, "로그인 단계 실행 실패")
            
            # 로그인 완료 후 성공 반환 (포인트 확인은 이제 TaskManager에서 수행)
            return self.create_result(True, MSG_LOGIN_SUCCESS)
            
        except Exception as e:
            error_msg = f"자동 로그인 실패: {str(e)}"
            self.log_error(error_msg)
            self._cleanup_on_error()
            return self.create_result(False, error_msg)
    
    def _execute_login_steps(self):
        """로그인 단계들을 순차적으로 실행합니다."""
        steps = [
            (MSG_LOGIN_STEP_SETUP, self._setup_driver),
            (MSG_LOGIN_STEP_NAVIGATE, self.navigate_to_doctorville),
            (MSG_LOGIN_STEP_CLICK_UNIFIED, self.click_unified_login),
            (MSG_LOGIN_STEP_WAIT_FORM, self.wait_for_login_form),
            (MSG_LOGIN_STEP_PERFORM, self.perform_login),
            (MSG_LOGIN_STEP_CHECK, self.check_login_success)
        ]
        
        for step_name, step_func in steps:
            # 과정 로그는 이모티콘 없이 기록 (시스템 로그 전용)
            self.log_info(f"{step_name} 중...")
            if not step_func():
                self.log_error(f"{step_name} 실패")
                return False
            self.log_info(f"{step_name} 완료")
        
        return True
    
    def _setup_driver(self):
        """웹드라이버를 설정합니다."""
        return self.web_automation.setup_driver()
    
    def _execute_post_login_tasks(self):
        """로그인 후 작업들을 실행합니다."""
        try:
            self.log_info("로그인 후 작업을 시작합니다...")
            
            # 로그인 성공 로그
            self.log_success("자동 로그인이 성공적으로 완료되었습니다!")
            
            # 로그인 후 자동으로 포인트 상태 확인 (출석체크와 동일한 방식)
            return self._check_points_after_login()
            
        except Exception as e:
            self.log_error(f"로그인 후 작업 실행 중 오류: {str(e)}")
            return None
    
    def _cleanup_on_error(self):
        """오류 발생 시 정리 작업을 수행합니다."""
        try:
            if self.web_automation:
                self.web_automation.close_driver()
                self.web_automation = None
            self.log_info("오류 발생으로 웹드라이버를 정리했습니다.")
        except Exception as e:
            self.log_error(f"정리 작업 중 오류: {str(e)}")
    
    def navigate_to_doctorville(self):
        """닥터빌 메인 페이지로 이동"""
        try:
            start_time = time.time()
            self.log_info("닥터빌 메인 페이지로 이동 중...")
            
            self.web_automation.driver.get(DOCTORVILLE_URLS['main'])
            
            # 페이지 로딩 대기
            self.web_automation.wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))
            elapsed_time = time.time() - start_time
            self.log_success(f"닥터빌 메인 페이지 로딩 완료 (소요시간: {elapsed_time:.2f}초)")
            return True
            
        except TimeoutException:
            self.log_error("페이지 로딩 시간 초과")
            return False
        except Exception as e:
            self.log_error(f"페이지 이동 실패: {str(e)}")
            return False
    
    def click_unified_login(self):
        """통합회원 로그인 버튼 클릭"""
        try:
            start_time = time.time()
            self.log_info("통합회원 로그인 버튼을 찾는 중...")
            
            # 통합회원 로그인 버튼 찾기
            login_button = self.web_automation.driver.find_element(By.CSS_SELECTOR, "a.btn_join.union")
            
            if not login_button:
                self.log_error("통합회원 로그인 버튼을 찾을 수 없습니다.")
                return False
            
            # 버튼 클릭
            self.log_info("통합회원 로그인 버튼 클릭 중...")
            login_button.click()
            
            # 로그인 페이지로 이동 대기
            time.sleep(WAIT_TIMES['after_click'])
            
            # URL 확인
            current_url = self.web_automation.driver.current_url
            if "mims-account" in current_url and "/login" in current_url:
                elapsed_time = time.time() - start_time
                self.log_success(f"로그인 페이지로 성공적으로 이동했습니다. (소요시간: {elapsed_time:.2f}초)")
                return True
            else:
                self.log_error(f"로그인 페이지 이동 실패. 현재 URL: {current_url}")
                return False
                
        except NoSuchElementException:
            self.log_error("통합회원 로그인 버튼을 찾을 수 없습니다.")
            return False
        except Exception as e:
            self.log_error(f"통합회원 로그인 버튼 클릭 실패: {str(e)}")
            return False
    
    def wait_for_login_form(self):
        """로그인 폼이 로드될 때까지 대기"""
        try:
            start_time = time.time()
            self.log_info("로그인 폼 로딩 대기 중...")
            
            # 아이디 입력 필드가 나타날 때까지 대기
            self.web_automation.wait.until(EC.presence_of_element_located((By.ID, "identifier")))
            
            # 비밀번호 입력 필드가 나타날 때까지 대기
            self.web_automation.wait.until(EC.presence_of_element_located((By.ID, "password")))
            
            # 로그인 버튼이 나타날 때까지 대기
            self.web_automation.wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "button[type='submit']")))
            
            elapsed_time = time.time() - start_time
            self.log_success(f"로그인 폼이 성공적으로 로드되었습니다. (소요시간: {elapsed_time:.2f}초)")
            return True
            
        except TimeoutException:
            self.log_error("로그인 폼 로딩 시간 초과")
            return False
        except Exception as e:
            self.log_error(f"로그인 폼 로딩 실패: {str(e)}")
            return False
    
    def perform_login(self):
        """아이디/비밀번호 입력 및 로그인 버튼 클릭"""
        try:
            start_time = time.time()
            self.log_info("로그인 정보 입력 중...")
            
            # 환경변수에서 계정 정보 가져오기 (BAT 파일에서 설정)
            username = os.environ.get('ACCOUNT_USERNAME', '')
            password = os.environ.get('ACCOUNT_PASSWORD', '')
            account_name = os.environ.get('ACCOUNT_NAME', '기본계정')
            self.log_info(f"계정 정보 로드: {account_name}")
            
            if not username or not password:
                self.log_error("로그인 정보가 설정되지 않았습니다.")
                return False
            
            # 아이디 입력
            username_field = self.web_automation.driver.find_element(By.ID, "identifier")
            username_field.clear()
            username_field.send_keys(username)
            self.log_info("아이디 입력 완료")
            
            # 비밀번호 입력
            password_field = self.web_automation.driver.find_element(By.ID, "password")
            password_field.clear()
            password_field.send_keys(password)
            self.log_info("비밀번호 입력 완료")
            
            # 로그인 버튼 클릭
            login_button = self.web_automation.driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
            login_button.click()
            self.log_info("로그인 버튼 클릭 완료")
            
            # 로그인 처리 대기
            time.sleep(WAIT_TIMES['after_click'])
            
            elapsed_time = time.time() - start_time
            self.log_success(f"로그인 정보 입력 및 버튼 클릭 완료 (소요시간: {elapsed_time:.2f}초)")
            return True
            
        except NoSuchElementException as e:
            self.log_error(f"로그인 폼 요소를 찾을 수 없습니다: {str(e)}")
            return False
        except Exception as e:
            self.log_error(f"로그인 수행 실패: {str(e)}")
            return False
    
    def check_login_success(self):
        """로그인 성공 여부 확인 - URL 확인으로 판단"""
        try:
            self.log_info("로그인 성공 여부를 확인합니다...")
            
            # 로그인 후 충분한 대기
            time.sleep(1)
            
            # 현재 URL로 로그인 성공 여부 판단
            current_url = self.web_automation.driver.current_url
            
            if "mims-account" in current_url:
                # 아직 로그인 페이지에 있음 = 실패
                self.log_error("로그인 실패 - 여전히 로그인 페이지에 있습니다.")
                return False
            else:
                # 로그인 페이지가 아님 = 성공 가능성 높음
                self.log_success("로그인 성공으로 판단합니다.")
                return True
                
        except Exception as e:
            self.log_error(f"로그인 상태 확인 실패: {str(e)}")
            return False
    
    def _check_points_after_login(self):
        """로그인 후 포인트 상태 확인 - BaseModule의 공통 메서드 사용"""
        return self.check_points_after_activity()