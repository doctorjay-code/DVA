#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
닥터빌 프로그램 자동 업데이트 도구
GitHub에서 최신 파일들을 다운로드하여 프로그램을 업데이트합니다.
개인 파일들(.bat, .exe, .ini, .log, .json)은 보존합니다.
"""

import os
import sys
import shutil
import requests
import zipfile
import json
import tkinter as tk
from tkinter import messagebox, ttk
from pathlib import Path
from datetime import datetime
import threading

class UpdateGUI:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("닥터빌 업데이트")
        self.root.geometry("400x200")
        self.progress_window = None
        
    def show_update_dialog(self):
        """업데이트 확인 팝업"""
        result = messagebox.askyesno(
            "업데이트 확인", 
            "닥터빌 프로그램을 최신 버전으로 업데이트하시겠습니까?"
        )
        return result
    
    def show_progress(self):
        """업데이트 진행 중 창"""
        self.progress_window = tk.Toplevel()
        self.progress_window.title("업데이트 중")
        self.progress_window.geometry("300x100")
        self.progress_window.resizable(False, False)
        
        # 중앙에 배치
        self.progress_window.transient(self.root)
        self.progress_window.grab_set()
        
        tk.Label(self.progress_window, text="업데이트 중입니다...", font=("맑은 고딕", 12)).pack(pady=20)
        
        # 프로그레스 바
        self.progress = ttk.Progressbar(self.progress_window, mode='indeterminate')
        self.progress.pack(pady=10, padx=20, fill='x')
        self.progress.start()
        
        self.progress_window.update()
    
    def close_progress(self):
        """진행 중 창 닫기"""
        if self.progress_window:
            self.progress_window.destroy()
            self.progress_window = None
    
    def show_complete(self, success):
        """완료 메시지"""
        if success:
            messagebox.showinfo("완료", "업데이트가 완료되었습니다!")
        else:
            messagebox.showerror("실패", "업데이트에 실패했습니다.")
    
    def run(self, auto_mode=False):
        """GUI 실행"""
        self.root.withdraw()  # 메인 창 숨기기
        
        # 업데이트 확인 (auto_mode일 경우 동의 대화상자 건너뜀)
        if auto_mode or self.show_update_dialog():
            # 진행 중 창 표시
            self.show_progress()
            
            # 백그라운드에서 업데이트 실행
            updater = DoctorBillUpdater()
            success = updater.run_update()
            
            # 진행 중 창 닫기
            self.close_progress()
            
            # 완료 메시지
            self.show_complete(success)
            
            # 💡 성공 시 메인 프로그램 자동 재시작
            if success:
                updater.relaunch_main_program()
        
        self.root.destroy()

class DoctorBillUpdater:
    def __init__(self):
        # update_program.py가 scripts 폴더에 있으므로, 부모의 부모 폴더(루트)를 기준으로 설정
        self.current_dir = Path(__file__).parent.parent
        self.backup_dir = self.current_dir / "backup_temp"
        self.github_repo = "https://api.github.com/repos/doctorjay-code/DVA"
        self.github_download = "https://github.com/doctorjay-code/DVA/archive/main.zip"
        
        # 보존할 파일 확장자들
        self.preserve_extensions = ['.bat', '.exe', '.ini', '.log', '.json']
        
        # 시작 시 기존 백업 폴더 정리 (오류 발생해도 무시)
        self._cleanup_backup_initial()
        
        # 업데이트할 파일/폴더들
        self.update_targets = [
            'main.py',
            'main_task_manager.py', 
            'web_automation.py',
            'modules/',
            'ui/',
            'docs/',
            'data/',
            'scripts/',
            'README.md',
            'chromedriver.exe',
            '.gitignore'
        ]
    
    def print_status(self, message):
        """상태 메시지 출력"""
        print(f"[{datetime.now().strftime('%H:%M:%S')}] {message}")
        
    def relaunch_main_program(self):
        """업데이트 완료 후 메인 프로그램을 재실행합니다."""
        import subprocess
        import sys
        
        main_script = self.current_dir / "main.py"
        self.print_status(f"메인 프로그램 재실행 시도: {main_script}")
        try:
            # detached process로 실행하여 업데이트 창이 닫혀도 메인 프로그램이 계속 실행되도록 함
            subprocess.Popen(
                [sys.executable, str(main_script)],
                cwd=str(self.current_dir),
                creationflags=subprocess.DETACHED_PROCESS if os.name == 'nt' else 0,
                close_fds=True
            )
            self.print_status("메인 프로그램 재실행 성공")
        except Exception as e:
            self.print_status(f"메인 프로그램 재실행 실패: {e}")
    
    def _cleanup_backup_initial(self):
        """시작 시 기존 백업 폴더 정리"""
        try:
            self.safe_remove_tree(self.backup_dir)
        except:
            pass
    
    def safe_remove_tree(self, path):
        """폴더를 안전하게 삭제 (권한 문제 무시)"""
        import os
        import stat
        
        def handle_remove_readonly(func, path, exc):
            """읽기 전용 파일 삭제 핸들러"""
            try:
                os.chmod(path, stat.S_IWRITE)
                func(path)
            except:
                pass
        
        try:
            if path.exists():
                shutil.rmtree(path, onerror=handle_remove_readonly)
        except:
            pass
    
    def create_backup(self):
        """현재 파일들을 백업"""
        self.print_status("백업 생성 중...")
        
        # 기존 백업 폴더 안전하게 삭제
        self.safe_remove_tree(self.backup_dir)
        
        self.backup_dir.mkdir()
        
        # 모든 파일을 백업 (.git 제외)
        for item in self.current_dir.iterdir():
            # 제외할 폴더들
            if item.name in ["backup_temp", "__pycache__", ".git"]:
                continue
            
            try:
                if item.is_file() and item.name != "update_program.py":
                    shutil.copy2(item, self.backup_dir / item.name)
                elif item.is_dir():
                    shutil.copytree(item, self.backup_dir / item.name)
            except Exception as e:
                self.print_status(f"백업 중 오류 (무시): {item.name} - {e}")
        
        self.print_status("백업 완료")
    
    def download_latest_version(self):
        """GitHub에서 최신 버전 다운로드"""
        self.print_status("최신 버전 다운로드 중...")
        
        try:
            response = requests.get(self.github_download, timeout=30)
            response.raise_for_status()
            
            zip_path = self.current_dir / "latest_version.zip"
            with open(zip_path, 'wb') as f:
                f.write(response.content)
            
            self.print_status("다운로드 완료")
            return zip_path
            
        except requests.RequestException as e:
            self.print_status(f"다운로드 실패: {e}")
            return None
    
    def extract_and_update(self, zip_path):
        """압축 파일을 해제하고 업데이트"""
        self.print_status("파일 업데이트 중...")
        
        extract_dir = self.current_dir / "temp_extract"
        
        try:
            # 압축 해제
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(extract_dir)
            
            # 압축 파일 내부의 실제 폴더 찾기 (보통 DVA-main 형태)
            extracted_folder = None
            for item in extract_dir.iterdir():
                if item.is_dir() and "DVA" in item.name:
                    extracted_folder = item
                    break
            
            if not extracted_folder:
                self.print_status("압축 파일 구조를 찾을 수 없습니다")
                return False
            
            # 파일 업데이트
            updated_count = 0
            for target in self.update_targets:
                source_path = extracted_folder / target
                dest_path = self.current_dir / target
                
                if source_path.exists():
                    if source_path.is_file():
                        # 개인 파일이 아닌 경우에만 업데이트
                        if not self.should_preserve_file(dest_path):
                            shutil.copy2(source_path, dest_path)
                            updated_count += 1
                            self.print_status(f"업데이트: {target}")
                    elif source_path.is_dir():
                        # 폴더의 경우 개인 파일 제외하고 업데이트
                        self.update_folder(source_path, dest_path)
                        updated_count += 1
                        self.print_status(f"폴더 업데이트: {target}")
            
            self.print_status(f"총 {updated_count}개 파일/폴더 업데이트 완료")
            return True
            
        except Exception as e:
            self.print_status(f"업데이트 실패: {e}")
            return False
        finally:
            # 임시 파일들 정리
            if extract_dir.exists():
                shutil.rmtree(extract_dir)
            if zip_path.exists():
                zip_path.unlink()
    
    def should_preserve_file(self, file_path):
        """파일을 보존해야 하는지 확인"""
        if not file_path.exists():
            return False
            
        file_name = file_path.name.lower()
        
        # 💡 사용자의 요청: 퀴즈 및 설문 정답 데이터는 최신본으로 덮어쓰기
        if file_name in ['quiz_problem.json', 'survey_problem.json']:
            return False
        
        # 확장자로 판단
        if file_path.suffix.lower() in self.preserve_extensions:
            return True
        
        # 특정 파일명으로 판단
        preserve_names = ['chromedriver', 'config', 'settings']
        if any(name in file_name for name in preserve_names):
            return True
        
        return False
    
    def update_folder(self, source_folder, dest_folder):
        """폴더 업데이트 (개인 파일 보존)"""
        if not dest_folder.exists():
            dest_folder.mkdir(parents=True)
        
        for item in source_folder.iterdir():
            dest_item = dest_folder / item.name
            
            if item.is_file():
                if not self.should_preserve_file(dest_item):
                    shutil.copy2(item, dest_item)
            elif item.is_dir():
                self.update_folder(item, dest_item)
    
    def restore_backup(self):
        """백업에서 복원"""
        self.print_status("백업에서 복원 중...")
        
        try:
            for item in self.backup_dir.iterdir():
                # .git 폴더는 건너뛰기
                if item.name == ".git":
                    continue
                    
                dest_path = self.current_dir / item.name
                
                try:
                    if item.is_file():
                        shutil.copy2(item, dest_path)
                    elif item.is_dir():
                        if dest_path.exists():
                            self.safe_remove_tree(dest_path)
                        shutil.copytree(item, dest_path)
                except Exception as e:
                    self.print_status(f"복원 중 오류 (계속): {item.name} - {e}")
            
            self.print_status("복원 완료")
            return True
            
        except Exception as e:
            self.print_status(f"복원 실패: {e}")
            return False
    
    def run_pip_install(self):
        """배경에서 pip install 실행"""
        self.print_status("필요한 패키지를 확인하고 설치 중입니다 (약 10~20초)...")
        import subprocess
        try:
            requirements_path = self.current_dir / "scripts" / "requirements.txt"
            if requirements_path.exists():
                subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", str(requirements_path), "--quiet", "--disable-pip-version-check"])
                self.print_status("패키지 설치 완료")
            else:
                self.print_status("requirements.txt 파일을 찾을 수 없어 패키지 설치를 건너뜁니다.")
        except Exception as e:
            self.print_status(f"패키지 설치 중 오류 (수동 설치 필요): {e}")

    def save_version_info(self):
        """최신 커밋 SHA 값을 조회하여 data/version.json에 저장"""
        self.print_status("로컬 버전 정보 갱신 중...")
        try:
            url = f"{self.github_repo}/commits/main"
            headers = {"User-Agent": "DVA-Updater"}
            response = requests.get(url, headers=headers, timeout=5)
            response.raise_for_status()
            data = response.json()
            sha = data.get("sha")
            if sha:
                version_file = self.current_dir / "data" / "version.json"
                version_file.parent.mkdir(parents=True, exist_ok=True)
                with open(version_file, "w", encoding="utf-8") as f:
                    json.dump({"latest_commit_sha": sha}, f, indent=4)
                self.print_status(f"버전 정보 갱신 완료: {sha}")
        except Exception as e:
            self.print_status(f"버전 정보 저장 중 실패 (무시): {e}")

    def remove_deprecated_files(self):
        """더 이상 사용되지 않는 파일들 제거 (예: 업데이트.bat)"""
        self.print_status("사용되지 않는 옛날 파일 정리 중...")
        deprecated_files = ['업데이트.bat']
        for file_name in deprecated_files:
            file_path = self.current_dir / file_name
            if file_path.exists():
                try:
                    file_path.unlink()
                    self.print_status(f"제거 완료: {file_name}")
                except Exception as e:
                    self.print_status(f"제거 실패 (무시): {file_name} - {e}")

    def cleanup(self):
        """임시 파일들 정리"""
        self.safe_remove_tree(self.backup_dir)
    
    def run_update(self):
        """업데이트 실행"""
        self.print_status("닥터빌 프로그램 업데이트를 시작합니다...")
        
        try:
            # 1. 백업 생성
            self.create_backup()
            
            # 2. 최신 버전 다운로드
            zip_path = self.download_latest_version()
            if not zip_path:
                return False
            
            # 3. 파일 업데이트
            success = self.extract_and_update(zip_path)
            
            if success:
                # 4. 의존성 패키지 업데이트
                self.run_pip_install()
                
                # 로컬 버전 정보 최신화
                self.save_version_info()
                
                # 사용되지 않는 옛날 파일 정리
                self.remove_deprecated_files()
                
                self.print_status("업데이트가 성공적으로 완료되었습니다!")
                self.print_status("백업 파일은 5초 후 자동으로 삭제됩니다...")
                
                # 5초 후 백업 삭제
                import time
                time.sleep(5)
                self.cleanup()
                
                return True
            else:
                self.print_status("업데이트 실패. 백업에서 복원합니다...")
                self.restore_backup()
                return False
                
        except Exception as e:
            self.print_status(f"업데이트 중 오류 발생: {e}")
            self.print_status("백업에서 복원합니다...")
            self.restore_backup()
            return False

def main():
    """메인 함수"""
    try:
        # CLI 인자 검사
        auto_mode = "--auto" in sys.argv
        
        # GUI 업데이트 도구 실행
        gui = UpdateGUI()
        gui.run(auto_mode=auto_mode)
    except Exception as e:
        # 오류 발생 시 메시지 박스로 표시
        import tkinter as tk
        from tkinter import messagebox
        root = tk.Tk()
        root.withdraw()
        messagebox.showerror("오류", f"업데이트 중 오류가 발생했습니다:\n{str(e)}")
        root.destroy()

if __name__ == "__main__":
    main()
