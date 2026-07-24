# -*- coding: utf-8 -*-
"""
세미나 문제 관리 모듈
퀴즈 문제와 정답 데이터 로직을 관리합니다. (GUI 코드는 ui/ 폴더로 분산됨)
"""

import json
import os
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
    
    def get_answer(self, question: str):
        """
        특정 문제의 정답을 가져옵니다.
        저장된 문제가 설문의 문제에 포함되어 있으면 해당 정답을 반환합니다.
        
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
            # 새로운 형식 처리
            if isinstance(quiz_data, dict):
                return quiz_data.get("answer")
            # 호환성: 구형식 처리
            else:
                return quiz_data
        
        # 2. 부분 일치: 저장된 문제가 추출된 문제에 포함되어 있는지 확인
        for saved_question, quiz_data in self.quiz_answers.items():
            # 저장된 문제(정규화됨)가 추출된 문제에 포함되어 있는지 확인
            if saved_question in normalized_question:
                if isinstance(quiz_data, dict):
                    return quiz_data.get("answer")
                else:
                    return quiz_data
        
        # 3. 역방향 확인: 추출된 문제의 일부가 저장된 문제에 포함되어 있는지
        # (추출된 문제가 너무 길 경우 대비)
        for saved_question, quiz_data in self.quiz_answers.items():
            # 최소 20자 이상 일치하면 부분 일치로 간주
            common_length = len(saved_question)
            if common_length > 20 and saved_question[:20] in normalized_question:
                if isinstance(quiz_data, dict):
                    return quiz_data.get("answer")
                else:
                    return quiz_data
        
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
            
        # 2. 부분 일치
        for saved_question in self.quiz_answers.keys():
            if saved_question in normalized_question:
                return saved_question
                
        # 3. 역방향 확인
        for saved_question in self.quiz_answers.keys():
            common_length = len(saved_question)
            if common_length > 20 and saved_question[:20] in normalized_question:
                return saved_question
                
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
        
        # 2. 부분 일치
        for saved_question, quiz_data in self.quiz_answers.items():
            if saved_question in normalized_question:
                return format_details(quiz_data)
        
        # 3. 역방향 확인
        for saved_question, quiz_data in self.quiz_answers.items():
            common_length = len(saved_question)
            if common_length > 20 and saved_question[:20] in normalized_question:
                return format_details(quiz_data)
                
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
