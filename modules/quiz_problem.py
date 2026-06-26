# -*- coding: utf-8 -*-
"""
일반 퀴즈 문제 관리 모듈
매일 진행되는 퀴즈 문제와 정답을 관리합니다.
"""

import json
import os
import re
from .survey_problem import SurveyProblemManager

class QuizProblemManager(SurveyProblemManager):
    """일일 퀴즈 문제와 정답을 관리하는 클래스"""
    
    def __init__(self, quiz_file=None):
        """
        초기화
        
        Args:
            quiz_file: 퀴즈 정보를 저장할 JSON 파일 경로
        """
        if quiz_file is None:
            # 1. 환경변수 계정 이름 확인
            account_name = os.environ.get('ACCOUNT_NAME', 'default')
            self.quiz_file = os.path.join("data", "quiz_problem.json")
        else:
            self.quiz_file = quiz_file
            
        self.quiz_answers = {}
        self.load_quizzes()

    def add_quiz(self, question: str, answer: str, category: str = "일반", answer_num: str = ""):
        """
        새로운 일일 퀴즈를 추가합니다.
        (설문과 달리 기본 카테고리를 '일반'으로 설정)
        """
        return super().add_quiz(question, answer, category, answer_num=answer_num)

    def _normalize_question(self, question: str) -> str:
        """
        일일 퀴즈에 특화된 정규화
        문제 번호, 불필요한 공백, 특수문자 제거
        """
        # 기본 정규화 수행
        cleaned = super()._normalize_question(question)
        
        # 일일 퀴즈 특유의 패턴 제거 (예: "Q. ", "문제: ")
        cleaned = re.sub(r'^(?:Q\.|문제:?)\s*', '', cleaned).strip()
        
        return cleaned
