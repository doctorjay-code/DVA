# -*- coding: utf-8 -*-
"""
닥터빌 자동화 프로그램 로그 메시지 상수 정의
이모티콘으로 시작하는 메시지는 GUI 로그창에 노출되고,
이모티콘이 없는 메시지는 시스템 로그 파일에만 기록됩니다.
"""

# --- 🔐 로그인 (Login) ---
MSG_LOGIN_START = "🔐 자동 로그인을 시작합니다..."
MSG_LOGIN_SUCCESS = "✅ 자동 로그인 성공"
MSG_LOGIN_STEP_SETUP = "웹드라이버 설정"
MSG_LOGIN_STEP_NAVIGATE = "닥터빌 메인 페이지 이동"
MSG_LOGIN_STEP_CLICK_UNIFIED = "통합회원 로그인 버튼 클릭"
MSG_LOGIN_STEP_WAIT_FORM = "로그인 폼 로딩 대기"
MSG_LOGIN_STEP_PERFORM = "로그인 정보 입력 및 로그인"
MSG_LOGIN_STEP_CHECK = "로그인 성공 여부 확인"

# --- 📅 출석체크 (Attendance) ---
MSG_ATTENDANCE_START = "📅 출석체크를 시작합니다..."
MSG_ATTENDANCE_SUCCESS = "✅ 출석체크 성공"
MSG_ATTENDANCE_ALREADY = "✅ 이미 출석체크가 완료되었습니다."

# --- 📝 퀴즈 (Quiz) ---
MSG_QUIZ_START = "📝 일일 퀴즈 풀기를 시작합니다..."
MSG_QUIZ_SUCCESS = "✅ 일일 퀴즈 풀기 성공 및 데이터 학습 완료"
MSG_QUIZ_ALREADY = "✅ 이미 오늘의 퀴즈를 완료했습니다."
MSG_QUIZ_SEARCH_BLOG = "🔍 정답을 찾기 위해 블로그를 검색합니다..."
MSG_QUIZ_FOUND_ANSWER = "💡 정답 후보를 찾았습니다: {answer}"

# --- 💰 포인트 및 요약 (Points & Summary) ---
MSG_POINTS_SUMMARY = "💰 현재 포인트: {points}P ({status})"
MSG_STARTUP_SUMMARY = "📊 오늘의 작업 현황 요약"

# --- 🔄 세미나 (Seminar) ---
MSG_SEMINAR_REFRESH = "🔄 세미나 목록을 새로고침합니다..."
MSG_SEMINAR_AUTO_APPLY_START = "🔎 자동 신청 가능 세미나 확인 중..."
MSG_SEMINAR_APPLY_SUCCESS = "✅ 자동 세미나 신청 완료: {count}개"
MSG_SEMINAR_APPLY_NONE = "🔍 신청할 수 있는 새로운 세미나가 없습니다."
MSG_SEMINAR_AUTO_ENTER = "🚪 세미나 자동 입장을 시작합니다: {title}"

# --- 🛵 배민 (Baemin) ---
MSG_BAEMIN_START = "🛵 배달의민족 쿠폰 구매 정보를 조회합니다..."
MSG_BAEMIN_PURCHASE_SUCCESS = "✅ 배민 쿠폰 구매 성공! ({message})"

# --- ⚠️ 알림 및 오류 (Alerts & Errors) ---
MSG_ALERT_SURVEY = "📝 설문 참여가 필요한 세미나가 발견되었습니다."
MSG_ERROR_GENERAL = "🚨 작업 중 오류가 발생했습니다: {error}"
