# -*- coding: utf-8 -*-
"""
Slack 알림 매니저
DVA 작업 결과를 Slack Webhook으로 전송합니다.
"""

import requests
import json
import logging
import os
from pathlib import Path

class SlackNotifier:
    def __init__(self, settings_path="data/settings.json"):
        self.base_dir = Path(__file__).parent.parent
        self.settings_path = self.base_dir / settings_path
        self.logger = logging.getLogger(self.__class__.__name__)

    def _load_settings(self):
        """설정 파일 로드 (ACCOUNT_NAME 환경변수 지원)"""
        account_name = os.environ.get('ACCOUNT_NAME', '').strip()
        if account_name:
            acc_path = self.base_dir / "data" / f"settings_{account_name}.json"
            if acc_path.exists():
                try:
                    with open(acc_path, 'r', encoding='utf-8') as f:
                        return json.load(f)
                except Exception as e:
                    self.logger.error(f"계정별 설정 파일 로드 중 오류 ({acc_path}): {str(e)}")

        if not self.settings_path.exists():
            return {}
        try:
            with open(self.settings_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            self.logger.error(f"설정 파일 로드 중 오류: {str(e)}")
            return {}

    def send_slack_message(self, text, category=None):
        """Slack Webhook으로 메시지 전송"""
        settings = self._load_settings()

        # 1. Slack 알림 활성화 여부 확인
        if not settings.get('slack_notify_enabled', False):
            return False

        # 2. 카테고리별 비활성화 상태 확인 (기본값 True)
        if category and not settings.get(category, True):
            return False

        webhook_url = settings.get('slack_webhook_url', '').strip()
        if not webhook_url:
            self.logger.warning("Slack Webhook URL이 설정되지 않아 메시지를 보낼 수 없습니다.")
            return False

        account_name = os.environ.get('ACCOUNT_NAME', '')
        prefix = f"[{account_name}] " if account_name else ""
        full_text = f"🔔 *[DVA 알림]* {prefix}\n{text}"

        payload = {
            "text": full_text
        }

        try:
            response = requests.post(webhook_url, json=payload, timeout=10)
            if response.status_code == 200 and response.text == "ok":
                self.logger.info("Slack 알림 전송 성공")
                return True
            else:
                self.logger.error(f"Slack 알림 전송 실패 ({response.status_code}): {response.text}")
                return False
        except Exception as e:
            self.logger.error(f"Slack 메시지 전송 중 예외 발생: {str(e)}")
            return False

    @staticmethod
    def send_test_message(webhook_url):
        """설정 다이얼로그용 테스트 메시지 전송"""
        if not webhook_url or not webhook_url.strip():
            return False, "Webhook URL을 입력해주세요."

        account_name = os.environ.get('ACCOUNT_NAME', '')
        prefix = f"[{account_name}] " if account_name else ""
        payload = {
            "text": f"✅ *[DVA 알림]* {prefix}Slack 알림 연동 테스트 성공!"
        }

        try:
            response = requests.post(webhook_url.strip(), json=payload, timeout=10)
            if response.status_code == 200 and response.text == "ok":
                return True, "Slack 연동 테스트 성공!"
            else:
                return False, f"전송 실패 ({response.status_code}): {response.text}"
        except Exception as e:
            return False, f"오류 발생: {str(e)}"
