---
name: personal-carrot
description: 당근마켓 매물 자동 수집 시스템 (Appium 기반)
---

# 당근마켓 자동 수집 스킬

Appium을 이용하여 실제 안드로이드 기기의 당근마켓 앱을 조작, 매물을 검색하고 추출하여 구글시트에 기록합니다.

## 실행 방법
- 메인 수집 실행: `python main.py`
- 특정 키워드 수집: `python main.py --keyword "검색어"`
- 구글시트 없이 로컬 저장만: `python main.py --local-only`

## 주의사항
- 본 시스템은 개인 학습 및 비상업적인 용도로만 사용해야 합니다.
- 실행 전 `setup_check.py`를 사용하여 Appium과 안드로이드 기기가 정상적으로 연결되어 있는지 확인하세요.
