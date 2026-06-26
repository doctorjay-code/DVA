# -*- coding: utf-8 -*-
"""
DVA 프로젝트 전역에서 사용되는 공통 유틸리티 함수 모음
"""

def get_status_tag(status):
    """
    신청상태에 따른 태그 반환
    
    Args:
        status (str): 세미나 신청 상태 텍스트
        
    Returns:
        str: 표준화된 상태 태그 ('신청가능', '신청완료', '신청마감', '입장하기', '대기중', '기타')
    """
    status_lower = status.lower().strip()
    
    if '신청가능' in status_lower or ('신청' in status_lower and '가능' in status_lower):
        return '신청가능'
    elif '신청완료' in status_lower or '완료' in status_lower:
        return '신청완료'
    elif '신청마감' in status_lower or '마감' in status_lower:
        return '신청마감'
    elif '입장' in status_lower or '입장하기' in status_lower:
        return '입장하기'
    elif '대기' in status_lower or '대기중' in status_lower:
        return '대기중'
    else:
        return '기타'

def normalize_date(date_str):
    """
    날짜 형식을 비교 가능한 형태로 통일 (예: 2.26, 02.26, 2/26 -> 2.26)
    
    Args:
        date_str (str): 날짜 텍스트
        
    Returns:
        str: 'M.D' 형식의 표준화된 날짜 문자열
    """
    if not date_str:
        return ""
    # 요일 제거 (수) 등
    clean = date_str.split('(')[0].strip()
    # 구분자 통일 (. , /)
    clean = clean.replace('/', '.').replace('-', '.')
    # 월/일 추출 시도
    parts = [p for p in clean.split('.') if p.strip()]
    if len(parts) >= 2:
        # '22.02.26' 또는 '2022.02.26' 대응 (뒤에서 2개 사용)
        try:
            m = int(parts[-2])
            d = int(parts[-1])
            return f"{m}.{d}"
        except (ValueError, IndexError):
            pass
    return clean
