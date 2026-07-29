# -*- coding: utf-8 -*-
import os
import sys
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)
sys.stdout.reconfigure(encoding='utf-8')

os.environ['ACCOUNT_NAME'] = '박범준'

from modules.messages import NotificationTemplates

print("=== NotificationTemplates 테스트 ===")
print("1. Remote Ack:")
print(NotificationTemplates.remote_ack("일일 퀴즈 풀이"))

print("\n2. Quiz Answer Ack:")
print(NotificationTemplates.quiz_answer_ack("당뇨병의 원인은?", "2", "닥터빌", ["3", "1"]))

print("\n3. Today Seminar Summary:")
sample_seminars = [
    {'date': '7/29', 'day': '수', 'time': '19:00', 'title': '최신 당뇨병 치료 동향', 'status': '신청가능'}
]
print(NotificationTemplates.today_seminar_summary(sample_seminars))

print("\n4. Seminar Apply Summary:")
print(NotificationTemplates.seminar_apply_summary(5, 2, 2, 1, ["최신 당뇨병 치료 동향", "고혈압 라이브 세미나"]))

print("\n5. Seminar Ended Notice:")
print(NotificationTemplates.seminar_ended_notice(["고혈압 라이브 세미나"]))

print("\n6. Task Result:")
print(NotificationTemplates.task_result("출석 체크", True))

print("\n7. Error Alert:")
print(NotificationTemplates.error_alert("로그인", "웹드라이버 연결 타임아웃"))

print("\n=== 테스트 성공적으로 완료 ===")
