# TROUBLESHOOTING.md

이 문서는 삼성전기 가치분석 앱을 이어받는 IDE/에이전트가 자주 만나는 문제를 빠르게 해결하기 위한 기록입니다.

## Streamlit 앱이 예전 코드로 뜨는 경우

증상:

```text
ImportError: cannot import name 'calc_pe_from_eps' from 'valuation_app.relative_valuation'
```

또는 코드에는 함수가 있는데 브라우저에는 여전히 이전 Traceback이 보입니다.

원인:

- Streamlit 프로세스가 이전 모듈 상태를 물고 있습니다.
- 함수명 변경 후 앱 프로세스를 재시작하지 않았습니다.

해결:

```powershell
$procs = Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -like '*streamlit*valuation_app/dashboard.py*' -and $_.ProcessId -ne $PID }
$procs | ForEach-Object { Stop-Process -Id $_.ProcessId -Force }
Start-Sleep -Seconds 2
$p = Start-Process -WindowStyle Hidden -FilePath python -ArgumentList @('-m','streamlit','run','valuation_app/dashboard.py','--server.port','8501','--server.headless','true','--browser.gatherUsageStats','false') -WorkingDirectory 'C:\Users\lee21\.gemini\antigravity\scratch\my-skills\skills\personal-record-trade' -PassThru
Start-Sleep -Seconds 5
Invoke-WebRequest -Uri 'http://localhost:8501/_stcore/health' -UseBasicParsing
```

## 포트 8501이 이미 사용 중인 경우

증상:

```text
Port 8501 is already in use
```

해결 1: 기존 Streamlit을 종료합니다.

```powershell
Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -like '*streamlit*' } | Select-Object ProcessId, CommandLine
Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -like '*streamlit*valuation_app/dashboard.py*' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force }
```

해결 2: 다른 포트로 실행합니다.

```powershell
python -m streamlit run valuation_app/dashboard.py --server.port 8502
```

## 테스트가 모듈 import에서 실패하는 경우

먼저 문법 확인:

```powershell
python -m py_compile valuation_app/dashboard.py valuation_app/relative_valuation.py valuation_app/reverse_dcf.py valuation_app/roic_reinvestment.py valuation_app/cap_duration.py
```

그 다음 관련 테스트만 좁혀서 실행합니다.

```powershell
python -m pytest tests/test_relative_valuation.py -v
```

마지막으로 전체 valuation 테스트를 실행합니다.

```powershell
python -m pytest tests/test_valuation_models.py tests/test_valuation_calculations.py tests/test_valuation_repository.py tests/test_valuation_audit.py tests/test_valuation_formatting.py tests/test_reverse_dcf.py tests/test_value_attribution.py tests/test_margin_scenario.py tests/test_roic_reinvestment.py tests/test_relative_valuation.py tests/test_cap_duration.py -q
```

## PER이 `데이터 필요`로 보이는 경우

원인:

- `data/valuation/009150/normalized/metrics.json`에 `net_income` 또는 `eps`가 빠졌을 가능성이 큽니다.

현재 기준값:

- 순이익: KRW `679,304,726,000`
- EPS: KRW `9,345`
- 출처: 삼성전기 2025 감사보고서 Note 23

관련 테스트:

```powershell
python -m pytest tests/test_valuation_repository.py tests/test_relative_valuation.py -v
```

## P/E와 EPS 기준 P/E가 다르게 보이는 경우

현재 앱은 두 값을 모두 보여줍니다.

```text
P/E = 시가총액 / 순이익
EPS 기준 P/E = 주가 / EPS
```

두 값이 다를 수 있는 이유:

- 현재가와 시가총액 기준 시점 차이
- 보통주/우선주 또는 희석주식수 처리 차이
- 시장 데이터 제공자의 주식수 업데이트 지연
- seed 데이터가 특정 날짜의 스냅샷이기 때문

이 차이를 없애려고 임의로 price, shares, market cap을 맞추지 마세요. 먼저 시장 데이터 기준일과 주식수 정의를 확인해야 합니다.

## ROIC 탭에서 `해 없음`이 나오는 경우

원인:

- McKinsey 1단계 가치 드라이버 공식이 현재 EV/NOPAT 배수를 설명할 수 없는 영역일 수 있습니다.

핵심:

```text
EV/NOPAT = (1 - g/ROIC) / (WACC - g)
```

예를 들어 WACC 9%, g 3%라면 이 공식의 최대 EV/NOPAT는 `1 / (9% - 3%) = 16.7배`입니다. 현재 EV/NOPAT가 이보다 훨씬 크면 단일 단계 공식으로는 해가 없습니다.

앱은 이 경우 별도로 투자자본 기반 미래 ROIC를 계산합니다.

```text
Future ROIC = g + EV * (WACC - g) / Invested Capital
```

## Reverse DCF 결과가 극단적으로 보이는 경우

가능한 의미:

- 현재 FCF가 일시적으로 낮습니다.
- 시장은 여러 해의 FCF 회복을 가격에 반영하고 있습니다.
- WACC와 영구성장률 차이가 너무 작습니다.
- 단일 단계 perpetuity가 이 회사 상황에 맞지 않습니다.

해야 할 일:

- WACC/g 민감도 표를 봅니다.
- 매출/마진 시나리오 탭에서 필요한 정상화 FCF를 봅니다.
- ROIC와 CAP 탭에서 장기 초과수익 가정을 따로 봅니다.

## yfinance 또는 시장 데이터가 공식 자료와 충돌하는 경우

원칙:

- 영업실적과 재무제표는 공식 공시 또는 회사 IR 자료를 우선합니다.
- yfinance는 시장 가격, 시가총액 등 편의 데이터로만 사용합니다.
- 충돌하면 화면에 `source conflict` 또는 설명을 남깁니다.

## 한글이 PowerShell에서 깨져 보이는 경우

파일 자체가 깨진 것이 아니라 터미널 인코딩 문제일 수 있습니다.

시도:

```powershell
Get-Content -Encoding UTF8 README.md
chcp 65001
```

문서를 수정할 때는 UTF-8을 유지합니다. 기존 한글 문서를 무리하게 재저장하지 마세요.

## `.superpowers/`가 계속 보이는 경우

증상:

```text
?? .superpowers/
```

원칙:

- 로컬 작업 흔적입니다.
- 사용자가 명시하지 않으면 커밋하지 않습니다.
- `git status --short`에서 남아 있어도 이상 상태가 아닙니다.

## 새 숫자를 추가할 때 체크리스트

`metrics.json`에 숫자를 추가할 때 최소한 아래를 확인합니다.

- `metric_key`가 계산 코드에서 기대하는 이름과 일치하는가?
- `unit`이 KRW, ratio, KRW/share 등 표시 코드와 맞는가?
- 원문 단위가 천원/백만원이면 KRW로 정규화했는가?
- `source_method`가 `dart_direct`, `calculated`, `market`, `manual` 중 적절한가?
- `statement_name`, `original_account_name`, `original_amount`가 채워져 있는가?
- 관련 테스트가 있는가?
