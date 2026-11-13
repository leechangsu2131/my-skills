# 카카오 '나에게 보내기' 설정 가이드

메뉴 이름은 2026년 10월 기준 카카오 디벨로퍼스 콘솔 표기다. 화면이 다르면 비슷한 이름의 메뉴를 찾도록 안내한다. 문서가 바뀔 수 있으니 의심되면 developers.kakao.com의 메시지 REST API 문서를 확인한다.

## 1. 앱과 키

1. developers.kakao.com 로그인 → 내 애플리케이션 → 앱 추가. 개인용이라 이름은 자유.
2. **[앱] > [플랫폼 키] > [REST API 키]**에서 REST API 키 확인 → `KAKAO_REST_API_KEY`.
3. 같은 화면의 **클라이언트 시크릿**: REST API 키는 클라이언트 시크릿이 기본으로 켜져 있어 토큰 발급·갱신 요청에 `client_secret`을 넣어야 한다 → `KAKAO_CLIENT_SECRET`.
   - 화면에 "카카오 로그인"용과 "비즈니스 인증"용이 나뉘어 있으면 **카카오 로그인용**을 쓴다. 리다이렉트 URI도 로그인 쪽에 등록한다.

## 2. 앱 설정 세 가지 + 도메인

- **리다이렉트 URI**: `http://localhost:3000/oauth` 등록. 안 하면 KOE006.
- **[카카오 로그인] > [사용 설정]**: 상태 ON. OFF면 KOE004.
- **[카카오 로그인] > [동의항목]**: 카카오톡 메시지 전송(`talk_message`) 설정.
- **[앱] > [제품 링크 관리] > [웹 도메인]**: 메시지 링크 도메인 등록. 영상 링크용으로 `https://www.youtube.com`. 등록하지 않으면 링크가 동작하지 않는다.

## 3. 리프레시 토큰 발급

1. 브라우저 주소창에 입력 (`REST키` 교체):

```
https://kauth.kakao.com/oauth/authorize?client_id=REST키&redirect_uri=http://localhost:3000/oauth&response_type=code&scope=talk_message
```

2. 로그인 후 동의하면 `http://localhost:3000/oauth?code=XXXX`로 이동한다. 페이지는 "사이트에 연결할 수 없음(ERR_CONNECTION_REFUSED)"으로 뜨는데 **정상**이다. 주소창에서 `code=` 뒤 문자열만 복사한다(`&`가 있으면 그 앞까지).
3. 코드는 **일회용이고 금방 만료**된다. 바로 아래를 실행한다.

윈도우 CMD:
```
curl -X POST https://kauth.kakao.com/oauth/token ^
  -d grant_type=authorization_code ^
  -d client_id=REST키 ^
  -d client_secret=클라이언트시크릿 ^
  -d redirect_uri=http://localhost:3000/oauth ^
  -d code=복사한코드
```
맥/리눅스/Git Bash는 줄 끝 `^` 대신 `\`.

4. 응답의 `refresh_token` → `KAKAO_REFRESH_TOKEN`. 유효기간은 응답의 `refresh_token_expires_in`(약 60일). `scope`에 `talk_message`가 있어야 한다.
5. 응답 전체를 대화에 붙여넣지 않도록 안내한다. 붙여넣었다면 클라이언트 시크릿 재발급 후 토큰 재발급을 권한다.

## 4. 토큰 갱신

- 액세스 토큰은 약 6시간. `main.py`는 실행할 때마다 리프레시 토큰으로 새 액세스 토큰을 받는다.
- 리프레시 토큰은 남은 기간이 1달 미만일 때 갱신하면 새 값이 오고 이전 값은 폐기된다. 새 값이 오면 `main.py`가 `new_refresh_token.txt`에 쓰고, 워크플로가 `GH_PAT`으로 `gh secret set KAKAO_REFRESH_TOKEN`을 실행해 Secrets를 갱신한다.
- `GH_PAT`: 깃허브 Settings → Developer settings → Fine-grained tokens → 해당 저장소만 선택 → Secrets: Read and write.

## 5. 오류 코드

| 증상 | 원인 |
|---|---|
| KOE006 | 리다이렉트 URI 미등록 또는 불일치 (로그인용/비즈니스 인증용 혼동 포함) |
| KOE004 | 카카오 로그인 사용 설정이 OFF |
| 토큰 요청 401/invalid_client | 클라이언트 시크릿 누락 또는 잘못된 값 |
| invalid_grant | 인가 코드를 이미 썼거나 만료 → 인가 주소를 다시 열어 새 코드 발급 |
| 메시지 전송 시 권한 오류 | `talk_message` 동의가 빠짐 → 인가 주소를 `scope=talk_message`로 다시 열어 동의 |

## 6. 친구에게 보내기

- 필요한 조건: 친구가 내 앱과 연결(앱에 로그인)된 상태, 친구 목록 제공 동의, 숨김·차단 친구가 아님, 프로필 공개 상태, 발송자의 메시지 전송 동의.
- **권한이 없으면 앱 팀 멤버만 가능**하다. 보낼 친구를 팀 멤버로 초대하고, 그 친구가 앱에 한 번 로그인해 동의해야 한다. 친구 목록 조회 API로 받은 uuid로 보낸다.
- 전체 사용자 대상 권한은 [앱] > [추가 기능 신청]에서 **비즈니스 정보 심사** 후 "카카오톡 친구 목록 / 메시지"를 신청해야 하고, 실제 동작 화면 첨부가 필요하다. 개인 자동화 용도는 통과가 어렵다고 보는 게 현실적이다. 신청 버튼이 막혀 있으면 Owner/Editor 권한과 비즈니스 정보 선행 여부를 확인한다.
- 수동으로 친구를 선택해 보내는 "카카오톡 공유하기"는 검수 없이 가능하지만 자동화에는 맞지 않는다.
