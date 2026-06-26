# -*- coding: utf-8 -*-
"""
포인트 확인 모듈
출석체크와 퀴즈풀기 완료 후 포인트 변화를 확인합니다.
"""

from datetime import datetime
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException
from modules.base_module import BaseModule, STATUS_ATTENDANCE_COMPLETE, STATUS_ATTENDANCE_INCOMPLETE, STATUS_QUIZ_COMPLETE, STATUS_QUIZ_INCOMPLETE, STATUS_KEY_ATTENDANCE, STATUS_KEY_QUIZ
from selenium.common.exceptions import TimeoutException
from modules.messages import MSG_POINTS_SUMMARY
# URL 상수 정의
POINTS_PAGE_URL = "https://www.doctorville.co.kr/my/point/pointUseHistoryList"
MAIN_PAGE_URL = "https://www.doctorville.co.kr/my/main"

# CSS 선택자 상수 정의
POINTS_BOX_SELECTOR = ".box_point"
POINTS_VALUE_SELECTOR = ".box_point .point em"
USER_INFO_SELECTOR = ".myinfo"
USER_NAME_SELECTOR = ".myinfo .txt_blue"
POINT_HISTORY_ROWS_SELECTOR = "tbody tr.tr_add"
DATE_CELL_SELECTOR = "td.date"
CONTENT_CELL_SELECTOR = "td:nth-child(3)"

# 활동 타입 상수 정의
ACTIVITY_TYPE_ATTENDANCE = "출석체크"
ACTIVITY_TYPE_QUIZ = "퀴즈"

# 날짜 형식 상수 정의
DATE_FORMAT = "%Y.%m.%d"
CACHE_DURATION_MINUTES = 5

# 에러 메시지 상수 정의
ERROR_POINTS_CHECK_FAILED = "포인트 확인 실패"
ERROR_ACTIVITY_SUMMARY_FAILED = "활동 요약 수집 실패"
ERROR_USER_INFO_FAILED = "사용자 정보 요약 수집 실패"
ERROR_GUI_UPDATE_FAILED = "GUI 업데이트 실패"
ERROR_UNKNOWN_ACTIVITY = "알 수 없는 활동 타입"

class PointsCheckModule(BaseModule):
    """
    닥터빌 포인트 확인 모듈
    
    주요 기능:
    - 사용자 정보 수집 (이름, 포인트)
    - 출석체크 및 퀴즈 참여 상태 확인
    - GUI 대시보드 자동 업데이트
    
    성능 최적화:
    - 페이지 이동 최소화 (메인 페이지에서 포인트 정보도 수집)
    - 적응적 대기 시간 (기본 대기 실패 시 재시도)
    - 일관된 에러 처리 및 사용자 친화적 메시지
    """
    
    def __init__(self, web_automation, gui_logger=None):
        """
        PointsCheckModule 초기화
        
        Args:
            web_automation: 웹 자동화 인스턴스
            gui_logger: GUI 로깅 함수
        """
        super().__init__(web_automation, gui_logger)
    
    def _get_today_date(self):
        """오늘 날짜를 표준 형식으로 반환"""
        return datetime.now().strftime(DATE_FORMAT)
    
    def _update_gui_directly(self, result):
        """GUI 업데이트 - 콜백 인터페이스 사용"""
        try:
            # 설정된 콜백이 있는지 확인
            if not hasattr(self, 'gui_callbacks') or not self.gui_callbacks:
                self.log_warning("GUI 콜백이 설정되지 않아 업데이트를 건너뜁니다.")
                return

            callbacks = self.gui_callbacks
            
            # 사용자 이름 업데이트
            if 'update_user_info' in callbacks:
                callbacks['update_user_info'](result['user_name'])
            
            # 포인트, 출석체크, 퀴즈 상태 업데이트
            if 'update_display' in callbacks:
                update_display = callbacks['update_display']
                update_display('points', result['points'])
                update_display(STATUS_KEY_ATTENDANCE, result[STATUS_KEY_ATTENDANCE])
                update_display(STATUS_KEY_QUIZ, result[STATUS_KEY_QUIZ])
            
            self.log_info("GUI 대시보드 업데이트 완료")
                
        except Exception as e:
            self.log_error(f"GUI 업데이트 중 오류: {str(e)}")
    
    def execute(self):
        """포인트 및 활동 상태 수집 실행"""
        result = self.get_user_info_summary()
        if result and result.get('success'):
            return result
        return self.create_result(False, "포인트 확인 실패")

    def get_user_info_summary(self):
        """사용자 정보 수집 - 메인 진입점"""
        try:
            self.log_info("사용자 정보 수집 시작...")
            
            # 1단계: 메인 페이지에서 사용자 이름만 수집
            user_name = self._get_user_name_from_main()
            
            # 2단계: 포인트 페이지에서 포인트+활동상태 모두 수집
            points_data = self._get_points_and_activities()
            
            # 3단계: 결과 합치기
            data = {
                'user_name': user_name,
                'points': points_data['points'],
                'attendance_status': points_data[STATUS_KEY_ATTENDANCE],
                'quiz_status': points_data[STATUS_KEY_QUIZ]
            }
            
            # 4단계: 상세 메시지 생성 (알림용)
            summary_msg = (
                f"[{user_name}님 상태 요약]\n"
                f"💰 포인트: {points_data['points']}P\n"
                f"📅 출석체크: {'완료' if points_data[STATUS_KEY_ATTENDANCE] == STATUS_ATTENDANCE_COMPLETE else '미완료'}\n"
                f"🧠 퀴즈참여: {'완료' if points_data[STATUS_KEY_QUIZ] == STATUS_QUIZ_COMPLETE else '미완료'}"
            )
            
            self.log_success(f"활동 정보 수집 완료: {data['attendance_status']}, {data['quiz_status']}")
            
            # 5단계: GUI 업데이트
            self._update_gui_directly(data)
            
            # 6단계: 카톡 알림 전송 (별도로 알림 전송)
            if hasattr(self, 'gui_callbacks') and 'notify_kakao' in self.gui_callbacks:
                self.gui_callbacks['notify_kakao'](summary_msg, cat="notify_startup_summary")
            
            # 7단계: 로그 기록
            self.log_success(summary_msg)
            
            return self.create_result(True, summary_msg, data)
            
        except Exception as e:
            error_msg = f"{ERROR_USER_INFO_FAILED}: {str(e)}"
            self.log_error(error_msg)
            return self.create_result(False, error_msg)
    
            # 1단계: 메인 페이지에서 사용자 이름만 수집
            user_name = self._get_user_name_from_main()
            
            # ... 

    def _get_user_name_from_main(self):
        """메인 페이지에서 사용자 이름만 수집"""
        try:
            self.log_info("메인 페이지에서 사용자 이름 수집 중...")
            
            # 메인 페이지로 이동 (렌더러 타임아웃 방어)
            try:
                self.web_automation.driver.get(MAIN_PAGE_URL)
            except TimeoutException:
                self.log_warning("메인 페이지 로딩 시간 초과 (렌더러 타임아웃), 페이지 로드를 강제 중단하고 진행합니다.")
                try:
                    self.web_automation.driver.execute_script("window.stop();")
                except:
                    pass
            
            # 사용자 이름 추출 (안전하게)
            user_info_element = self.find_element_safe(By.CSS_SELECTOR, USER_INFO_SELECTOR)
            user_name_element = user_info_element.find_element(By.CSS_SELECTOR, USER_NAME_SELECTOR)
            user_name = user_name_element.text.strip()
            
            # "님," "님" 제거
            if user_name.endswith("님,"):
                user_name = user_name[:-2]
            elif user_name.endswith("님"):
                user_name = user_name[:-1]
            
            self.log_info(f"사용자 이름: {user_name}")
            return user_name
            
        except Exception as e:
            self.log_error(f"메인 페이지에서 사용자 이름 수집 실패: {e}")
            return "사용자"
    
    def _get_points_and_activities(self):
        """포인트 페이지에서 포인트+활동상태 모두 수집"""
        try:
            self.log_info("포인트 페이지에서 정보 수집 중...")
            
            # 포인트 페이지로 이동 (렌더러 타임아웃 방어)
            try:
                self.web_automation.driver.get(POINTS_PAGE_URL)
            except TimeoutException:
                self.log_warning("포인트 페이지 로딩 시간 초과 (렌더러 타임아웃), 페이지 로드를 강제 중단하고 진행합니다.")
                try:
                    self.web_automation.driver.execute_script("window.stop();")
                except:
                    pass
            
            self.find_element_safe(By.CSS_SELECTOR, POINTS_BOX_SELECTOR)
            
            # 포인트 정보 수집
            try:
                points_element = self.find_element_safe(By.CSS_SELECTOR, POINTS_VALUE_SELECTOR)
                current_points = points_element.text.strip()
                self.log_info(f"현재 포인트: {current_points}P")
            except NoSuchElementException:
                current_points = "0"
                self.log_warning("포인트 정보를 찾을 수 없음")
            
            # 오늘 활동 상태 확인
            today = self._get_today_date()
            attendance_done = self._check_today_activity("출석체크", today)
            quiz_done = self._check_today_activity("퀴즈", today)
            
            return {
                'points': current_points,
                STATUS_KEY_ATTENDANCE: STATUS_ATTENDANCE_COMPLETE if attendance_done else STATUS_ATTENDANCE_INCOMPLETE,
                STATUS_KEY_QUIZ: STATUS_QUIZ_COMPLETE if quiz_done else STATUS_QUIZ_INCOMPLETE
            }
            
        except Exception as e:
            self.log_error(f"포인트 페이지 정보 수집 실패: {e}")
            return {
                'points': "0",
                STATUS_KEY_ATTENDANCE: STATUS_ATTENDANCE_INCOMPLETE,
                STATUS_KEY_QUIZ: STATUS_QUIZ_INCOMPLETE
            }
    
    def _check_today_activity(self, activity_type_key, today):
        """오늘 활동 여부 확인"""
        try:
            rows = self.find_elements_safe(By.CSS_SELECTOR, POINT_HISTORY_ROWS_SELECTOR)
            
            for row in rows:
                try:
                    date_text = row.find_element(By.CSS_SELECTOR, DATE_CELL_SELECTOR).text.strip()
                    content_text = row.find_element(By.CSS_SELECTOR, CONTENT_CELL_SELECTOR).text.strip()
                    
                    if date_text == today and activity_type_key in content_text:
                        self.log_success(f"{activity_type_key} 활동 발견!")
                        return True
                        
                except NoSuchElementException:
                    continue
            
            self.log_info(f"{activity_type_key} 활동을 찾을 수 없습니다.")
            return False
            
        except Exception as e:
            self.log_error(f"{activity_type_key} 활동 확인 중 오류: {str(e)}")
            return False
