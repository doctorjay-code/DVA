# -*- coding: utf-8 -*-
import os
import sys
import time

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)
sys.stdout.reconfigure(encoding='utf-8')

os.environ['ACCOUNT_NAME'] = '박범준'

from main_task_manager import TaskManagerState
from modules.messages import NotificationTemplates

state = TaskManagerState()
today_seminars = [{'date': '7/29', 'day': '수', 'time': '19:00', 'title': '테스트 세미나', 'status': '신청가능'}]
slack_msg = NotificationTemplates.today_seminar_summary(today_seminars)

def simulate_send_notice(state, slack_msg):
    now_ts = time.time()
    last_time = getattr(state, '_last_today_seminar_notice_time', None)
    last_hash = getattr(state, '_last_today_seminar_hash', "")
    
    if last_time and (now_ts - last_time < 30) and (last_hash == slack_msg):
        print(f"[{time.strftime('%H:%M:%S')}] 🚫 중복 알림 억제됨 (30초 이내 쿨다운 발동)")
        return False
    else:
        state._last_today_seminar_notice_time = now_ts
        state._last_today_seminar_hash = slack_msg
        print(f"[{time.strftime('%H:%M:%S')}] ✅ 알림 발송됨!")
        return True

print("=== 세미나 알림 중복 억제 쿨다운 테스트 ===")
print("1차 시도 (첫 요청 시):")
simulate_send_notice(state, slack_msg)

print("\n2차 시도 (1초 후 연속 자동신청/새로고침으로 또 발생 시):")
time.sleep(1)
simulate_send_notice(state, slack_msg)

print("\n=== 테스트 성공 완료 ===")
