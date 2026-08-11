# -*- coding: utf-8 -*-
"""
세미나 문제 관리 모듈
퀴즈 문제와 정답 데이터 로직을 관리합니다. (GUI 코드는 ui/ 폴더로 분산됨)
"""

import json
import os
import time
import uuid
from pathlib import Path


class SurveyProblemManager:
    """설문 퀴즈 문제와 정답을 관리하는 클래스"""
    
    def __init__(self, quiz_file=None):
        """
        초기화
        
        Args:
            quiz_file: 퀴즈 정보를 저장할 JSON 파일 경로
        """
        if quiz_file is None:
            # 1. 환경변수 계정 이름 확인
            account_name = os.environ.get('ACCOUNT_NAME', 'default')
            self.quiz_file = os.path.join("data", "survey_problem.json")
        else:
            self.quiz_file = quiz_file
            
        self.quiz_answers = {}
        self.load_quizzes()
    
    def load_quizzes(self):
        """퀴즈 정보를 파일에서 로드합니다."""
        try:
            if os.path.exists(self.quiz_file):
                with open(self.quiz_file, 'r', encoding='utf-8') as f:
                    self.quiz_answers = json.load(f)
            else:
                self.quiz_answers = {}
        except Exception as e:
            print(f"퀴즈 로드 실패: {str(e)}")
            self.quiz_answers = {}
    
    def save_quizzes(self):
        """퀴즈 정보를 파일에 저장합니다."""
        for attempt in range(3):
            try:
                with open(self.quiz_file, 'w', encoding='utf-8') as f:
                    json.dump(self.quiz_answers, f, ensure_ascii=False, indent=2)
                return True
            except Exception as e:
                if attempt < 2:
                    import time
                    time.sleep(0.1)
                else:
                    print(f"퀴즈 저장 실패: {str(e)}")
                    return False
    
    def add_quiz(self, question: str, answer: str, category: str = "", answer_num: str = ""):
        """
        새로운 퀴즈를 추가합니다.
        
        Args:
            question: 문제 텍스트
            answer: 정답 (예: "1", "2", "O", "X", 또는 보기 텍스트 등)
            category: 카테고리 (예: "제미다파", "글리벤클라마이드" 등)
            answer_num: 정답 번호 (예: "1", "2" 등)
        
        Returns:
            성공 여부
        """
        if not question or not answer:
            return False
        
        # 문제 제목 정규화 (특수문자 제거)
        normalized_question = self._normalize_question(question)
        
        # 기존 카테고리 및 정답 번호 보존
        existing_category = ""
        existing_answer_num = ""
        if normalized_question in self.quiz_answers:
            existing = self.quiz_answers[normalized_question]
            if isinstance(existing, dict):
                existing_category = existing.get("category", "")
                existing_answer_num = existing.get("answer_num", "")
        
        target_category = category if category else existing_category
        target_answer_num = answer_num if answer_num else existing_answer_num
        
        # 중복 체크: 이미 동일한 문제가 동일한 답변/카테고리/정답번호로 등록되어 있다면 파일 저장 생략하고 True 반환
        if normalized_question in self.quiz_answers:
            existing = self.quiz_answers[normalized_question]
            if isinstance(existing, dict):
                if (existing.get("answer") == answer and 
                    existing.get("category", "") == target_category and 
                    existing.get("answer_num", "") == target_answer_num):
                    return True
            else:
                # 하위 호환성 (단순 문자열 답변인 경우)
                if existing == answer and not target_category and not target_answer_num:
                    return True
        
        # 새로운 형식: {문제: {answer: "정답", category: "카테고리", answer_num: "정답번호"}}
        self.quiz_answers[normalized_question] = {
            "answer": answer,
            "category": target_category,
            "answer_num": target_answer_num
        }
        return self.save_quizzes()
    
    def update_quiz(self, question: str, answer: str):
        """
        기존 퀴즈를 수정합니다.
        
        Args:
            question: 문제 텍스트
            answer: 새로운 정답
        
        Returns:
            성공 여부
        """
        if question not in self.quiz_answers:
            return False
        
        self.quiz_answers[question] = answer
        return self.save_quizzes()
    
    def delete_quiz(self, question: str):
        """
        퀴즈를 삭제합니다.
        
        Args:
            question: 문제 텍스트
        
        Returns:
            성공 여부
        """
        if question not in self.quiz_answers:
            return False
        
        del self.quiz_answers[question]
        return self.save_quizzes()
    
    def acquire_answer_prompt_lock(self, stale_after_seconds: int = 360):
        """Claim the one shared Slack-answer prompt across running accounts."""
        lock_path = Path("data") / "survey_answer_prompt.lock"
        token = uuid.uuid4().hex
        payload = {"token": token, "created_at": time.time()}

        try:
            fd = os.open(str(lock_path), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except FileExistsError:
            try:
                existing = json.loads(lock_path.read_text(encoding="utf-8"))
                created_at = float(existing.get("created_at", 0))
                if time.time() - created_at <= stale_after_seconds:
                    return None
                lock_path.unlink()
                fd = os.open(str(lock_path), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            except (OSError, ValueError, json.JSONDecodeError):
                return None
        except OSError:
            return None

        try:
            with os.fdopen(fd, "w", encoding="utf-8") as lock_file:
                json.dump(payload, lock_file)
            return token
        except OSError:
            try:
                lock_path.unlink(missing_ok=True)
            except OSError:
                pass
            return None

    def release_answer_prompt_lock(self, token: str):
        """Release the shared prompt lock only when this process owns it."""
        if not token:
            return

        lock_path = Path("data") / "survey_answer_prompt.lock"
        try:
            existing = json.loads(lock_path.read_text(encoding="utf-8"))
            if existing.get("token") == token:
                lock_path.unlink()
        except (OSError, ValueError, json.JSONDecodeError):
            pass

    def _is_polarity_conflict(self, text_a: str, text_b: str) -> bool:
        """두 문제 텍스트 간에 긍정/부정 표현이 충돌하는지 확인합니다.
        예: 한쪽은 '옳지 않은', 반대쪽은 '올바른' → 충돌 → True 반환
        """
        negative_keywords = ['않은', '아닌', '잘못된', '틀린', '올바르지 않은', '적절하지 않은', '맞지 않은']
        positive_keywords = ['올바른', '옳은', '맞는', '적절한', '바른', '알맞은']

        def has_negative(text):
            return any(kw in text for kw in negative_keywords)

        def has_positive(text):
            return any(kw in text for kw in positive_keywords)

        a_neg, a_pos = has_negative(text_a), has_positive(text_a)
        b_neg, b_pos = has_negative(text_b), has_positive(text_b)

        # 한쪽만 부정형이면 충돌
        if a_neg and not b_neg and b_pos:
            return True
        if b_neg and not a_neg and a_pos:
            return True
        # 한쪽은 부정형인데 반대쪽은 긍정형도 부정형도 없는 경우는 충돌 아님
        return False

    def get_answer(self, question: str):
        """
        특정 문제의 정답을 가져옵니다.
        저장된 문제가 설문의 문제에 포함되어 있으면 해당 정답을 반환합니다.

        매칭 전략 (안전 우선):
        1. 완전 일치
        2. 부분 포함 (DB키 ⊂ 웹문제, 단 DB키 최소 40자 이상) + 긍정/부정 충돌 없을 때
        ※ 앞 20자 매칭(역방향 추정) 제거 — 오매칭으로 오답 제출 위험

        Args:
            question: 문제 텍스트 (설문에서 긁어온 전체 문제 + 선택지)

        Returns:
            정답 (없으면 None)
        """
        # 문제 제목 정규화 후 조회
        normalized_question = self._normalize_question(question)

        # 1. 완전 일치 먼저 시도
        if normalized_question in self.quiz_answers:
            quiz_data = self.quiz_answers[normalized_question]
            if isinstance(quiz_data, dict):
                return quiz_data.get("answer")
            else:
                return quiz_data

        # 2. 부분 포함: DB 키가 웹 문제에 포함 (상대적 유사도 기반, 최소 15자 이상)
        for saved_question, quiz_data in self.quiz_answers.items():
            min_len = max(15, int(len(normalized_question) * 0.25))
            if len(saved_question) >= min_len and saved_question in normalized_question:
                # 긍정/부정 충돌 검사
                if self._is_polarity_conflict(saved_question, normalized_question):
                    continue
                if isinstance(quiz_data, dict):
                    return quiz_data.get("answer")
                else:
                    return quiz_data

        # ※ 앞 20자 역방향 매칭 제거 (오매칭으로 3번 기회 소진 위험)
        return None
    
    def get_matched_question(self, question: str) -> str:
        """
        주어진 질문에 매칭되는 DB 내의 기존 질문 키(원본 형태)를 반환합니다.
        매칭되는 항목이 없으면 정규화된 질문 텍스트를 반환합니다.
        """
        normalized_question = self._normalize_question(question)

        # 1. 완전 일치
        if normalized_question in self.quiz_answers:
            return normalized_question

        # 2. 부분 포함 (상대적 유사도 기반, 최소 15자 이상 + 긍정/부정 충돌 없음)
        for saved_question in self.quiz_answers.keys():
            min_len = max(15, int(len(normalized_question) * 0.25))
            if len(saved_question) >= min_len and saved_question in normalized_question:
                if not self._is_polarity_conflict(saved_question, normalized_question):
                    return saved_question

        # ※ 앞 20자 역방향 매칭 제거
        return normalized_question
    
    def get_question_details(self, question: str):
        """
        특정 문제의 전체 정보(정답 + 카테고리 + 정답번호)를 가져옵니다.
        
        Args:
            question: 문제 텍스트
        
        Returns:
            {"answer": "...", "category": "...", "answer_num": "..."} 딕셔너리 또는 None
        """
        normalized_question = self._normalize_question(question)
        
        def format_details(data):
            if isinstance(data, dict):
                res = data.copy()
                if "answer_num" not in res:
                    res["answer_num"] = ""
                # choices가 있을 수 있으나 UI 호환성 등을 위해 반환 딕셔너리에 보존
                return res
            else:
                return {"answer": data, "category": "", "answer_num": ""}
        
        # 1. 완전 일치
        if normalized_question in self.quiz_answers:
            return format_details(self.quiz_answers[normalized_question])

        # 2. 부분 포함 (DB키 최소 40자 이상 + 긍정/부정 충돌 없음)
        for saved_question, quiz_data in self.quiz_answers.items():
            if len(saved_question) >= 40 and saved_question in normalized_question:
                if not self._is_polarity_conflict(saved_question, normalized_question):
                    return format_details(quiz_data)

        # ※ 앞 20자 역방향 매칭 제거
        return None
    
    def _normalize_question(self, question: str) -> str:
        """
        문제 제목을 정규화합니다.
        [퀴즈] 태그와 후행 특수문자(*, ?, 등)를 제거합니다.
        
        Args:
            question: 원본 문제 텍스트
        
        Returns:
            정규화된 문제 텍스트
        """
        import re
        
        # [퀴즈] 태그 제거
        cleaned = question.replace("[퀴즈]", "").strip()
        
        # 선행 숫자 및 기호 제거 (예: "1. ", "Q1. ", "① ")
        # 숫자 뒤에 분리 기호가 1개 이상 있을 때만 제거하도록 제한하여 '3제 이상의...'에서 '3'이 지워지는 버그를 방지합니다.
        cleaned = re.sub(r'^(?:Q?\d+[\.\s:]+|[①-⑨]\s*)', '', cleaned).strip()
        
        # 후행 특수문자 제거 (*, ?, 숫자 옆의 특수문자 등)
        # 문제 끝의 *, ?, 공백 제거
        cleaned = re.sub(r'[\*\?]+\s*$', '', cleaned).strip()
        
        # 여러 개의 공백을 단일 공백으로 정규화
        cleaned = re.sub(r'\s+', ' ', cleaned)
        
        return cleaned
    
    def get_all_quizzes(self):
        """
        모든 퀴즈를 가져옵니다.
        
        Returns:
            {문제: 정답} 딕셔너리
        """
        return self.quiz_answers.copy()
    
    def has_quiz(self, question: str):
        """
        해당 문제가 존재하는지 확인합니다.
        
        Args:
            question: 문제 텍스트
        
        Returns:
            존재 여부
        """
        return question in self.quiz_answers
    
    def clear_all(self):
        """모든 퀴즈를 삭제합니다."""
        self.quiz_answers = {}
        return self.save_quizzes()


if __name__ == "__main__":
    # 테스트 코드
    manager = SurveyProblemManager()
    
    # 샘플 데이터 추가
    manager.add_quiz("DPP-4와 SGLT-2i 병용의 이점은?", "3")
    manager.add_quiz("바이트 프로틴 관련 문제", "O")
    
    # 목록 출력
    print("저장된 퀴즈:")
    for question, answer in manager.get_all_quizzes().items():
        print(f"Q: {question} → A: {answer}")
