# -*- coding: utf-8 -*-
"""
새로운 퀴즈풀기 모듈
닥터빌 퀴즈풀기 기능을 담당합니다.
"""

from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, WebDriverException
from .base_module import BaseModule
from .quiz_problem import QuizProblemManager
from .messages import MSG_QUIZ_START, MSG_QUIZ_ALREADY, MSG_QUIZ_SUCCESS
import time
import os

# URL 상수 정의
MEDICINE_PAGE_URL = "https://www.doctorville.co.kr/product/medicineList"
INSTRUMENT_PAGE_URL = "https://www.doctorville.co.kr/product/instrumentList"

# CSS 선택자 상수 정의
QUIZ_CSS_SELECTOR = ".quiz_bg"
QUIZ_BANNER_BUTTON_ID = "btn_quiz_banner"
QUIZ_LAYER_POP_ID = "quizLayerPop"
QUESTION_AREA_CONTAINER_ID = "questionArea"  # 퀴즈 문제 영역 컨테이너 (여기 안에서만 수집)
PRODUCT_TITLE_ID = "product_title"
PRODUCT_CATEGORY_ID = "product_categoryNm"
PRODUCT_TITLE_ENG_ID = "product_titleEng"
QUIZ_POINT_ID = "quiz_point"
QUESTION_AREA_SELECTOR = ".question_area"
QUESTION_TEXT_SELECTOR = ".txt_question"
QUESTION_CHOICE_SELECTOR = ".question_choice li"
ANSWER_CONFIRM_BUTTON_ID = "answerConfirmBtn"
CHOICE_LABEL_SELECTOR = "label"
CHOICE_INPUT_SELECTOR = "input"

# 대기 시간 상수 정의
DEFAULT_SHORT_TIMEOUT = 1

# 정답 매핑 상수
ANSWER_MAPPING = {'O': '1', 'X': '2'}

# 유효한 답안 값들
VALID_ANSWER_VALUES = ['1', '2', '3', '4', '5']

# 최소 퀴즈 요소 개수
MIN_QUIZ_ELEMENTS = 2

class QuizModule(BaseModule):
    def __init__(self, web_automation, gui_logger=None):
        super().__init__(web_automation, gui_logger)
        self.problem_manager = QuizProblemManager()
        self.original_window = None
        self.blog_window = None
    
    def wait_for_page_load(self, timeout=None):
        """페이지 로딩 완료 대기 (JS readyState 활용으로 최적화)"""
        try:
            # document.readyState가 complete가 될 때까지 대기 (body 찾는 것보다 정확하고 빠름)
            from selenium.webdriver.support.ui import WebDriverWait
            WebDriverWait(self.web_automation.driver, timeout or 10).until(
                lambda d: d.execute_script('return document.readyState') == 'complete'
            )
            return True
        except Exception:
            return False
    
    def wait_for_element_presence(self, element_id, timeout=None):
        """특정 요소의 존재 대기"""
        try:
            self.find_element_safe(By.ID, element_id, timeout=timeout or DEFAULT_SHORT_TIMEOUT)
            return True
        except Exception:
            return False
    
    def wait_for_element_clickable(self, element_id, timeout=None):
        """특정 요소의 클릭 가능 상태 대기"""
        try:
            from selenium.webdriver.support.ui import WebDriverWait
            from selenium.webdriver.support import expected_conditions as EC
            short_timeout = timeout or DEFAULT_SHORT_TIMEOUT
            WebDriverWait(self.web_automation.driver, short_timeout).until(
                EC.element_to_be_clickable((By.ID, element_id))
            )
            return True
        except Exception:
            return False
    
    def handle_element_not_found(self, element_name):
        """요소를 찾을 수 없을 때의 공통 처리 (하위 호환성 위해 BaseModule로 전달)"""
        return self.handle_error('element', element_name, "페이지가 갱신 중이거나 구조가 변경되었을 수 있습니다.")

    def handle_general_error(self, operation_name, error):
        """일반적인 오류 처리 (하위 호환성 위해 BaseModule로 전달)"""
        return self.handle_error('unknown', f"{operation_name} 실패: {str(error)}")
    
    def _navigate_to_quiz_page(self):
        """퀴즈 페이지 찾기 및 이동"""
        self.quiz_page_type = self.find_quiz_page()
        return bool(self.quiz_page_type)

    def _check_quiz_completed(self):
        """이미 퀴즈를 완료했는지 확인"""
        # find_quiz_page에서 찾지 못했다면 이미 완료했거나 오늘 퀴즈가 없는 것으로 간주
        if not hasattr(self, 'quiz_page_type') or not self.quiz_page_type:
            return True
        return False

    def _attempt_quiz(self):
        """실제 퀴즈 풀기 프로세스 (팝업 열기 -> 수집 -> 풀기 -> 제출)"""
        try:
            # 1. 팝업 열기
            if not self.open_quiz_popup():
                return False
                
            # 2. 🔥 이미 풀었는지 즉시 확인
            if self._is_popup_quiz_solved():
                self.log_info(MSG_QUIZ_ALREADY)
                return True
                
            # 3. 정보 수집
            quiz_data = self.collect_quiz_info()
            if not quiz_data:
                return False
                
            # 4. 문제 풀기 (각 문제별 정답 찾기 및 클릭)
            blog_answers_str = ""
            blog_searched = False
            
            for i, q_info in enumerate(quiz_data['questions']):
                success, blog_answers_str, blog_searched = self._process_single_question(
                    q_info, i, quiz_data, blog_answers_str, blog_searched
                )
                if not success:
                    self.log_error(f"문제 {i+1} 풀기 도중 중단됨")
                    return False
            
            # 5. 제출 (모든 문제를 푼 후)
            if not self.click_submit_button():
                return False
                
            # 6. 정답 학습 (성공 후 로컬 DB 저장)
            if blog_answers_str:
                self.save_to_local_db(quiz_data, blog_answers_str)
                
            return True
            
        except Exception as e:
            self.log_error(f"퀴즈 시도 중 오류: {str(e)}")
            return False

    def _is_popup_quiz_solved(self):
        """팝업 내부에서 이미 퀴즈를 풀었는지 확인 (지연 시간 최소화)"""
        try:
            # 1. '축하드립니다' 또는 '성공' 문구 확인 (가장 확실함)
            is_finished_text = self.web_automation.driver.execute_script("""
                var text = document.body.innerText;
                return text.includes('퀴즈 성공') || text.includes('축하드립니다') || text.includes('내일 다시');
            """)
            if is_finished_text:
                self.log_info("🔍 팝업에 '완료 문구'가 확인됩니다.")
                return True

            # 2. 이미 선택된 정답이 있는지 확인 (라디오 버튼 checked 상태)
            is_any_checked = self.web_automation.driver.execute_script("""
                return document.querySelector('input[type="radio"]:checked') !== null;
            """)
            if is_any_checked:
                self.log_info("🔍 이미 선택된 답변이 있습니다. 완료된 것으로 간주합니다.")
                return True
                
            # 3. 정답 도전 버튼이 아예 없는지 확인 (초고속 체크)
            try:
                submit_btn = self.web_automation.driver.find_element(By.ID, ANSWER_CONFIRM_BUTTON_ID)
                if not submit_btn.is_displayed():
                    return True
            except:
                return True # 버튼이 없으면 완료
                
            return False
        except Exception:
            return False

    def execute(self):
        """일일 퀴즈 풀기 작업 실행 (외부 호출 엔트리 포인트)"""
        is_success = False
        result_msg = ""
        
        try:
            if hasattr(self.web_automation.driver, 'current_window_handle'):
                self.original_window = self.web_automation.driver.current_window_handle
            self.log_info(MSG_QUIZ_START)
            
            # 1. 퀴즈 페이지 이동
            if not self._navigate_to_quiz_page():
                self.log_info(MSG_QUIZ_ALREADY)
                return self.create_result(True, MSG_QUIZ_ALREADY)
            
            # 2. 퀴즈 풀기 시도 (이미 푼 경우 내부적으로 True 반환)
            if self._attempt_quiz():
                is_success = True
                result_msg = MSG_QUIZ_SUCCESS
                # 이미 푼 경우 MSG_QUIZ_ALREADY 로그가 이전에 찍혔을 것임
            else:
                is_success = False
                result_msg = "일일 퀴즈 풀기 실패"
                
        except Exception as e:
            is_success = False
            result_msg = f"퀴즈 실행 중 오류 발생: {str(e)}"
            self.log_error(result_msg)
            
        finally:
            # 🗑️ 블로그 탭 정리 (남아있다면)
            try:
                if hasattr(self, 'blog_window') and self.blog_window:
                    self.web_automation.driver.switch_to.window(self.blog_window)
                    self.web_automation.driver.close()
                    self.log_info("🔓 블로그 참고 탭을 닫았습니다.")
                    if self.original_window:
                        self.web_automation.driver.switch_to.window(self.original_window)
            except:
                pass
                
            return self.create_result(is_success, result_msg)

    def _process_single_question(self, q_info, index, quiz_data, blog_answers_str, blog_searched):
        """단일 문제에 대해 정답을 찾고 선택하는 로직 처리"""
        q_text = q_info['question']
        
        # 1. 로컬 DB에서 정답 찾기
        ans = self._find_answer_in_local_db(q_text)
        
        # 2. 로컬 DB에 없으면 블로그 검색 (최초 1회만)
        if not ans and not blog_searched:
            blog_searched = True
            ans, blog_answers_str = self._search_answer_from_blog(index)
        
        # 3. 블로그에도 없거나 이미 검색했었다면 캐시된 블로그 정답 확인
        if not ans and blog_answers_str and index < len(blog_answers_str):
            ans = blog_answers_str[index]
            
        # 4. 그래도 없으면 수동 개입 유도
        if not ans:
            self.log_warning(f"문제 {index+1}의 정답을 찾을 수 없습니다. 수동 입력을 요청합니다.")
            if self.prompt_single_question_intervention(quiz_data, index):
                self.problem_manager.load_quizzes()
                ans = self.problem_manager.get_answer(q_text)
                
        # 5. 정답 선택
        if ans:
            if self.select_single_answer(q_info, ans):
                self.log_success(f"✅ 문제 {index+1} 답변 선택 완료: {ans}")
                return True, blog_answers_str, blog_searched
            else:
                self.log_error(f"❌ 문제 {index+1} 답변 선택 실패")
                return False, blog_answers_str, blog_searched
                
        self.log_error(f"❌ 문제 {index+1}의 정답을 끝내 확보하지 못했습니다.")
        return False, blog_answers_str, blog_searched

    def _find_answer_in_local_db(self, q_text):
        """DB에서 문제를 정규화하여 정답 검색"""
        self.log_info(f"🔍 [DEBUG] 웹 문제 원문: '{q_text[:60]}...'")
        normalized = self.problem_manager._normalize_question(q_text)
        self.log_info(f"🔍 [DEBUG] 정규화 후: '{normalized[:60]}...'")
        
        self.log_info(f"🔍 [DEBUG] DB에 저장된 키 {len(self.problem_manager.quiz_answers)}개:")
        for db_key in self.problem_manager.quiz_answers:
            if db_key in normalized:
                self.log_info(f"   ✅ 부분일치 발견! (DB키 ⊂ 정규화문제): '{db_key[:60]}...'")
            elif normalized in db_key:
                self.log_info(f"   ✅ 역방향 부분일치 발견! (정규화문제 ⊂ DB키): '{db_key[:60]}...'")
                
        ans = self.problem_manager.get_answer(q_text)
        self.log_info(f"🔍 [DEBUG] get_answer 결과: {ans}")
        return ans

    def _search_answer_from_blog(self, current_index):
        """1회성 블로그 검색 수행 및 탭 정리"""
        self.log_info("로컬 DB에 정답이 없어 블로그 검색을 1회 수행합니다...")
        
        # 블로그 검색 전 현재 열린 탭 상태 저장
        initial_handles = set(self.web_automation.driver.window_handles)
        
        blog_answers_str = self.try_blog_search()
        
        # 블로그 검색에 따른 탭 정리 (새로 열린 탭만 식별)
        self._close_blog_tab_safely(initial_handles)
        
        ans = None
        if blog_answers_str and current_index < len(blog_answers_str):
            ans = blog_answers_str[current_index]
            
        return ans, blog_answers_str

    def _close_blog_tab_safely(self, initial_handles):
        """검색 목록 탭은 닫고 게시글 탭만 남기는 로직 (원래 창으로 복귀 포함)"""
        current_handles = self.web_automation.driver.window_handles
        new_handles = [h for h in current_handles if h not in initial_handles]
        
        if new_handles:
            # 새로 열린 탭 중 가장 마지막 탭(게시글 본문)을 힌트용으로 저장
            self.blog_window = new_handles[-1]
            
            # 나머지 중간 과정 탭(검색 결과 등)은 모두 닫음
            for handle in new_handles[:-1]:
                try:
                    self.web_automation.driver.switch_to.window(handle)
                    self.web_automation.driver.close()
                    self.log_info("🗑️ 블로그 검색 중간 목록 탭 닫기 완료")
                except Exception:
                    pass
        else:
            self.blog_window = None
            
        # 원래 탭으로 복귀
        try:
            self.web_automation.driver.switch_to.window(self.original_window)
        except Exception as e:
            self.log_error(f"원본 탭 복귀 실패: {str(e)}")

    def find_quiz_page(self):
        """1단계: 퀴즈가 있는 페이지 찾기"""
        try:
            self.log_info("퀴즈가 있는 페이지를 찾는 중...")
            
            # 의약품 페이지에서 시도
            if self.check_page_for_quiz(MEDICINE_PAGE_URL, "의약품"):
                return "medicine"
                
            # 기구 페이지에서 시도  
            if self.check_page_for_quiz(INSTRUMENT_PAGE_URL, "기구"):
                return "instrument"
                
            return None  # 퀴즈가 있는 페이지 없음
            
        except Exception as e:
            self.log_error(f"퀴즈 페이지 찾기 실패: {str(e)}")
            return None

    def check_page_for_quiz(self, url, page_name):
        """특정 페이지에 퀴즈가 있는지 확인"""
        try:
            self.log_info(f"{page_name} 페이지에서 퀴즈 확인 중...")
            
            # 페이지로 이동
            if not self.navigate_to_page(url, page_name):
                return False
            
            # 퀴즈 요소만 확인 (클릭하지 않음)
            if self.has_quiz_elements():
                self.log_success(f"{page_name} 페이지에서 퀴즈 발견!")
                return True
            else:
                self.log_warning(f"{page_name} 페이지에 퀴즈가 없습니다.")
                return False
                
        except Exception as e:
            self.log_error(f"{page_name} 페이지 확인 실패: {str(e)}")
            return False



    def navigate_to_page(self, url, page_name):
        """페이지로 이동하고 로딩 완료 대기"""
        try:
            self.log_info(f"🔄 {page_name} 페이지로 이동 중...")
            
            self.web_automation.driver.get(url)
            
            # 페이지 로딩 대기
            if self.wait_for_page_load():
                return True
            else:
                self.log_error(f"❌ {page_name} 페이지 로딩 시간 초과")
                return False
                
        except Exception as e:
            self.log_error(f"{page_name} 페이지 이동 실패: {str(e)}")
            return False



    def has_quiz_elements(self):
        """퀴즈 요소가 있는지 확인 (1단계용 - 클릭하지 않음)"""
        try:
            self.log_info("퀴즈 요소 확인 중...")
            
            # JavaScript를 사용하여 더 빠르게 퀴즈 요소 확인
            try:
                quiz_count = self.web_automation.driver.execute_script(
                    f"return document.querySelectorAll('{QUIZ_CSS_SELECTOR}').length;"
                )
                
                if quiz_count >= MIN_QUIZ_ELEMENTS:
                    self.log_success(f"퀴즈 요소 {quiz_count}개 발견")
                    return True
                else:
                    self.log_warning(f"퀴즈 요소 {quiz_count}개 발견 (최소 {MIN_QUIZ_ELEMENTS}개 필요)")
                    return False
                    
            except Exception as js_error:
                self.log_warning(f"JavaScript 확인 실패, 일반 방법으로 시도: {str(js_error)}")
                
                # JavaScript 실패 시 일반 방법으로 확인
                quiz_elements = self.find_elements_safe(By.CSS_SELECTOR, QUIZ_CSS_SELECTOR)
                
                if len(quiz_elements) >= MIN_QUIZ_ELEMENTS:
                    self.log_success(f"퀴즈 요소 {len(quiz_elements)}개 발견")
                    return True
                else:
                    self.log_warning(f"퀴즈 요소 {len(quiz_elements)}개 발견 (최소 {MIN_QUIZ_ELEMENTS}개 필요)")
                    return False
                
        except Exception as e:
            self.log_error(f"퀴즈 요소 확인 실패: {str(e)}")
            return False
    
    def click_quiz_element(self):
        """2단계: 퀴즈 요소 클릭 (페이지 이동)"""
        try:
            self.log_info("퀴즈 요소를 클릭하는 중...")
            
            # quiz_bg 클래스를 가진 요소들 찾기
            quiz_elements = self.find_elements_safe(By.CSS_SELECTOR, QUIZ_CSS_SELECTOR)
            
            if len(quiz_elements) >= MIN_QUIZ_ELEMENTS:
                self.log_success(f"퀴즈 요소 {len(quiz_elements)}개 발견")
                
                # 두 번째 퀴즈 요소 클릭 (페이지 이동)
                if self.click_second_quiz_element(quiz_elements[1]):
                    self.log_success("퀴즈 요소 클릭 완료 - 페이지 이동됨")
                    return True
                
                return False
            else:
                self.log_warning(f"퀴즈 요소가 {len(quiz_elements)}개 발견되었습니다. (최소 {MIN_QUIZ_ELEMENTS}개 필요)")
                return False
                
        except Exception as e:
            self.log_error(f"퀴즈 요소 클릭 실패: {str(e)}")
            return False

    def click_second_quiz_element(self, second_quiz):
        """두 번째 퀴즈 요소 클릭 (페이지 이동)"""
        try:
            # 부모 요소(링크)를 찾아서 JavaScript로 클릭
            parent_link = second_quiz.find_element(By.XPATH, "./..")
            
            # JavaScript를 사용한 클릭 (더 빠르고 안정적)
            self.web_automation.driver.execute_script("arguments[0].click();", parent_link)
            
            self.log_success("퀴즈 요소 클릭 완료 - 페이지 이동 중...")
            
            # 페이지 로딩 대기
            if not self.wait_for_page_load():
                self.log_error("페이지 로딩 시간 초과")
                return False
            return True
                
        except Exception as e:
            self.log_error(f"퀴즈 요소 클릭 실패: {str(e)}")
            return False



    def click_quiz_button(self):
        """2단계: 퀴즈 버튼 클릭 (팝업 열기)"""
        try:
            self.log_info("퀴즈 버튼을 클릭하는 중...")
            
            # 퀴즈 버튼 찾기
            quiz_button = self.find_element_safe(By.ID, QUIZ_BANNER_BUTTON_ID)
            
            if quiz_button:
                # 퀴즈 버튼 클릭
                quiz_button.click()
                self.log_success("퀴즈 버튼 클릭 완료 - 팝업창이 열렸습니다")
                return True
            else:
                self.log_error("퀴즈 버튼을 찾을 수 없습니다.")
                return False
                
        except Exception as e:
            return self.handle_general_error("퀴즈 버튼 클릭", e)



    def collect_quiz_info(self):
        """퀴즈 팝업창에서 문제와 보기 정보를 수집"""
        try:
            self.log_info("퀴즈 정보 수집 시작...")
            
            # 제품 정보 수집 (안전하게 탐색)
            product_title = self.find_element_safe(By.ID, PRODUCT_TITLE_ID).text.strip()
            product_category = self.find_element_safe(By.ID, PRODUCT_CATEGORY_ID).text.strip()
            product_title_eng = self.find_element_safe(By.ID, PRODUCT_TITLE_ENG_ID).text.strip()
            quiz_point = self.find_element_safe(By.ID, QUIZ_POINT_ID).text.strip()
            
            self.log_info(f"=== 퀴즈 정보 ===")
            self.log_info(f"제품명: {product_title}")
            self.log_info(f"카테고리: {product_category}")
            self.log_info(f"영문명: {product_title_eng}")
            self.log_info(f"포인트: {quiz_point}")
            self.log_info(f"==================")
            
            # 퀴즈 데이터 구조 생성
            quiz_data = {
                'product_info': {
                    'title': product_title,
                    'category': product_category,
                    'title_eng': product_title_eng,
                    'point': quiz_point
                },
                'questions': []
            }
            
            # 퀴즈 문제 영역 컨테이너만 사용
            try:
                quiz_container = self.find_element_safe(By.ID, QUESTION_AREA_CONTAINER_ID)
            except Exception:
                self.log_error(f"퀴즈 문제 영역(id={QUESTION_AREA_CONTAINER_ID})을 찾을 수 없습니다.")
                return None
            
            # 실제 존재하는 문제 개수 확인 (.question1, .question2, ... 순으로 확인)
            question_count = 0
            for n in range(1, 10):
                try:
                    quiz_container.find_element(By.CSS_SELECTOR, f".question{n}")
                    question_count = n
                except NoSuchElementException:
                    break
            
            if question_count == 0:
                self.log_error("존재하는 퀴즈 문제(.questionN)를 찾을 수 없습니다.")
                return None
            
            self.log_info(f"실제 퀴즈 문제 개수: {question_count}개")
            
            # 각 문제 번호(n)에 대해 해당 .question{n}을 포함한 .question_area만 수집
            for n in range(1, question_count + 1):
                try:
                    # 각 요소 수집 시 stale 에러 방지를 위해 매번 driver 기반으로 찾거나 safe 함수 활용
                    # quiz_container가 stale될 수 있으므로 driver 기반 find_element_safe 활용 권장
                    question_num_elem = self.find_element_safe(By.CSS_SELECTOR, f"#{QUESTION_AREA_CONTAINER_ID} .question{n}")
                    question_number = question_num_elem.text.strip()
                    
                    # .question{n}이 속한 .question_area 찾기
                    question_area = self.web_automation.driver.execute_script(
                        "return arguments[0].closest('.question_area');", question_num_elem
                    )
                    
                    if not question_area:
                        self.log_error(f"문제 {n}: .question_area를 찾을 수 없습니다.")
                        continue
                    
                    # q_area 내부 요소도 safe하게 찾기 위해 base_selector 구성
                    q_area_css = f"#{QUESTION_AREA_CONTAINER_ID} .question{n}"
                    parent_area_selector = f"div.question_area:has(.question{n})" # CSS :has 지원 시
                    
                    # 텍스트 및 보기 수집
                    question_text = self.web_automation.driver.execute_script(
                        f"var qElem = arguments[0].querySelector('{QUESTION_TEXT_SELECTOR}'); return qElem ? qElem.innerText.trim() : '';", question_area
                    )
                    
                    # 보기들 수집 (JS로 한 번에 가져오는 것이 가장 안전)
                    choice_data = self.web_automation.driver.execute_script(f"""
                        var choices = arguments[0].querySelectorAll('{QUESTION_CHOICE_SELECTOR}');
                        return Array.from(choices).map(c => {{
                            var label = c.querySelector('{CHOICE_LABEL_SELECTOR}');
                            var input = c.querySelector('{CHOICE_INPUT_SELECTOR}');
                            return {{
                                text: label ? label.innerText.trim() : '',
                                value: input ? input.value : ''
                            }};
                        }});
                    """, question_area)
                    
                    choice_list = [f"{c['value']}. {c['text']}" for c in choice_data]
                    choice_values = [str(c['value']) for c in choice_data]
                    
                    quiz_data['questions'].append({
                        'number': question_number,
                        'question': question_text,
                        'choices': choice_list,
                        'choice_values': choice_values
                    })
                    
                    self.log_info(f"--- {question_number} ---")
                    self.log_info(f"문제: {question_text}")
                    for choice in choice_list:
                        self.log_info(f"보기: {choice}")
                    self.log_info(f"----------------")
                        
                except Exception as e:
                    self.log_error(f"문제 {n} 수집 중 오류: {str(e)}")
                    continue
            
            return quiz_data
            
        except Exception as e:
            self.log_error(f"퀴즈 정보 수집 실패: {str(e)}")
            return None

    def select_single_answer(self, question, answer):
        """특정 문제 하나에 대한 정답 선택 (번호 및 텍스트 매핑 지원)"""
        try:
            # 🔥 0. 항상 닥터빌 메인 탭으로 전환 후 시작
            if self.original_window:
                self.web_automation.driver.switch_to.window(self.original_window)
            
            # 🔥 1. 퀴즈 팝업이 아직 열려있는지 확인
            try:
                quiz_popup = self.web_automation.driver.find_element(By.ID, QUIZ_LAYER_POP_ID)
                if not quiz_popup.is_displayed():
                    self.log_warning("퀴즈 팝업이 숨겨져 있습니다. 다시 표시 시도...")
                    self.web_automation.driver.execute_script(
                        "arguments[0].style.display = 'block';", quiz_popup
                    )
                    time.sleep(0.5)
            except:
                self.log_warning("퀴즈 팝업 상태 확인 실패 - 계속 진행합니다.")
                
            question_num = question['number']
            
            # 입력값 정규화
            clean_input = str(answer).strip()
            
            # DB 세부 정보 로드
            q_details = self.problem_manager.get_question_details(question['question'])
            answer_num_val = q_details.get("answer_num", "") if q_details else ""
            
            # 헬퍼 함수: 보기 번호(value)에 해당하는 텍스트 가져오기
            def get_choice_text_by_value(q_info, val):
                if 'choices' in q_info and 'choice_values' in q_info:
                    for ch, ch_val in zip(q_info['choices'], q_info['choice_values']):
                        if str(ch_val).strip() == str(val).strip():
                            parts = ch.split('. ', 1)
                            return parts[1].strip() if len(parts) > 1 else ch.strip()
                return None

            # 헬퍼 함수: 보기 텍스트에 매칭되는 번호(value) 가져오기
            def get_choice_value_by_text(q_info, txt):
                if 'choices' in q_info and 'choice_values' in q_info:
                    txt_lower = txt.lower().strip()
                    for ch, ch_val in zip(q_info['choices'], q_info['choice_values']):
                        parts = ch.split('. ', 1)
                        ch_text = parts[1].strip().lower() if len(parts) > 1 else ch.strip().lower()
                        if txt_lower in ch_text or ch_text in txt_lower:
                            return ch_val
                return None

            correct_val = None
            
            # 1. 텍스트 우선 매칭 (clean_input이 숫자가 아닌 경우)
            if not clean_input.isdigit():
                matched_val = get_choice_value_by_text(question, clean_input)
                if matched_val:
                    self.log_success(f"정답 텍스트 '{clean_input}'에 매칭되는 보기 번호 발견: '{matched_val}'")
                    correct_val = matched_val
            
            # 2. 텍스트 매칭에 실패했거나 정답이 숫자인 경우, 정답 번호 기반 Fallback 실행
            if not correct_val:
                target_num = clean_input if clean_input.isdigit() else answer_num_val
                if target_num and target_num.isdigit():
                    choice_text = get_choice_text_by_value(question, target_num)
                    if choice_text:
                        self.log_success(f"정답 번호 '{target_num}'에 매칭되는 보기 텍스트 '{choice_text}'를 획득하여 DB에 자동 업데이트합니다.")
                        matched_q = self.problem_manager.get_matched_question(question['question'])
                        self.problem_manager.add_quiz(matched_q, choice_text, "", answer_num=target_num)
                    correct_val = target_num
            
            # 3. 최후의 수단 (매핑 테이블 활용)
            if not correct_val:
                clean_upper = clean_input.upper()
                correct_val = ANSWER_MAPPING.get(clean_upper, clean_upper)
                if correct_val not in VALID_ANSWER_VALUES:
                    try:
                        correct_val = str(int(float(clean_upper)))
                    except (ValueError, TypeError):
                        pass
            
            # 4. 라디오 버튼 선택 (JS 완전 제어 - 팝업 내부 요소 대응)
            try:
                # 팝업 자체가 사라졌는지 재검사
                if not self.wait_for_condition_safe(lambda: self.find_element_safe(By.ID, QUIZ_LAYER_POP_ID).is_displayed()):
                    self.log_error("퀴즈 팝업이 사라졌습니다.")
                    return False

                num_only = "".join(filter(str.isdigit, question_num))
                radio_selector = f"input[name='an_{num_only}'][value='{correct_val}']"
                self.log_info(f"🔍 셀렉터: {radio_selector}")
                
                # 🔥 순수 JS로 모든 작업 수행 (Selenium 클릭 우회) 헬퍼 메서드로 분리
                click_result = self._inject_radio_click_js(radio_selector)
                
                self.log_info(f"🔍 클릭 결과: {click_result}")
                
                if click_result and 'FAILED' not in click_result and 'NOT_FOUND' not in click_result:
                    return True
                else:
                    self.log_error(f"라디오 버튼 선택 실패: {click_result}")
                    return False
            except Exception as e:
                self.log_error(f"라디오 버튼(값:{correct_val}) 오류: {str(e)}")
                return False
        except Exception as e:
            self.log_error(f"단일 답안 선택 로직 오류: {str(e)}")
            return False

    def _inject_radio_click_js(self, radio_selector):
        """라디오 버튼 강제 클릭을 위한 순수 JavaScript 헬퍼 메서드"""
        js_code = """
            var radio = document.querySelector(arguments[0]);
            if (!radio) return 'RADIO_NOT_FOUND';
            
            // 🔥 이미 체크되어 있다면 중복 클릭 방지
            if (radio.checked) return 'ALREADY_CHECKED';
            
            // 방법 1: 부모 li 안의 label을 JS 클릭
            var li = radio.closest('li');
            if (li) {
                var label = li.querySelector('label');
                if (label) {
                    label.click();
                    if (radio.checked) return 'LABEL_CLICK_OK';
                }
            }
            
            // 방법 2: label[for=id] 클릭
            if (radio.id) {
                var forLabel = document.querySelector("label[for='" + radio.id + "']");
                if (forLabel) {
                    forLabel.click();
                    if (radio.checked) return 'FOR_LABEL_CLICK_OK';
                }
            }
            
            // 방법 3: 강제 체크 + change 이벤트
            radio.checked = true;
            radio.dispatchEvent(new Event('change', {bubbles: true}));
            radio.dispatchEvent(new Event('click', {bubbles: true}));
            return radio.checked ? 'FORCE_CHECK_OK' : 'FAILED';
        """
        return self.web_automation.driver.execute_script(js_code, radio_selector)


    def click_submit_button(self):
        """정답 도전 버튼 클릭"""
        try:
            self.log_info("정답 도전 버튼을 찾는 중...")
            
            # 정답 도전 버튼 찾기
            submit_button = self.find_element_safe(By.ID, ANSWER_CONFIRM_BUTTON_ID)
            
            if submit_button:
                # 정답 도전 버튼 클릭
                submit_button.click()
                self.log_success("정답 도전 버튼 클릭 완료")
                
                # 결과 처리 대기
                time.sleep(2)
                return True
            else:
                self.log_error("정답 도전 버튼을 찾을 수 없습니다.")
                return False
                
        except Exception as e:
            return self.handle_general_error("정답 도전 버튼 클릭", e)



    def save_to_local_db(self, quiz_data, extracted_answer):
        """새로 알아낸 정답을 로컬 DB에 자동 저장 (학습)"""
        try:
            self.log_info("새로운 퀴즈 정보를 로컬 DB에 학습시키는 중...")
            answer_chars = list(extracted_answer)
            product_title = quiz_data['product_info']['title'] # 카테고리로 제품명 사용
            
            saved_count = 0
            for i, question_info in enumerate(quiz_data['questions']):
                if i < len(answer_chars):
                    q_text = question_info['question']
                    ans = answer_chars[i]
                    ans_num = ans if ans.isdigit() else ""
                    
                    # 만약 ans가 숫자이고, 보기에서 매칭되는 텍스트가 있다면 텍스트로 저장
                    if ans.isdigit() and 'choices' in question_info and 'choice_values' in question_info:
                        for ch, ch_val in zip(question_info['choices'], question_info['choice_values']):
                            if str(ch_val).strip() == str(ans).strip():
                                parts = ch.split('. ', 1)
                                option_text = parts[1].strip() if len(parts) > 1 else ch.strip()
                                if option_text:
                                    ans = option_text
                                break
                                
                    # SurveyProblemManager에 추가 (파일 자동 저장 포함됨)
                    matched_q = self.problem_manager.get_matched_question(q_text)
                    if self.problem_manager.add_quiz(matched_q, ans, product_title, answer_num=ans_num):
                        saved_count += 1
            
            if saved_count > 0:
                self.log_success(f"{saved_count}개의 새로운 퀴즈 데이터를 로컬 DB에 저장했습니다.")
                return True
            return False
        except Exception as e:
            self.log_error(f"로컬 DB 저장 중 오류: {str(e)}")
            return False

    def prompt_single_question_intervention(self, quiz_data, question_index):
        """특정 문제 하나에 대해 수동 개입 유도 (단순 대기 방식)"""
        try:
            q_info = quiz_data['questions'][question_index]
            q_text = q_info['question']
            prod_title = quiz_data['product_info']['title']
            
            # 1. GUI 호출 (이미지 없이 정보만 전달)
            if 'on_quiz_problem' in self.gui_callbacks:
                self.gui_callbacks['on_quiz_problem'](
                    initial_question=q_text,
                    initial_category=prod_title,
                    image_path=None  # 이미지 경로 제거
                )
                self.log_info(f"❓ 문제 {question_index+1} 정답을 입력창에 입력해 주세요.")
                
                # 2. 동기식 실시간 루프 대기
                self.log_info(f"⌛ 정답 등록 대기 중... (최대 10분)")
                waiting_seconds = 0
                max_wait = 600
                
                while waiting_seconds < max_wait:
                    # 🔥 사용자의 작업 중지(취소) 요청 시 루프 강제 탈출 (Graceful Exit)
                    if hasattr(self.web_automation, 'is_running') and not self.web_automation.is_running:
                        self.log_warning("작업 중지 신호 감지: 대기를 강제 종료합니다.")
                        return False

                    try: _ = self.web_automation.driver.title
                    except: return False

                    self.problem_manager.load_quizzes()
                    if self.problem_manager.get_answer(q_text):
                        self.log_success(f"새로운 정답 확인완료 ({waiting_seconds}초 대기함)")
                        return True
                        
                    time.sleep(1.0)
                    waiting_seconds += 1
                
                self.log_warning(f"입력 대기 시간({max_wait}초)이 초과되었습니다.")
            else:
                self.log_error("GUI 콜백(on_quiz_problem) 누락")
                
        except Exception as e:
            self.log_error(f"수동 개입 유도 오류: {str(e)}")
        return False


    def open_quiz_popup(self):
        """2단계: 퀴즈 팝업 열기"""
        try:
            self.log_info("퀴즈 팝업을 여는 중...")
            
            # 1. 퀴즈 요소 클릭 (페이지 이동)
            if not self.click_quiz_element():
                return False
            
            # 2. 새 페이지에서 퀴즈 버튼 찾기
            if not self.wait_for_quiz_button():
                return False
            
            # 3. 퀴즈 버튼 클릭 (팝업 열기)
            if not self.click_quiz_button():
                return False
            
            self.log_success("퀴즈 팝업 열기 완료!")
            return True
            
        except Exception as e:
            self.log_error(f"퀴즈 팝업 열기 실패: {str(e)}")
            return False

    def wait_for_quiz_button(self):
        """새 페이지에서 퀴즈 버튼이 나타날 때까지 대기"""
        try:
            self.log_info("새 페이지에서 퀴즈 버튼을 찾는 중...")
            
            # 페이지 로딩 대기
            if not self.wait_for_page_load():
                self.log_error("페이지 로딩 시간 초과")
                return False
            
            # 퀴즈 버튼이 나타날 때까지 대기
            if not self.wait_for_element_presence(QUIZ_BANNER_BUTTON_ID):
                self.log_error("퀴즈 버튼을 찾을 수 없습니다")
                return False
            
            self.log_success("퀴즈 버튼 발견!")
            return True
            
        except Exception as e:
            self.log_error(f"퀴즈 버튼 대기 실패: {str(e)}")
            return False



    def try_blog_search(self):
        """블로그 검색 모듈 안전하게 실행"""
        try:
            # 블로그 검색 모듈 임포트 시도
            try:
                from modules.blog_search_module import BlogSearchModule
            except ImportError as import_error:
                self.log_error(f"블로그 검색 모듈 임포트 실패: {import_error}")
                return None
            
            # 블로그 검색 모듈 초기화 시도
            try:
                blog_search_module = BlogSearchModule(self.web_automation, self.gui_logger)
            except Exception as init_error:
                self.log_error(f"블로그 검색 모듈 초기화 실패: {init_error}")
                return None
            
            # 블로그 검색 실행 시도
            try:
                result = blog_search_module.execute()
                
                is_success = False
                if isinstance(result, dict):
                    is_success = result.get('success', False)
                else:
                    is_success = bool(result)

                if is_success:
                    answer = blog_search_module.get_extracted_answer()
                    if answer:
                        return answer
                    else:
                        self.log_warning("블로그 검색 완료되었지만 정답을 추출하지 못했습니다")
                        return None
                else:
                    msg = result.get('message', '블로그 검색 실행 실패') if isinstance(result, dict) else '블로그 검색 실행 실패'
                    self.log_warning(msg)
                    return None
                    
            except Exception as exec_error:
                self.log_error(f"블로그 검색 실행 중 오류: {exec_error}")
                return None
                
        except Exception as e:
            self.log_error(f"블로그 검색 전체 실패: {str(e)}")
            return None

