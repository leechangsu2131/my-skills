# PyKrx 통합 테스트 가이드

## 개요

PyKrx 프로젝트는 `pytest-vcr`와 `vcrpy`를 사용하여 HTTP 요청/응답을 녹화하고 재생합니다. 이를 통해:
- 실제 네트워크 없이 빠른 테스트 실행
- CI 환경에서 안정적인 테스트
- API 응답 변경 사항 추적
- **대용량 응답(Ticker List 등)을 공통 Cassette로 관리하여 저장소 용량 최적화**

## 디렉터리 구조

```
tests/
├── cassettes/              
│   ├── common/             # 🔥 공통 대용량 응답 저장소 (Master DB)
│   │   ├── etx_ticker_init.yaml  # ETF/ETN/ELW Ticker 리스트 (약 3.6MB)
│   │   ├── stock_ticker_init.yaml
│   │   └── ...
│   ├── TestEtfPdf.test_with_business_day.yaml  # 개별 테스트 (약 2KB)
│   ├── TestShortBalanceByDate.test_with_default_param.yaml
│   └── ...
├── integration/            # 통합 테스트 코드
│   ├── test_bond_api.py
│   ├── test_etf_api.py
│   ├── ...
├── extract_common_cassettes.py # 🔥 Cassette 용량 최적화 스크립트
└── conftest.py             # pytest 설정 & 공통 Cassette 주입 로직
```

## Cassette 최적화 전략 (Common Cassettes)

PyKrx 테스트의 VCR 파일 용량은 원래 약 **123MB**였으나, **31MB**로 최적화되었습니다.
이는 모든 테스트에서 반복적으로 호출되는 "대용량 Ticker List 조회" 응답을 **Common Cassette**로 분리했기 때문입니다.

### 동작 원리
1. `tests/cassettes/common/` 디렉토리에 대용량 응답을 미리 저장해둡니다.
2. `conftest.py`에서 테스트 실행 전 이 공통 Cassette들을 로드합니다 (Scope: Module).
3. `vcr.VCR.use_cassette`를 Monkeypatching하여, 공통 Cassette에 대해서는 `allow_playback_repeats=True`를 강제 적용합니다.
4. 개별 테스트(`TestEtf...`)가 실행될 때, Ticker List 조회 요청이 발생하면 공통 Cassette에서 응답을 찾아 재생합니다.
5. 따라서 개별 테스트의 Cassette 파일에는 해당 테스트 고유의 요청만 기록되어 파일 크기가 매우 작아집니다 (3MB -> 4KB).

## 테스트 실행 방법

### 기본 실행 (녹화된 Cassette 사용)

```bash
# 전체 Integration 테스트 실행
pytest tests/integration/ -v

# 특정 테스트 파일 실행
pytest tests/integration/test_etf_api.py -v
```

### 새 Cassette 녹화 및 최적화

새로운 기능을 개발하거나 기존 Cassette를 갱신해야 할 경우 다음 절차를 따릅니다.

1. **테스트 실행 및 녹화**
   * 최초 실행 시에는 개별 Cassette 파일에 대용량 응답이 그대로 기록될 수 있습니다.
   ```bash
   # 예: test_new_feature.py 실행
   pytest tests/integration/test_new_feature.py
   ```

2. **용량 최적화 (Deduplication)**
   * `extract_common_cassettes.py` 스크립트를 실행하여 중복된 대용량 응답을 공통 DB로 추출하고, 개별 파일에서 제거합니다.
   ```bash
   python tests/extract_common_cassettes.py
   ```
   * 이 스크립트는 `tests/cassettes/` 하위의 모든 YAML 파일을 스캔하여 알려진 대용량 BLD 코드(`MDCSTAT04601` 등)를 식별하고 정리합니다.

## VCR 설정 (`conftest.py`)

### Custom Matchers

PyKrx는 날짜 파라미터가 매일 변하더라도 기존 Cassette를 재사용할 수 있도록 커스텀 Matcher를 사용합니다.

```python
def uri_without_dates(r1, r2):
    """날짜 파라미터(strtDd, endDd 등)를 무시하고 URI 비교"""

def form_body_matcher(r1, r2):
    """POST Body에서 날짜 파라미터를 무시하고 비교"""
```

### Monkeypatching

`pytest-vcr`의 기본 동작인 `record_mode='once'`는 동일한 Cassette 내에서 같은 요청이 반복되면 에러(`CannotOverwriteExistingCassetteException`)를 발생시킵니다.
공통 Cassette를 여러 테스트가 공유해야 하므로, `conftest.py`에서 `vcr.VCR.use_cassette`를 패치하여 이를 허용하도록 수정되어 있습니다.

## 트러블슈팅

### ❌ `KeyError: 'output'` 또는 `IndexError`

* **원인**: 공통 Cassette(`tests/cassettes/common/*.yaml`)가 손상되었거나 로드되지 않음.
* **해결**: 
  * `conftest.py`의 `COMMON_CASSETTES` 리스트 확인.
  * 필요 시 `tests/cassettes/common/` 파일들을 복구하거나 재녹화해야 할 수 있습니다.

### ⚠️ Cassette 용량이 다시 커짐

* **원인**: 새로운 테스트를 작성하고 `extract_common_cassettes.py`를 실행하지 않음.
* **해결**:
  ```bash
  python tests/extract_common_cassettes.py
  ```

### ❌ "Can't overwrite existing cassette" 에러

* **원인**: `conftest.py`의 Monkeypatch가 제대로 적용되지 않았거나, `record_mode` 설정 충돌.
* **해결**: `tests/conftest.py` 파일이 최신 상태인지 확인하고, `pytest` 실행 시 별도의 VCR 옵션을 주지 않았는지 확인하세요.

## Git 관리

* ✅ **Cassette 파일은 Git에 커밋합니다.**
* 최적화 덕분에 Git LFS 없이도 충분히 관리가 가능한 수준(총 30~50MB)을 유지하고 있습니다.
* PR을 올리기 전에 반드시 `python tests/extract_common_cassettes.py`를 실행하여 용량을 줄여주세요.
