# -*- coding: utf-8 -*-
"""
Supabase 클라이언트 모듈 (경량 REST API 기반)
별도 외부 의존성 없이 표준 requests 모듈을 사용하여 PostgREST API와 통신합니다.
"""

import os
import sys
import json
import logging
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, Optional

import requests

logger = logging.getLogger("dva_supabase")
if not logger.handlers:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter("[%(asctime)s][%(levelname)s] Supabase: %(message)s"))
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)


class SupabaseClient:
    """Supabase REST API 통신 클라이언트"""

    _instance = None
    _lock = threading.Lock()

    @classmethod
    def get_instance(cls):
        """싱글톤 인스턴스 반환"""
        with cls._lock:
            if cls._instance is None:
                cls._instance = cls()
            return cls._instance

    def __init__(self):
        self.base_url: str = ""
        self.api_key: str = ""
        self.timeout: float = 4.0  # 타임아웃 4초 (로컬 응답 지연 방지)
        self._load_config()

    def _load_config(self):
        """환경변수 또는 .env 파일에서 설정 로드"""
        # 1. os.environ 확인
        self.base_url = os.environ.get("SUPABASE_URL", "").strip().rstrip("/")
        self.api_key = os.environ.get("SUPABASE_KEY", "").strip()

        # 2. .env 파일 확인 (프로젝트 루트 및 현재 작업 디렉터리)
        if not (self.base_url and self.api_key):
            search_paths = [
                Path(__file__).resolve().parent.parent / ".env",
                Path.cwd() / ".env"
            ]
            for env_path in search_paths:
                if env_path.exists():
                    try:
                        with open(env_path, "r", encoding="utf-8") as f:
                            for line in f:
                                line = line.strip()
                                if not line or line.startswith("#"):
                                    continue
                                if "=" in line:
                                    k, v = line.split("=", 1)
                                    k = k.strip()
                                    v = v.strip().strip("'\"")
                                    if k == "SUPABASE_URL" and not self.base_url:
                                        self.base_url = v.rstrip("/")
                                    elif k == "SUPABASE_KEY" and not self.api_key:
                                        self.api_key = v
                    except Exception as e:
                        logger.warning(f".env 파일 로드 중 오류: {e}")
                    if self.base_url and self.api_key:
                        break

        # os.environ에도 세팅하여 다른 모듈에서 참조 가능하도록 함
        if self.base_url:
            os.environ["SUPABASE_URL"] = self.base_url
        if self.api_key:
            os.environ["SUPABASE_KEY"] = self.api_key

    def is_configured(self) -> bool:
        """연결 설정 유효성 검사"""
        return bool(self.base_url and self.api_key)

    def _get_headers(self, prefer: Optional[str] = None) -> Dict[str, str]:
        """API 요청 공통 헤더 생성"""
        headers = {
            "apikey": self.api_key,
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        if prefer:
            headers["Prefer"] = prefer
        return headers

    def fetch_all_problems(self, problem_type: Optional[str] = None) -> Dict[str, Dict[str, str]]:
        """
        Supabase에서 문제 목록 전체를 딕셔너리로 조회합니다.
        
        Args:
            problem_type: 'survey' 또는 'quiz' (None이면 전체)
            
        Returns:
            {question: {"answer": str, "category": str, "answer_num": str}}
        """
        if not self.is_configured():
            return {}

        results: Dict[str, Dict[str, str]] = {}
        try:
            url = f"{self.base_url}/rest/v1/dva_problems"
            params = {
                "select": "question,answer,category,answer_num,problem_type",
                "order": "id.asc",
                "limit": "2000"
            }
            if problem_type:
                params["problem_type"] = f"eq.{problem_type}"

            headers = self._get_headers()
            response = requests.get(url, headers=headers, params=params, timeout=self.timeout)
            
            if response.status_code == 200:
                data = response.json()
                for row in data:
                    q = row.get("question")
                    if q:
                        results[q] = {
                            "answer": row.get("answer", "") or "",
                            "category": row.get("category", "") or "",
                            "answer_num": row.get("answer_num", "") or ""
                        }
                logger.info(f"Supabase에서 {problem_type or '전체'} 문제 {len(results)}건 로드 완료")
            else:
                logger.warning(f"Supabase 조회 실패 (HTTP {response.status_code}): {response.text}")
        except Exception as e:
            logger.warning(f"Supabase 조회 중 예외 발생 (로컬 캐시 사용): {e}")

        return results

    def upsert_problem(self, problem_type: str, question: str, answer: str, 
                       category: str = "", answer_num: str = "") -> bool:
        """
        단일 문제를 Supabase에 Upsert(추가 또는 갱신)합니다.
        
        Args:
            problem_type: 'survey' 또는 'quiz'
            question: 문제 본문
            answer: 정답
            category: 카테고리
            answer_num: 객관식 번호
            
        Returns:
            성공 여부
        """
        if not self.is_configured() or not question or not answer:
            return False

        try:
            url = f"{self.base_url}/rest/v1/dva_problems?on_conflict=problem_type,question"
            headers = self._get_headers(prefer="resolution=merge-duplicates,return=minimal")
            payload = {
                "problem_type": problem_type,
                "question": question,
                "answer": answer,
                "category": category or "",
                "answer_num": answer_num or "",
                "updated_at": datetime.now(timezone.utc).isoformat()
            }
            response = requests.post(url, headers=headers, json=payload, timeout=self.timeout)
            if response.status_code in (200, 201, 204):
                return True
            else:
                logger.warning(f"Supabase Upsert 실패 (HTTP {response.status_code}): {response.text}")
                return False
        except Exception as e:
            logger.warning(f"Supabase Upsert 중 오류: {e}")
            return False

    def background_upsert(self, problem_type: str, question: str, answer: str, 
                          category: str = "", answer_num: str = ""):
        """
        메인 스레드를 블로킹하지 않고 백그라운드 스레드에서 조용히 Upsert를 수행합니다.
        """
        t = threading.Thread(
            target=self.upsert_problem,
            args=(problem_type, question, answer, category, answer_num),
            daemon=True
        )
        t.start()

    def bulk_upsert_problems(self, problem_type: str, problems_dict: Dict[str, Any], 
                             chunk_size: int = 100) -> int:
        """
        대량의 문제 딕셔너리를 Supabase에 일괄 Upsert합니다. (초기 마이그레이션용)
        
        Args:
            problem_type: 'survey' 또는 'quiz'
            problems_dict: {question: {"answer": ..., "category": ..., "answer_num": ...}} 또는 {question: "answer"}
            chunk_size: 한 번에 전송할 데이터 건수
            
        Returns:
            성공적으로 업로드된 건수
        """
        if not self.is_configured() or not problems_dict:
            return 0

        rows = []
        now_iso = datetime.now(timezone.utc).isoformat()

        for q, details in problems_dict.items():
            if not q:
                continue
            if isinstance(details, dict):
                ans = details.get("answer", "")
                cat = details.get("category", "")
                num = details.get("answer_num", "")
            else:
                ans = str(details)
                cat = ""
                num = ""

            if not ans:
                continue

            rows.append({
                "problem_type": problem_type,
                "question": q,
                "answer": ans,
                "category": cat or "",
                "answer_num": num or "",
                "updated_at": now_iso
            })

        total_uploaded = 0
        url = f"{self.base_url}/rest/v1/dva_problems?on_conflict=problem_type,question"
        headers = self._get_headers(prefer="resolution=merge-duplicates,return=minimal")

        for i in range(0, len(rows), chunk_size):
            chunk = rows[i:i + chunk_size]
            try:
                response = requests.post(url, headers=headers, json=chunk, timeout=10.0)
                if response.status_code in (200, 201, 204):
                    total_uploaded += len(chunk)
                else:
                    logger.warning(f"청크 업로드 실패 (HTTP {response.status_code}): {response.text}")
            except Exception as e:
                logger.error(f"청크 업로드 예외 발생: {e}")

        logger.info(f"[{problem_type}] 총 {total_uploaded}/{len(rows)}건 Supabase 업로드 완료")
        return total_uploaded

    def delete_problem(self, problem_type: str, question: str) -> bool:
        """
        Supabase에서 문제를 삭제합니다.
        """
        if not self.is_configured() or not question:
            return False

        try:
            url = f"{self.base_url}/rest/v1/dva_problems"
            params = {
                "problem_type": f"eq.{problem_type}",
                "question": f"eq.{question}"
            }
            headers = self._get_headers()
            response = requests.delete(url, headers=headers, params=params, timeout=self.timeout)
            return response.status_code in (200, 204)
        except Exception as e:
            logger.warning(f"Supabase 삭제 중 오류: {e}")
            return False

    def background_delete(self, problem_type: str, question: str):
        """
        백그라운드 스레드에서 문제를 삭제합니다.
        """
        t = threading.Thread(
            target=self.delete_problem,
            args=(problem_type, question),
            daemon=True
        )
        t.start()
