# 독도 + 주변 해저 3D 프린트

## 출력물

- `output/dokdo_gebco_copernicus_200mm.stl`: 200 × 200 mm, 밑판 3 mm, 전체 높이 약 28.21 mm
- `preview/dokdo_gebco_copernicus_preview.png`: 출력 전 지형 높이 미리보기
- `output/stl_report.json`: GEBCO + Copernicus 모델의 자료와 메시 정보
- `output/ngii_2025/dokdo_gebco_ngii_2025_200mm.stl`: GEBCO 해저 + 국토정보플랫폼 2025 공개DEM 육상 모델
- `preview/ngii_2025/dokdo_gebco_ngii_2025_200mm_preview.png`: 2025 공개DEM 모델 미리보기
- `output/ngii_2025/stl_report.json`: 2025 공개DEM 모델의 자료와 메시 정보
- `output/island_focus/dokdo_island_focus_copernicus_200mm_2x.stl`: 독도를 크게 배치한 1.2 × 1.2 km 확대 모델
- `preview/island_focus/dokdo_island_focus_copernicus_200mm_2x_preview.png`: 확대 모델의 표고 미리보기
- `output/island_focus/stl_report.json`: 확대 모델의 자료와 메시 정보
- `models/thingiverse_3183098/Dokdo_korean.stl`: Thingiverse에서 받은 한글판 모델
- `models/thingiverse_3183098/Dokdoenglish.stl`: Thingiverse에서 받은 영문판 모델
- `models/thingiverse_3183098/SOURCE.md`: 출처, 라이선스, STL 검사 메모
- `output/mold_master/dokdo_relief_mandu_master_80mm.stl`: 실리콘 몰드 캐스팅용 독도 양각 마스터
- `preview/mold_master/dokdo_relief_mandu_master_80mm_preview.png`: 마스터의 표고와 윤곽 미리보기
- `output/mold_master/stl_report.json`: 마스터의 크기와 메시 검사 결과
- `create_dokdo_mold_master.py`: 몰드 마스터 재생성 스크립트

STL은 독도 중심의 6 × 6 km 영역을 UTM 52N으로 투영한 뒤 만들었습니다. 수평과 수직의 축척은 동일하게 적용했고(수직 과장 1배), 밑판을 포함한 닫힌 메시로 내보냈습니다. Cura나 PrusaSlicer에서 불러와 방향과 프린터 설정을 확인하면 됩니다.

## 사용한 자료

- 해저: [GEBCO 2026 gridded bathymetry](https://www.gebco.net/data-products/gridded-bathymetry-data), CEDA OPeNDAP 부분 격자. 15 arc-second 격자라 독도 주변에서 대략 동서 370 m, 남북 463 m 간격입니다. 이번 부분 격자의 수심 값은 -797~-23 m였습니다. 원본 ASCII와 Type Identifier(TID) 격자를 `data/`에 보관했습니다.
- 육상: [Copernicus DEM GLO-30](https://dataspace.copernicus.eu/explore-data/data-collections/copernicus-contributing-missions/collections-description/COP-DEM), AWS 공개 타일 `Copernicus_DSM_COG_10_N37_00_E131_00_DEM.tif`. 타일은 3600 × 3600, EPSG:4326, 1 arc-second(약 30 m)입니다. 제품은 DSM이므로 식생·시설물이 포함될 수 있습니다.
- 육상 대안: 국토지리정보원 국토정보플랫폼 [공개DEM](https://map.ngii.go.kr/)에서 2025년 `독도 37116` 도엽을 내려받았습니다. 압축 원본은 `data/(B080)공개DEM_37116_img_2025.zip`, 래스터는 `data/ngii_2025_publicdem/37116/37116.img`입니다. HFA/IMG, EPSG:5179, 267 × 325 격자, 90 m 해상도입니다. 전체 도엽의 표고 범위는 -4.95~111.23 m입니다. IMG 메타데이터에 수직 기준은 명시되어 있지 않습니다.
- 처리: 각 모델은 선택된 육상 래스터의 유효한 0 m 초과 표고를 육상으로 분류하고, 나머지 영역은 GEBCO 해저 표고로 채웁니다. NGII 도엽은 바다 영역 일부가 NoData이므로 NoData를 해저로 처리합니다. 양쪽 자료의 해안 경계는 원자료 해상도 차이로 단차가 남을 수 있으며 수직 과장은 하지 않았습니다.

## 정확도와 한계

GEBCO 요청 중 위도 행 인덱스가 남위 자료를 가리키는 오류를 발견했습니다. 그 데이터는 사용하지 않았고, 반환된 위도 배열이 북위 37.20625~37.27292°인지 확인한 확장 부분 격자만 모델에 반영했습니다. 재요청한 GEBCO 격자에는 독도 육지가 양의 표고로 나타나지 않아, 육상 DSM을 별도로 결합했습니다.

Copernicus GLO-30 DSM은 독도처럼 작고 경사가 급한 암석섬의 최고점을 충분히 표현하지 못할 수 있습니다. 이번 모델 범위의 Copernicus 표고는 최대 34.5 m입니다. NGII 2025 공개DEM은 같은 범위에서 최대 106.2 m를 표현하지만 원 해상도는 90 m라 작은 암석과 급경사를 매끄럽게 만듭니다. 두 모델 모두 측량급 결과가 아니라 공개 격자 자료를 결합한 수업·시각화용 지형입니다. 육상 래스터의 수직 기준이 확인되지 않아 GEBCO 해저 자료와 수직 기준을 정합하지 않았으므로 해안부 절대고도는 근사값입니다.

## 독도 확대 모델

넓은 바다에 비해 독도가 작게 보이는 문제를 줄이기 위해 별도 확대본을 만들었습니다. 출력 면적은 실제 지상 1.2 × 1.2 km이며, 200 × 200 mm로 출력합니다. 육상에는 약 30 m 해상도 Copernicus DSM, 해저에는 GEBCO 2026을 사용하고, 표고 과장은 2배입니다. 해안선은 큐빅 보간한 표고가 1 m를 넘는 경계로 분류해 Copernicus 해안 주변의 낮은 양수 잡음을 줄였습니다.

이 확대본은 두 주요 섬이 더 크게 보이지만, 30 m 원자료 한 격자는 출력물에서 약 5 mm입니다. 따라서 작은 바위의 외곽은 여전히 단순화되어 있습니다. 보간으로 격자 계단을 완화할 수는 있어도 원자료에 없는 세부 윤곽을 복원할 수는 없습니다. 해안선을 더 정밀하게 표현하려면 고해상도 벡터 해안선 또는 더 세밀한 DEM이 필요합니다. 확대본의 Copernicus 표고 최대값은 38.5 m이며, 모델 높이는 밑판을 포함해 약 61.7 mm입니다.

## 만쥬용 실리콘 몰드 마스터

`output/mold_master/dokdo_relief_mandu_master_80mm.stl`은 80 × 80 mm 판 위에 독도 지형을 양각한 **실리콘 몰드 캐스팅용 마스터**입니다. 판 두께는 3 mm, 섬의 최대 양각은 약 6.66 mm이며, 실제 지상 900 × 900 m 범위를 사용했습니다. Copernicus DEM의 30 m 원 격자 한 칸은 이 마스터에서 약 2.67 mm입니다. 출력할 때 평평한 판 뒷면을 프린터 베드에 놓습니다.

이 파일 자체를 음식에 직접 접촉시키는 용도가 아닙니다. 양각 마스터를 이용해 실리콘 음각을 뜨는 패턴입니다. 사용하려는 실리콘 제품의 제조사 문서에서 원하는 음식 종류, 온도, 반복 사용 및 경화 조건에 적합한지 확인하고, 혼합·경화·후경화·세척 지침을 따르세요. “백금 경화” 또는 포괄적인 “FDA compliant” 문구만으로 완성 몰드의 식품 접촉 적합성을 단정하지 마세요. 자세한 내용은 `references/food-mold-masters.md`를 참고하세요.

## Thingiverse에서 받은 모델

[Thingiverse 모델 페이지](https://www.thingiverse.com/thing:3183098)에서 한글판과 영문판 STL을 받았습니다. 페이지에는 제작자 `woojung`, 게시일 2018-10-29, 라이선스 **CC BY-NC 4.0**이 표시됩니다. 이 라이선스는 저작자 표시와 비상업적 이용을 요구하므로, 상업용 출력이나 재배포 전에 라이선스 조건을 확인하세요. 상세 출처는 `models/thingiverse_3183098/SOURCE.md`에 기록했습니다.

두 파일은 STL을 mm로 읽었을 때 각각 약 272 × 229 × 45.7 mm, 272 × 232 × 45.7 mm입니다. STL은 단위를 저장하지 않으므로 슬라이서에서 출력 크기를 직접 설정하세요. 자동 메시 검사에서는 한글판 75,294면·515개 연결 조각, 영문판 105,814면·524개 연결 조각이었고, 둘 다 watertight가 아니었습니다. 파일이 열리는 것은 확인했지만 슬라이서 복구와 출력 가능 여부는 아직 확인하지 않았으므로, 출력 전 슬라이스 미리보기에서 열린 면과 분리된 조각을 확인하세요.

## 다시 만들기

프로젝트 폴더에서 가상환경을 만든 뒤 의존성을 설치하고 다음 명령을 실행합니다.

기본 독도 지형 STL:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe convert_gebco_ascii.py
.\.venv\Scripts\python.exe process_dokdo.py
.\.venv\Scripts\python.exe process_dokdo.py `
  --land-dem "data/ngii_2025_publicdem/37116/37116.img" `
  --land-dataset "NGII Public DEM 2025, sheet 37116" `
  --land-source-url "https://map.ngii.go.kr/" `
  --land-native-resolution "90 m" `
  --land-product-type "Digital elevation model (DEM)" `
  --land-classification "valid positive raster samples treated as land" `
  --land-vertical-reference "Not specified in raster metadata; no vertical datum conversion applied" `
  --output-stem "dokdo_gebco_ngii_2025_200mm" `
  --output-dir "output/ngii_2025" `
  --preview-dir "preview/ngii_2025"
```

독도 확대 모델 재생성 예시:

```powershell
.\.venv\Scripts\python.exe process_dokdo.py `
  --extent-m 1200 `
  --grid-spacing-m 5 `
  --vertical-exaggeration 2 `
  --land-threshold-m 1 `
  --land-dem "data/Copernicus_DSM_COG_10_N37_00_E131_00_DEM.tif" `
  --land-dataset "Copernicus DEM GLO-30" `
  --land-native-resolution "1 arc-second / approximately 30 m" `
  --land-product-type "DSM" `
  --land-classification "cubic-interpolated samples above 1 m" `
  --output-stem "dokdo_island_focus_copernicus_200mm_2x" `
  --output-dir "output/island_focus" `
  --preview-dir "preview/island_focus"
```

만쥬 몰드 마스터 재생성:

```powershell
.\.venv\Scripts\python.exe create_dokdo_mold_master.py `
  --extent-m 900 `
  --center-offset-x-m -175 `
  --center-offset-y-m 112 `
  --size-mm 80 `
  --grid-spacing-m 3 `
  --base-mm 3 `
  --vertical-exaggeration 2 `
  --land-threshold-m 1 `
  --output-dir "output/mold_master" `
  --preview-dir "preview/mold_master"
```

## 확인 결과

원래 두 STL은 각각 161,600개 삼각형이고, 확대 STL과 몰드 마스터는 각각 232,320개 및 362,400개 삼각형입니다. 이 네 메시 모두 watertight 및 양의 부피로 확인했습니다. 원래 Copernicus 모델 높이는 약 28.21 mm, NGII 2025 모델은 약 30.60 mm, 확대 모델은 약 61.73 mm, 몰드 마스터는 약 9.66 mm입니다. Thingiverse에서 받은 한글판과 영문판은 watertight가 아니므로 슬라이서 복구와 미리보기가 필요합니다. 실제 프린터 출력 및 실리콘 캐스팅은 확인하지 않았습니다.
