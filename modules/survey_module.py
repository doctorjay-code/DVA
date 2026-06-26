# -*- coding: utf-8 -*-
"""
설문참여 모듈
닥터빌 세미나 설문참여 기능을 담당합니다.
"""

import os
import threading
import time
import re
import ctypes
import requests
import json
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from .base_module import BaseModule
from .survey_problem import SurveyProblemManager

# URL 상수 정의
VOD_LIST_PAGE_URL = "https://www.doctorville.co.kr/seminar/seminarVodReplayList?categoryCd=&metaCd=&sort=apply&query="

# CSS 선택자 상수 정의
LIVE_LIST_CONTAINER_SELECTOR = ".live_list .list_cont"
FIRST_SEMINAR_LINK_SELECTOR = ".live_list .list_cont:first-child a.list_detail"
SEMINAR_TITLE_SELECTOR = ".tit"
REENTER_BUTTON_SELECTOR = ".btn_bn.btn_enter.btn_seminar_agree"

# 에러 메시지 상수 정의
ERROR_FIRST_SEMINAR_SELECTION = "첫 번째 세미나 자동 선택 실패"
ERROR_REENTER_BUTTON_CLICK = "재입장하기 버튼 클릭 실패"
ERROR_SURVEY_PAGE_NAVIGATION = "설문참여 페이지 이동 중 오류"
ERROR_SURVEY_BUTTON_CLICK = "설문참여 버튼 클릭 실패"

class SurveyModule(BaseModule):
    _is_running = False  # 정적 변수로 실행 중 여부 관리
    _lock = threading.Lock()

    def __init__(self, web_automation, gui_logger=None):
        super().__init__(web_automation, gui_logger)
        self.problem_manager = SurveyProblemManager()

    def _get_radio_label_text(self, radio):
        """라디오 버튼 인접 노드에서 실제 보기 텍스트를 추출하는 JS 헬퍼"""
        js_script = """
        var radio = arguments[0];
        
        // 1. ID 기반 label 매칭 (단, 해당 label이 여러 input을 포함하는 거대 label이 아니어야 함)
        if (radio.id) {
            var label = document.querySelector('label[for="' + radio.id + '"]');
            if (label) {
                var labelInputs = label.querySelectorAll('input[type="radio"], input[type="checkbox"]');
                if (labelInputs.length <= 1) {
                    var txt = label.innerText.trim();
                    if (txt) return txt;
                }
            }
        }
        
        // 2. 바로 뒤의 형제 엘리먼트 텍스트 확인
        var next = radio.nextElementSibling;
        if (next && (next.tagName === 'SPAN' || next.tagName === 'LABEL' || next.tagName === 'DIV')) {
            var txt = next.innerText.trim();
            if (txt) return txt;
        }
        
        // 3. 바로 뒤의 인접 텍스트 노드들 합쳐서 확인
        var node = radio.nextSibling;
        var textParts = [];
        while (node) {
            if (node.nodeType === 3) {
                textParts.push(node.nodeValue);
            } else if (node.nodeType === 1) {
                if (node.tagName === 'INPUT' || node.tagName === 'DIV' || node.tagName === 'P' || node.tagName === 'BR') {
                    break;
                }
                if (['SPAN', 'FONT', 'B', 'I', 'STRONG', 'EM', 'LABEL'].indexOf(node.tagName) !== -1) {
                    textParts.push(node.innerText);
                }
            }
            node = node.nextSibling;
        }
        var siblingText = textParts.join('').trim();
        if (siblingText) return siblingText;
        
        // 4. 상위 엘리먼트 중 '오직 이 input 하나만 포함하고 있는' 가장 인접한 부모 컨테이너 찾기
        var parent = radio.parentElement;
        while (parent && parent.tagName !== 'BODY') {
            var siblingInputs = parent.querySelectorAll('input[type="radio"], input[type="checkbox"]');
            if (siblingInputs.length === 1) {
                var cloned = parent.cloneNode(true);
                var inputs = cloned.querySelectorAll('input');
                for (var i = 0; i < inputs.length; i++) {
                    inputs[i].remove();
                }
                var labelText = cloned.innerText.trim();
                if (labelText) {
                    return labelText;
                }
            }
            parent = parent.parentElement;
        }
        
        // 5. 최후의 수단: 단순히 parent의 텍스트를 반환하되, 줄바꿈이 있는 경우 첫 번째 의미있는 줄만 반환
        try {
            var fullText = radio.parentElement.innerText.trim();
            var lines = fullText.split('\\n').map(function(l) { return l.trim(); }).filter(Boolean);
            if (lines.length > 0) {
                return lines[0];
            }
            return fullText;
        } catch(e) {
            return '';
        }
        """
        try:
            return self.web_automation.driver.execute_script(js_script, radio).strip()
        except:
            return ""

    # 세션 내 모델 캐시 (프로세스 재시작 전까지 유지)
    _cached_gemini_model = None
    _cached_gemini_api_key = None  # 키가 바뀌면 캐시 무효화

    def _get_available_gemini_model(self, api_key, exclude=None):
        """사용 가능한 Gemini Flash 모델을 자동으로 탐색하고 캐싱합니다."""
        if exclude is None:
            exclude = set()

        # 캐시된 모델이 exclude에 포함되어 있으면 캐시 무효화
        if SurveyModule._cached_gemini_model in exclude:
            SurveyModule._cached_gemini_model = None
            SurveyModule._cached_gemini_api_key = None

        # 같은 API 키에서 이미 찾은 모델이 있으면 재사용
        if (SurveyModule._cached_gemini_model and
                SurveyModule._cached_gemini_api_key == api_key):
            return SurveyModule._cached_gemini_model

        # 우선순위 모델 후보 목록 (가볍고 제한이 널널한 Lite 모델 우선 권장)
        CANDIDATE_MODELS = [
            "gemini-2.5-flash-lite",
            "gemini-2.5-flash",
            "gemini-2.0-flash-lite",
            "gemini-2.0-flash",
            "gemini-1.5-flash",
            "gemini-1.5-flash-latest",
            "gemini-2.5-pro",
            "gemini-1.5-pro",
        ]

        # exclude 필터링
        candidates = [m for m in CANDIDATE_MODELS if m not in exclude]
        if not candidates:
            self.log_warning("❌ 모든 후보 모델이 제외되었습니다.")
            return None

        self.log_info("🔍 사용 가능한 Gemini 모델을 탐색합니다...")

        # 1단계: ListModels API로 실제 지원 목록 조회
        try:
            list_url = f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key}"
            list_resp = requests.get(list_url, timeout=8)
            if list_resp.status_code == 200:
                available = list_resp.json().get("models", [])
                # 지원 목록에서 generateContent 가능한 모델만 추출
                supported_names = set()
                for m in available:
                    name = m.get("name", "")  # "models/gemini-2.5-flash" 형태
                    methods = m.get("supportedGenerationMethods", [])
                    if "generateContent" in methods:
                        short = name.replace("models/", "")
                        supported_names.add(short)

                # 후보 목록과 교집합을 우선순위 순으로 선택
                for candidate in candidates:
                    if candidate in supported_names:
                        self.log_success(f"Gemini 모델 자동 선택: {candidate}")
                        SurveyModule._cached_gemini_model = candidate
                        SurveyModule._cached_gemini_api_key = api_key
                        return candidate

                # 후보 목록에 없더라도 제외되지 않은 flash 계열 첫 번째 모델 사용
                for name in supported_names:
                    if name not in exclude and "flash" in name:
                        self.log_success(f"Gemini 모델 자동 선택 (목록 우선): {name}")
                        SurveyModule._cached_gemini_model = name
                        SurveyModule._cached_gemini_api_key = api_key
                        return name
        except Exception as e:
            self.log_warning(f"ListModels API 조회 실패, 직접 시도로 전환합니다: {e}")

        # 2단계: ListModels 실패 시 후보 모델을 직접 하나씩 시도
        test_payload = {
            "contents": [{"parts": [{"text": "test"}]}],
            "generationConfig": {"maxOutputTokens": 1}
        }
        for candidate in candidates:
            try:
                test_url = f"https://generativelanguage.googleapis.com/v1beta/models/{candidate}:generateContent?key={api_key}"
                resp = requests.post(test_url, headers={"Content-Type": "application/json"},
                                     json=test_payload, timeout=8)
                if resp.status_code == 200:
                    self.log_success(f"Gemini 모델 직접 탐색 성공: {candidate}")
                    SurveyModule._cached_gemini_model = candidate
                    SurveyModule._cached_gemini_api_key = api_key
                    return candidate
            except Exception:
                continue

        return None  # 모두 실패

    def _generate_ai_answer(self, question_text, char_limits=None):
        """Gemini API를 사용하여 질문에 대한 자연스러운 의학적 답변을 생성합니다."""
        # API 키 가져오기
        api_key = ""
        if hasattr(self, 'gui_callbacks') and 'gui_instance' in self.gui_callbacks:
            try:
                api_key = self.gui_callbacks['gui_instance'].get_setting('gemini_api_key')
            except Exception as e:
                self.log_warning(f"설정에서 Gemini API Key를 가져오지 못했습니다: {e}")
                
        if not api_key:
            return None
            
        self.log_info("🤖 Gemini AI 답변 생성을 시작합니다...")
        
        # 설정에서 저장된 프롬프트 템플릿 가져오기
        prompt_template = ""
        if hasattr(self, 'gui_callbacks') and 'gui_instance' in self.gui_callbacks:
            try:
                prompt_template = self.gui_callbacks['gui_instance'].get_setting('gemini_prompt_template')
            except Exception as e:
                self.log_warning(f"설정에서 Gemini Prompt Template을 가져오지 못했습니다: {e}")
                
        # 기본 템플릿
        if not prompt_template:
            prompt_template = (
                "의학 세미나 설문조사 주관식 질문입니다. 의사 또는 의료 전문가 관점에서 신뢰감 있고 전문적으로 답변해 주세요.\n\n"
                "답변을 작성할 때 반드시 다음 규칙을 지켜주세요:\n"
                "1. 큰따옴표(\"\"), 작은따옴표(''), 대괄호([]), 소괄호(()) 등의 모든 따옴표와 괄호 기호를 절대로 사용하지 마세요.\n"
                "2. 사람이 직접 손으로 타이핑한 것 같이 자연스러운 존댓말 형태로 작성해 주세요.\n"
                "3. 줄바꿈을 하지 말고 하나의 완성된 문단(단일 paragraph)으로만 답변을 작성해 주세요.\n"
                "4. 답변 외에 다른 군더더기 메타 설명(예: '답변:', '작성된 의견:', '최소 글자 수를 만족하는 답변입니다')은 절대 포함하지 마세요.\n\n"
                "{length_condition}\n\n"
                "질문: {question}"
            )
            
        # 상황별 세부 지시문 템플릿 가져오기
        template_min = ""
        template_max = ""
        template_no = ""
        if hasattr(self, 'gui_callbacks') and 'gui_instance' in self.gui_callbacks:
            try:
                gui_inst = self.gui_callbacks['gui_instance']
                template_min = gui_inst.get_setting('gemini_prompt_min_limit')
                template_max = gui_inst.get_setting('gemini_prompt_max_limit')
                template_no = gui_inst.get_setting('gemini_prompt_no_limit')
            except Exception as e:
                self.log_warning(f"설정에서 상황별 지시문 템플릿을 가져오지 못했습니다: {e}")
                
        # 기본값 fallback
        if not template_min:
            template_min = "답변의 길이는 공백을 포함하여 반드시 {min_limit}자 이상 {min_plus_100}자 이하로 넉넉하게 작성해 주세요."
        if not template_max:
            template_max = "답변의 길이는 공백을 포함하여 반드시 {max_safe_min}자 이상 {max_safe_max}자 이하로 작성해 주세요. (절대 {max_limit}자를 넘으면 안 됩니다.)"
        if not template_no:
            template_no = "답변의 길이는 공백을 포함하여 40자 내외로 간결하게 작성해 주세요."

        # 글자 수 조건 파싱
        min_limit = None
        max_limit = None
        if isinstance(char_limits, dict):
            min_limit = char_limits.get("min")
            max_limit = char_limits.get("max")
            
        # 포맷팅 변수 딕셔너리 준비
        variables = {
            "min_limit": min_limit or 0,
            "max_limit": max_limit or 0,
            "min_plus_100": (min_limit or 0) + 100,
            "max_safe_min": int((max_limit or 0) * 0.5),
            "max_safe_max": int((max_limit or 0) * 0.7),
        }
        
        # 최소/최대 둘 다 있는 특수한 경우를 위한 변수 보정
        if min_limit and max_limit:
            variables["max_safe_min"] = max(min_limit, int(max_limit * 0.6))
            variables["max_safe_max"] = int(max_limit * 0.9)

        # 실제 치환 적용
        length_instruction = ""
        try:
            if min_limit and max_limit:
                # 최소/최대 둘 다 있는 경우 최대 조건 템플릿을 연동하되 변수는 보정된 값 사용
                length_instruction = template_max.format(**variables)
            elif min_limit:
                length_instruction = template_min.format(**variables)
            elif max_limit:
                length_instruction = template_max.format(**variables)
            else:
                length_instruction = template_no.format(**variables)
        except Exception as e:
            self.log_warning(f"상황별 지시문 템플릿 치환 실패로 기본 지시문을 사용합니다: {e}")
            # 진짜 기본값 fallback
            if min_limit and max_limit:
                length_instruction = f"답변의 길이는 공백을 포함하여 반드시 {variables['max_safe_min']}자 이상 {variables['max_safe_max']}자 이하로 작성해 주세요. (절대 {max_limit}자를 넘으면 안 됩니다.)"
            elif min_limit:
                length_instruction = f"답변의 길이는 공백을 포함하여 반드시 {min_limit}자 이상 {min_limit + 100}자 이하로 넉넉하게 작성해 주세요."
            elif max_limit:
                length_instruction = f"답변의 길이는 공백을 포함하여 반드시 {variables['max_safe_min']}자 이상 {variables['max_safe_max']}자 이하로 작성해 주세요. (절대 {max_limit}자를 넘으면 안 됩니다.)"
            else:
                length_instruction = "답변의 길이는 공백을 포함하여 40자 내외로 간결하게 작성해 주세요."
            
        # 템플릿 치환 적용
        try:
            prompt = prompt_template.format(
                length_condition=length_instruction,
                question=question_text
            )
        except Exception as e:
            self.log_warning(f"프롬프트 템플릿 치환 실패로 기본 포맷을 사용합니다: {e}")
            prompt = (
                "의학 세미나 설문조사 주관식 질문입니다. 의사 또는 의료 전문가 관점에서 신뢰감 있고 전문적으로 답변해 주세요.\n\n"
                "답변을 작성할 때 반드시 다음 규칙을 지켜주세요:\n"
                "1. 큰따옴표(\"\"), 작은따옴표(''), 대괄호([]), 소괄호(()) 등의 모든 따옴표와 괄호 기호를 절대로 사용하지 마세요.\n"
                "2. 사람이 직접 손으로 타이핑한 것 같이 자연스러운 존댓말 형태로 작성해 주세요.\n"
                "3. 줄바꿈을 하지 말고 하나의 완성된 문단(단일 paragraph)으로만 답변을 작성해 주세요.\n"
                "4. 답변 외에 다른 군더더기 메타 설명(예: '답변:', '작성된 의견:', '최소 글자 수를 만족하는 답변입니다')은 절대 포함하지 마세요.\n\n"
                f"{length_instruction}\n\n"
                f"질문: {question_text}"
            )
            
        # API 키 앞뒤 공백 제거 보장
        api_key = str(api_key).strip()
        
        failed_models = set()
        
        while True:
            # 사용 가능한 모델 자동 탐색 (캐시 활용, 실패 제외)
            model_name = self._get_available_gemini_model(api_key, exclude=failed_models)
            if not model_name:
                self.log_warning("❌ 사용 가능한 Gemini 모델을 더 이상 찾을 수 없습니다. API 키 상태 혹은 목록을 확인해주세요.")
                return None
                
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={api_key}"
            headers = {"Content-Type": "application/json"}
            
            # 동일 모델에 대해 최대 3회 시도 (503 또는 예외 발생 시 백오프 재시도)
            response = None
            for attempt in range(1, 4):
                try:
                    payload = {
                        "contents": [{
                            "parts": [{"text": prompt}]
                        }],
                        "generationConfig": {
                            "temperature": 0.7
                        }
                    }
                    response = requests.post(url, headers=headers, json=payload, timeout=15)
                    
                    if response.status_code == 503:
                        if attempt < 3:
                            wait_sec = 2 ** attempt  # 2초 → 4초 대기
                            self.log_warning(f"⚠️ Gemini 서버 과부하(503) [{model_name}]. {wait_sec}초 후 재시도합니다... ({attempt}/3)")
                            time.sleep(wait_sec)
                            continue
                    break
                except Exception as e:
                    if attempt < 3:
                        wait_sec = 2 ** attempt
                        self.log_warning(f"⚠️ Gemini 호출 중 예외 발생 [{model_name}]: {str(e)}. {wait_sec}초 후 재시도합니다... ({attempt}/3)")
                        time.sleep(wait_sec)
                        continue
                    else:
                        self.log_error(f"Gemini API 호출 중 최종 예외 발생 ({model_name}): {str(e)}")
                        response = None
                        break
            
            # API 호출이 결국 완전 실패한 경우
            if not response:
                failed_models.add(model_name)
                if SurveyModule._cached_gemini_model == model_name:
                    SurveyModule._cached_gemini_model = None
                    SurveyModule._cached_gemini_api_key = None
                self.log_warning(f"⚠️ {model_name} 호출 예외 발생으로 다음 사용 가능한 모델로 자동 전환을 시도합니다.")
                continue
                
            # 재시도 후에도 오류인 경우
            if response.status_code != 200:
                self.log_warning(f"⚠️ {model_name} 호출 실패 (상태 코드: {response.status_code})")
                try:
                    error_details = response.json()
                    error_msg = error_details.get('error', {}).get('message', '상세 오류 없음')
                    self.log_warning(f"  └ API 에러 상세: {error_msg}")
                except:
                    self.log_warning(f"  └ API 에러 상세: {response.text[:200]}")
                    
                # 이 모델은 실패했으므로 제외 목록에 추가
                failed_models.add(model_name)
                if SurveyModule._cached_gemini_model == model_name:
                    SurveyModule._cached_gemini_model = None
                    SurveyModule._cached_gemini_api_key = None
                self.log_warning(f"⚠️ {model_name}이(가) 실패하여 다음 사용 가능한 모델로 자동 전환을 시도합니다.")
                continue  # 루프의 다음 반복으로 넘어가 다른 모델 사용
                
            try:
                result = response.json()
                if 'candidates' not in result or not result['candidates']:
                    self.log_warning(f"Gemini API 응답에서 답변 후보를 찾을 수 없습니다. ({model_name})")
                    failed_models.add(model_name)
                    continue
                    
                answer = result['candidates'][0]['content']['parts'][0]['text'].strip()
                
                # [이중 안전장치] 최소 글자 수 제한이 있고 길이가 부족한 경우 재요청
                if min_limit and len(answer) < min_limit:
                    self.log_warning(f"⚠️ AI 답변의 길이({len(answer)}자)가 최소 요구 글자 수({min_limit}자)보다 작습니다. 보완 요청 중...")
                    
                    retry_prompt = (
                        f"이전 답변: '{answer}'\n\n"
                        f"위 답변은 공백 포함 {len(answer)}자로, 최소 요구치인 {min_limit}자에 미달합니다.\n"
                        "반드시 다음 조건들을 철저히 만족해 주세요:\n"
                        "1. 큰따옴표, 작은따옴표, 대괄호, 소괄호 등의 기호를 절대로 쓰지 마세요.\n"
                        f"2. 반드시 공백 포함 {min_limit}자 이상 {min_limit + 100}자 이하가 되도록 관련 세부 설명, 임상적 혜택 혹은 사례를 덧붙여 훨씬 길고 풍부한 단일 문단으로 완성해 주세요. 메타 설명 없이 완성 본문만 출력해 주세요."
                    )
                    
                    payload = {
                        "contents": [{
                            "parts": [{"text": retry_prompt}]
                        }],
                        "generationConfig": {
                            "temperature": 0.7
                        }
                    }
                    
                    response = requests.post(url, headers=headers, json=payload, timeout=10)
                    if response.status_code == 200:
                        result = response.json()
                        retry_answer = result['candidates'][0]['content']['parts'][0]['text'].strip()
                        if len(retry_answer) >= min_limit:
                            answer = retry_answer
                            self.log_success(f"재요청을 통해 글자 수 충족 완료 ({len(answer)}자)")
                        else:
                            merged = answer + " 추가적으로, 실제 처방 사례에 비추어 볼 때 환자의 치료 만족도를 높이기 위한 면밀한 복약 지도와 장기적 추적 관찰이 중요하며, 관련 지표의 동반 개선을 통해 임상 혜택을 극대화할 수 있을 것입니다."
                            if len(merged) >= min_limit:
                                answer = merged
                                self.log_success("템플릿 문장 합치기를 통해 글자 수 강제 충족 완료")
                
                # [최종 강제 포맷 제거 후처리] 양 끝 및 본문 내부의 따옴표, 괄호 등 제거하고 줄바꿈을 공백으로 단일문단화
                answer = re.sub(r'["\'\(\)\[\]\{\}“”‘’]', '', answer)
                answer = re.sub(r'\s+', ' ', answer).strip() # 다중 공백 및 줄바꿈을 단일 공백으로 치환해 한 문단으로 강제
                
                # 성공 시 캐시 설정
                SurveyModule._cached_gemini_model = model_name
                SurveyModule._cached_gemini_api_key = api_key
                
                # [카카오톡 알림 전송] 
                if hasattr(self, 'gui_callbacks') and 'notify_kakao' in self.gui_callbacks:
                    # 질문 텍스트가 너무 길면 말줄임표 처리 (가독성 확보)
                    short_q = question_text[:60] + "..." if len(question_text) > 60 else question_text
                    kakao_msg = (
                        f"[설문 주관식 작성]\n"
                        f"Q: {short_q}\n"
                        f"A: {answer}"
                    )
                    sent = self.gui_callbacks['notify_kakao'](kakao_msg, cat="notify_subjective_answer")
                    if sent:
                        self.log_info("💬 [카톡알림] 주관식 답변 알림 전송 완료")
                        
                return answer
            except Exception as e:
                self.log_error(f"응답 가공 중 오류 발생 ({model_name}): {str(e)}")
                failed_models.add(model_name)
                if SurveyModule._cached_gemini_model == model_name:
                    SurveyModule._cached_gemini_model = None
                    SurveyModule._cached_gemini_api_key = None
                continue

        self.log_error("❌ 모든 시도된 Gemini 모델이 실패했습니다.")
        return None
    
    def _recover_to_original_window(self, original_window):
        """오류 또는 종료 후 원래 메인 창으로 안전하게 복구합니다."""
        if not self.web_automation or not self.web_automation.driver:
            return
            
        self.log_info("원래 창으로 복구를 시도합니다...")
        try:
            # 1. 원래 창 핸들이 여전히 존재하는지 확인
            handles = self.web_automation.driver.window_handles
            if original_window in handles:
                self.web_automation.driver.switch_to.window(original_window)
                self.log_info("원래 창으로 복구 완료")
                return
            
            # 2. 존재하지 않으면 첫 번째 핸들로 전환
            if handles:
                self.web_automation.driver.switch_to.window(handles[0])
                self.log_info("원래 창이 없어 첫 번째 활성 창으로 복구 완료")
                return
        except Exception as e:
            self.log_warning(f"창 복구 중 오류 발생: {e}")

    def execute(self, target_url=None, target_title=None, skip_urls=None):
        """설문참여 페이지로 이동하고 첫 번째 세미나 자동 선택"""
        original_window = None
        try:
            # 중복 실행 방지
            with SurveyModule._lock:
                if SurveyModule._is_running:
                    self.log_info("ℹ 이미 설문 참여가 진행 중입니다. 중복 방지를 위해 취소합니다.")
                    return self.create_result(False, "이미 설문 참여가 진행 중입니다.")
                SurveyModule._is_running = True

            if not self.web_automation or not self.web_automation.driver:
                self.log_error("웹드라이버가 초기화되지 않았습니다. 먼저 로그인해주세요.")
                SurveyModule._is_running = False
                return self.create_result(False, "웹드라이버가 초기화되지 않았습니다.")
            
            original_window = self.web_automation.driver.current_window_handle
            
            self.log_info("설문참여 페이지로 이동합니다...")
            
            # VOD 목록 페이지로 이동
            self.web_automation.driver.get(VOD_LIST_PAGE_URL)
            self.log_info("설문참여 페이지로 이동 완료")
            
            # 🔥 첫 번째 세미나 자동 클릭
            self.log_info("첫 번째 세미나를 자동으로 선택합니다...")
            
            return self._auto_click_seminar(original_window, target_url, target_title, skip_urls)
            
        except Exception as e:
            SurveyModule._is_running = False
            error_msg = f"{ERROR_SURVEY_PAGE_NAVIGATION}: {str(e)}"
            self.log_error(error_msg)
            return self.create_result(False, error_msg)

    def _auto_click_seminar(self, original_window, target_url=None, target_title=None, skip_urls=None):
        """내부에서 동기적으로 세미나 클릭 및 설문 로직을 수행합니다."""
        try:
            from datetime import datetime
            today_str = datetime.now().strftime("%Y-%m-%d")
            self.log_info(f"📅 오늘 날짜({today_str}) 세미나 설문 조사를 시작합니다.")

            # 1. 대상 세미나 URL 선행 수집
            targets = []
            skipped_count = 0  # skip_urls로 건너뛴 세미나 수
            if target_url:
                targets.append({'url': target_url, 'title': target_title or "지연 설문"})
            else:
                self.find_element_safe(By.CSS_SELECTOR, LIVE_LIST_CONTAINER_SELECTOR)
                
                containers = self.find_elements_safe(By.CSS_SELECTOR, ".live_list .list_cont")
                skipped_count = 0
            
                for container in containers:
                    try:
                        # container가 stale된 경우를 대비해 텍스트와 하위 요소를 안전하게 가져옴
                        text = container.text
                        if today_str in text:
                            # 하위 요소 탐색 시에도 driver 기반 selector 권장이나, 
                            # 여기서는 container를 그대로 쓰되 에러 시 skip
                            link_elem = container.find_element(By.CSS_SELECTOR, "a.list_detail")
                            href = link_elem.get_attribute('href')
                            title = container.find_element(By.CSS_SELECTOR, SEMINAR_TITLE_SELECTOR).text.strip()
                            
                            # 중복 방지 + 이미 확정 종료된 URL은 건너뜀
                            if href and not any(t['url'] == href for t in targets):
                                if skip_urls and href in skip_urls:
                                    self.log_info(f"⏭ 이미 확인된 종료 세미나 건너뜁니다: {title}")
                                    skipped_count += 1
                                    continue
                                targets.append({'url': href, 'title': title})
                    except Exception:
                        continue

            if not targets:
                if skipped_count > 0:
                    self.log_info(f"⏭ 오늘 세미나 {skipped_count}건 모두 이미 종료된 세미나입니다. (설문 참여 생략)")
                else:
                    self.log_warning(f"오늘 날짜({today_str})의 세미나를 찾을 수 없습니다.")
                return self.create_result(True, "오늘 참여할 세미나가 없습니다.")

            self.log_info(f"📋 오늘 참여 대상 세미나 {len(targets)}건을 발견했습니다.")

            # 2. 수집된 URL 순차 방문 및 처리
            success_count = 0
            for i, target in enumerate(targets):
                try:
                    self.log_info(f"🔍 세미나 확인 중 ({i+1}/{len(targets)}): {target['title']}")
                    
                    # 상세 페이지로 직접 이동
                    self.web_automation.driver.get(target['url'])
                    time.sleep(0.5)

                    # 재입장하기 버튼 확인 및 처리
                    res = self.auto_click_reenter_button()
                    
                    is_success = False
                    reason = None
                    error_message = None
                    quiz_result = None
                    
                    if isinstance(res, dict):
                        is_success = res.get('success', False)
                        reason = res.get('reason')
                        error_message = res.get('message')
                        quiz_result = res.get('quiz_result')
                    else:
                        is_success = bool(res)
                        
                    if is_success:
                        target['success'] = True
                        target['reason'] = 'success'
                        quiz_result = res.get('quiz_result') if isinstance(res, dict) else None
                        success_msg = f"설문 참여 성공: {target['title']}"
                        if quiz_result:
                            success_msg += f"\n👉 {quiz_result}"
                            
                        self.log_success(f"✅ {success_msg}")
                        
                        # 개별 항목별 카톡 알림 전송
                        if hasattr(self, 'gui_callbacks') and 'notify_success' in self.gui_callbacks:
                            self.gui_callbacks['notify_success'](success_msg)
                        
                        success_count += 1
                        # 설문 페이지가 열렸을 수 있으므로 목록 페이지로 리셋
                        self.web_automation.driver.get(VOD_LIST_PAGE_URL)
                        time.sleep(1)
                    else:
                        target['success'] = False
                        target['reason'] = reason or 'failed'
                        # 진짜 실패인 경우에만 카톡 실패 알림 전송
                        if reason == "failed" or (not is_success and reason not in ["no_reenter_button", "user_cancelled"]):
                            fail_msg = f"❌ 설문 참여 실패: {target['title']}"
                            if error_message:
                                fail_msg += f"\n사유: {error_message}"
                            else:
                                fail_msg += "\n사유: 설문 자동 진행 오류"
                            
                            self.log_error(fail_msg)
                            
                            if hasattr(self, 'gui_callbacks') and 'notify_kakao' in self.gui_callbacks:
                                self.gui_callbacks['notify_kakao'](fail_msg, cat="notify_error")
                        else:
                            if reason == "user_cancelled":
                                self.log_warning(f"⚠️ 사용자가 설문 창을 닫아 작업을 중단합니다. ({target['title']})")
                            elif reason == "no_reenter_button":
                                self.log_info(f"🔒 이미 종료된 세미나: {target['title']}")
                            else:
                                self.log_info(f"ℹ 재입장 버튼 없음 (혹은 이미 완료): {target['title']}")
                            
                        # 상세 페이지에서 바로 다음으로 넘어가면 되므로 get 생략 가능하지만 안전을 위해 호출
                        # (상태가 바뀌어 있을 수도 있으므로 다시 목록으로 나감)
                        try:
                            self.web_automation.driver.get(VOD_LIST_PAGE_URL)
                            time.sleep(1)
                        except Exception as ge:
                            self.log_warning(f"VOD 목록 페이지 복귀 실패: {str(ge)}")

                except Exception as ie:
                    target['success'] = False
                    target['reason'] = 'error'
                    
                    err_msg = str(ie)
                    is_window_closed = "no such window" in err_msg or "window already closed" in err_msg
                    
                    if is_window_closed:
                        self.log_warning(f"사용자가 설문 창을 닫아 작업을 중단합니다. ({target['title']})")
                        self._recover_to_original_window(original_window)
                    else:
                        self.log_error(f"⚠️ 세미나 처리 중 오류 ({target['title']}): {err_msg}")
                        
                        # 진짜 오류인 경우에만 카톡 실패 알림 전송
                        fail_msg = f"❌ 설문 참여 에러: {target['title']}\n사유: {err_msg}"
                        if hasattr(self, 'gui_callbacks') and 'notify_kakao' in self.gui_callbacks:
                            self.gui_callbacks['notify_kakao'](fail_msg, cat="notify_error")
                        
                    try:
                        self.web_automation.driver.get(VOD_LIST_PAGE_URL)
                        time.sleep(1)
                    except Exception as ge:
                        self.log_warning(f"VOD 목록 페이지 복귀 실패: {str(ge)}")
            
            closed_count = sum(1 for t in targets if t.get('reason') == 'no_reenter_button')
            summary_parts = [f"총 {len(targets)}건 중 {success_count}건의 설문을 처리했습니다."]
            if closed_count > 0:
                summary_parts.append(f"({closed_count}건은 이미 종료된 세미나)")
            return self.create_result(True, " ".join(summary_parts), {
                "targets": targets,
                "success_count": success_count
            })

        except Exception as e:
            error_msg = f"설문 세미나 순회 중 오류: {str(e)}"
            self.log_error(error_msg)
            return self.create_result(False, error_msg)

        finally:
            if original_window and self.web_automation and self.web_automation.driver:
                try:
                    self._recover_to_original_window(original_window)
                    self.log_info("설문참여 완료 후 추가 창을 정리합니다...")
                    self.web_automation.close_other_windows(original_window)
                except Exception as e:
                    self.log_warning(f"창 정리 중 오류: {str(e)}")
                finally:
                    # 실행 종료 표시
                    SurveyModule._is_running = False
            else:
                SurveyModule._is_running = False

    
    def auto_click_reenter_button(self):
        """재입장하기 버튼을 자동으로 클릭합니다."""
        try:
            self.log_info("재입장하기 버튼 검색 중...")
            
            # 재입장하기 버튼이 있는지 먼저 확인
            try:
                # find_element_safe를 사용하여 짧은 타임아웃으로 확인
                reenter_button = self.find_element_safe(By.CSS_SELECTOR, REENTER_BUTTON_SELECTOR, timeout=1)
                
                self.log_info("재입장하기 버튼 발견")
                
                # 버튼 클릭
                reenter_button.click()
                
                self.log_info("✅ 재입장하기 버튼 자동 클릭 완료")
                self.log_info("새로운 팝업 창에서 설문참여 버튼을 찾는 중...")
                
                # 🔥 새로운 팝업 창에서 설문참여 버튼 자동 클릭
                res = self.auto_click_survey_in_popup()
                if isinstance(res, dict):
                    return res
                elif res is False:
                    return {"success": False, "reason": "failed", "message": "설문 팝업 진입 또는 답변 처리 중 실패"}
                return {"success": True}
                
            except TimeoutException:
                # 재입장하기 버튼이 없는 경우 (이미 설문 완료)
                self.log_info("재입장하기 버튼이 없습니다. 이미 설문이 완료되었거나 참여할 설문이 없습니다.")
                return {"success": False, "reason": "no_reenter_button"}
                
        except Exception as e:
            self.log_error(f"{ERROR_REENTER_BUTTON_CLICK}: {str(e)}")
            return {"success": False, "reason": "failed", "message": f"재입장 버튼 클릭 실패: {str(e)}"}
    
    def auto_click_survey_in_popup(self):
        """새로운 팝업 창에서 설문참여 버튼을 자동으로 클릭합니다."""
        original_window = None
        try:
            self.log_info("새로운 팝업 창 대기 중...")
            
            # 새로운 팝업 창이 열릴 때까지 대기
            time.sleep(2)  # 팝업 창 로딩 대기
            
            # 현재 열려있는 모든 창 핸들 가져오기
            original_window = self.web_automation.driver.current_window_handle
            all_windows = self.web_automation.driver.window_handles
            
            # 새로 열린 팝업 창 찾기
            popup_window = None
            for window in all_windows:
                if window != original_window:
                    popup_window = window
                    break
            
            if not popup_window:
                self.log_error("새로운 팝업 창을 찾을 수 없습니다")
                return {"success": False, "reason": "failed", "message": "새로운 팝업 창을 찾을 수 없습니다"}
            
            # 팝업 창으로 전환
            self.web_automation.driver.switch_to.window(popup_window)
            
            self.log_info("팝업 창으로 전환 완료")
            self.log_info("설문참여 버튼 검색 중...")
            
            # 설문참여 버튼 찾기 (안전하게)
            survey_button = self.find_element_safe(By.CSS_SELECTOR, "#surveyEnter")
            
            self.log_info("설문참여 버튼 발견")
            
            # 버튼 클릭
            survey_button.click()
            
            self.log_info("✅ 설문참여 버튼 자동 클릭 완료")
            self.log_info("개인정보 동의 팝업에서 설문하기 버튼을 찾는 중...")
            
            # 🔥 개인정보 동의 팝업에서 설문하기 버튼 자동 클릭
            result = self.auto_click_survey_button_in_agree_popup()
            
            # 작업을 마친 팝업 창(VOD/설문진입창) 닫기
            try:
                current_handle = self.web_automation.driver.current_window_handle
                if current_handle and current_handle != original_window:
                    self.web_automation.driver.close()
                    self.log_info("🧹 현재 팝업 창을 닫았습니다.")
            except:
                pass

            # 원래 창으로 돌아가기
            if original_window:
                self._recover_to_original_window(original_window)
            
            if isinstance(result, dict):
                return result
            elif result is False:
                return {"success": False, "reason": "failed", "message": "설문 작성 및 제출 실패"}
            return {"success": True}
            
        except Exception as e:
            err_msg = str(e)
            if "no such window" in err_msg or "window already closed" in err_msg:
                if original_window:
                    self._recover_to_original_window(original_window)
                self.log_warning("사용자가 설문 창을 닫아 작업을 중단합니다.")
                return {"success": False, "reason": "user_cancelled", "message": "사용자가 설문 창을 닫았습니다."}
            self.log_error(f"팝업 창에서 설문참여 버튼 클릭 실패: {err_msg}")
            
            if original_window:
                self._recover_to_original_window(original_window)
            
            return {"success": False, "reason": "failed", "message": f"팝업 창에서 설문참여 버튼 클릭 실패: {err_msg}"}
    
    def auto_click_survey_button_in_agree_popup(self):
        """개인정보 동의 팝업에서 설문하기 버튼을 자동으로 클릭합니다."""
        try:
            self.log_info("개인정보 동의 팝업 대기 중...")
            
            # 개인정보 동의 팝업이 나타날 때까지 대기
            self.web_automation.wait.until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "#agreeInfo"))
            )
            
            self.log_info("개인정보 동의 팝업 발견")
            self.log_info("동의 체크박스 자동 체크 중...")
            
            # 동의 체크박스 자동 체크
            try:
                agree_checkbox = self.find_element_safe(By.CSS_SELECTOR, "#agreeInfo #agree")
                
                # 체크박스가 체크되지 않은 경우에만 체크
                if not agree_checkbox.is_selected():
                    try:
                        agree_checkbox.click()
                    except Exception:
                        self.web_automation.driver.execute_script("arguments[0].click();", agree_checkbox)
                    self.log_info("✅ 동의 체크박스 자동 체크 완료")
                else:
                    self.log_info("동의 체크박스가 이미 체크되어 있습니다")
                        
            except Exception as e:
                self.log_warning(f"동의 체크박스 처리 중 오류: {str(e)}")
            
            # 설문하기 버튼 찾기 및 클릭
            self.log_info("설문하기 버튼 검색 중...")
            
            # 설문하기 버튼 찾기 (안전하게)
            survey_button = self.find_element_safe(By.CSS_SELECTOR, "#agreeInfo .btn_answer")
            
            self.log_info("설문하기 버튼 발견")
            
            # 버튼 클릭
            survey_button.click()
            
            self.log_info("✅ 설문하기 버튼 자동 클릭 완료")
            self.log_info("설문 페이지로 이동 중...")
            self.log_info("새로운 설문 창에서 자동 답변을 시작합니다...")
            
            # 🔥 새로운 설문 창에서 자동 답변 및 제출
            result = self.auto_fill_and_submit_survey()
            if isinstance(result, dict):
                return result
            elif result is False:
                return {"success": False, "reason": "failed", "message": "설문 답변 작성 실패"}
            return {"success": True}
            
        except Exception as e:
            err_msg = str(e)
            if "no such window" in err_msg or "window already closed" in err_msg:
                try:
                    handles = self.web_automation.driver.window_handles
                    if handles:
                        self.web_automation.driver.switch_to.window(handles[0])
                except:
                    pass
                self.log_warning("사용자가 동의 팝업 창을 닫아 작업을 중단합니다.")
                return {"success": False, "reason": "user_cancelled", "message": "사용자가 동의 팝업 창을 닫았습니다."}
            self.log_error(f"개인정보 동의 팝업에서 설문하기 버튼 클릭 실패: {err_msg}")
            return {"success": False, "reason": "failed", "message": f"개인정보 동의 팝업에서 설문하기 버튼 클릭 실패: {err_msg}"}
    
    def auto_fill_and_submit_survey(self):
        """새로운 설문 창에서 모든 질문의 첫 번째 보기를 자동 선택하고 제출합니다."""
        try:
            self.log_info("새로운 설문 창 대기 중...")
            
            # 새로운 설문 창이 열릴 때까지 대기
            time.sleep(3)  # 설문 창 로딩 대기 (1초 → 3초로 증가)
            
            # 현재 열려있는 모든 창 핸들 가져오기
            original_window = self.web_automation.driver.current_window_handle
            all_windows = self.web_automation.driver.window_handles
            
            # 새로 열린 설문 창 찾기
            survey_window = None
            for window in all_windows:
                if window != original_window:
                    # 설문 창인지 확인 (URL에 survey.villeway.com이 포함된 창)
                    try:
                        self.web_automation.driver.switch_to.window(window)
                        if "survey.villeway.com" in self.web_automation.driver.current_url:
                            survey_window = window
                            break
                    except:
                        continue
            
            if not survey_window:
                self.log_error("❌ 새로운 설문 창을 찾을 수 없습니다")
                return {"success": False, "reason": "failed", "message": "새로운 설문 창을 찾을 수 없습니다"}
            
            self.log_info("설문 창으로 전환 완료")
            self.log_info("설문 페이지 로딩 대기 중...")
            
            # 설문 페이지 로딩 완료 대기
            self.find_element_safe(By.CSS_SELECTOR, "form[id^='surveyForm']")
            
            self.log_info("설문 페이지 로딩 완료")
            self.log_info("여러 페이지 설문 처리 시작...")
            
            # 🔥 팝업 확인 및 처리
            self.handle_survey_popup()
            
            # 🔥 여러 페이지 설문 처리 (간단한 방식)
            page_count = 1
            
            while True:
                self.log_info(f"=== {page_count}페이지 처리 중 ===")
                
                # 현재 페이지에서 문제 순서대로 하나씩 처리
                if not self.auto_fill_questions_in_order():
                    self.log_error("퀴즈 정답 미등록으로 설문 자동 답변을 중단합니다.")
                    return {"success": False, "reason": "failed", "message": "퀴즈 정답 미등록으로 설문 자동 답변 중단"}
                
                # 🔥 모든 필수 항목이 제대로 채워졌는지 확인
                if not self.validate_required_fields():
                    self.log_warning("필수 항목이 모두 채워지지 않았습니다. 재시도합니다...")
                    
                    # 재시도: 안 채워진 부분만 다시 채우기
                    if not self.retry_fill_missing_fields():
                        self.log_error("재시도 후에도 필수 항목이 채워지지 않았습니다. 설문 제출을 중단합니다.")
                        return {"success": False, "reason": "failed", "message": "필수 항목이 채워지지 않아 설문 제출 중단"}
                    else:
                        self.log_success("재시도 후 모든 필수 항목이 채워졌습니다.")
                
                self.log_info(f"{page_count}페이지 답변 완료")
                
                # 페이지 하단 버튼 확인
                try:
                    footer_button = self.find_element_safe(
                        By.CSS_SELECTOR, 
                        'footer input[type="submit"][value="다음"], footer input[type="submit"][value="제출하기"]'
                    )
                    
                    # 버튼 텍스트 확인
                    button_text = footer_button.get_attribute('value') or footer_button.text
                    
                    self.log_info(f"페이지 하단 버튼 발견: {button_text}")
                    
                    if "다음" in button_text:
                        # 다음 버튼 클릭
                        self.log_info("다음 버튼 클릭, 다음 페이지로 이동...")
                        footer_button.click()
                        
                        # 다음 페이지 로딩 대기
                        time.sleep(2)
                        
                        # 다음 페이지에서 답변할 수 있도록 대기
                        try:
                            self.find_element_safe(By.CSS_SELECTOR, "form[id^='surveyForm']", timeout=10)
                        except Exception:
                            self.log_warning("다음 페이지 로딩 대기 시간 초과, 계속 진행...")
                        
                        page_count += 1
                        
                    elif "제출하기" in button_text:
                        # [수정] 설문 자동 제출 설정 확인
                        auto_submit = True
                        if hasattr(self, 'gui_callbacks') and 'gui_instance' in self.gui_callbacks:
                            try:
                                auto_submit = self.gui_callbacks['gui_instance'].get_setting('auto_survey_submit')
                            except Exception as se:
                                self.log_warning(f"설정 로드 실패로 자동 제출을 활성화합니다: {se}")
                                
                        quiz_result_msg = None
                        if auto_submit:
                            self.log_info("제출하기 버튼 발견, 설문 자동 제출 중...")
                            footer_button.click()
                            self.log_success("설문 제출 완료!")
                            break  # 반복문 종료
                        else:
                            self.log_warning("⚠️ 설문 자동 제출이 비활성화되어 있습니다.")
                            
                            # 안내 팝업 메시지
                            try:
                                def run_popup():
                                    msg = "📋 설문 답변 작성이 완료되었습니다.\n\n브라우저 창에서 입력 내용을 확인하시고 직접 [제출하기] 버튼을 클릭해 완료해주세요."
                                    ctypes.windll.user32.MessageBoxW(0, msg, "DVA 설문 알림", 0x40 | 0x1000)
                                threading.Thread(target=run_popup, daemon=True).start()
                            except:
                                pass
                            
                            # 사용자가 직접 제출을 누르고 설문 창이 닫힐 때까지 대기
                            self.log_info("⌛ 사용자의 수동 제출 완료를 대기합니다 (대기 시간 최대 10분)...")
                            start_wait = time.time()
                            user_closed = False
                            while time.time() - start_wait < 600:
                                # 세션 유효성 확인
                                try:
                                    _ = self.web_automation.driver.title
                                except:
                                    user_closed = True
                                    break
                                    
                                try:
                                    handles = self.web_automation.driver.window_handles
                                    if survey_window not in handles:
                                        user_closed = True
                                        break
                                        
                                    # [추가] 수동 제출 시에도 outro 페이지 감시하여 결과 가로채기
                                    current_url = self.web_automation.driver.current_url
                                    if "outro" in current_url:
                                        self.log_success("outro 페이지 감지! 수동 제출 성공으로 판단합니다.")
                                        quiz_result_msg = self._get_quiz_result_from_outro()
                                        break
                                except:
                                    user_closed = True
                                    break
                                time.sleep(1)
                                
                            if user_closed:
                                self.log_success("설문 창이 닫혔습니다. 수동 제출 완료로 판단하여 진행합니다.")
                            else:
                                if not quiz_result_msg:
                                    self.log_error("❌ 수동 제출 대기 시간(10분)이 초과되어 대기를 중단합니다.")
                                
                            break  # 반복문 종료
                        
                    else:
                        # 예상하지 못한 버튼
                        self.log_warning(f"예상하지 못한 버튼: {button_text}")
                        break
                        
                except NoSuchElementException:
                    self.log_info("페이지 하단 버튼을 찾을 수 없습니다")
                    break
                except Exception as e:
                    self.log_warning(f"버튼 처리 중 오류: {str(e)}")
                    break
            
            self.log_info(f"총 {page_count}페이지 처리 완료")
            
            # auto_submit인 경우 또는 수동 감지 시 아직 획득하지 못한 경우 팝업 및 결과 확인 시도
            if auto_submit:
                # 확인 팝업 처리
                self._handle_submit_confirmation_popup()
                # outro 결과 추출
                quiz_result_msg = self._get_quiz_result_from_outro()
            
            # 제출이 완료된 설문 창 닫기
            try:
                current_handle = self.web_automation.driver.current_window_handle
                if current_handle and current_handle == survey_window:
                    self.web_automation.driver.close()
                    self.log_info("🧹 제출이 완료된 설문 창을 닫았습니다.")
            except:
                pass

            # 원래 창으로 돌아가기
            try:
                self.web_automation.driver.switch_to.window(original_window)
            except:
                pass
            
            # 포인트 확인 모듈 실행은 상위로직(execute의 finally)에서 일괄 처리합니다.
            
            return {"success": True, "quiz_result": quiz_result_msg}
            
        except Exception as e:
            err_msg = str(e)
            if "no such window" in err_msg or "window already closed" in err_msg:
                try:
                    handles = self.web_automation.driver.window_handles
                    if original_window in handles:
                        self.web_automation.driver.switch_to.window(original_window)
                    elif handles:
                        self.web_automation.driver.switch_to.window(handles[0])
                except:
                    pass
                self.log_warning("사용자가 설문 창을 닫아 작업을 중단합니다.")
                return {"success": False, "reason": "user_cancelled", "message": "사용자가 설문 창을 닫았습니다."}
            self.log_error(f"설문 자동 답변 및 제출 실패: {err_msg}")
            
            # 오류 발생 시 원래 창으로 돌아가기
            try:
                self.web_automation.driver.switch_to.window(original_window)
            except:
                pass
            
            return {"success": False, "reason": "failed", "message": err_msg}
    
    def handle_survey_popup(self):
        """설문 시작 시 나타날 수 있는 팝업을 처리합니다."""
        try:
            self.log_info("설문 시작 팝업 확인 중...")
            
            # 팝업이 나타날 때까지 동적 대기
            try:
                popup_container = self.find_element_safe(By.CSS_SELECTOR, "#headlessui-portal-root", timeout=5)
                
                self.log_info("팝업 발견, 닫기 버튼 검색 중...")
                
                # 팝업 내부에 "닫기" 버튼이 있는지 확인
                try:
                    close_button = popup_container.find_element(
                        By.XPATH, 
                        './/button[contains(text(), "닫기")]'
                    )
                    
                    if close_button:
                        self.log_info("설문 시작 팝업 발견, 닫기 버튼 클릭 중...")
                        
                        # 닫기 버튼 클릭
                        close_button.click()
                        
                        self.log_success("설문 시작 팝업 닫기 완료")
                        
                        # 팝업이 사라질 때까지 짧게 대기
                        time.sleep(0.5)
                        
                except NoSuchElementException:
                    # "닫기" 텍스트가 없는 경우, btn-primary 클래스를 가진 버튼 찾기
                    try:
                        close_button = popup_container.find_element(
                            By.CSS_SELECTOR, 
                            'button.btn-primary'
                        )
                        
                        if close_button:
                            self.log_info("팝업 버튼 발견 (btn-primary), 클릭 중...")
                            
                            # 버튼 클릭
                            close_button.click()
                            
                            self.log_success("팝업 버튼 클릭 완료")
                            
                            # 팝업이 사라질 때까지 짧게 대기
                            time.sleep(0.5)
                            
                    except NoSuchElementException:
                        self.log_info("팝업은 있지만 닫기 버튼을 찾을 수 없습니다")
                        
                except Exception as e:
                    self.log_warning(f"닫기 버튼 처리 중 오류: {str(e)}")
                        
            except TimeoutException:
                self.log_info("설문 시작 팝업이 없습니다. 바로 진행합니다.")
            except Exception as e:
                self.log_warning(f"팝업 처리 중 오류: {str(e)}")
                    
        except Exception as e:
            self.log_warning(f"팝업 확인 중 오류: {str(e)}")
    
    def _handle_submit_confirmation_popup(self):
        """제출 확인 팝업에서 확인 버튼을 자동으로 클릭합니다."""
        try:
            # 팝업이 나타날 때까지 대기
            time.sleep(2)
            
            # 확인 버튼 찾기 (여러 방법 시도)
            confirm_selectors = [
                "//button[contains(text(), '확인')]",
                "//input[@value='확인']", 
                "//button[contains(@class, 'btn') and contains(text(), '확인')]",
                "//div[contains(@class, 'popup')]//button[contains(text(), '확인')]"
            ]
            
            confirm_button = None
            for selector in confirm_selectors:
                try:
                    confirm_button = self.web_automation.driver.find_element(By.XPATH, selector)
                    if confirm_button:
                        break
                except:
                    continue
            
            if confirm_button:
                self.log_info("확인 팝업 발견, 확인 버튼 클릭 중...")
                
                confirm_button.click()
                
                self.log_success("확인 팝업 처리 완료")
            else:
                self.log_warning("확인 팝업을 찾을 수 없습니다")
                    
        except Exception as e:
            self.log_warning(f"확인 팝업 처리 중 오류: {str(e)}")
    
    def _get_quiz_result_from_outro(self):
        """설문 완료(outro) 페이지에서 퀴즈 결과 텍스트를 추출합니다."""
        try:
            # outro 페이지 로딩 대기 (최대 5초)
            WebDriverWait(self.web_automation.driver, 5).until(
                EC.url_contains("/outro")
            )
            time.sleep(1)  # 텍스트 렌더링 대기
            
            # body 텍스트 가져오기
            body_text = self.web_automation.driver.find_element(By.TAG_NAME, "body").text
            
            # 퀴즈 결과 관련 텍스트 추출 (예: "[퀴즈] 퀴즈 3문항 중 2문항 정답으로...")
            for line in body_text.split('\n'):
                line = line.strip()
                if "[퀴즈]" in line and "정답" in line:
                    return line
            
            # 대안으로 "지급됩니다" 또는 "문항 중" 등의 키워드로 검색
            for line in body_text.split('\n'):
                line = line.strip()
                if "문항 중" in line and "정답" in line:
                    return line
                    
            return None
        except Exception as e:
            self.log_warning(f"outro 페이지 결과 추출 중 오류: {str(e)}")
            return None

    def _run_points_check_module(self):
        """설문 완료 후 포인트 확인 모듈을 실행합니다 - BaseModule의 공통 메서드 사용"""
        self.check_points_after_activity()
    
    def validate_required_fields(self):
        """모든 필수 항목이 제대로 채워졌는지 확인합니다."""
        try:
            missing_fields = []
            
            # 설문 폼 요소 찾기 (범위 제한)
            try:
                form = self.web_automation.driver.find_element(By.CSS_SELECTOR, "form[id^='surveyForm']")
            except:
                # 폼을 찾을 수 없으면 전체 드라이버 사용
                form = self.web_automation.driver

            # 1. 라디오 버튼 그룹별로 하나씩 선택되었는지 확인
            radio_groups = form.find_elements(By.CSS_SELECTOR, 'input[type="radio"]')
            processed_groups = set()
            
            for radio in radio_groups:
                try:
                    # 보이지 않는 요소는 건너뜀 (다른 페이지 요소 등)
                    if not radio.is_displayed():
                        continue
                        
                    name = radio.get_attribute('name')
                    if name and name not in processed_groups:
                        # 해당 그룹에서 선택된 라디오 버튼이 있는지 확인
                        try:
                            # 폼 내에서 해당 이름의 체크된 라디오 버튼 검색
                            checked_selector = f'input[type="radio"][name="{name}"]:checked'
                            form.find_element(By.CSS_SELECTOR, checked_selector)
                        except:
                            missing_fields.append(f"라디오 버튼 그룹 '{name}'")
                        processed_groups.add(name)
                except Exception as ie:
                    self.log_warning(f"라디오 버튼 확인 중 개별 오류: {str(ie)}")
            
            # 2. 텍스트 입력 필드가 비어있지 않은지 확인
            text_inputs = form.find_elements(By.CSS_SELECTOR, 'input[type="text"]')
            for i, text_input in enumerate(text_inputs):
                try:
                    if text_input.is_displayed() and not text_input.get_attribute('value').strip():
                        missing_fields.append(f"텍스트 입력 필드 {i+1}번")
                except:
                    continue
            
            # 3. 이메일 필드가 유효한 이메일 형식인지 확인
            email_inputs = form.find_elements(By.CSS_SELECTOR, 'input[type="email"]')
            for i, email_input in enumerate(email_inputs):
                try:
                    if email_input.is_displayed():
                        email_value = email_input.get_attribute('value').strip()
                        if not email_value or '@' not in email_value:
                            missing_fields.append(f"이메일 필드 {i+1}번")
                except:
                    continue
            
            # 4. textarea 필드가 비어있지 않은지 확인
            textarea_inputs = form.find_elements(By.CSS_SELECTOR, 'textarea')
            for i, textarea in enumerate(textarea_inputs):
                try:
                    if textarea.is_displayed() and not textarea.get_attribute('value').strip():
                        missing_fields.append(f"textarea 필드 {i+1}번")
                except:
                    continue
            
            # 5. 체크박스 필드가 최소 1개 이상 선택되었는지 확인 (보이는 것만)
            checkboxes = form.find_elements(By.CSS_SELECTOR, 'input[type="checkbox"]')
            visible_checkboxes = [cb for cb in checkboxes if cb.is_displayed()]
            
            if visible_checkboxes:
                checked_visible = [cb for cb in visible_checkboxes if cb.is_selected()]
                if not checked_visible:
                    # 필수 항목인지 여부를 확인하기 어려우므로 경고만 하고 missing에는 추가하지 않음 (유연한 대응)
                    self.log_warning("체크박스가 하나도 선택되지 않았습니다. (선택 항목일 수 있음)")
            
            if missing_fields:
                self.log_error(f"채워지지 않은 필수 항목: {', '.join(missing_fields)}")
                return False
            
            self.log_success("모든 필수 항목이 올바르게 채워졌습니다")
            return True
            
        except Exception as e:
            import traceback
            error_details = traceback.format_exc()
            self.log_error(f"필수 항목 검증 중 오류: {type(e).__name__} - {str(e)}")
            self.log_info(f"상세 오류 내역: {error_details.splitlines()[-1]}")
            return False
    
    def retry_fill_missing_fields(self):
        """안 채워진 필수 항목만 다시 채우기"""
        try:
            self.log_info("재시도: 안 채워진 필수 항목을 다시 채우는 중...")
            
            # 1. 라디오 버튼 그룹별로 안 선택된 것들 다시 선택
            radio_groups = self.web_automation.driver.find_elements(By.CSS_SELECTOR, 'input[type="radio"]')
            processed_groups = set()
            
            for radio in radio_groups:
                name = radio.get_attribute('name')
                if name and name not in processed_groups:
                    try:
                        # 해당 그룹에서 선택된 라디오 버튼이 있는지 확인
                        selected_radio = self.web_automation.driver.find_element(
                            By.CSS_SELECTOR, f'input[type="radio"][name="{name}"]:checked'
                        )
                    except:
                        # 선택되지 않은 경우 첫 번째 라디오 버튼 클릭
                        try:
                            first_radio = self.web_automation.driver.find_element(
                                By.CSS_SELECTOR, f'input[type="radio"][name="{name}"]'
                            )
                            first_radio.click()
                            self.log_info(f"재시도: 라디오 버튼 그룹 '{name}' 첫 번째 옵션 선택")
                        except:
                            pass
                    processed_groups.add(name)
            
            # 2. 텍스트 입력 필드가 비어있는 것들 다시 채우기
            text_inputs = self.web_automation.driver.find_elements(By.CSS_SELECTOR, 'input[type="text"]')
            for i, text_input in enumerate(text_inputs):
                if not text_input.get_attribute('value').strip():
                    try:
                        # 최소 글자수 제한이 있는지 확인
                        parent_li = text_input.find_element(By.XPATH, "./ancestor::li")
                        if self._get_char_limits(parent_li).get("min"):
                            self.log_warning(f"재시도: 텍스트 입력 필드 {i+1}번은 글자수 제한이 있어 자동 입력을 건너뜁니다.")
                            continue
                            
                        text_input.clear()
                        text_input.send_keys("없습니다.")
                        self.log_info(f"재시도: 텍스트 입력 필드 {i+1}번 답변 입력")
                    except:
                        pass
            
            # 3. 이메일 필드가 유효하지 않은 것들 다시 채우기
            email_inputs = self.web_automation.driver.find_elements(By.CSS_SELECTOR, 'input[type="email"]')
            for i, email_input in enumerate(email_inputs):
                email_value = email_input.get_attribute('value').strip()
                if not email_value or '@' not in email_value:
                    try:
                        email_input.clear()
                        email_input.send_keys("a@gmail.com")
                        self.log_info(f"재시도: 이메일 필드 {i+1}번 답변 입력")
                    except:
                        pass
            
            # 4. textarea 필드가 비어있는 것들 다시 채우기
            textarea_inputs = self.web_automation.driver.find_elements(By.CSS_SELECTOR, 'textarea')
            for i, textarea in enumerate(textarea_inputs):
                if not textarea.get_attribute('value').strip():
                    try:
                        # 최소 글자수 제한이 있는지 확인
                        parent_li = textarea.find_element(By.XPATH, "./ancestor::li")
                        if self._get_char_limits(parent_li).get("min"):
                            self.log_warning(f"재시도: textarea {i+1}번은 글자수 제한이 있어 자동 입력을 건너뜁니다.")
                            continue

                        textarea.clear()
                        textarea.send_keys("없습니다.")
                        self.log_info(f"재시도: textarea 필드 {i+1}번 답변 입력")
                    except:
                        pass
            
            # 5. 체크박스가 하나도 선택되지 않은 경우 다시 선택
            checkbox_inputs = self.web_automation.driver.find_elements(By.CSS_SELECTOR, 'input[type="checkbox"]')
            if checkbox_inputs:
                selected_checkboxes = self.web_automation.driver.find_elements(By.CSS_SELECTOR, 'input[type="checkbox"]:checked')
                if not selected_checkboxes:
                    try:
                        # sr-only나 readonly가 아닌 실제 클릭 가능한 체크박스 찾기
                        clickable_checkbox = None
                        for checkbox in checkbox_inputs:
                            # 보이지 않는 것은 건너뜀
                            if not checkbox.is_displayed():
                                continue
                                
                            # sr-only 클래스나 readonly 속성이 없는 체크박스 찾기
                            checkbox_class = checkbox.get_attribute('class') or ''
                            checkbox_readonly = checkbox.get_attribute('readonly')
                            
                            if 'sr-only' not in checkbox_class and not checkbox_readonly:
                                clickable_checkbox = checkbox
                                break
                        
                        # 클릭 가능한 체크박스를 찾지 못한 경우, 첫 번째 보이는 것 시도
                        if not clickable_checkbox:
                            for cb in checkbox_inputs:
                                if cb.is_displayed():
                                    clickable_checkbox = cb
                                    break
                        
                        if clickable_checkbox and not clickable_checkbox.is_selected():
                            clickable_checkbox.click()
                            self.log_info("재시도: 체크박스 선택")
                    except:
                        pass
            
            # 재시도 후 다시 검증
            return self.validate_required_fields()
            
        except Exception as e:
            self.log_error(f"재시도 중 오류: {str(e)}")
            return False
    
    def auto_fill_questions_in_order(self):
        """문제 순서대로 하나씩 처리합니다."""
        try:
            self.log_info("문제 순서대로 처리 시작...")
            
            # 모든 질문 요소를 순서대로 찾기
            questions = self.web_automation.driver.find_elements(
                By.CSS_SELECTOR, 
                'li[data-question-number]'
            )
            
            processed_count = 0
            
            for question in questions:
                # 세션 유효성 확인
                try:
                    _ = self.web_automation.driver.title
                except:
                    return False

                try:
                    question_number = question.get_attribute('data-question-number')
                    if not question_number:
                        continue
                    
                    self.log_info(f"문제 {question_number}번 처리 중...")
                    
                    # 🔥 문제 제목 추출 (퀴즈 여부 판단용)
                    question_text = ""
                    try:
                        # 실제 HTML 구조: li > label > div.whitespace-pre-wrap
                        text_elem = question.find_element(By.CSS_SELECTOR, 'div.whitespace-pre-wrap')
                        
                        # div 안의 모든 텍스트 추출 (span[퀴즈] 포함)
                        question_text = text_elem.text.strip() if text_elem else ""
                        
                        if not question_text:
                            # 대체 선택자
                            try:
                                question_text = question.find_element(By.CSS_SELECTOR, 'label').text.strip()
                            except:
                                pass
                    except:
                        # 제목을 찾지 못한 경우 빈 문자열 사용
                        question_text = ""
                    
                    # 문제 제목 정규화 (저장된 정답과 비교하기 위해)
                    normalized_question = self._normalize_question_text(question_text)
                    
                    # 각 질문에서 첫 번째 input/textarea 요소만 찾아서 유형별로 바로 처리
                    question_processed = False
                    
                    try:
                        # 첫 번째 input 또는 textarea 요소 찾기
                        first_input = question.find_element(By.CSS_SELECTOR, 'input, textarea')
                        input_type = first_input.get_attribute('type')
                        
                        # 🔥 [퀴즈] 문제 여부 확인
                        is_quiz = "[퀴즈]" in question_text
                        quiz_answer = None
                        
                        if is_quiz:
                            # 퀴즈 정답 조회 (원본 문제 텍스트로 - get_answer에서 정규화함)
                            quiz_answer = self.problem_manager.get_answer(question_text)
                            if quiz_answer:
                                self.log_success(f"퀴즈 정답 발견: {normalized_question[:40]}... → {quiz_answer}")
                            else:
                                self.log_warning(f"퀴즈이지만 정답 미등록: {normalized_question[:45]}...")
                                    
                            if not quiz_answer:
                                # 퀴즈지만 정답이 없는 경우, 보기 선택하지 않고 '설문문제' 창 띄우기
                                if hasattr(self, 'gui_callbacks') and 'gui_instance' in self.gui_callbacks:
                                    gui = self.gui_callbacks['gui_instance']
                                    if hasattr(gui, 'root') and hasattr(gui, 'open_survey_problem'):
                                        self.log_warning(f"문제 {question_number}번: 정답 미등록. 설문 문제 자동 관리 창을 엽니다.")

                                        # 카테고리 추출 (페이지 타이틀에서)
                                        category = ""
                                        try:
                                            title_text = self.web_automation.driver.title
                                            matches = re.findall(r'\(([^)]+)\)', title_text)
                                            if matches:
                                                last_paren = matches[-1]
                                                category = last_paren.split('_')[0].strip()
                                        except Exception:
                                            pass
                                            
                                        # 문제 텍스트에서 첫 줄만 추출 (보기 제외)
                                        display_question = ""
                                        for line in question_text.split('\n'):
                                            cleaned_line = line.strip()
                                            if cleaned_line:
                                                display_question = cleaned_line
                                                break
                                        
                                        # "1. " 같은 말머리 번호 제거
                                        display_question = re.sub(r'^\d+\.\s*', '', display_question)
                                        # [퀴즈] 태그 및 불필요한 별표(*) 제거
                                        display_question = display_question.replace('[퀴즈]', '').replace('*', '').strip()
                                            
                                        # 람다 함수로 인수 전달 (이미지 없이 정보만 전달)
                                        gui.root.after(0, lambda q=display_question, c=category: gui.open_survey_problem(initial_question=q, initial_category=c, image_path=None))
                                        
                                        # 정답이 새로 등록될 때까지 대기
                                        self.log_info(f"⌛ 문제 {question_number}번 정답이 등록될 때까지 대기합니다...")
                                        
                                        waiting_count = 0
                                        while True:
                                            # 세션 유효성 확인
                                            try:
                                                _ = self.web_automation.driver.title
                                            except:
                                                return False

                                            time.sleep(1.0)
                                            waiting_count += 1
                                            
                                            # 다시 정답 확인
                                            self.problem_manager.load_quizzes()
                                            new_answer = self.problem_manager.get_answer(question_text)
                                            if new_answer:
                                                quiz_answer = new_answer
                                                self.log_success(f"새로운 정답 확인완료, 답변을 계속 진행합니다: {quiz_answer}")
                                                break
                                                
                                            if waiting_count > 300: # 5분 타임아웃
                                                self.log_error("대기 시간(5분) 초과로 설문 자동 답변을 중단합니다.")
                                                return False
                                                
                            if not quiz_answer:
                                return False  # 전체 처리 중단 (gui를 열 수 없거나 팝업 이후 대기 타임아웃/오류 발생 시)
                        
                        if input_type == 'radio':
                            # 라디오 버튼: 퀴즈면 정답 선택, 아니면 첫 번째 옵션 선택
                            if is_quiz and quiz_answer:
                                # 퀴즈 정답에 해당하는 라디오 버튼 선택
                                try:
                                    radios = question.find_elements(By.CSS_SELECTOR, 'input[type="radio"]')
                                    answer_value = str(quiz_answer).strip()
                                    
                                    # DB 세부 정보 로드
                                    q_details = self.problem_manager.get_question_details(question_text)
                                    answer_num_val = q_details.get("answer_num", "") if q_details else ""
                                    radio_selected = False
                                    
                                    # 전략 1: 보기 텍스트로 먼저 찾아서 클릭 (우선순위 1)
                                    # answer_value가 숫자가 아닌 경우에만 텍스트 매칭 시도
                                    if not answer_value.isdigit():
                                        for idx, radio in enumerate(radios):
                                            try:
                                                option_text = self._get_radio_label_text(radio)
                                                if option_text and (answer_value.upper() in option_text.upper() or option_text.upper() in answer_value.upper()):
                                                    if not radio.is_selected():
                                                        radio.click()
                                                        self.log_success(f"문제 {question_number}번: 퀴즈 정답 텍스트 '{answer_value}' 선택 완료")
                                                        question_processed = True
                                                        radio_selected = True
                                                    break
                                            except:
                                                continue
                                                
                                    # 전략 2: 텍스트 매칭에 실패했거나 정답이 숫자인 경우, 번호(answer_num_val 또는 answer_value)로 선택 (우선순위 2 - Fallback)
                                    if not radio_selected:
                                        target_num = answer_value if answer_value.isdigit() else answer_num_val
                                        if target_num and target_num.isdigit():
                                            answer_num = int(target_num)
                                            if 1 <= answer_num <= len(radios):
                                                target_radio = radios[answer_num - 1]
                                                
                                                # 풀면서 정답 텍스트를 구하여 DB에 자동 업데이트(마이그레이션)
                                                try:
                                                    option_text = self._get_radio_label_text(target_radio)
                                                    if option_text:
                                                        matched_q = self.problem_manager.get_matched_question(question_text)
                                                        self.problem_manager.add_quiz(matched_q, option_text, "", answer_num=target_num)
                                                        self.log_success(f"문제 {question_number}번: 정답 번호 '{target_num}'를 보기 텍스트 '{option_text}'로 DB 자동 업데이트 완료")
                                                except Exception as e:
                                                    self.log_warning(f"보기 텍스트 자동 업데이트 실패: {str(e)}")
                                                    
                                                if not target_radio.is_selected():
                                                    target_radio.click()
                                                    self.log_info(f"문제 {question_number}번: 퀴즈 정답 번호 {target_num}번 선택")
                                                    question_processed = True
                                                    radio_selected = True
                                    
                                    # 정답을 찾지 못한 경우 첫 번째 선택
                                    if not radio_selected:
                                        if not first_input.is_selected():
                                            first_input.click()
                                            self.log_warning(f"문제 {question_number}번: 퀴즈 정답 '{answer_value}' 미등록, 첫 번째 옵션 선택")
                                            question_processed = True
                                except Exception as e:
                                    self.log_error(f"문제 {question_number}번 퀴즈 정답 선택 오류: {str(e)}")
                                    if not first_input.is_selected():
                                        first_input.click()
                                        question_processed = True
                            else:
                                # 일반 문제: 첫 번째 옵션 선택
                                if not first_input.is_selected():
                                    first_input.click()
                                    self.log_info(f"문제 {question_number}번: 라디오 버튼 첫 번째 옵션 선택")
                                    question_processed = True
                                
                        elif input_type == 'checkbox':
                            # 체크박스: 두 번째 체크박스 선택 (첫 번째는 sr-only)
                            checkbox_inputs = question.find_elements(By.CSS_SELECTOR, 'input[type="checkbox"]')
                            if len(checkbox_inputs) >= 2:
                                clickable_checkbox = checkbox_inputs[1]
                                if not clickable_checkbox.is_selected():
                                    clickable_checkbox.click()
                                    self.log_info(f"문제 {question_number}번: 체크박스 첫 번째 옵션 선택")
                                    question_processed = True
                                
                        elif input_type == 'text':
                            # 텍스트 입력: 글자수 제한 확인
                            char_limits = self._get_char_limits(question)
                            
                            # AI 답변 생성 시도
                            ai_answer = self._generate_ai_answer(question_text, char_limits)
                            
                            if ai_answer:
                                first_input.clear()
                                first_input.send_keys(ai_answer)
                                self.log_success(f"문제 {question_number}번: Gemini AI 자동 답변 입력 완료 ({len(ai_answer)}자)")
                                question_processed = True
                            else:
                                # Fallback: 기존 수동 또는 기본값 기입 로직
                                min_limit = char_limits.get("min")
                                if min_limit:
                                    self.log_warning(f"⚠️ {question_number}번 문제: 최소 {min_limit}자 제한이 발견되었습니다. 직접 입력을 대기합니다 (2분)...")
                                    if self._wait_for_manual_input(first_input, min_limit):
                                        self.log_success(f"✅ {question_number}번 문제: 직접 입력 확인 완료.")
                                        question_processed = True
                                    else:
                                        self.log_error(f"❌ {question_number}번 문제: 대기 시간 초과")
                                        return False
                                else:
                                    if not first_input.get_attribute('value').strip():
                                        first_input.clear()
                                        text_to_enter = "없습니다."
                                        first_input.send_keys(text_to_enter)
                                        self.log_info(f"문제 {question_number}번: 텍스트 '{text_to_enter}' 자동 입력 완료")
                                        question_processed = True
                                
                        elif input_type == 'email':
                            # 이메일 입력: "a@gmail.com" 입력
                            email_value = first_input.get_attribute('value').strip()
                            if not email_value or '@' not in email_value:
                                first_input.clear()
                                first_input.send_keys("a@gmail.com")
                                self.log_info(f"문제 {question_number}번: 이메일 입력 답변 완료")
                                question_processed = True
                                
                        elif first_input.tag_name == 'textarea': # input_type for textarea is usually None or empty string, so check tag_name
                            # 텍스트란 글자수 제한 확인
                            char_limits = self._get_char_limits(question)
                            
                            # AI 답변 생성 시도
                            ai_answer = self._generate_ai_answer(question_text, char_limits)
                            
                            if ai_answer:
                                first_input.clear()
                                first_input.send_keys(ai_answer)
                                self.log_success(f"문제 {question_number}번: Gemini AI 주관식 자동 답변 입력 완료 ({len(ai_answer)}자)")
                                question_processed = True
                            else:
                                # Fallback: 기존 로직
                                min_limit = char_limits.get("min")
                                if min_limit:
                                    self.log_warning(f"⚠️ {question_number}번 문제: 최소 {min_limit}자 주관식 제한이 발견되었습니다. 직접 입력을 대기합니다 (2분)...")
                                    if self._wait_for_manual_input(first_input, min_limit):
                                        self.log_success(f"✅ {question_number}번 문제: 주관식 직접 입력 확인 완료.")
                                        question_processed = True
                                    else:
                                        self.log_error(f"❌ {question_number}번 문제: 주관식 대기 시간 초과")
                                        return False
                                else:
                                    if not first_input.get_attribute('value'):
                                        text_to_enter = "없습니다."
                                        first_input.send_keys(text_to_enter)
                                        self.log_info(f"문제 {question_number}번: 주관식 '{text_to_enter}' 자동 입력 완료")
                                        question_processed = True
                                    else:
                                        self.log_info(f"문제 {question_number}번: 주관식 이미 입력되어 있음")
                                
                    except Exception as e:
                        self.log_error(f"문제 {question_number}번 처리 중 오류: {str(e)}")
                        pass
                    
                    if question_processed:
                        processed_count += 1
                    
                except Exception as e:
                    self.log_error(f"문제 {question_number}번 처리 중 오류: {str(e)}")
                    continue
            
            self.log_info(f"✅ 총 {processed_count}개 문제 순서대로 처리 완료")
            
            return True
            
        except Exception as e:
            self.log_error(f"문제 순서대로 처리 실패: {str(e)}")
            return False
    
    def _get_char_limits(self, question_elem):
        """질문 항목 내에 최소 및 최대 글자 수 제한이 있는지 확인하여 반환합니다."""
        limits = {"min": None, "max": None}
        try:
            text = question_elem.text
            
            # 최소 글자 수 추출
            if "최소" in text and "자" in text:
                match_min = re.search(r'최소\s*(\d+)\s*자', text)
                if match_min:
                    limits["min"] = int(match_min.group(1))
                    
            # 최대 글자 수 추출
            if "최대" in text and "자" in text:
                match_max = re.search(r'최대\s*(\d+)\s*자', text)
                if match_max:
                    limits["max"] = int(match_max.group(1))
        except Exception as e:
            self.log_warning(f"글자수 제한 판별 중 오류: {str(e)}")
            
        return limits

    def _wait_for_manual_input(self, input_elem, limit, timeout=600): # 10분으로 증가
        """사용자가 직접 최소 글자 수 이상 입력할 때까지 대기합니다."""
        # 팝업 알림 띄우기
        self._show_manual_input_alert(limit)
        
        start_time = time.time()
        while time.time() - start_time < timeout:
            # 세션 유효성 확인
            try:
                _ = self.web_automation.driver.title
            except:
                return False

            try:
                current_value = input_elem.get_attribute('value').strip()
                if len(current_value) >= limit:
                    return True
            except:
                pass
            
            time.sleep(1)
        return False

    def _show_manual_input_alert(self, limit):
        """윈도우 팝업 알림을 띄웁니다."""
        try:
            def run_popup():
                msg = f"⚠️ 주관식 답변에 최소 {limit}자 제한이 발견되었습니다.\n\n브라우저 창을 열어 직접 입력을 완료해주세요.\n(내용 입력 후 질문 창을 벗어나면 자동으로 다음 단계가 진행됩니다.)"
                # MB_OK(0) | MB_ICONINFORMATION(0x40) | MB_SYSTEMMODAL(0x1000)
                ctypes.windll.user32.MessageBoxW(0, msg, "DVA 설문 알림", 0x40 | 0x1000)
            
            threading.Thread(target=run_popup, daemon=True).start()
        except:
            pass

    def _normalize_question_text(self, question: str) -> str:
        
        # [퀴즈] 태그 제거
        cleaned = question.replace("[퀴즈]", "").strip()
        
        # 후행 특수문자 제거 (*, ?, 공백 등)
        cleaned = re.sub(r'[\*\?]+\s*$', '', cleaned).strip()
        
        # 여러 개의 공백을 단일 공백으로 정규화
        cleaned = re.sub(r'\s+', ' ', cleaned)
        
        return cleaned
    
    def auto_select_first_options(self):
        """모든 질문의 첫 번째 보기를 자동으로 선택하고 텍스트 필드에 점을 입력합니다."""
        try:
            # 1. 객관식 - 모든 라디오 버튼 그룹의 첫 번째 옵션 선택
            radio_groups = self.web_automation.driver.find_elements(By.CSS_SELECTOR, 'input[type="radio"]')
            selected_count = 0
            processed_groups = set()
            
            for radio in radio_groups:
                try:
                    name = radio.get_attribute('name')
                    if name not in processed_groups:
                        radio.click()
                        processed_groups.add(name)
                        selected_count += 1
                        self.log_info(f"객관식 {selected_count}번 첫 번째 보기 선택 완료")
                except:
                    continue
            
            # 2. 체크박스 - 모든 체크박스 그룹의 첫 번째 옵션 선택
            checkbox_inputs = self.web_automation.driver.find_elements(By.CSS_SELECTOR, 'input[type="checkbox"]')
            checkbox_count = 0
            
            for checkbox in checkbox_inputs:
                try:
                    # 체크박스가 체크되지 않은 경우에만 체크
                    if not checkbox.is_selected():
                        checkbox.click()
                        checkbox_count += 1
                        self.log_info(f"체크박스 {checkbox_count}번 선택 완료")
                except:
                    continue
            
            # 3. 주관식 - 텍스트 입력 필드에 "." 입력
            text_inputs = self.web_automation.driver.find_elements(By.CSS_SELECTOR, 'input[type="text"]')
            text_count = 0
            
            for text_input in text_inputs:
                try:
                    # 최소 글자수 제한이 있는지 확인
                    parent_li = text_input.find_element(By.XPATH, "./ancestor::li")
                    if self._get_char_limits(parent_li).get("min"):
                        self.log_warning(f"주관식 {text_count+1}번은 글자수 제한이 있어 자동 입력을 건너뜁니다.")
                        continue

                    text_input.clear()
                    text_input.send_keys("없습니다.")
                    text_count += 1
                    self.log_info(f"주관식 {text_count}번 답변 입력 완료")
                except:
                    continue
            
            # 4. 이메일 필드 - "a@gmail.com" 입력
            email_inputs = self.web_automation.driver.find_elements(By.CSS_SELECTOR, 'input[type="email"]')
            email_count = 0
            
            for email_input in email_inputs:
                try:
                    email_input.clear()
                    email_input.send_keys("a@gmail.com")
                    email_count += 1
                    self.log_info(f"이메일 {email_count}번 답변 입력 완료")
                except:
                    continue
            
            # 5. textarea 필드 - "." 입력
            textarea_inputs = self.web_automation.driver.find_elements(By.CSS_SELECTOR, 'textarea')
            textarea_count = 0
            
            for textarea in textarea_inputs:
                try:
                    # 최소 글자수 제한이 있는지 확인
                    parent_li = textarea.find_element(By.XPATH, "./ancestor::li")
                    if self._get_char_limits(parent_li).get("min"):
                        self.log_warning(f"textarea {textarea_count+1}번은 글자수 제한이 있어 자동 입력을 건너뜁니다.")
                        continue

                    textarea.clear()
                    textarea.send_keys("없습니다.")
                    textarea_count += 1
                    self.log_info(f"textarea {textarea_count}번 답변 입력 완료")
                except:
                    continue
            
            self.log_success(f"객관식 {selected_count}개, 체크박스 {checkbox_count}개, 주관식 {text_count}개, 이메일 {email_count}개, textarea {textarea_count}개 자동 답변 완료")
            
            return True
            
        except Exception as e:
            self.log_error(f"자동 답변 실패: {str(e)}")
            return False
