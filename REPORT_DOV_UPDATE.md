# B2Mark DOV 구현 리포트

## 1) 목적

- 기존 B2Mark 워터마크 삽입/검출 시스템에 Data Ownership Verification(DOV) 기능을 추가해, 특정 구매자 ID에 대한 소유권 주장 검증을 가능하게 함.

## 2) 수정 파일 및 변경 사항

- `watermark.py`
  - `B2MarkDetector._collect_bit_stats(...)` 추가
    - 비트별 `green/total` 통계 및 Z-score 계산 로직을 공통화.
  - `B2MarkDetector.verify_ownership(...)` 추가
    - 입력: `suspect_path`, `meta_data`, `claimed_buyer_id`, `bit_length`, `z_threshold`, `min_match_ratio` 등.
    - 처리:
      - 비트별 판정(bit=1 if z > z_threshold)
      - `claimed_buyer_id` 대비 비트 일치율(`match_ratio`) 계산
      - `min_match_ratio` 기준 소유권 검증 성공/실패 결정
    - 반환:
      - `detected_id`, `match_ratio`, `ownership_verified`, `bit_stats`, `z_scores` 포함 상세 결과.
  - 기존 `detect(...)`는 공통 수집 함수 재사용하도록 리팩터링(기능 유지).
- `main.py`
  - CLI 명령 `dov` 추가.
  - 인자:
    - `--input`, `--meta`, `--claimed_id`, `--bit_len`
    - `--z_threshold`(default: 1.645)
    - `--min_match_ratio`(default: 0.8)
  - 출력:
    - `Claimed ID`, `Detected ID`, `Matched`, `Match Ratio`, 최종 판정(`OWNERSHIP VERIFIED`/`NOT VERIFIED`).
- `gui.py`
  - 새 탭: `Data Ownership Verification (DOV)` 추가.
  - 입력 위젯:
    - 유출 CSV, 메타 JSON, 주장 구매자 ID, ID 길이, Z 임계값, 최소 일치율
  - 실행 버튼 `✅ DOV 검증 시작` 추가.
  - 결과 표시:
    - 로그 창 + 팝업으로 검증 결과/일치율/판정 출력.
  - 메타 파일 선택은 JSON 전용 chooser(`select_json_file`)로 분리.
  - 창 크기 조정(`500x450` -> `560x540`)으로 DOV UI 수용.
- `make_robustness_dataset.py`
  - `VariantResult`에 DOV 평가 필드 추가:
    - `dov_verified`, `dov_match_ratio`
  - 신규 인자:
    - `--dov_z_threshold`(default: 1.645)
    - `--dov_min_match_ratio`(default: 0.8)
  - 변형(variant)별 평가 시:
    - 기존 `detect` 결과와 함께 `verify_ownership` 호출
    - `report.json`/`report.csv`에 DOV 결과 반영
  - `report.json.summary`에 DOV 집계 추가:
    - `dov_verified`, `dov_not_verified`

## 3) 사용 방법

- CLI DOV:
  - `./.venv/bin/python main.py dov --input leaked.csv --meta sold.csv.meta.json --claimed_id 10110 --bit_len 5`
- GUI DOV:
  - `./.venv/bin/python gui.py` 실행 후 `Data Ownership Verification (DOV)` 탭 사용.
- Robustness + DOV 평가:
  - `./.venv/bin/python make_robustness_dataset.py --out_dir robustness_dataset --rows 3000 --seed 42 --buyer_id 10110 --bit_len 5`
  - 필요 시 DOV 임계값 조정:
    - `--dov_z_threshold 1.645 --dov_min_match_ratio 0.8`

## 4) 검증 내역

- 문법/컴파일 검증:
  - `./.venv/bin/python -m py_compile gui.py watermark.py main.py`
- 결과:
  - 에러 없이 통과.

## 5) 기대 효과

- 단순 워터마크 검출(ID 복원)에서 확장되어, 특정 사용자 소유권 주장에 대한 정량적 검증(일치율 기반)이 가능해짐.
- 강인성 데이터셋 평가 단계에서 DOV 성능까지 함께 추적 가능해짐.

