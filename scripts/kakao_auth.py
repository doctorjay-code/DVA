import requests
import json
import webbrowser
from pathlib import Path

def setup_kakao_auth():
    settings_path = Path("data/settings.json")
    
    # 1. 기존 설정 로드
    if settings_path.exists():
        with open(settings_path, 'r', encoding='utf-8') as f:
            settings = json.load(f)
    else:
        settings = {}

    print("=== 카카오톡 알림 최초 인증 스크립트 ===")
    
    # 2. REST API Key 확인
    rest_api_key = settings.get('kakao_rest_api_key')
    if not rest_api_key:
        rest_api_key = input("카카오 REST API 키를 입력해주세요: ").strip()
        settings['kakao_rest_api_key'] = rest_api_key

    # 3. Redirect URI 확인 (기본값 설정)
    redirect_uri = settings.get('kakao_redirect_uri', "http://localhost")
    if not settings.get('kakao_redirect_uri'):
        settings['kakao_redirect_uri'] = redirect_uri

    # 4. 인증 URL 생성 및 브라우저 열기
    auth_url = (
        f"https://kauth.kakao.com/oauth/authorize?"
        f"client_id={rest_api_key}&"
        f"redirect_uri={redirect_uri}&"
        f"response_type=code&"
        f"scope=talk_message"
    )
    
    print("\n브라우저를 열어 카카오 로그인을 진행합니다...")
    print("로그인 및 동의 후, 주소창에 나타나는 URL을 확인해주세요.")
    print(f"예: {redirect_uri}/?code=여기에_있는_코드_내용")
    
    webbrowser.open(auth_url)

    # 5. 인가 코드(Code) 입력받기
    print("\n" + "="*50)
    auth_code = input("주소창의 'code=' 뒤에 있는 값을 복사해서 입력해주세요: ").strip()
    if not auth_code:
        print("코드가 입력되지 않았습니다. 종료합니다.")
        return

    # 6. 토큰 교환 요청
    token_url = "https://kauth.kakao.com/oauth/token"
    data = {
        "grant_type": "authorization_code",
        "client_id": rest_api_key,
        "redirect_uri": redirect_uri,
        "code": auth_code
    }
    
    print("\n토큰 발급 요청 중...")
    response = requests.post(token_url, data=data)
    result = response.json()

    if response.status_code == 200:
        # 7. 토큰 저장
        settings['kakao_access_token'] = result.get('access_token')
        settings['kakao_refresh_token'] = result.get('refresh_token')
        settings['kakao_notify_enabled'] = True  # 인증 성공 시 알림 활성화
        
        with open(settings_path, 'w', encoding='utf-8') as f:
            json.dump(settings, f, indent=2, ensure_ascii=False)
            
        print("\n\u2705 인증 및 토큰 발급 성공!")
        print(f"- Access Token: {settings['kakao_access_token'][:10]}...")
        print(f"- Refresh Token: {settings['kakao_refresh_token'][:10]}...")
        print("\n이제 프로그램에서 카카오톡 알림을 사용할 수 있습니다.")
    else:
        print(f"\n\u274c 토큰 발급 실패: {result.get('error_description', result.get('error'))}")

if __name__ == "__main__":
    setup_kakao_auth()
