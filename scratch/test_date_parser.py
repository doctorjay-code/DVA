# -*- coding: utf-8 -*-
import os
import sys
import datetime

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)
sys.stdout.reconfigure(encoding='utf-8')

os.environ['ACCOUNT_NAME'] = '박범준'

from main_task_manager import TaskManagerState
from modules.messages import NotificationTemplates

tm = TaskManagerState()
# mock _parse_seminar_target_date method call via a dummy instance
from main_task_manager import TaskManager
tm_obj = TaskManager.__new__(TaskManager)

sample_seminars = [
    {'date': '7/29', 'day': '수', 'time': '19:00', 'title': '오늘 세미나 (당뇨병)', 'status': '신청가능'},
    {'date': '7/30', 'day': '목', 'time': '19:00', 'title': '내일 세미나 (고혈압)', 'status': '신청가능'},
    {'date': '7/31', 'day': '금', 'time': '20:00', 'title': '7/31 세미나 (심장학)', 'status': '신청가능'}
]

print("=== 동적 세미나 날짜 파싱 테스트 ===")

test_inputs = ["오늘 세미나", "내일 세미나", "모레 세미나", "7/31 세미나", "07/31 세미나"]

for inp in test_inputs:
    date_label, target_strs = tm_obj._parse_seminar_target_date(inp)
    filtered = [s for s in sample_seminars if s.get('date', '').strip() in target_strs]
    msg = NotificationTemplates.today_seminar_summary(filtered, date_label=date_label)
    print(f"\n입력: '{inp}' ➔ 파싱 날짜 라벨: '{date_label}'")
    print(msg)

print("\n=== 동적 날짜 파싱 테스트 성공적으로 완료 ===")
