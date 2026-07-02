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

    def _find_browser_hwnd(self):
        """브라우저의 Win32 HWND를 찾아 반환합니다."""
        if not self.driver or self.headless:
            return None
        
        try:
            import ctypes
            import time
            
            # 브라우저 제목을 일시적으로 고유하게 변경
            original_title = "DoctorVille" # 기본값
            try: original_title = self.driver.title
            except: pass
            
            unique_mark = f"DVA_{int(time.time()*1000)}"
            try:
                self.driver.execute_script(f"document.title = '{unique_mark}'")
            except:
                return None
            
            time.sleep(0.5) # 제목 반영 대기
            
            found_hwnd = [0]
            
            # EnumWindows를 사용하여 모든 창을 순회하며 제목에 unique_mark가 포함된 창 찾기
            WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_int, ctypes.c_void_p)
            
            def enum_callback(hwnd, lParam):
                length = ctypes.windll.user32.GetWindowTextLengthW(hwnd)
                if length > 0:
                    buff = ctypes.create_unicode_buffer(length + 1)
                    ctypes.windll.user32.GetWindowTextW(hwnd, buff, length + 1)
                    if unique_mark in buff.value:
                        found_hwnd[0] = hwnd
                        return False # 찾았으므로 중단
                return True
            
            ctypes.windll.user32.EnumWindows(WNDENUMPROC(enum_callback), 0)
            
            # 원래 제목 복구 (실패해도 무관)
            try:
                self.driver.execute_script(f"document.title = {json.dumps(original_title)}")
            except:
                pass
            
            if found_hwnd[0]:
                self.logger.info(f"✅ 브라우저 핸들 획득 성공 (HWND: {found_hwnd[0]})")
                return found_hwnd[0]
            else:
                # 💡 마지막 수단: 현재 포커스된 창이 Chrome 계열인지 확인 (방금 띄웠을 가능성 높음)
                hwnd = ctypes.windll.user32.GetForegroundWindow()
                length = ctypes.windll.user32.GetWindowTextLengthW(hwnd)
                if length > 0:
                    buff = ctypes.create_unicode_buffer(length + 1)
                    ctypes.windll.user32.GetWindowTextW(hwnd, buff, length + 1)
                    if "Chrome" in buff.value or "닥터빌" in buff.value:
                        self.logger.info(f"✅ 포커스된 창으로 핸들 획득 (HWND: {hwnd})")
                        return hwnd
                
                self.logger.warning("⚠️ 브라우저 핸들을 찾을 수 없습니다.")
            return None
        except Exception as e:
            if hasattr(self, 'logger'):
                self.logger.error(f"❌ 브라우저 핸들 찾기 중 예외 발생: {e}")
            return None

    def set_visibility(self, visible):
        """브라우저 창의 가시성을 제어합니다 (Hide/Show)"""
        if self.headless or not self.driver:
            return
            
        try:
            import ctypes
            # 핸들이 없으면 다시 찾기 시도
            if not hasattr(self, '_hwnd') or not self._hwnd:
                self._hwnd = self._find_browser_hwnd()
            
            if self._hwnd:
                # 💡 ShowWindow를 더 확실하게 먹이기 위해 추가 명령 사용
                sw_cmd = 5 if visible else 0 # 5: SW_SHOW, 0: SW_HIDE
                
                # 가끔 한 번에 안 먹히는 경우가 있어 두 번 호출하거나 관련 API 함께 사용
                ctypes.windll.user32.ShowWindow(self._hwnd, sw_cmd)
                
                # 나타날 때 포커스도 함께 주기
                if visible:
                    ctypes.windll.user32.SetForegroundWindow(self._hwnd)
                    
                state_str = "보임" if visible else "숨김"
                self.logger.info(f"🖥️ 브라우저 창 상태 변경: {state_str}")
            else:
                self.logger.warning("⚠️ 브라우저 핸들이 없어 가시성을 제어할 수 없습니다.")
        except Exception as e:
            self.logger.error(f"❌ 브라우저 가시성 제어 오류: {e}")
