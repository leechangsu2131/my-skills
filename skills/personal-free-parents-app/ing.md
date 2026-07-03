# 🛝 한명만 앱 - 네이버 지도 SDK 401 오류 해결 및 장애 추적 기록 (ing.md)

이 문서는 '한명만' (One Parent Watch) 앱 개발 도중 발생한 네이버 지도 SDK 연동 오류의 히스토리와 해결 과정, 그리고 정상 로딩을 위한 최종 해결책을 기록한 트러블슈팅 문서입니다.

---

## 🚨 1. 주요 증상 (Symptom)
* **증상**: 앱 로그인 후 지도 화면 진입 시, 연두색/하늘색 핀만 꽂힌 채 배경 지도가 회색/하얀색 격자 무늬(Fallback Grid)로 표시되고 실감 지도가 로딩되지 않음.
* **디버그 콘솔 로그**:
  ```text
  E/NaverMap(13069): Authorization failed: [401] Unauthorized client
  ```
  * 네이버 인증 서버로부터 401(미인증 클라이언트) 오류를 응답받아 SDK 차단이 걸린 상태.

---

## 🔍 2. 발생 원인 및 추적 히스토리 (Root Causes & History)

### ❶ [해결] AndroidManifest.xml 메타데이터 키 규격 불일치
* **문제**: 레거시 네이버 SDK 규격인 `com.naver.maps.map.CLIENT_ID` 로 정의되어 있어 인증 헤더 전송 시 무시됨.
* **조치**: 최신 규격인 `com.naver.maps.map.NCP_KEY_ID` 로 변경 완료.

### ❷ [해결] NCP 콘솔 등록 패키지명 오타
* **문제**: 에뮬레이터 앱 빌드의 실제 패키지명(applicationId)은 `com.example.one_parent_watch` (언더바 `_`)였으나, NCP 콘솔 서비스 설정에는 `com.example.one.parent_watch` (점 `.`)으로 오타가 기재되어 불일치 판정됨.
* **조치**: 콘솔의 등록 정보를 제거하고, 올바른 패키지명인 **`com.example.one_parent_watch`**로 변경하여 저장 완료.

---

## 🛠️ 3. 최종 해결 조치 내역 (Official Resource Spec Integration)

### ❶ [해결] 공식 가이드 규격에 맞춘 `ncp_key_id.xml` 리소스 적용
* **문제**: `AndroidManifest.xml`에 직접 하드코딩하거나 이중으로 Client ID 메타데이터를 선언하는 방식은 네이버 지도 SDK 렌더러가 메타데이터를 파싱할 때 환경변수 및 타입 불일치 오류를 유발할 수 있습니다.
* **조치**: 공식 가이드(`https://navermaps.github.io/android-map-sdk/guide-ko/1.html`) 명세에 맞추어 `android/app/src/main/res/values/ncp_key_id.xml` 파일을 신설하여 키 값을 안전하게 격리하고, `AndroidManifest.xml`에서 리소스 참조 방식으로 연결했습니다.
  * **ncp_key_id.xml**:
    ```xml
    <?xml version="1.0" encoding="utf-8"?>
    <resources>
        <string name="naver_map_sdk_ncp_key_id" translatable="false">5x8vkw4tdj</string>
    </resources>
    ```
  * **AndroidManifest.xml**:
    ```xml
    <meta-data
        android:name="com.naver.maps.map.NCP_KEY_ID"
        android:value="@string/naver_map_sdk_ncp_key_id" />
    ```

### ❷ [해결] `android.permission.INTERNET` 인터넷 권한 추가
* **문제**: 네이버 지도가 렌더링에 필요한 타일 이미지를 네트워크 서버로부터 수신하기 위해서는 인터넷 권한이 필수적이나, 기존 프로젝트의 `AndroidManifest.xml`에는 해당 권한 선언이 누락되어 지도 로딩이 전면 차단되었습니다.
* **조치**: `AndroidManifest.xml` 최상단에 인터넷 권한을 추가하여 데이터 통신을 허용했습니다.
  ```xml
  <uses-permission android:name="android.permission.INTERNET" />
  ```

### ❸ [해결] 다트 단 `NaverMapSdk.instance.initialize` 다중인증 충돌 및 어설션 우회
* **문제**: 다트(Flutter) 단에서 `.env`에 정의된 `NAVER_MAP_CLIENT_ID`를 명시적으로 주입하며 `initialize` 메서드를 호출하는 방식이 네이티브 Manifest 리소스 파싱 주기와 충돌하여 401 오류를 재생산했습니다.
* **조치**: `lib/main.dart` 에서는 `NaverMapSdk.instance.initialize()`를 인자(clientId) 없이 호출하여 다트 단의 초기화 어설션(`isInitialized`) 요건만 충족시킵니다. 이후 실제 인증 키 획득은 네이티브 단의 `@string/naver_map_sdk_ncp_key_id` 리소스를 직접 참조하여 자동 연동되게 함으로써 `401 Unauthorized client` 오류를 완벽히 종식시켰습니다.

### ❹ [해결] 에뮬레이터 Impeller 그래픽 엔진 충돌로 인한 지도 렌더링 실패 우회 (Skia 스왑)
* **문제**: 401 인증을 해결한 이후에도 에뮬레이터 상에 아이보리색 격자만 보이고 타일 렌더링이 안 되는 현상은 Flutter 3.16+의 기본 그래픽 백엔드인 **Impeller**가 네이버 지도 SDK의 네이티브 TextureView/PlatformView와 쉐이더 호환성 충돌을 일으키기 때문이었습니다.
* **조치**: Flutter 빌드/실행 명령어에 **`--no-enable-impeller`** 지시어를 결합하여 Skia 렌더러로 앱을 실행시켰습니다. 이로써 아파트 동 라인, 도로선, 지리적 정보 및 마커 핀들이 화면 상에 100% 정상적이고 선명하게 출력되는 것을 스크린샷 캡처를 통해 확인 완료하였습니다.
  * **실행 명령어**: `flutter run -d "emulator-5554" --no-enable-impeller`

---

## 📌 4. 기타 오류 해결 내역
* **로그아웃 미동작 버그 해결**: '내 정보' 탭 최하단에 분홍빛 카드의 **[로그아웃]** 메뉴 위젯을 이식 완료하고 Supabase Auth `signOut` 및 라우팅 전이를 연계 완료하였습니다.
* **Riverpod ref lifecycle 크래시 해결**: 로그인 도중 비동기 실행이 지연되는 사이 위젯이 dispose되었을 때 발생하는 Riverpod context 꼬임 예외 방지를 위해 `login_page.dart` 에 `if (!mounted) return;` 안전 가드를 추가 조치했습니다.
* **FontWeight.w850 컴파일 에러 해결**: Flutter의 `FontWeight`에는 100단위 상만 존재하므로, 직접 입력한 `w850` 오타를 표준 상수인 `w900` 및 `w800`으로 일괄 교정하였습니다.

---

## 🎨 5. 디자인 시스템 및 프리미엄 UI 개편 (Design Overhaul)

* **테마 리브랜딩 ("어반 네온 & 소프트 모던")**:
  * 기존의 소박한 시골풍 양피지/갈색 조합에서 **세련된 테크 테마인 딥 인디고 퍼플(0xFF6366F1), 일렉트릭 시안(0xFF06B6D4), 민트 에메랄드(0xFF10B981)** 기반의 세련된 조화 톤으로 업그레이드하였습니다.
* **글래스모피즘(Glassmorphism) 폼 카드 이식**:
  * `login_page.dart` 의 로그인 폼 영역에 투명도 0.75의 반투명 백그라운드 필터(BackdropFilter Blur 16.0)와 퍼플 글로우 입체 쉐도우를 입혀 트렌디함을 부여하였습니다.
* **내 정보 탭 (`_MyInfoTab`) 리디자인**:
  * 밋밋하던 프로필 카드를 **딥 오로라 퍼플 선형 그라데이션(LinearGradient)**으로 감싸고, 페이스 리터칭 아바타 실루엣과 세련된 메뉴 카드로 전면 개편했습니다.
* **알림 탭 (`_NotificationTab`) 및 추천 장소 카드**:
  * 사각 카드를 라운드 모서리(Radius 18)와 투명 보더 테두리(glassBorder) 구조로 변경하여 시각적으로 맑고 고급스러운 깊이감을 연출했습니다.
* **실시간 감독 대시보드 (`supervision_dashboard_page.dart`) 리빌딩**:
  * 딥 슬레이트 블랙 미드나잇 밤하늘 배경에 **호흡하는 네온 게이지 원형 타이머(CircularProgressIndicator)**와 SOS 긴급 싸이렌의 플래시 애니메이션을 주입하여 세련된 관제 센터 스타일로 전면 리모델링 완료했습니다.

