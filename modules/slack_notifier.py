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
from modules.messages import NotificationTemplates

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

    def send_slack_message(self, text, category=None, raw_text=False, blocks=None):
        """Slack Bot API(채널 ID 우선) 또는 Webhook으로 메시지 전송"""
        settings = self._load_settings()

        # 1. Slack 알림 활성화 여부 확인
        if not settings.get('slack_notify_enabled', False):
            return False

        # 2. 카테고리별 비활성화 상태 확인 (기본값 True)
        if category and not settings.get(category, True):
            return False

        slack_channel = settings.get('slack_channel', '').strip()
        slack_bot_token = settings.get('slack_bot_token', '').strip() or os.environ.get('SLACK_BOT_TOKEN', '').strip()
        webhook_url = settings.get('slack_webhook_url', '').strip()

        if not (slack_channel and slack_bot_token) and not webhook_url:
            self.logger.warning("Slack 채널 ID/Bot Token 또는 Webhook URL이 설정되지 않아 메시지를 보낼 수 없습니다.")
            return False

        # 이미 포맷팅된 메시지이거나 *[DVA 헤더가 있는 경우 중복 헤더 부착 방지
        if raw_text or "*[DVA" in text:
            full_text = text
        else:
            header = NotificationTemplates.format_header("🔔", "알림")
            full_text = f"{header}\n{text}"

        # 1순위: 현대적인 Slack Bot API (WebClient) 사용
        if slack_channel and slack_bot_token:
            try:
                from slack_sdk.web import WebClient
                client = WebClient(token=slack_bot_token)
                res = client.chat_postMessage(
                    channel=slack_channel,
                    text=full_text,
                    blocks=blocks
                )
                if res.get("ok"):
                    self.logger.info(f"Slack Bot API 알림 전송 성공 (채널: {slack_channel})")
                    return True
            except Exception as e:
                err_str = str(e)
                account_name = os.environ.get('ACCOUNT_NAME', '').strip()
                bot_hint = f"@dva_{account_name}" if account_name else "@DVA봇"
                if "not_in_channel" in err_str:
                    self.logger.error(
                        f"Slack Bot API 전송 실패: 봇이 채널({slack_channel})에 초대되어 있지 않습니다. "
                        f"채널에서 '/invite {bot_hint}' 명령어로 봇을 초대해 주세요."
                    )
                else:
                    self.logger.error(f"Slack Bot API 메시지 전송 중 오류: {err_str}")

                # 채널 전송 실패 시 Webhook URL이 있으면 폴백 시도
                if not webhook_url:
                    return False
                self.logger.info("Slack Webhook URL로 폴백 전송을 시도합니다...")

        # 2순위: 기존 Incoming Webhook 방식 (폴백 또는 채널 미입력 시)
        if webhook_url:
            payload = {
                "text": full_text
            }
            if blocks:
                payload["blocks"] = blocks

            try:
                response = requests.post(webhook_url, json=payload, timeout=10)
                if response.status_code == 200 and response.text == "ok":
                    self.logger.info("Slack Webhook 알림 전송 성공")
                    return True
                else:
                    self.logger.error(f"Slack Webhook 알림 전송 실패 ({response.status_code}): {response.text}")
                    return False
            except Exception as e:
                self.logger.error(f"Slack Webhook 메시지 전송 중 예외 발생: {str(e)}")
                return False

        return False

    @staticmethod
    def send_test_message(channel=None, bot_token=None, webhook_url=None):
        """설정 다이얼로그용 테스트 메시지 전송 (Bot API 우선 검증)"""
        account_name = os.environ.get('ACCOUNT_NAME', '').strip()
        prefix = f" | {account_name}" if account_name else ""
        test_text = f"✅ *[DVA{prefix}]* Slack 알림 연동 테스트 성공!"

        # 1. 채널 ID + Bot Token 테스트 (신형 Bot API)
        channel = (channel or '').strip()
        bot_token = (bot_token or '').strip() or os.environ.get('SLACK_BOT_TOKEN', '').strip()
        if channel and bot_token:
            try:
                from slack_sdk.web import WebClient
                client = WebClient(token=bot_token)
                res = client.chat_postMessage(channel=channel, text=test_text)
                if res.get("ok"):
                    return True, f"Slack Bot API로 테스트 메시지를 전송했습니다! (채널: {channel})"
            except Exception as e:
                err_str = str(e)
                bot_hint = f"@dva_{account_name}" if account_name else "@DVA봇"
                if "not_in_channel" in err_str:
                    return False, f"봇이 채널에 초대되어 있지 않습니다.\n해당 슬랙 채널에서 '/invite {bot_hint}' 명령어를 입력해주세요."
                if "channel_not_found" in err_str:
                    return False, f"채널 ID({channel})를 찾을 수 없습니다.\n채널 ID를 다시 확인해주세요."
                return False, f"Bot API 전송 실패: {err_str}"

        # 2. Webhook URL 테스트 (구형 방식 / 폴백)
        webhook_url = (webhook_url or '').strip()
        if webhook_url:
            try:
                payload = {
                    "text": test_text
                }
                response = requests.post(webhook_url, json=payload, timeout=10)
                if response.status_code == 200 and response.text == "ok":
                    return True, "Slack Webhook 연동 테스트 성공!"
                else:
                    return False, f"Webhook 전송 실패 ({response.status_code}): {response.text}"
            except Exception as e:
                return False, f"Webhook 오류 발생: {str(e)}"

        return False, "Slack 채널 ID(및 Bot Token) 또는 Webhook URL을 입력해주세요."
