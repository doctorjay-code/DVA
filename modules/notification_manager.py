# -*- coding: utf-8 -*-
"""
카카오 알림 매니저
카카오톡 나에게 보내기 기능을 관리합니다.
"""

import requests
import json
import logging
from pathlib import Path

class NotificationManager:
    def __init__(self, settings_path="data/settings.json"):
        # 실행 디렉토리에 상관없이 settings.json을 찾을 수 있도록 절대 경로 구성
        self.base_dir = Path(__file__).parent.parent
        self.settings_path = self.base_dir / settings_path
        self.logger = logging.getLogger(self.__class__.__name__)
        self.token_url = "https://kauth.kakao.com/oauth/token"
        self.send_url = "https://kapi.kakao.com/v2/api/talk/memo/default/send"

    def _load_settings(self):
        """설정 파일 로드"""
        if not self.settings_path.exists():
            return {}
        try:
            with open(self.settings_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            self.logger.error(f"설정 파일 로드 중 오류: {str(e)}")
            return {}

    def _save_settings(self, settings):
        """설정 파일 저장"""
        try:
            with open(self.settings_path, 'w', encoding='utf-8') as f:
                json.dump(settings, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            self.logger.error(f"설정 파일 저장 중 오류: {str(e)}")
            return False

    def refresh_token(self):
        """refresh_token을 사용하여 새로운 access_token 발급"""
        settings = self._load_settings()
        refresh_token = settings.get('kakao_refresh_token')
        rest_api_key = settings.get('kakao_rest_api_key')

        if not refresh_token or not rest_api_key:
            self.logger.error("카카오 인증 정보가 부족합니다 (refresh_token 또는 rest_api_key)")
            return False

        data = {
            "grant_type": "refresh_token",
            "client_id": rest_api_key,
            "refresh_token": refresh_token
        }

        try:
            response = requests.post(self.token_url, data=data)
            result = response.json()

            if response.status_code == 200:
                settings['kakao_access_token'] = result.get('access_token')
                # refresh_token이 새로 발급된 경우 업데이트
                if 'refresh_token' in result:
                    settings['kakao_refresh_token'] = result.get('refresh_token')
                
                self._save_settings(settings)
                self.logger.info("카카오 액세스 토큰 갱신 성공")
                return True
            else:
                self.logger.error(f"카카오 토큰 갱신 실패: {result}")
                return False
        except Exception as e:
            self.logger.error(f"카카오 토큰 갱신 중 예외 발생: {str(e)}")
            return False

    def send_kakao_message(self, text, category=None):
        """카카오톡 '나에게 보내기' 메시지 전송"""
        settings = self._load_settings()
        
        # 1. 전체 알림 비활성화 상태면 중단
        if not settings.get('kakao_notify_enabled', False):
            return False

        # 2. 카테고리별 비활성화 상태 확인 (기본값 True)
        if category and not settings.get(category, True):
            return False

        access_token = settings.get('kakao_access_token')
        if not access_token:
            self.logger.warning("카카오 액세스 토큰이 없어 메시지를 보낼 수 없습니다.")
            return False

        def attempt_post(token):
            headers = {
                "Authorization": f"Bearer {token}"
            }
            
            # 3. 사용자명(계정명) 접두어 추가
            import os
            account_name = os.environ.get('ACCOUNT_NAME', '')
            prefix = f"[{account_name}] " if account_name else ""
            full_text = f"{prefix}{text}"

            template_object = {
                "object_type": "text",
                "text": f"[DVA 알림]\n{full_text}",
                "link": {
                    "web_url": "https://www.doctorville.co.kr",
                    "mobile_web_url": "https://www.doctorville.co.kr"
                },
                "button_title": "확인하기"
            }
            payload = {
                "template_object": json.dumps(template_object)
            }
            return requests.post(self.send_url, headers=headers, data=payload)

        try:
            # 1차 전송 시도
            response = attempt_post(access_token)
            
            # 토큰 만료(401) 시 갱신 후 재시도
            if response.status_code == 401:
                self.logger.info("카카오 토큰 만료 감지, 갱신 후 재시도합니다.")
                if self.refresh_token():
                    # 갱신된 토큰으로 재시도
                    new_token = self._load_settings().get('kakao_access_token')
                    response = attempt_post(new_token)
            
            if response.status_code == 200:
                self.logger.info("카카오 알림 전송 성공")
                return True
            else:
                self.logger.error(f"카카오 알림 전송 실패 ({response.status_code}): {response.text}")
                return False
                
        except Exception as e:
            self.logger.error(f"카카오 메시지 전송 중 예외 발생: {str(e)}")
            return False
