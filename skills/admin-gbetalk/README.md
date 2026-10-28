# 지비톡 요약 도구

Windows에 설치된 지비톡에서 **현재 열린 대화방 하나**의 텍스트를 가져와 요약합니다. 메시지를 전송하거나 대화방을 바꾸지 않습니다.

## 준비

PowerShell에서 도구 폴더로 이동한 뒤 Python 3.10 이상과 의존성을 설치합니다.

```powershell
cd "C:\경로\skills\admin-gbetalk"
python -m pip install -r requirements.txt
$env:ANTHROPIC_API_KEY = "발급받은 API 키"
```

API 키는 이 PowerShell 창에서만 사용할 수 있습니다. 키를 코드나 파일에 직접 적지 마세요. 사용할 수 있는 모델은 계정에서 접근 가능한 Anthropic 모델이어야 하며, 기본 모델은 `claude-sonnet-4-5`입니다. 변경하려면 `$env:ANTHROPIC_MODEL = "모델 ID"` 또는 `--model "모델 ID"`를 지정합니다.

## 1단계: 지비톡 화면 확인

지비톡을 직접 실행하고 로그인한 뒤, 요약할 대화방을 열어 둡니다. 프로그램은 로그인·인증을 대신하지 않습니다.

```powershell
python .\gbtalk_summary.py probe
```

지비톡 창이 여러 개라면 목록에서 번호를 확인하고 `--window 1`처럼 지정할 수 있습니다. 생성된 `out/probe_*.txt`에서 대화 문장이 보이면 UIA 읽기를 시도합니다. 컨트롤 트리에 대화가 없으면 UIA가 지원되지 않는 것이므로 클립보드 방식을 사용합니다.

## 요약하기

### UI Automation 방식

```powershell
python .\gbtalk_summary.py uia
```

### 클립보드 방식

지비톡에서 대화 내용을 선택해 복사한 뒤:

```powershell
python .\gbtalk_summary.py clipboard
```

이 명령은 복사한 내용을 곧바로 Anthropic API에 보내 요약합니다.

### 쪽지를 날짜별로 모아 두기

쪽지를 하나씩 열고 본문을 복사합니다. 복사한 내용을 **로컬에 저장만** 하려면 `archive`를 실행합니다.

왼쪽 탐색에서 **받은쪽지함**을 명시적으로 선택해야 합니다. 기본 **쪽지함** 목록은 보낸 쪽지를 섞어 보여 줄 수 있습니다. `UltariList` 아래의 현재 선택 행을 클릭하면 그 행에 포커스가 갑니다. 이때 포커스된 접근성 요소 번호가 목록의 선택 행 요소 번호와 일치하는지 확인한 뒤 `Home`/`↓`를 사용합니다. 본문 편집 컨트롤의 `Ctrl+A`, `Ctrl+C`도 전체 내용을 복사했습니다. 복사본의 줄바꿈 표기는 UIA 본문 값과 달랐지만 공백을 정규화했을 때 내용이 일치했습니다. 목록에서 `Ctrl+A`, `Ctrl+C`는 전체 쪽지 내보내기로 동작하지 않았습니다.

매 이동 직후 첫 UIA 응답이 이전 행을 보여 준 적이 있으므로 행과 본문 지문이 모두 바뀐 뒤 같은 쌍이 연속 확인될 때까지 다시 읽습니다. 한쪽만 갱신된 혼합 상태에서는 저장하지 않습니다. 선택 행이 정확히 `취소된 메시지입니다.`이면 미리보기 UIA 값에 직전 본문이 남을 수 있으므로 목록의 취소 표식을 placeholder 본문으로 사용합니다. 입력의 중심은 `Home`/`↓` 키보드 매크로이며, 본문은 UIA 값으로 읽습니다. 날짜는 접근성 트리에 수신 머리글 값이 있으면 먼저 사용하고, 없을 때만 같은 안정된 쪽지 화면의 머리글을 Windows OCR로 읽어 `received_date`(YYYY-MM-DD)를 기록합니다. 날짜 판독을 위해 행을 다시 열거나 이동하지 않습니다. 같은 날짜가 이어지면 날짜 값을 유지하고, 날짜가 바뀌면 체크포인트의 날짜 그룹 수를 갱신합니다. 화면에 연도가 나오지 않는 경우 기준 연도는 캡처 설정 또는 확인한 경계 연도에서 가져옵니다. 날짜 판독 실패, 행·본문 불일치, 날짜 역행이면 저장하지 않고 재개 위치를 남깁니다. 발신자는 UIA에서 신뢰할 수 있게 제공되지 않으므로 별도 검증이 필요합니다. 전달된 원문 시각은 수신 시각과 다를 수 있습니다. 날짜 OCR 한 건과 임시 목록 배치는 확인했지만, 날짜 경계가 바뀌는 실제 앱 순회와 2분 처리량은 아직 검증하지 않았습니다. 자동 입력 중에는 관리함이 전경으로 활성화됩니다.

날짜를 한 건씩 입력하며 보관하는 연속 모드가 있습니다. 복사한 본문과 입력한 날짜를 월별 Markdown에 저장하며, 기준일보다 오래된 날짜를 만나면 완료 처리합니다. 실행마다 체크포인트를 `inbox\.sessions\YYYY-MM-DD-month.json`에 원자적으로 기록하므로, 중단 후 재실행하면 마지막 저장 날짜와 발신자를 보여 줍니다. 목록에서 그 항목 다음의 더 오래된 쪽지부터 재개하세요. 기존 보관 파일만 있고 체크포인트가 없으면 가장 오래된 기록을 재개 경계로 사용합니다.

```powershell
python .\gbtalk_summary.py archive-session --before 2026-10-01 --period month
```

실행 중에는 각 쪽지의 수신 날짜/시각과 발신자/제목을 입력하고, 본문을 복사했는지 확인합니다. 보관 직전에 체크포인트에 쓰기 의도와 기존 파일 앞부분의 크기/해시를 기록하고, 월별 Markdown에 쪽지를 추가한 뒤 체크포인트를 확정합니다. 완전한 파일 추가 직후 프로그램이 종료되면 재실행 시 기존 앞부분과 추가 블록의 크기/해시를 모두 확인해 체크포인트를 복구하므로 같은 쪽지를 다시 입력할 필요가 없습니다. 파일 앞부분이 바뀌었거나 일부만 기록됐거나 예상과 다른 내용이 있으면 자동으로 고치거나 진행하지 않고 멈춥니다. 오류가 발생하거나 복사 확인을 하지 않으면 진행을 멈추고 원인과 마지막 저장 지점을 기록합니다. 완료 상태인 기간은 같은 명령을 재실행해도 자동으로 다시 수집하지 않습니다.

목록이 최신순인지 확인하세요. 직전 저장 항목보다 더 최신인 날짜를 입력하면 순서 오류로 저장을 멈춥니다. 이미 보관한 본문과 같으면 선택을 되돌리거나 확인을 받습니다. `s`는 현재 항목이 이미 저장된 같은 쪽지일 때 추가 저장 없이 재개 지점만 갱신하고, `d`는 본문이 같은 별개의 쪽지임을 확인했을 때만 중복 저장합니다. 기준일보다 오래된 쪽지를 만나면 세션을 완료 처리하고, `q`를 입력하면 일시 중단합니다.

체크포인트는 진행 위치와 복구 정보를 기록하지만 지비톡 목록을 직접 이동하지는 않습니다. 재개할 때 선택 행의 수신 날짜/발신자와 마지막 확정 기록을 대조하세요. 새 전체 순회는 받은쪽지함에서 `Home`으로 시작합니다. 본문을 읽은 뒤 목록으로 돌아갈 때는 현재 선택된 `UltariList` 행을 클릭하고, 그 행 번호가 실제 포커스와 일치하는지 확인한 다음에만 `↓`를 보냅니다. 본문에서 `Shift+Tab`을 보내는 경로는 매크로에서 목록 포커스가 아닌 본문 패널로 이동했는데도 일반 창 포커스를 목록으로 오인한 사례가 있어 사용하지 않습니다. `Tab`은 본문에서 스크롤바, 다시 `Tab`하면 `삭제` 버튼으로 이동했으므로 고정 횟수 Tab 매크로도 사용하지 마세요. Computer Use 키 입력은 관리함 창을 전경으로 활성화하므로 백그라운드 동시 작업도 보장되지 않습니다.

### 키보드 매크로로 원문 묶음 캡처

`scripts/capture_macro.mjs`의 `captureRawBodies`는 Computer Use `sky`로 유일한 `쪽지관리함` 창을 지정해 실행합니다. 시작 전에 **받은쪽지함**을 선택합니다. 매크로는 필요할 때만 선택된 자식 행을 클릭해 목록 포커스를 잡고, 이동은 `Home`/`↓` 키보드로 수행하며 본문은 UIA 값으로 읽습니다. 한 번 실행은 최대 30건으로 제한합니다. 각 행을 JSONL에 동기화하고 체크포인트에 본문/행 해시를 기록하므로, 실행이 중간에 끝나면 확정된 행을 검증한 뒤 재개합니다. 재탐색 때 행 지문이 달라져도 본문 해시가 저장 구간에 한 번만 나타나면 일치로 인정하고, 중복 본문이면 중단합니다. 미완성 마지막 JSONL 줄이 예상 기록의 일부와 일치할 때만 미확정 꼬리를 복구하고, 앞부분 해시나 예상 내용이 다르면 중단합니다. 날짜 경계가 확인되면 `stopBeforeRowSha256`에 경계 행 지문을 지정할 수 있으며, 해당 값이 체크포인트에 보존되어 행 지문 또는 본문 지문이 맞는 행부터 기록하지 않고 멈춥니다.

이 단계는 원문 백업용 임시 캡처입니다. 출력 폴더에는 `raw-bodies.jsonl`과 `capture-checkpoint.json`만 만들며, 화면 이미지와 사진·첨부 파일은 저장하지 않습니다. 새 레코드에는 `received_date`, 검토된 `sender`, `sender_evidence`가 포함됩니다. 캡처 함수는 지문별로 확인된 `senderReader`가 없으면 시작을 거부하며, OCR 후보만으로는 발신자를 저장하지 않습니다. 기존 raw를 월별 보관으로 옮길 때는 발신자/날짜를 대조해 `sequence,title` CSV와 `received_date`를 준비한 뒤 `build_archive_input.py`로 검증합니다. 각 30건 묶음 뒤에는 순번, 본문 해시, 발신자 누락, 체크포인트 앞부분 해시를 확인하고 다음 묶음을 시작합니다. 관리함 입력은 전경 창을 사용합니다.

취소 placeholder의 행/본문 지문이 기존 raw에 여러 번 있으면 자동으로 통과하지 않습니다. 모호한 후보는 저장 전 `paused-ambiguous-existing` 체크포인트에 지문과 기준 매치 순번을 기록합니다. `captureOlderThanKnown`의 `confirmedDistinctCandidate`는 화면에서 확인한 날짜/발신자, 기준 매치 순번 전체, 바로 앞에 저장된 순번 및 행/본문 지문이 일치할 때만 그 취소 쪽지를 별개 항목으로 저장합니다. 이 확인 정보는 일반 레코드의 `sender`에도 대조해 저장되며 다음 실행에서 다시 검증됩니다. 현재 행이나 직전 커서가 바뀌면 확인 객체를 전달하지 말고 화면에서 후보를 다시 대조하세요.

캡처 전에 화면에서 발신자·날짜와 행/본문 지문을 확인한 목록을 준비한 뒤 reader를 만듭니다. 각 항목은 `sequence`, `received_date`, `row_sha256`, `body_sha256`, `sender`, `verification_method`, `manually_verified: true`, `visible_header` 또는 `visible_list_label`을 가져야 합니다. 캡처 함수는 현재 선택의 행/본문 지문과 날짜가 이 매핑과 정확히 맞는지 재검증합니다.

```javascript
import { createVerifiedSenderReader } from "./scripts/capture_macro.mjs";

// verifiedSenderMap은 화면에서 직접 확인한 sender sidecar입니다.
const senderReader = createVerifiedSenderReader(verifiedSenderMap.records);
```

앱 입력이 멈춘 동안에는 저장된 원문과 화면 자료로 발신자/제목을 정리할 수 있습니다. `sequence,title` CSV만 만들면 raw JSONL의 `received_date`를 사용합니다. 기존 raw에 날짜가 없는 행이라면 CSV에 `received_date`(날짜만) 또는 `received_at`(시각 포함)을 기록하세요. 다음 도구가 원문 순번, 본문 SHA-256, 월 범위, 최신순을 검증하고 별도 JSONL을 만듭니다.

```powershell
python .\scripts\build_archive_input.py .\out\capture-2026-10-received-run1\raw-bodies.jsonl .\out\capture-2026-10-received-run1\metadata-map.csv .\out\capture-2026-10-received-run1\verified-2026-10.jsonl --month 2026-10 --markdown-output .\inbox\2026-10-received.md --range-manifest .\out\capture-2026-10-received-run1\range-manifest.json
```

`--markdown-output`은 새 파일만 생성하며 이미 있는 파일은 덮어쓰지 않습니다. 기존 월별 파일이 다른 목록 범위에서 왔거나 같은 시각·발신자의 본문이 원문 캡처와 다르면 한 파일에 섞지 말고 `2026-10-received.md`처럼 받은쪽지 전용 파일을 만듭니다. `archive-batch`는 오래된 기록을 뒤에 추가하는 모드이므로 전체 최신순 입력을 기존 기록에 그대로 넣으면 안 됩니다. 원문 JSONL·메타데이터 CSV·검증 JSONL은 서로 연결해 보존하고, 9월 경계 행은 월별 결과에 포함하지 않습니다.

`--range-manifest`는 검증한 보관 구간의 최신/최오래된 날짜, 발신자, 본문 미리보기, 행·본문 해시와 검증 JSONL 해시를 기록합니다. 이 파일은 이후 새 쪽지를 최신 경계에서 멈추거나, 저장 구간보다 오래된 쪽지를 과거 경계에서 이어 읽는 기준으로 씁니다. 이미 같은 내용의 매니페스트가 있으면 재사용할 수 있지만, 다른 내용으로 덮어쓰지는 않습니다.

### 새로 온 쪽지만 증분 저장

새 수신함 캡처는 기준 raw JSONL을 읽기 전용으로 사용하고, 매 회차마다 별도 출력 폴더를 지정합니다. 매크로는 `Home`에서 시작하고 한 번에 최대 30건을 저장합니다. 기존 캡처에서 **행 지문과 본문 지문이 모두 같은 항목**을 만나면 그 항목을 쓰지 않고 `paused-existing-boundary`로 멈춥니다. 이 일치는 경계 후보입니다. 같은 내용의 쪽지가 다시 올 수도 있으므로 화면에 선택된 행의 날짜/발신자를 기준 메타데이터와 대조하기 전에는 전체 증분 구간 완료로 표시하지 않습니다. 행 지문만 또는 본문 지문만 겹치면 기존 쪽지라고 단정하지 않고 `paused-ambiguous-existing`로 멈춰 확인을 요구합니다. 본문만 같은 다른 쪽지는 있을 수 있으므로 본문 해시 하나만으로 경계를 넘기지 않습니다.

Computer Use에서 다음처럼 실행합니다. `baselineRawJsonl`은 검증된 받은쪽지함 raw 파일이어야 하며, `outputDir`은 그 기준 폴더와 다른 새 폴더여야 합니다.

```javascript
const result = await captureNewUntilKnown({
  sky,
  window: managerWindow,
  baselineRawJsonl: "C:/.../capture-2026-10-received-run1/raw-bodies.jsonl",
  baselineVerifiedJsonl: "C:/.../capture-2026-10-received-run1/verified-2026-10.jsonl",
  baselineRangeManifest: "C:/.../capture-2026-10-received-run1/range-manifest.json",
  outputDir: "C:/.../capture-2026-10-incremental-01",
  senderReader,
  maxItems: 30,
  delayMs: 100,
});
```

`paused-batch-complete`이면 같은 폴더로 다시 실행해 이어가되, 먼저 체크포인트의 기준 파일 SHA와 신규 행을 검증합니다. 재개할 때 `Home`부터 이미 저장한 새 행의 행/본문 지문이 조금이라도 달라지면 중단합니다. `paused-existing-boundary`에 도달한 뒤 후보 행의 날짜/발신자를 기준 메타데이터와 대조해야 증분 캡처가 끝난 것으로 봅니다. `paused-ambiguous-existing`, `paused-before-known-boundary`, 또는 행 지문 오류는 수동 대조가 끝날 때까지 보관 입력에 넣지 않습니다. 경계 확인 후 신규 raw의 수신 날짜/발신자를 CSV로 대조하고, 아래처럼 기존 **받은쪽지 전용** 월별 파일에 새 JSONL을 앞에 합칩니다.

```powershell
python .\scripts\build_archive_input.py .\out\capture-2026-10-incremental-01\new-bodies.jsonl .\out\capture-2026-10-incremental-01\metadata-map.csv .\out\capture-2026-10-incremental-01\verified.jsonl --month 2026-10 --prepend-to .\inbox\2026-10-received.md
```

앞에 합치기는 새 항목이 기존 파일 맨 위 시각보다 모두 최신이고 정확한 동일 항목이 없을 때만 실행됩니다. 원본 월별 파일은 임시 파일을 검증한 뒤 원자적으로 교체합니다. 증분 출력 폴더가 기존/새 메시지를 모두 포함한 경계 상태에 도달한 뒤에는 나중 도착분을 위해 새 폴더를 시작합니다.

### 저장 구간보다 오래된 쪽지 이어 받기

검증 JSONL과 범위 매니페스트가 있으면 가장 오래된 보관 경계를 다시 찾고, 그보다 오래된 쪽지를 별도 JSONL에 30건씩 이어 저장할 수 있습니다. 첫 호출은 기준 경계 후보를 찾기만 하고 아무 쪽지도 쓰지 않습니다. 화면에 선택된 행의 날짜와 발신자를 매니페스트의 `oldest`와 직접 대조한 다음, 같은 출력 폴더로 확인값을 전달해 캡처를 시작합니다. 다음 호출 때 후보 지문이 현재 선택과 모두 같으면 Home부터 다시 찾지 않고 그 행에서 이어갑니다. 앵커 뒤에서 기준 raw에 이미 저장된 미검증 행/본문 쌍은 중복으로 쓰지 않고 건너뜁니다. 쌍이 중복되거나 한 지문만 겹치면 추정하지 않고 멈춥니다.

```javascript
const candidate = await captureOlderThanKnown({
  sky,
  window: managerWindow,
  baselineRawJsonl: "C:/.../capture-2026-10-received-run1/raw-bodies.jsonl",
  baselineVerifiedJsonl: "C:/.../capture-2026-10-received-run1/verified-2026-10.jsonl",
  baselineRangeManifest: "C:/.../capture-2026-10-received-run1/range-manifest.json",
  outputDir: "C:/.../capture-before-2026-10-01",
  maxItems: 30,
});
// 화면의 후보 행 날짜와 발신자가 매니페스트와 일치하는지 확인한 뒤에만 실행
const batch = await captureOlderThanKnown({
  sky,
  window: managerWindow,
  baselineRawJsonl: "C:/.../capture-2026-10-received-run1/raw-bodies.jsonl",
  baselineVerifiedJsonl: "C:/.../capture-2026-10-received-run1/verified-2026-10.jsonl",
  baselineRangeManifest: "C:/.../capture-2026-10-received-run1/range-manifest.json",
  outputDir: "C:/.../capture-before-2026-10-01",
  confirmedAnchor: { received_at: "2026-10-01T08:28:00", sender: "권윤옥" },
  senderReader,
  maxItems: 30,
});
```

`paused-batch-complete`이면 같은 폴더로 재실행합니다. 현재 선택이 체크포인트의 `next_row`와 행/본문 지문 모두 일치하고 그 쌍이 raw 기준/저장 접두부와 겹치지 않으면 그 커서부터 계속합니다. 일치하지 않거나 모호하면 Home부터 확인된 경계와 저장된 과거 구간을 다시 대조하고, 기준 raw의 이미 캡처된 꼬리를 건너뜁니다. `paused-oldest-reached`만 목록 끝까지 확인한 상태입니다. 날짜/발신자 메타데이터를 입력한 뒤, 오래된 쪽지들을 해당 월의 받은쪽지 전용 파일에 합칩니다. `--append-to`는 이미 존재하는 월 파일에서 모든 새 시각이 가장 오래된 시각보다 이르고 중복이 없을 때만 원자적으로 뒤에 붙입니다. 월 파일이 없다면 첫 검증 배치에 `--markdown-output`을 사용하고, 이후 배치부터 `--append-to`를 사용합니다. 한 번의 과거 캡처가 여러 달에 걸치면 `--month`를 바꿔 각각 별도 월 파일로 처리할 수 있습니다.

```powershell
python .\scripts\build_archive_input.py .\out\capture-before-2026-10-01\older-bodies.jsonl .\out\capture-before-2026-10-01\metadata-map.csv .\out\capture-before-2026-10-01\verified-2026-09.jsonl --month 2026-09 --append-to .\inbox\2026-09-received.md --range-manifest .\out\capture-before-2026-10-01\range-2026-09.json
```

범위 매니페스트와 지문은 후보 위치를 찾는 근거입니다. 앱 목록에서 보이는 날짜/발신자 확인을 대신하지 않습니다. 동일한 본문과 행이 반복되거나 기준 범위가 수정되면 자동 저장을 멈추고 확인을 요구합니다.

다른 UI에도 적용할 수 있는 포커스 탐색, 한 단계씩의 안전한 키 입력, 배치 크기 조정, 중단 복구 원칙은 [키보드 매크로 방법론](references/keyboard-macro-methodology.md)에 정리했습니다. 지비톡에서 확인한 키 경로나 컨트롤 구조를 다른 앱에서도 그대로 가정하지 말고, 대상 앱에서 다시 짧게 검증합니다.

확인한 쪽지를 묶어 빠르게 로컬에 저장하려면 JSONL 배치 모드를 사용할 수 있습니다. 각 줄은 `received_at`, `title`, `body`를 가진 JSON 객체이며, 쪽지관리함의 수신 시각 기준으로 최신순에서 오래된순으로 정렬합니다.

```jsonl
{"received_at":"2026-10-19 09:40:00","title":"발신자","body":"쪽지 본문 전체"}
{"received_at":"2026-10-19 09:31:00","title":"다른 발신자","body":"다음 쪽지 본문 전체"}
```

```powershell
python .\gbtalk_summary.py archive-batch .\out\verified-notes.jsonl --before 2026-10-01 --period month
```

배치 모드는 입력 파일의 SHA-256, 처리한 JSONL 앞부분 해시, 다음 행을 체크포인트에 기록합니다. 중단 후 이미 처리한 앞부분을 그대로 유지하면 미처리 뒷부분을 보완하거나 추가해 재개할 수 있습니다. 날짜 순서가 어긋나거나 본문만 같은 중복이 발견되면 기본적으로 멈춥니다. 정확히 같은 시각·제목·본문인 기존 항목은 안전하게 건너뜁니다. 본문만 같은 별개의 쪽지임을 확인한 경우에만 재실행할 때 `--allow-duplicate-bodies`를 지정하세요. 입력 끝까지 갔더라도 10월 1일보다 오래된 쪽지를 확인하지 못하면 완료 처리하지 않습니다. 배치 모드는 UI를 조작하지 않으므로 쪽지 탐색/복사는 Computer Use 흐름에서 별도로 수행해야 합니다.

```powershell
python .\gbtalk_summary.py archive --period week --title "출장 안내"
```

`--period`는 `day`(기본값), `week`, `month` 중에서 고릅니다. `--title`은 선택 사항입니다. 파일은 `inbox\YYYY-MM-DD.md`, `inbox\YYYY-Www.md`, `inbox\YYYY-MM.md` 형식으로 만들어지고, 각 쪽지에는 날짜와 시각이 기록됩니다. 예를 들어 주별 보관은 `inbox\2026-W43.md`에 쌓입니다. 이 명령은 API를 호출하지 않습니다.

과거 쪽지를 보관할 때는 목록에 표시된 원래 수신 시각을 `--sent-at`으로 지정해야 기간별 파일과 항목 날짜가 맞습니다.

```powershell
python .\gbtalk_summary.py archive --period month --title "발신자 또는 제목" --sent-at "2026-08-01 09:30:00"
```

나중에 보관 파일 하나를 요약하려면:

```powershell
python .\gbtalk_summary.py file .\inbox\2026-W43.md
```

기본 입력 상한은 60,000자이며, 넘으면 파일 뒤쪽 최근 내용을 요약합니다. 월별 파일이 상한을 넘으면 `--max-chars` 값을 늘리거나 주별 파일로 나누어 처리하세요.

### 텍스트 파일 방식

```powershell
python .\gbtalk_summary.py file .\chat.txt
```

`uia`, `clipboard`, `file` 모드는 요약을 요청하며, 결과는 `out/summary_날짜시간.md`에 저장되고 화면에도 출력됩니다. 입력 원문은 요약 모드에서 기본적으로 파일에 저장하지 않습니다. 디버깅 목적으로 원문 저장을 명시할 때만 `--save-raw`를 추가하세요. 입력 상한은 `--max-chars 30000`처럼 조절할 수 있습니다. `archive`는 별도 보관 명령으로, 복사한 원문을 날짜별 파일에 저장합니다.

## 기존 캡처의 날짜 누락 보완

기존 raw JSONL에 빠진 날짜를 채울 때는 원본을 수정하지 말고, 검증된 메타데이터와 지문 매핑을 새 JSONL로 합칩니다. 날짜 매핑은 해당 raw 파일의 SHA-256 및 각 행의 순번·행 지문·본문 지문에 연결되어야 합니다. 날짜가 한 건이라도 없거나 매핑이 충돌하면 출력 파일을 만들지 않습니다.

```powershell
python .\scripts\apply_date_backfill.py `
  .\out\capture-2026-10-received-run1\raw-bodies.jsonl `
  .\out\date-backfill-20261027\october-raw-dated.jsonl `
  --verified-metadata .\out\capture-2026-10-received-run1\verified-2026-10.jsonl `
  --date-map .\out\date-backfill-20261027\october-date-map.json
```

2026-10-27 보강본은 `out/date-backfill-20261027/`에 있다. 10월 원문 171건은 검증 메타데이터 169건과 화면 날짜 매핑 2건을 합쳤고, 과거 원문 398건은 기존 날짜 138건과 화면 날짜 매핑 260건을 합쳤다. 두 출력 모두 `received_date`가 100% 채워졌고 날짜 순서가 유지된다. 입력 raw JSONL은 그대로 보존된다. `out/date-completeness-audit-20261027.json`의 `raw_before_backfill`은 원래 누락을, `date_enrichment`는 보강본과 SHA-256을 기록한다.

## 기존 캡처의 발신자 보완

발신자를 추가할 때는 raw JSONL을 수정하지 않고 새 JSONL을 만든다. `scripts/apply_sender_backfill.py`는 원본 SHA-256, 행/본문 SHA-256, 메시지 날짜를 함께 사용해 기존 `sender` 또는 `title` 메타데이터를 1:1로 연결한다. 반복 placeholder는 날짜로도 구분되지 않으면 보강하지 않는다. 발신자 없는 행은 `sender_capture_status: missing`으로 남긴다.

```powershell
python .\scripts\apply_sender_backfill.py `
  .\out\date-backfill-20261027\october-raw-dated.jsonl `
  .\out\sender-backfill-20261028\october-raw-with-senders-verified.jsonl `
  --verified-metadata .\out\capture-2026-10-received-run1\verified-2026-10.jsonl `
  --manual-map .\out\sender-backfill-20261028\october-manual-sender-map.json

python .\scripts\apply_sender_backfill.py `
  .\out\date-backfill-20261027\older-bodies-dated.jsonl `
  .\out\sender-backfill-20261028\older-bodies-with-senders-verified.jsonl `
  --verified-metadata .\out\capture-2026-10-older-backfill-continuation-263\older-bodies.jsonl
```

2026-10-28 기준 10월 171건은 기존 검증 메타데이터 169건과 관리함에서 직접 확인한 2건을 합쳐 발신자 171건을 모두 채웠다. 과거 398건은 기존 sender 4건만 있으며 394건은 미확인이다. `out/sender-backfill-20261028/sender-completeness-audit.json`에 원본·출력 SHA-256, 누락 수, 판독 이력을 기록했다. 기존 보강본은 원본 행을 수정하지 않는다.

한국어 Windows OCR이 화면의 `이명숙`을 `이영숙`으로 반복 오독했으므로 발신자 OCR은 검증되지 않은 후보로만 취급한다. 화면과 대조하지 않은 OCR값을 저장하지 않는다. 검색으로 쪽지를 찾은 뒤 탭을 닫았을 때 목록 강조와 미리보기가 달라진 사례도 있어, 검색 탭을 닫은 뒤에는 새 화면 상태를 확인하기 전까지 키 입력을 보내지 않는다. 자세한 실패와 복구는 [트러블슈팅 이력](references/troubleshooting.md)과 [키보드 매크로 방법론](references/keyboard-macro-methodology.md)에 기록했다.

## UIA가 작동하지 않을 때

- 지비톡 창 제목이 기본 패턴(지비톡/GBTalk)과 다르면 `GBTALK_WINDOW_TITLE_RE` 환경변수로 정규식을 지정합니다.
- 대화창이 Chromium/WebView 기반이면 접근성 트리에 대화 텍스트가 나오지 않을 수 있습니다. 이때는 클립보드 방식으로 전환합니다.
- 클립보드 복사는 선택된 내용에 따라 일부 대화만 들어올 수 있습니다. 지비톡에서 필요한 메시지 범위를 확인한 후 실행하세요.

## 범위와 제한

- 현재 열린 대화방 하나를 읽습니다. 방 목록 순회, 새 메시지 감시, 예약 실행, 답장 입력 및 전송은 구현하지 않았습니다.
- 보관함에 저장한 쪽지 원문은 로컬 Markdown 파일에 남습니다. 필요할 때만 해당 파일을 `file` 모드로 요약해 API에 전달하세요.
- 화면 읽기는 pywinauto의 Windows UI Automation 접근성을 이용합니다. 화면 캡처 기반 Computer Use/OCR은 사용하지 않습니다.
- 메시지 내용은 Anthropic API로 전송되어 요약됩니다. 실제 업무에 사용하기 전에 기관의 외부 AI 및 개인정보 처리 기준을 확인하세요.
- 요약 결과는 누락·오해가 있을 수 있으므로 원문을 확인하세요. 메시지 속 지시는 데이터로 취급하고 따르지 않도록 프롬프트에 명시되어 있습니다.

## 다음 구현 단계 후보

1. 테스트 대화방에서 UIA 결과의 순서·발신자·시간 표시를 확인합니다.
2. 여러 대화방 순회는 읽기 전용으로 별도 구현하고, 방별 결과를 비교 검증합니다.
3. 새 메시지 감지는 지비톡 알림/공식 기능이 있는지 확인한 뒤 추가합니다.
4. 답장 초안이나 전송은 요약과 분리된 후속 기능으로 다룹니다.
