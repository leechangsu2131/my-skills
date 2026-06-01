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

## Risk/Downside 탭에서 민감도 표가 빈칸으로 보이는 경우

원인:

- WACC가 영구성장률 이하일 때 영구가치 공식이 성립하지 않아 `None`을 반환합니다.
- 이 경우 해당 셀은 `-`로 표시됩니다.

해결:

- 이는 정상 동작입니다. WACC > g인 조합만 유효한 추정 EV를 보여줍니다.
- 민감도 표의 왼쪽 위(낮은 WACC, 높은 g)에서 빈칸이 많으면 정상입니다.

## Risk/Downside 탭에서 괴리율이 극단적으로 보이는 경우

가능한 의미:

- 정상화 영업이익률이 현재 실적과 크게 다릅니다.
- FCF 전환율 가정이 사업 특성에 맞지 않습니다.
- 단일 단계 영구가치 모형의 한계로, WACC와 g의 작은 차이가 극단적인 결과를 만듭니다.

해야 할 일:

- 매출/마진 시나리오 탭에서 비슷한 가정을 넣어 교차 확인합니다.
- Reverse DCF 탭의 민감도와 비교합니다.
- 정상화 영업이익률 슬라이더를 조정하며 결과의 안정성을 확인합니다.

관련 테스트:

```powershell
python -m pytest tests/test_risk_downside.py -v
```

## 종합 결론 탭(11번) 또는 Advanced 역산 탭(12번)이 안 보이거나 에러가 나는 경우

원인:

- 대시보드 렌더링 시 `st.tabs`의 개수와 배열된 탭 이름의 개수가 일치하지 않는 경우.
- `evaluate_signals()` 또는 `calc_implied_growth_from_peg()` 모듈을 찾을 수 없는 경우.

해결:

- `dashboard.py`의 `st.tabs([...])` 리스트 안에 "12. Advanced 역산"이 정확히 12번째에 있는지 확인합니다. (총 14개)
- 좌변 변수 튜플 `(tab_audit, ..., tab_advanced, tab_formula, tab_source)`의 개수가 일치하는지 확인합니다.

관련 테스트:

```powershell
python -m pytest tests/test_synthesis.py tests/test_advanced_reverse.py -v
```

## `pipeline/ingest_report.py` 실행 시 "PDF 읽기 오류"가 발생하는 경우

원인:

- `pypdf` 라이브러리가 설치되어 있지 않거나, PDF 파일이 손상되었거나 암호화되어 있을 수 있습니다.

해결:

- 먼저 `pip install pypdf` 명령으로 라이브러리가 설치되어 있는지 확인합니다.
- 추출이 불가능한 이미지 형태의 PDF인 경우, 해당 스크립트는 OCR을 자체 지원하지 않으므로 텍스트 추출이 빈 문자열로 반환됩니다.

## 시트의 '애널목표가', '투자의견' 열이 업데이트되지 않는 경우

원인:

- `data/report_context/{ticker}.json` 파일이 없거나 JSON 포맷이 잘못되었기 때문입니다.

해결:

- `pipeline/ingest_report.py`를 실행하여 해당 티커의 리포트 JSON 파일이 먼저 생성되었는지 확인하세요.
- `sheet_updater.py`는 `report_context` 디렉토리에 유효한 JSON이 있을 때만 해당 열(W, X, Y)과 K열(섹터PER대비%)을 동적으로 덮어씁니다.

## 매매일지 기록 시 엉뚱한 열에 데이터가 들어가는 경우 (포지션 ID 누락)

원인:

- 과거 버전의 `2_add_trade.py` 스크립트가 시트의 최신 열 구조(매매일, 포지션ID, 티커, 종목명, 구분, 수량, 금액, 매매근거, 만족도...)를 반영하지 못해 발생합니다. 
- 특히 `포지션ID` 열(B열)이 누락되어 데이터가 우측으로 하나씩 밀리고, `단가` 데이터가 추가되어 열 매핑이 완전히 어긋납니다.

해결 및 원칙:

- `2_add_trade.py`의 `parse_trade()` 함수가 반환하는 리스트가 실제 구글 시트 `📒 매매일지`의 열 순서와 완벽히 일치하는지 확인해야 합니다.
- **포지션 ID 개념**: 특정 기업에 대한 매수/매도를 너무 잘게 나누지 않고, 하나의 전략적 진입/청산 흐름(특정 기간에 걸친 기록들)을 '하나의 포지션'으로 묶어서 관리하기 위해 만든 식별자입니다. 한 기업당 무조건 1개의 ID가 고정되는 것이 아니며, 투자 시기나 전략 단위에 따라 같은 기업이라도 여러 포지션으로 나뉘거나 묶일 수 있습니다. 매매일지 기록 시 이 맥락을 고려하여 B열에 기록해야 합니다.
