# -*- coding: utf-8 -*-
"""
웹 자동화 기본 클래스
Chrome 웹드라이버를 설정하고 관리합니다.
"""

import sys
import os
import logging
import locale
from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from webdriver_manager.chrome import ChromeDriverManager
import shutil
import json

# 브라우저 설정
BROWSER_CONFIG = {
    'headless': False,  # False: 브라우저 창 표시, True: 백그라운드 실행
    'window_size': (1200, 800),
    'implicit_wait': 2,  # 최적화: 10초 → 5초 → 2초
    'page_load_timeout': 15  # 최적화: 30초 → 15초
}

class WebAutomation:
    def __init__(self, headless=None):
        self.driver = None
        self.wait = None
        self._hwnd = None
        self._browser_process_id = None
        self.logger = self._setup_logger()
        
        # 설정 로드
        self.headless = headless
        if self.headless is None:
            self.headless = self._load_headless_setting()
        
        # BROWSER_CONFIG 업데이트
        BROWSER_CONFIG['headless'] = self.headless

    def _load_headless_setting(self):
        """환경설정 파일에서 headless 설정을 로드합니다."""
        try:
            # 1. 공통 설정 파일 확인 (data/settings.json, 절대 경로 사용)
            base_dir = os.path.dirname(os.path.abspath(__file__))
            settings_path = os.path.join(base_dir, "data", "settings.json")
            if os.path.exists(settings_path):
                with open(settings_path, 'r', encoding='utf-8') as f:
                    settings = json.load(f)
                return settings.get('browser_headless', False)

            # 2. 로컬 settings.json 확인 (독립 실행 방식)
            settings_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "settings.json")
            if os.path.exists(settings_path):
                with open(settings_path, 'r', encoding='utf-8') as f:
                    settings = json.load(f)
                return settings.get('browser_headless', False)
        except Exception as e:
            if hasattr(self, 'logger'):
                self.logger.warning(f"설정 로드 중 오류 발생 (기본값 False 사용): {e}")
        return False
        
    def _setup_logger(self):
        """로거 설정 - 상세 정보는 파일에만 남음"""
        return logging.getLogger(__name__)

    def setup_driver(self):
        """Chrome 웹드라이버 설정 (로컬 우선, 실패 시 자동 업데이트)"""
        # 1단계: 로컬 chromedriver로 시도
        try:
            return self._try_local_chromedriver()
        except Exception as e:
            error_msg = str(e)
            
            # 버전 오류 또는 파일 없음 확인
            need_update = False
            if "This version of ChromeDriver only supports Chrome version" in error_msg:
                self.logger.warning("ChromeDriver 버전 불일치 감지 - 자동 업데이트 시작...")
                need_update = True
            elif "Unable to obtain driver" in error_msg:
                self.logger.warning("ChromeDriver 파일 없음 감지 - 자동 다운로드 시작...")
                need_update = True
            elif "chromedriver" in error_msg.lower() and (
                "cannot find" in error_msg.lower()
                or "no such file" in error_msg.lower()
                or "does not exist" in error_msg.lower()
                or "not found" in error_msg.lower()
                or "executable needs to be in path" in error_msg.lower()
                or "filenotfounderror" in error_msg.lower()
            ):
                self.logger.warning("ChromeDriver 파일 없음 감지 - 자동 다운로드 시작...")
                need_update = True
            elif not os.path.exists(os.path.join(os.path.dirname(os.path.abspath(__file__)), "chromedriver.exe")):
                self.logger.warning("chromedriver.exe 파일이 없습니다 - 자동 다운로드 시작...")
                need_update = True
            
            if need_update:
                # 2단계: webdriver-manager로 최신 버전 다운로드 & 교체
                if self._update_chromedriver():
                    self.logger.info("ChromeDriver 업데이트 완료 - 재시도 중...")
                    
                    # 3단계: 업데이트된 로컬 파일로 재시도
                    try:
                        result = self._try_local_chromedriver()
                        
                        # 성공 시 백업 파일 삭제
                        if result:
                            self._cleanup_old_chromedriver()
                        
                        return result
                    except Exception as retry_error:
                        self.logger.error(f"업데이트 후 재시도 실패: {str(retry_error)}")
                        return False
            
            self.logger.error(f"웹드라이버 설정 실패: {error_msg}")
            return False
    
    def _try_local_chromedriver(self):
        """로컬 chromedriver.exe로 실행 시도"""
        chrome_options = Options()
        
        # 브라우저 설정 적용 (인스턴스 설정 사용)
        if self.headless:
            chrome_options.add_argument('--headless')
        
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--window-size={},{}'.format(*BROWSER_CONFIG['window_size']))
        chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
        
        # 다운로드 폴더 설정 (modules 폴더로)
        current_dir = os.path.dirname(os.path.abspath(__file__))
        modules_dir = os.path.join(current_dir, "modules")
        chrome_options.add_experimental_option("prefs", {
            "download.default_directory": modules_dir,
            "download.prompt_for_download": False,
            "download.directory_upgrade": True,
            # Chrome의 유출된 비밀번호 경고가 자동화 화면을 가리는 것을 방지합니다.
            # 안전 브라우징은 계속 켜 둔 채 비밀번호 관리자와 유출 감지만 비활성화합니다.
            "credentials_enable_service": False,
            "profile.password_manager_enabled": False,
            "profile.password_manager_leak_detection": False,
            "safebrowsing.enabled": True
        })
        
        # 로커 파일 핸들러 제거 (Root Logger가 처리)
        # 로컬 ChromeDriver 사용
        chromedriver_path = os.path.join(current_dir, "chromedriver.exe")
        
        # 파일 존재 여부 먼저 확인
        if not os.path.exists(chromedriver_path):
            raise FileNotFoundError(f"chromedriver.exe not found: {chromedriver_path}")
        
        service = Service(chromedriver_path)
        
        # 웹드라이버 생성
        self.driver = webdriver.Chrome(service=service, options=chrome_options)
        self.driver.implicitly_wait(BROWSER_CONFIG['implicit_wait'])
        self.driver.set_page_load_timeout(BROWSER_CONFIG['page_load_timeout'])
        
        # 💡 브라우저 핸들(HWND) 캡처 (가시성 제어용)
        self._hwnd = self._find_browser_hwnd()
        
        # WebDriverWait 설정
        self.wait = WebDriverWait(self.driver, 3)
        
        self.logger.debug("웹드라이버가 성공적으로 설정되었습니다.")
        return True
    
    def _update_chromedriver(self):
        """webdriver-manager로 최신 chromedriver 다운로드 후 교체"""
        try:
            self.logger.info("최신 ChromeDriver 다운로드 중...")
            
            # webdriver-manager로 최신 버전 다운로드
            latest_driver_path = ChromeDriverManager().install()
            
            # 실제 chromedriver.exe 파일 찾기
            # webdriver-manager가 반환하는 경로는 디렉토리이거나 잘못된 파일일 수 있음
            driver_dir = os.path.dirname(latest_driver_path)
            actual_driver_path = None
            
            # chromedriver.exe 파일 찾기
            for root, dirs, files in os.walk(driver_dir):
                for file in files:
                    if file.lower() == "chromedriver.exe":
                        actual_driver_path = os.path.join(root, file)
                        break
                if actual_driver_path:
                    break
            
            if not actual_driver_path or not os.path.exists(actual_driver_path):
                self.logger.error("다운로드된 chromedriver.exe 파일을 찾을 수 없습니다.")
                return False
            
            # 현재 디렉토리의 chromedriver.exe 경로
            current_dir = os.path.dirname(os.path.abspath(__file__))
            local_chromedriver_path = os.path.join(current_dir, "chromedriver.exe")
            
            # 기존 파일 백업 (있으면)
            if os.path.exists(local_chromedriver_path):
                backup_path = os.path.join(current_dir, "chromedriver_old.exe")
                if os.path.exists(backup_path):
                    os.remove(backup_path)
                os.rename(local_chromedriver_path, backup_path)
                self.logger.info("기존 ChromeDriver 백업 완료")
            
            # 다운로드된 파일을 로컬로 복사
            shutil.copy2(actual_driver_path, local_chromedriver_path)
            self.logger.info(f"ChromeDriver 업데이트 완료! ({actual_driver_path})")
            
            return True
            
        except Exception as e:
            self.logger.error(f"ChromeDriver 업데이트 실패: {str(e)}")
            return False
    
    def _cleanup_old_chromedriver(self):
        """백업된 구 버전 chromedriver 삭제"""
        try:
            current_dir = os.path.dirname(os.path.abspath(__file__))
            backup_path = os.path.join(current_dir, "chromedriver_old.exe")
            
            if os.path.exists(backup_path):
                os.remove(backup_path)
                self.logger.info("구 버전 ChromeDriver 삭제 완료")
        except Exception as e:
            self.logger.warning(f"구 버전 ChromeDriver 삭제 실패 (무시 가능): {str(e)}")
    
    def get_current_url(self):
        """현재 URL 반환"""
        if self.driver:
            return self.driver.current_url
        return None
    
    def get_page_title(self):
        """현재 페이지 제목 반환"""
        if self.driver:
            return self.driver.title
        return None
    
    def is_alive(self):
        """브라우저가 열려있는지 확인"""
        try:
            if not self.driver:
                return False
                
            # 1. 살아있는 전체 윈도우 핸들 목록 획득
            try:
                handles = self.driver.window_handles
            except Exception:
                # handles 조차 가져오지 못하면 브라우저 프로세스가 완전히 죽은 것임
                return False
                
            if not handles:
                return False
                
            # 2. 현재 바라보고 있는 핸들이 실제 살아있는 목록에 존재하는지 대조 및 복구
            try:
                current_handle = self.driver.current_window_handle
                if current_handle not in handles:
                    # 닫혀버린 유령 창이므로 첫 번째 살아있는 탭으로 즉시 전환 복구
                    self.driver.switch_to.window(handles[0])
                    self.logger.info("바라보던 창이 닫혀있음을 감지하여 첫 번째 메인 탭으로 포커스를 복구했습니다.")
            except Exception:
                # current_window_handle 호출 시 예외가 발생한 경우도 강제 복구 시도
                try:
                    self.driver.switch_to.window(handles[0])
                    self.logger.info("닫힌 탭 예외를 감지하여 첫 번째 메인 탭으로 포커스를 복구했습니다.")
                except:
                    return False
            
            # 3. 최종 생존 상태 검사
            _ = self.driver.current_url
            return True
        except Exception:
            return False
    
    def close_driver(self):
        """웹드라이버 종료"""
        try:
            if self.driver:
                self.driver.quit()
                self.driver = None
        except Exception as e:
            self.logger.error(f"드라이버 종료 중 오류 발생: {str(e)}")
            
    def close_other_windows(self, keep_window_handle):
        """지정된 윈도우 핸들을 제외한 모든 창을 닫습니다."""
        try:
            if not self.driver:
                return
                
            all_windows = self.driver.window_handles
            for window in all_windows:
                if window != keep_window_handle:
                    try:
                        self.driver.switch_to.window(window)
                        self.driver.close()
                    except Exception as e:
                        self.logger.error(f"창 닫기 실패: {str(e)}")
                        
            # 다시 메인 창으로 포커스
            self.driver.switch_to.window(keep_window_handle)
        except Exception as e:
            self.logger.error(f"창 정리 중 오류: {str(e)}")

    def _get_window_process_id(self, hwnd):
        """Windows 李??몃뱾???뚯쑀 ?꾨줈?몄뒪 ID瑜?諛섑솚?⑸땲??"""
        if not hwnd:
            return None
        try:
            import ctypes
            from ctypes import wintypes
            process_id = wintypes.DWORD()
            ctypes.windll.user32.GetWindowThreadProcessId(hwnd, ctypes.byref(process_id))
            return process_id.value or None
        except Exception:
            return None

    def _is_valid_browser_hwnd(self, hwnd):
        """?꾩옱 WebDriver媛 ?앹꽦??Chrome 李쎌씤吏 ?덉쟾?섍쾶 寃利앺빀?덈떎."""
        if not hwnd:
            return False
        try:
            import ctypes
            if not ctypes.windll.user32.IsWindow(hwnd):
                return False
            if self._browser_process_id:
                return self._get_window_process_id(hwnd) == self._browser_process_id
            return False
        except Exception:
            return False

    def _find_browser_hwnd(self):
        """?꾩옱 WebDriver??Chrome 李??몃뱾???덉쟾?섍쾶 李얠븘 諛섑솚?⑸땲??"""
        if not self.driver or self.headless:
            return None

        try:
            import ctypes
            import time
            import uuid

            original_title = "DoctorVille"
            try:
                original_title = self.driver.title
            except Exception:
                pass

            # ?몄뒪?댁뒪留덈떎 異⑸룎?섏? ?딅뒗 ?좏겙???꾩옱 ???쒕ぉ???좎떆 諛섏쁺?⑸땲??
            unique_mark = f"DVA_{uuid.uuid4().hex}"
            try:
                self.driver.execute_script(
                    f"document.title = {json.dumps(unique_mark)}"
                )
            except Exception as e:
                self.logger.warning(f"釉뚮씪?곗? 李??앸퀎???쒕ぉ ?ㅼ젙 ?ㅽ뙣: {e}")
                return None

            try:
                time.sleep(0.5)
                found_hwnd = [0]
                WNDENUMPROC = ctypes.WINFUNCTYPE(
                    ctypes.c_bool, ctypes.c_int, ctypes.c_void_p
                )

                def enum_callback(hwnd, l_param):
                    length = ctypes.windll.user32.GetWindowTextLengthW(hwnd)
                    if length <= 0:
                        return True
                    title_buffer = ctypes.create_unicode_buffer(length + 1)
                    ctypes.windll.user32.GetWindowTextW(
                        hwnd, title_buffer, length + 1
                    )
                    if unique_mark not in title_buffer.value:
                        return True

                    found_hwnd[0] = hwnd
                    return False

                ctypes.windll.user32.EnumWindows(WNDENUMPROC(enum_callback), 0)
            finally:
                # ?쒕ぉ 蹂듦뎄???ㅽ뙣?섎뜑?쇰룄 ?ㅻⅨ 怨꾩젙??李쎌쓣 ????좏깮?섏? ?딆뒿?덈떎.
                try:
                    self.driver.execute_script(
                        f"document.title = {json.dumps(original_title)}"
                    )
                except Exception:
                    pass

            if found_hwnd[0]:
                self._browser_process_id = self._get_window_process_id(found_hwnd[0])
                self.logger.info(
                    "釉뚮씪?곗? 李??몃뱾 ?띾뱷 ?깃났 "
                    f"(HWND: {found_hwnd[0]}, PID: {self._browser_process_id})"
                )
                return found_hwnd[0]

            self.logger.warning(
                "?꾩옱 ?먮룞???몄뒪?댁뒪??Chrome 李쎌쓣 寃利앺븯吏 紐삵뻽?듬땲?? "
                "?ㅻⅨ Chrome 李쎌? ?쒖뼱?섏? ?딆뒿?덈떎."
            )
            return None
        except Exception as e:
            if hasattr(self, 'logger'):
                self.logger.error(f"釉뚮씪?곗? 李??몃뱾 李얘린 以??덉쇅 諛쒖깮: {e}")
            return None

    def set_visibility(self, visible):
        """?꾩옱 ?먮룞???몄뒪?댁뒪媛 ?뚯쑀??Chrome 李쎈쭔 ?④린嫄곕굹 ?쒖떆?⑸땲??"""
        if self.headless or not self.driver:
            return False

        try:
            import ctypes
            import time

            # 湲곗〈 ?몃뱾???좏슚?섏? ?딄굅???ㅻⅨ ?꾨줈?몄뒪 ?뚯쑀?대㈃ ?덉쟾?섍쾶 ?ㅼ떆 李얠뒿?덈떎.
            if not self._is_valid_browser_hwnd(self._hwnd):
                self._hwnd = None
                for attempt in range(3):
                    self._hwnd = self._find_browser_hwnd()
                    if self._is_valid_browser_hwnd(self._hwnd):
                        break
                    self._hwnd = None
                    if attempt < 2:
                        time.sleep(0.25)

            if not self._hwnd:
                self.logger.warning(
                    "?꾩옱 怨꾩젙??Chrome 李쎌쓣 ?뺤씤?섏? 紐삵빐 李??곹깭瑜?諛붽씀吏 ?딆뒿?덈떎."
                )
                return False

            sw_cmd = 5 if visible else 0  # SW_SHOW / SW_HIDE
            ctypes.windll.user32.ShowWindow(self._hwnd, sw_cmd)
            if visible:
                ctypes.windll.user32.SetForegroundWindow(self._hwnd)

            state_str = "蹂댁엫" if visible else "?④?"
            self.logger.info(
                "寃利앸맂 Chrome 李??곹깭 蹂寃? "
                f"{state_str} (HWND: {self._hwnd}, PID: {self._browser_process_id})"
            )
            return True
        except Exception as e:
            self.logger.error(f"釉뚮씪?곗? 媛?쒖꽦 ?쒖뼱 ?ㅻ쪟: {e}")
            return False
