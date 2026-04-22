# 트러블슈팅 및 개발 기록 (Troubleshooting & History)

이 문서는 `util-school-print` 스킬을 개발하며 겪었던 주요 기술적 한계와, 이를 우회(Bypass)하기 위해 찾아낸 해결 과정을 기록합니다. 향후 비슷한 자동화 스크립트를 작성하거나 유지보수할 때 귀중한 단서가 됩니다.

---

## 1. HWP OLE 인쇄 매수(Copies) 속성 주입 오류

### 🚨 문제 상황
- 최초 OLE 자동화 스크립트에서 인쇄 매수를 설정하기 위해 `pset.HSet.SetItem("Copies", n)` 또는 `pset.Copies = n`을 시도함.
- `Property '<unknown>.Copies' can not be set.` 오류 발생 및 무조건 1장씩만 인쇄되는 현상 발생.

### 💡 원인 및 해결 방법
- HWP OLE 내부적으로 `HPrint` 파라미터 규격이 엄격하게 정해져 있음. 
- 복사본(매수)을 지정하는 정확한 키 이름은 `Copies`가 아니라 **`NumCopy`** 였음.
- 올바른 HWP OLE 파라미터 주입 패턴 적용:
  ```python
  act = hwp.CreateAction("Print")
  hset = act.CreateSet()
  act.GetDefault(hset)
  hset.SetItem("NumCopy", copies)  # 매수 지정 성공
  act.Execute(hset)
  ```

---

## 2. HWP OLE 트레이(용지함) 강제 제어 불가

### 🚨 문제 상황
- 간지(색지)는 B세트(트레이 2), 안내장 본문은 A세트(트레이 1)에서 번갈아가며 나오게 해야 함.
- HWP OLE 파라미터 중 트레이(용지 공급원)를 제어할 수 있는 속성을 찾으려 했으나 작동하지 않음.
- 위키독스(한글 OLE 공식 규격) 확인 결과: `HPrint`에는 `NumCopy`, `Collate`, `Duplex`, `UsePrinterName`은 존재하나, **용지 공급원(트레이)에 해당하는 `DEVMODE.dmDefaultSource` 제어 속성은 아예 노출되어 있지 않음**을 확인.

---

## 3. 프린터 트레이 동적 전환과 권한(Access Denied) 문제

이 문제는 스크립트 완성의 가장 큰 난제였습니다. HWP OLE로 트레이를 바꿀 수 없으므로, **"프린터의 시스템 기본 설정을 파이썬으로 잠깐 바꿨다가 윈도우 인쇄를 넘기고 다시 되돌리는"** 전략을 취했습니다.

### ❌ 실패 1: `PRINTER_INFO_2` 레벨을 통한 시스템 전역 기본값 변경
- `win32print.GetPrinter(h, 2)` 를 호출하여 프린터 전체의 기본 `DEVMODE` 속성을 불러옴.
- 용지함 번호를 `dm.DefaultSource = 3` (트레이2) 으로 변경 후 `win32print.SetPrinter(h, 2, info, 0)` 시도.
- **결과**: `pywintypes.error: (5, 'SetPrinter', '액세스가 거부되었습니다')` 오류 발생.
- **원인**: 레벨 2(`PRINTER_INFO_2`)는 시스템 전역 프린터 속성이므로 **관리자 권한**이 있는 계정이나 프로세스에서만 수정 가능함. 학교 공용 PC의 일반 교사 계정/환경에서는 막힐 수밖에 없음.

### ✅ 최종 해결: `PRINTER_INFO_9` (사용자 레벨) 우회 적용
- 관리자 권한이 없어도 임시로 인쇄 설정을 바꾸기 위해 `win32print.GetPrinter(h, 9)` 를 사용함.
- **원리**: 레벨 9(`PRINTER_INFO_9`)는 프린터 기기 자체의 세팅이 아니라, **현재 로그인된 사용자의 (Per-User) 프린터 기본 설정**만을 담고 있음. 이를 수정하면 관리자 권한(`Access Denied`) 에러 없이 변경되며, 즉시 그 사용자가 날리는 인쇄 Job에 반영됨.
- **성공적 적용 코드 (`test_print.py` / `batch_print_v2.py`)**:
  ```python
  import win32print
  h = win32print.OpenPrinter(PRINTER_NAME)
  info = win32print.GetPrinter(h, 9)     # Level 9 (User Default) 
  dm = info.get("pDevMode")              # DEVMODE 구조체 접근
  
  orig_tray = dm.DefaultSource           # 원본 기억
  dm.DefaultSource = 3                   # 트레이 2 (고유번호 3) 삽입
  win32print.SetPrinter(h, 9, info, 0)   # 에러 없이 적용 성공!
  # 인쇄 후 orig_tray로 다시 복원 (SetPrinter)
  ```

---

## 4. 교훈 및 디버깅 팁

1. **하드웨어의 Auto Tray Switching 기능 주의**: 트레이 제어 코드가 완벽해도, 정작 1번 트레이에 백지가 다 떨어지면 복합기는 인쇄를 멈추지 않고 **대체 용지함(동일한 크기가 들어있는 색지함 등)**에서 종이를 마음대로 끌어다 씁니다! 스크립트를 비정상 강제 종료하더라도 이미 스풀된 작업들은 연달아 색지로 나올 수 있으니, 배치 인쇄 전에는 반드시 본문용 용지를 넉넉하게 적재해야 합니다.
2. 드라이버마다 "트레이 2"의 내부 번호가 다릅니다. 후지필름 복합기의 경우 `3`이 트레이 2였으나, 다른 곳에서는 `262` 등의 높은 숫자를 쓸 수 있습니다. **(`list_trays.bat`을 만들어 진단 도구로 평생 활용할 수 있게 된 계기입니다.)**
3. 윈도우 인쇄 제어에서 **"액세스가 거부되었습니다(Error 5)"** 가 뜨면, 프로그램 자체를 무리하게 관리자로 실행하려 하지 말고 사용자 레벨 권한(예: Level 9)으로 제어할 방법이 없는지 API를 우회하는 것이 훨씬 권장됩니다.
4. HWP OLE 자동화는 속성 대입 시 무심코 `.Properties`를 직접 점찍기보단, `SetItem("키이름", 값)` 메서드를 사용하는 것이 안전합니다.
