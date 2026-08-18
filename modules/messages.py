# -*- coding: utf-8 -*-
"""
닥터빌 자동화 프로그램 로그 메시지 상수 및 알림 템플릿 정의
이모티콘으로 시작하는 메시지는 GUI 로그창에 노출되고,
이모티콘이 없는 메시지는 시스템 로그 파일에만 기록됩니다.
"""

import os

# --- 🔐 로그인 (Login) ---
MSG_LOGIN_START = "🔐 자동 로그인을 시작합니다..."
MSG_LOGIN_SUCCESS = "✅ 자동 로그인 성공"
MSG_LOGIN_STEP_SETUP = "웹드라이버 설정"
MSG_LOGIN_STEP_NAVIGATE = "닥터빌 메인 페이지 이동"
MSG_LOGIN_STEP_CLICK_UNIFIED = "통합회원 로그인 버튼 클릭"
MSG_LOGIN_STEP_WAIT_FORM = "로그인 폼 로딩 대기"
MSG_LOGIN_STEP_PERFORM = "로그인 정보 입력 및 로그인"
MSG_LOGIN_STEP_CHECK = "로그인 성공 여부 확인"

# --- 📅 출석 체크 (Attendance) ---
MSG_ATTENDANCE_START = "📅 출석 체크를 시작합니다..."
MSG_ATTENDANCE_SUCCESS = "✅ 출석 체크 성공"
MSG_ATTENDANCE_ALREADY = "✅ 이미 출석 체크가 완료되었습니다."

# --- 📝 퀴즈 (Quiz) ---
MSG_QUIZ_START = "📝 일일 퀴즈 풀기를 시작합니다..."
MSG_QUIZ_SUCCESS = "✅ 일일 퀴즈 풀기 성공"
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


class NotificationTemplates:
    """Slack 및 Kakao 알림 메시지 포맷 중앙 관리 템플릿"""

    @staticmethod
    def get_account_name() -> str:
        """환경변수에서 계정명 추출"""
        return os.environ.get('ACCOUNT_NAME', '').strip()

    @classmethod
    def format_header(cls, emoji: str, title: str) -> str:
        """표준 헤더 포맷 생성: [이모지] *[DVA | {계정명}]* {제목}"""
        account = cls.get_account_name()
        prefix = f" | {account}" if account else ""
        return f"{emoji} *[DVA{prefix}]* {title}".strip()

    @classmethod
    def remote_ack(cls, task_desc: str) -> str:
        """원격 요청 수신 확인 알림"""
        header = cls.format_header("🚀", "원격 요청 수신 완료")
        return f"{header}\n*{task_desc}* 작업을 시작합니다!"

    @classmethod
    def quiz_answer_ack(cls, display_q: str, answer: str, custom_tag: str = "", remaining_ans: list = None) -> str:
        """퀴즈 정답 수동 등록 피드백 알림"""
        tag_info = f" ('{custom_tag}')" if custom_tag else ""
        header = cls.format_header("💡", f"퀴즈 정답 등록 완료{tag_info}")
        msg = f"{header}\n• 문제: \"{display_q}\"\n• 정답: `{answer}` (으)로 등록하여 풀이를 재개합니다!"
        if remaining_ans:
            msg += f"\n📋 *다음 미등록 퀴즈 대기열:* `{', '.join(remaining_ans)}`"
        return msg

    @classmethod
    def today_seminar_summary(cls, today_seminars: list, date_label: str = "오늘") -> str:
        """세미나 목록 요약 알림 (날짜 지정 지원)"""
        header_title = f"{date_label} 닥터빌 세미나 목록" if "닥터빌" not in date_label else date_label
        header = cls.format_header("📊", header_title)
        lines = [header]
        if today_seminars:
            for s in today_seminars:
                d = s.get('date', '')
                day = s.get('day', '')
                tm = s.get('time', '')
                t = s.get('title', '')
                st = s.get('status', '')
                if t:
                    lines.append(f"• *{d}({day}) {tm}* | {t} (`{st}`)")
        else:
            lines.append(f"• {date_label} 예정된 세미나가 없습니다.")
        return "\n".join(lines)

    @classmethod
    def seminar_apply_summary(cls, total: int, applied_already: int, success: int, closed: int, applied_titles: list) -> str:
        """세미나 자동 신청 요약 알림"""
        final_applied = applied_already + success
        header = cls.format_header("📊", f"세미나 자동 신청 요약 (신청완료 {final_applied}/{total}건)")
        lines = [header, f"• 전체: {total}건 | 신청완료: {final_applied}건 | 신청마감: {closed}건"]
        if applied_titles:
            lines.append(f"\n✅ *이번 자동 신청 ({success}건):*")
            for title in applied_titles:
                lines.append(f"• {title}")
        return "\n".join(lines)

    @classmethod
    def seminar_ended_notice(cls, ended_titles: list) -> str:
        """세미나 종료 감지 알림"""
        header = cls.format_header("📢", "세미나 종료 감지")
        if not ended_titles:
            return f"{header}: 종료된 세미나가 있습니다."
        if len(ended_titles) == 1:
            return f"{header}: {ended_titles[0]}"
        return f"{header}: {ended_titles[0]} 외 {len(ended_titles)-1}건"

    @classmethod
    def task_result(cls, module_name: str, success: bool, detail: str = "") -> str:
        """단일 모듈 수행 결과 알림"""
        emoji = "✅" if success else "❌"
        status_text = "완료" if success else "실패"
        header = cls.format_header(emoji, f"{module_name} {status_text}")
        if detail:
            return f"{header}\n• {detail}"
        return header

    @classmethod
    def error_alert(cls, module_name: str, error_msg: str) -> str:
        """오류 발생 알림"""
        header = cls.format_header("🚨", f"{module_name} 오류 발생")
        return f"{header}: {error_msg}"
