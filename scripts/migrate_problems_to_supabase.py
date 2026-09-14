# -*- coding: utf-8 -*-
"""
로컬 JSON (survey_problem.json, quiz_problem.json) -> Supabase 일괄 마이그레이션 스크립트
"""

import os
import sys
import json
from pathlib import Path

# 프로젝트 루트 경로 추가
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from modules.supabase_client import SupabaseClient


def migrate():
    print("=== DVA 퀴즈/설문 데이터 Supabase 마이그레이션 시작 ===")
    client = SupabaseClient.get_instance()
    
    if not client.is_configured():
        print("[ERROR] Supabase 연결 설정(.env)을 찾을 수 없습니다.")
        sys.exit(1)

    print(f"연결 URL: {client.base_url}")
    
    # 1. survey_problem.json 마이그레이션
    survey_file = Path("data") / "survey_problem.json"
    if survey_file.exists():
        with open(survey_file, "r", encoding="utf-8") as f:
            survey_data = json.load(f)
        print(f"\n[1/2] 설문 정답({survey_file.name}) 로드: {len(survey_data)}건")
        uploaded = client.bulk_upsert_problems("survey", survey_data, chunk_size=100)
        print(f" -> 설문 정답 {uploaded}건 Supabase 업로드 완료")
    else:
        print(f"\n[1/2] {survey_file} 파일이 없습니다.")

    # 2. quiz_problem.json 마이그레이션
    quiz_file = Path("data") / "quiz_problem.json"
    if quiz_file.exists():
        with open(quiz_file, "r", encoding="utf-8") as f:
            quiz_data = json.load(f)
        print(f"\n[2/2] 일일 퀴즈({quiz_file.name}) 로드: {len(quiz_data)}건")
        uploaded = client.bulk_upsert_problems("quiz", quiz_data, chunk_size=100)
        print(f" -> 일일 퀴즈 {uploaded}건 Supabase 업로드 완료")
    else:
        print(f"\n[2/2] {quiz_file} 파일이 없습니다.")

    # 3. 검증
    print("\n=== Supabase 업로드 결과 검증 ===")
    survey_remote = client.fetch_all_problems("survey")
    quiz_remote = client.fetch_all_problems("quiz")
    print(f"Supabase 내 설문(survey) 총 건수: {len(survey_remote)}건")
    print(f"Supabase 내 퀴즈(quiz) 총 건수: {len(quiz_remote)}건")
    print("=== 마이그레이션 완료! ===")


if __name__ == "__main__":
    migrate()
