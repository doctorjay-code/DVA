# -*- coding: utf-8 -*-
"""
DVA CLI Runner (헤드리스 CLI 실행 엔진)
Hermes Agent 및 외부 시스템에서 커맨드라인으로 DVA 기능을 실행하고 결과를 반환받습니다.
"""

import sys
import os
import argparse
import json
import logging
from pathlib import Path

# 프로젝트 루트 경로를 sys.path에 추가
BASE_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(BASE_DIR))

from web_automation import WebAutomation
from main_task_manager import ModuleFactory
from modules.notification_manager import NotificationManager

def run_task(task_name, headless=True, json_output=False, account_name=None):
    """
    DVA 작업을 헤드리스 모드로 동기 실행
    """
    if account_name:
        os.environ['ACCOUNT_NAME'] = account_name

    # 로거 설정 (CLI 모드에서는 stdout으로 출력)
    logging.basicConfig(
        level=logging.INFO,
        format='[%(asctime)s] %(levelname)s: %(message)s',
        datefmt='%H:%M:%S'
    )
    logger = logging.getLogger("CLIRunner")

    def cli_log(message):
        if not json_output:
            print(f"[DVA CLI] {message}")

    gui_callbacks = {
        'log_message': cli_log,
        'update_points': lambda pts: None,
        'update_status': lambda status, data: None,
    }

    results = {}
    web_auto = None

    try:
        cli_log(f"웹 드라이버 초기화 중... (Headless={headless})")
        web_auto = WebAutomation(headless=headless)

        # 1. 로그인 수행
        cli_log("로그인 시도 중...")
        login_class = ModuleFactory.create_module_class('login')
        login_module = login_class(web_auto, cli_log)
        login_module.set_callbacks(gui_callbacks)
        login_res = login_module.execute()

        if not login_res.get('success', False):
            results['login'] = login_res
            cli_log(f"❌ 로그인 실패: {login_res.get('message', '알 수 없는 오류')}")
            if json_output:
                print(json.dumps(results, ensure_ascii=False, indent=2))
            return False

        cli_log("✅ 로그인 성공")
        results['login'] = login_res

        # 2. 지정된 작업 실행 목록 결정
        tasks_to_run = []
        if task_name == 'all':
            tasks_to_run = ['attendance', 'quiz', 'points']
        elif task_name in ModuleFactory.MODULE_INFO:
            tasks_to_run = [task_name]
        else:
            cli_log(f"❌ 지원되지 않는 작업입니다: {task_name}")
            return False

        # 3. 작업 순차 실행
        for t in tasks_to_run:
            if t == 'login':
                continue
            cli_log(f"▶ 작업 시작: {t}")
            mod_class = ModuleFactory.create_module_class(t)
            module_inst = mod_class(web_auto, cli_log)
            module_inst.set_callbacks(gui_callbacks)
            res = module_inst.execute()
            results[t] = res
            
            success_str = "성공" if res.get('success', False) else "실패"
            cli_log(f"◀ 작업 완료 [{t}]: {success_str} - {res.get('message', '')}")

    except Exception as e:
        logger.error(f"CLI 실행 중 예외 발생: {str(e)}")
        results['error'] = str(e)
    finally:
        if web_auto:
            cli_log("웹 드라이버 종료 중...")
            web_auto.quit()

    if json_output:
        print(json.dumps(results, ensure_ascii=False, indent=2))

    return all(r.get('success', False) for r in results.values() if isinstance(r, dict))

def main():
    parser = argparse.ArgumentParser(description="DVA CLI Runner (Hermes Agent / Remote Control)")
    parser.add_argument(
        '--task', '-t',
        choices=['login', 'attendance', 'quiz', 'points', 'seminar', 'survey', 'baemin', 'all'],
        default='points',
        help='실행할 DVA 작업 선택 (기본값: points)'
    )
    parser.add_argument(
        '--no-headless',
        action='store_true',
        help='브라우저 창을 화면에 표시합니다 (기본값: 헤드리스 모드)'
    )
    parser.add_argument(
        '--json', '-j',
        action='store_true',
        help='결과를 JSON 포맷으로 출력합니다.'
    )
    parser.add_argument(
        '--account', '-a',
        type=str,
        default=None,
        help='계정 이름 설정 (계정별 설정 파일 사용 시)'
    )

    args = parser.parse_args()
    headless_mode = not args.no_headless

    success = run_task(
        task_name=args.task,
        headless=headless_mode,
        json_output=args.json,
        account_name=args.account
    )

    sys.exit(0 if success else 1)

if __name__ == '__main__':
    main()
