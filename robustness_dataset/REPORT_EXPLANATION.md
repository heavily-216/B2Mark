## `report.json` 파일 설명

`robustness_dataset/report.json`은 “워터마킹된 CSV를 여러 방식으로 손상시킨 뒤에도 `detect`가 원래 구매자 ID를 복원하는지”를 변형별로 요약한 결과 파일입니다.

- **`buyer_id_expected`**: 기대하는(삽입한) 구매자 ID 비트열
- **`bit_len`**: ID 비트 길이
- **`base_csv`**: 워터마크 삽입 전 더미 원본 CSV 경로
- **`watermarked_csv`**: 워터마크 삽입된 CSV 경로
- **`meta_json`**: 검출에 필요한 메타데이터(가격 범위/시드 등) 경로
- **`variants`**: 손상(변형) 버전별 결과 리스트
  - **`name`**: 변형 이름
  - **`path`**: 해당 변형 CSV 경로
  - **`detected_id`**: 그 변형 파일에서 검출된 ID
  - **`ok`**: `detected_id == buyer_id_expected` 여부
- **`summary`**
  - **`total`**: 변형 개수
  - **`ok`**: 성공 개수
  - **`fail`**: 실패 개수

이번 실행에서는 `summary.ok == summary.total`이면 “모든 손상 변형에서도 ID가 동일 복원됨”을 의미합니다.

## 변형(`variants.name`)이 의미하는 손상 종류

- **`wm_clean`**: 손상 없이 워터마킹된 파일 그대로(기준선)
- **`round_int`**: `price`를 정수로 반올림(자리수 손실)
- **`round_2dp`**: `price`를 소수 둘째 자리로 반올림
- **`gaussian_noise_10pct_small`**: 전체 행 중 10%의 `price`에 작은 가우시안 노이즈 추가
- **`gaussian_noise_30pct_small`**: 전체 행 중 30%의 `price`에 작은 가우시안 노이즈 추가
- **`uniform_jitter_20pct`**: 전체 행 중 20%의 `price`에 작은 균등 잡음(±) 추가
- **`clip_1_99`**: `price`를 1~99퍼센타일 범위로 클리핑(이상치/극단값 손상 가정)
- **`scale_shift_small`**: `price`에 약한 스케일/시프트 적용(단위 변환/정규화 같은 변환 가정)
- **`string_format_1dp`**: 전달/저장 과정에서 포맷이 강제되는 상황(소수 1자리 문자열화 후 수치화)

## 결과 해석 기준(보고서용)

### 1) 기본 판정 기준(정답 완전 일치)

- **Pass**: 변형 파일에서 `detected_id == buyer_id_expected` (0-bit error)
- **Fail**: 하나라도 다르면 Fail

발표/보고서에서 “손상에도 워터마크에 이상이 없다”를 가장 강하게 말하려면 이 기준이 깔끔합니다.

### 2) 강인성(robustness) 주장 기준(데이터셋 단위)

변형 종류가 \(N\)개일 때, 성공률 \(p = \frac{\#Pass}{N}\).

- **Strong**: \(p = 1.0\) (100% 성공)
- **Good**: \(p \ge 0.9\)
- **Weak**: \(p < 0.9\)

### 3) 비트 오류 허용 기준(선택: 더 관대한 기준)

ID 길이가 \(L\)일 때 기대 ID와 검출 ID의 해밍거리 \(d\)로 평가할 수도 있습니다.

- **Pass(관대)**: \(d \le 1\) (예: 5비트면 1비트까지 오류 허용)
- **Fail**: \(d > 1\)

단, “이상 없음”을 보여주려면 0-bit error를 기본으로 두는 것이 일반적으로 더 설득력 있습니다.

### 4) Z-score 리포트 기준(코드 로직과의 연결)

`watermark.py`의 `detect()`는 비트별로 Z-score를 계산하고, 임계값 **1.645(95% 신뢰)** 기준으로 1/0을 판정합니다.

- 따라서 변형(손상) 후에도 각 비트의 Z-score가 동일한 쪽으로 유지되어(> 1.645 또는 ≤ 1.645) 최종 ID가 동일하게 복원되면 “통계적으로도 판정이 안정적”이라고 설명할 수 있습니다.

## (추가) 변형별 Z-score 리포트 저장

`make_robustness_dataset.py`를 아래처럼 실행하면 변형별 `detect()` 출력(비트별 Z-score)이 파일로 저장됩니다.

```bash
python3 make_robustness_dataset.py --out_dir robustness_dataset --save_detection_logs
```

저장 위치:

- `robustness_dataset/detection_logs/<variant>.txt`

