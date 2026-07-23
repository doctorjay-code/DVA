# -*- coding: utf-8 -*-
"""
DVA Slack Bot Listener (원격 제어 봇)
아이폰 Slack 메신저에서 보낸 명령어를 수신하여 DVA CLI 작업을 자동 수행하고 결과를 답장합니다.
"""

import sys
import os
import time
import json
import logging
import subprocess
from pathlib import Path

# 프로젝트 루트 경로를 sys.path에 추가
BASE_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(BASE_DIR))

from slack_sdk.web import WebClient
from slack_sdk.socket_mode import SocketModeClient
from slack_sdk.socket_mode.response import SocketModeResponse
from slack_sdk.socket_mode.request import SocketModeRequest

# 토큰 정의
SLACK_BOT_TOKEN = os.environ.get("SLACK_BOT_TOKEN", "xoxb-11649655972307-11657869117457-klRsKH448VknFk9msaMVoZ2O")
SLACK_APP_TOKEN = os.environ.get("SLACK_APP_TOKEN", "xapp-1-A0BKDJ3D1PE-11649706492979-7702281ae98722cd849255e8324975633c7082c7f682ca332938b1c685a47497")

logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] SlackBot: %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger("DVA_SlackBot")

def run_dva_task(task_name, account_name=None):
    """cli_runner.py 스크립트를 동기 실행하고 결과를 수집"""
    python_exe = sys.executable
    cli_script = BASE_DIR / "scripts" / "cli_runner.py"

    cmd = [python_exe, str(cli_script), "--task", task_name, "--json"]
    if account_name:
        cmd.extend(["--account", account_name])

    try:
        process = subprocess.run(
            cmd,
            cwd=str(BASE_DIR),
            capture_output=True,
            text=True,
            encoding='utf-8',
            timeout=180
        )
        stdout_text = process.stdout
        
        # JSON 파싱 시도
        try:
            # JSON 블록 추출
            start_idx = stdout_text.find('{')
            end_idx = stdout_text.rfind('}')
            if start_idx != -1 and end_idx != -1:
                json_str = stdout_text[start_idx:end_idx+1]
                data = json.loads(json_str)
                return True, data, stdout_text
        except:
            pass

        return process.returncode == 0, {}, stdout_text
    except Exception as e:
        return False, {}, str(e)

def process_command(text):
    """사용자가 입력한 자연어 텍스트 분석하여 작업 매핑"""
    text_lower = text.lower()

    if any(k in text for k in ["출석", "출석체크", "출체"]):
        return "attendance", "📅 출석 체크"
    elif any(k in text for k in ["퀴즈", "문제"]):
        return "quiz", "🧠 일일 퀴즈 풀이"
    elif any(k in text for k in ["포인트", "잔액", "상태"]):
        return "points", "💰 포인트 및 사용자 상태 조회"
    elif any(k in text for k in ["세미나"]):
        return "seminar", "📢 세미나 확인"
    elif any(k in text for k in ["설문", "설문조사"]):
        return "survey", "📋 세미나 설문 응답"
    elif any(k in text for k in ["전체", "모두", "다해줘"]):
        return "all", "🔄 전체 자동화 (출석+퀴즈+포인트)"
    else:
        return None, None

def handle_socket_mode_request(client: SocketModeClient, req: SocketModeRequest):
    # 이벤트 승인 응답 즉시 전송
    response = SocketModeResponse(envelope_id=req.envelope_id)
    client.send_socket_mode_response(response)

    if req.type == "events_api":
        event = req.payload.get("event", {})
        event_type = event.get("type")

        # 봇 자신의 메시지는 무시
        if event.get("bot_id") or event.get("subtype") in ["bot_message", "channel_join"]:
            return

        # 앱 언급(app_mention) 또는 메시지(message) 수신 시
        if event_type in ["app_mention", "message"]:
            text = event.get("text", "").strip()
            channel_id = event.get("channel")
            thread_ts = event.get("ts")

            if not text or not channel_id:
                return

            logger.info(f"수신된 Slack 메시지: '{text}' (Channel: {channel_id}, Event: {event_type})")

            task_key, task_desc = process_command(text)
            web_client = client.web_client

            if not task_key:
                # app_mention 이거나 1:1 대화인 경우에만 도움말 표시
                is_dm = event.get("channel_type") == "im"
                if event_type == "app_mention" or is_dm:
                    help_msg = (
                        "🤖 *[DVA 원격 제어 봇 사용 안내]*\n\n"
                        "아래 키워드를 포함해서 메시지를 보내주시면 작업을 자동으로 수행합니다:\n"
                        "• *출석체크*: `출석체크` 또는 `출석`\n"
                        "• *퀴즈풀이*: `퀴즈` 또는 `퀴즈풀이`\n"
                        "• *포인트조회*: `포인트` 또는 `상태`\n"
                        "• *세미나조회*: `세미나` 또는 `세미나 확인`\n"
                        "• *전체실행*: `전체` 또는 `전체 실행`\n"
                    )
                    web_client.chat_postMessage(channel=channel_id, text=help_msg, thread_ts=thread_ts)
                return

            # 시작 안내 메시지 전송
            web_client.chat_postMessage(
                channel=channel_id,
                text=f"⏳ *[DVA 실행 시작]* {task_desc} 작업을 백그라운드에서 진행합니다. (약 15~30초 소요)",
                thread_ts=thread_ts
            )

            # 백그라운드 스레드에서 DVA CLI 실행
            def worker():
                try:
                    logger.info(f"작업 스레드 시작: {task_key}")
                    success, result_data, raw_output = run_dva_task(task_key)
                    logger.info(f"작업 스레드 완료: {task_key} (성공={success})")

                    status_icon = "✅" if success else "❌"
                    summary_lines = [f"{status_icon} *[DVA 작업 완료]* {task_desc}"]

                    if result_data:
                        for k, v in result_data.items():
                            if isinstance(v, dict):
                                msg = v.get('message', '')
                                if msg:
                                    summary_lines.append(f"• *{k}*: {msg}")
                    else:
                        clean_out = raw_output[-500:] if raw_output else "결과 출력 없음"
                        summary_lines.append(f"```\n{clean_out}\n```")

                    reply_text = "\n".join(summary_lines)
                    web_client.chat_postMessage(channel=channel_id, text=reply_text, thread_ts=thread_ts)
                except Exception as ex:
                    logger.error(f"작업 실행 중 오류 발생: {str(ex)}")
                    web_client.chat_postMessage(
                        channel=channel_id,
                        text=f"❌ *[DVA 실행 오류]* {task_desc} 중 오류가 발생했습니다: {str(ex)}",
                        thread_ts=thread_ts
                    )

            import threading
            threading.Thread(target=worker, daemon=True).start()


def main():
    logger.info("DVA Slack Bot Listener (원격 제어 서비스)를 개시합니다...")
    
    web_client = WebClient(token=SLACK_BOT_TOKEN)
    socket_client = SocketModeClient(
        app_token=SLACK_APP_TOKEN,
        web_client=web_client
    )

    socket_client.socket_mode_request_listeners.append(handle_socket_mode_request)
    socket_client.connect()

    logger.info("✅ Slack Socket Mode 연결 완료! 아이폰 Slack 메시지를 수신 대기 중입니다.")
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("봇을 종료합니다.")

if __name__ == '__main__':
    main()
