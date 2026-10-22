# 독도 + 주변 해저 3D 프린트

## 출력물

- `output/dokdo_gebco_copernicus_200mm.stl`: 200 × 200 mm, 밑판 3 mm, 전체 높이 약 28.21 mm
- `preview/dokdo_gebco_copernicus_preview.png`: 출력 전 지형 높이 미리보기
- `output/stl_report.json`: 사용한 자료와 모델 검증 정보

STL은 독도 중심의 6 × 6 km 영역을 UTM 52N으로 투영한 뒤 만들었습니다. 수평과 수직의 축척은 동일하게 적용했고(수직 과장 1배), 밑판을 포함한 닫힌 메시로 내보냈습니다. Cura나 PrusaSlicer에서 불러와 방향과 프린터 설정을 확인하면 됩니다.

## 사용한 자료

- 해저: [GEBCO 2026 gridded bathymetry](https://www.gebco.net/data-products/gridded-bathymetry-data), CEDA OPeNDAP 부분 격자. 15 arc-second 격자라 독도 주변에서 대략 동서 370 m, 남북 463 m 간격입니다. 이번 부분 격자의 수심 값은 -797~-23 m였습니다. 원본 ASCII와 Type Identifier(TID) 격자를 `data/`에 보관했습니다.
- 육상: [Copernicus DEM GLO-30](https://dataspace.copernicus.eu/explore-data/data-collections/copernicus-contributing-missions/collections-description/COP-DEM), AWS 공개 타일 `Copernicus_DSM_COG_10_N37_00_E131_00_DEM.tif`. 타일은 3600 × 3600, EPSG:4326, 1 arc-second(약 30 m)입니다. 제품은 DSM이므로 식생·시설물이 포함될 수 있습니다.
- 처리: Copernicus DSM의 0 m 초과 표고를 육상으로 분류하고, 그 밖의 지점은 GEBCO 해저 표고를 사용했습니다. 양쪽 자료의 해안 경계는 원자료 해상도 차이로 단차가 남을 수 있으며 임의 보간이나 수직 과장은 하지 않았습니다.

## 정확도와 한계

GEBCO 요청 중 위도 행 인덱스가 남위 자료를 가리키는 오류를 발견했습니다. 그 데이터는 사용하지 않았고, 반환된 위도 배열이 북위 37.20625~37.27292°인지 확인한 확장 부분 격자만 모델에 반영했습니다. 재요청한 GEBCO 격자에는 독도 육지가 양의 표고로 나타나지 않아, 육상 DSM을 별도로 결합했습니다.

Copernicus GLO-30 DSM은 독도처럼 작고 경사가 급한 암석섬의 최고점을 충분히 표현하지 못할 수 있습니다. 이번 타일의 독도 영역 표고는 최대 약 37.6 m로, 이를 측량급 고도 자료로 간주하면 안 됩니다. 따라서 이 STL은 공개 격자 자료를 결합한 수업·시각화용 지형 모델입니다. 더 정확한 독도 육상 형상이 필요하면 국토지리정보원의 고해상도 DEM 또는 측량 자료를 확보해 교체해야 합니다. 해저와 육상 자료의 수직 기준 차이는 이 파일에서 별도 보정하지 않았으므로 해안부 절대고도는 근사값입니다.

## 다시 만들기

프로젝트 폴더에서 가상환경을 만든 뒤 의존성을 설치하고 다음 명령을 실행합니다.

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe convert_gebco_ascii.py
.\.venv\Scripts\python.exe process_dokdo.py
```

## 확인 결과

STL을 다시 열어 경계 크기 200 × 200 × 28.21 mm, 삼각형 161,600개, watertight 및 양의 부피를 확인했습니다. 슬라이서별 설정과 실제 프린터 출력은 아직 확인하지 않았습니다.
