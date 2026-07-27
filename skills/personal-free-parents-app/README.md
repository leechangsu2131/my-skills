# one_parent_watch

Flutter로 만드는 부모 공동 놀이터 현황 앱입니다. 현재 핵심 화면은 네이버 지도에서 등록된 놀이터를 확인하고, 가까운 위치의 마커를 탐색하는 흐름입니다.

## 현재 상태

- `flutter_naver_map` 기반 네이버 지도 렌더링 확인
- Supabase `playgrounds` 조회 연결
- 실제 데이터 조회 실패 시 릴리스 빌드에서 데모 인물이나 가짜 현황을 표시하지 않음
- Android 앱 ID, namespace, MainActivity 패키지를 `com.example.one_parent_watch`로 통일

`00003_group_contract.sql`은 실제 모임 생성과 참여에 필요한 DB 호환 필드를 준비합니다. 원격 Supabase에 적용하기 전에는 중복된 기존 `00002` 마이그레이션의 적용 이력을 반드시 확인해야 합니다.

## 실행

```powershell
flutter pub get
flutter run -d emulator-5554
```

로컬 Android 환경에서 ADB가 PATH에 없다면 다음 경로를 사용합니다.

```powershell
C:\Users\lee21\AppData\Local\Android\Sdk\platform-tools\adb.exe devices
```

## 검증

```powershell
C:\flutter\bin\cache\dart-sdk\bin\dart.exe format lib\features\group\presentation\group_matching_page.dart
flutter analyze
flutter test
flutter build apk --debug
```

네이버 지도 설정과 변경 이력은 [ing.md](ing.md), 화면·제품 원칙은 [SKILL.md](SKILL.md)에 정리되어 있습니다.
