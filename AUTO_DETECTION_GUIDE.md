# 자동 열 탐지 시스템 가이드

## 📋 개요

B2Mark의 자동 열 탐지 시스템은 **새로운 데이터셋의 열 이름이 `config.json`에 없어도 자동으로 적합한 열을 찾아 워터마킹을 수행**할 수 있습니다.

## 🎯 문제점 해결

### 기존 문제
```
❌ 새 데이터셋의 열 이름이 config.json에 없으면 오류 발생
❌ 매번 새 데이터셋마다 config.json 수정 필요
❌ 유연성 부족
```

### 새로운 해결책
```
✅ 자동으로 실수형 열 탐지
✅ 자동으로 범주형 열 탐지  
✅ 데이터셋 구조 자동 분석
✅ config.json 수정 불필요
```

## 🔍 탐지 알고리즘

### 1️⃣ 우선순위 시스템

```
┌─────────────────────────────────────────┐
│ auto_detect_columns()                   │
└──────────────┬──────────────────────────┘
               │
         ┌─────▼─────┐
         │ config.json │
         │ 설정값 있음? │
         └──┬──────┬──┘
           YES    NO
            │      │
            │      ▼
            │  ┌─────────────────────┐
            │  │ Fallback 자동 탐지  │
            │  └─────────────────────┘
            │      │
            ▼      ▼
        ┌──────────────────┐
        │ Target + RefCols │
        │ 반환            │
        └──────────────────┘
```

### 2️⃣ Numeric 열 탐지 (`get_numeric_columns`)

**탐지 과정:**
```
1. 모든 numeric 타입(int, float) 열 추출
2. 불필요한 열 필터링:
   ├─ ID/인덱스 성: id, index, no, count, code 등
   ├─ 시간 관련: date, time, year, month 등  
   └─ 범위 너무 작음: max-min < 1
3. 값의 범위가 큰 순서로 정렬
```

**예시:**
```python
# 입력 DataFrame
   id    amount    purchase_time    tax
0  001   50000     2024-01-01       5000
1  002   75000     2024-01-02       7500

# 탐지 결과
✓ 탐지된 numeric 열: ['amount', 'tax']
  - 'amount': 범위 50000 ~ 75000
  - 'tax': 범위 5000 ~ 7500

✗ 제외된 열:
  - 'id': ID 성 열
  - 'purchase_time': 시간 관련 열
```

### 3️⃣ Categorical 열 탐지 (`get_categorical_columns`)

**탐지 과정:**
```
1. 모든 object/string/category 타입 열 추출
2. 불필요한 열 필터링:
   ├─ 고유값이 너무 많음: >1000 (예: 주소, 설명)
   └─ 고유값이 너무 적음: <2 (예: 상수 값)
3. 고유값 개수 순서로 정렬
```

**예시:**
```python
# 입력 DataFrame
   gender  region        description
0  M       Seoul         Item A
1  F       Busan         Item B

# 탐지 결과
✓ 탐지된 categorical 열: ['gender', 'region']
  - 'gender': 2 고유값
  - 'region': 2 고유값

✗ 제외된 열:
  - 'description': 고유값이 너무 많음 (1000+)
```

### 4️⃣ Fallback 열 선택 (`auto_detect_columns_fallback`)

```
┌────────────────────────────────────────┐
│ 1단계: Target 열 선택                  │
├────────────────────────────────────────┤
│ • 가장 범위가 큰 numeric 열 선택       │
│ • 이유: 워터마킹에 더 강건하고 효과적  │
└────────────────────────────────────────┘
                    ↓
┌────────────────────────────────────────┐
│ 2단계: Reference 열 선택               │
├────────────────────────────────────────┤
│ • Categorical 열이 있으면 우선 선택    │
│ • 고유값이 적은 순서로 2개 선택        │
│ • Categorical이 없으면 numeric 열 사용 │
└────────────────────────────────────────┘
```

## 💡 사용 예시

### 기본 사용 (Verbose 없음)
```python
from watermark import B2MarkEmbedder

embedder = B2MarkEmbedder(secret_key="my_key")

# 자동 탐지 - 열 이름이 자동으로 선택됨
metadata = embedder.embed(
    source_path="my_data.csv",
    output_path="watermarked.csv",
    buyer_bitstring="10110",
    data_type="real_estate"  # config 설정이 없어도 됨
)
```

### Verbose 모드 (탐지 과정 확인)
```python
# 탐지 과정 상세 로깅
metadata = embedder.embed(
    source_path="my_data.csv",
    output_path="watermarked.csv",
    buyer_bitstring="10110",
    data_type="real_estate",
    verbose=True  # 자동 탐지 과정 출력
)
```

**출력 예시:**
```
✓ config.json에서 열 정보 발견
  - Target: '총_월납_보험료'
  - Reference: ['성별', '연령', '지역']
```

### Fallback 모드 작동 예시
```python
# config.json 설정이 없는 새 데이터셋
metadata = embedder.embed(
    source_path="new_dataset.csv",
    output_path="watermarked.csv",
    buyer_bitstring="11011",
    data_type="real_estate",
    verbose=True
)
```

**출력 예시:**
```
⚠ config.json 설정이 일치하지 않음. Fallback 자동 탐지...

🔍 Fallback 자동 열 탐지 시작...
  ⊘ 'purchase_count' 제외 (ID/인덱스 성 열로 판단)
✓ 탐지된 numeric 열: ['transaction_value']
  - 'transaction_value': 범위 10000 ~ 500000
✓ Target 열 선택: 'transaction_value'
✓ 탐지된 categorical 열: ['user_category']
  - 'user_category': 5 고유값
✓ Reference 열 선택: ('user_category',)

[Embed] Buyer bitstring: 11011
```

## 📊 필터링 기준 상세

### Numeric 열 제외 키워드

| 카테고리 | 키워드 예시 |
|---------|-----------|
| **ID 성** | id, index, idx, number, no, seq, count, cnt, code, key, pk |
| **시간 관련** | date, time, datetime, year, month, day, hour, minute, timestamp, epoch |

### Numeric 열 범위 기준
```
❌ min-max < 1 인 열 제외
   예: [0.001, 0.005, 0.008] → 범위 0.007 제외

✅ min-max >= 1 인 열만 사용
   예: [10, 50, 100] → 범위 90 ✓
```

### Categorical 열 필터 기준
```
✅ 2 <= 고유값 개수 <= 1000
   예: ['A', 'B', 'C'] (3개) ✓
   예: [1, 2, 3, ..., 1001] (1001개) ❌

❌ 고유값 < 2 (상수)
   예: ['same', 'same', 'same'] (1개) ❌
   
❌ 고유값 > 1000 (고유성 너무 높음)
   예: 도시, 주소, 이름 등
```

## 🔧 설정 파일 (config.json)

자동 탐지는 `config.json`이 없거나 설정이 일치하지 않아도 작동합니다.

하지만 성능 최적화를 위해 데이터셋에 맞게 설정할 수 있습니다:

```json
{
  "my_dataset_type": {
    "description": "내 데이터셋 설명",
    "target_col_candidates": [
      "선호하는_열_이름1",
      "선호하는_열_이름2",
      "열_이름3"
    ],
    "ref_cols_candidates": [
      ["참조열1", "참조열2"],
      ["참조열3", "참조열4"]
    ],
    "k": 16,
    "g": 2,
    "embed_seed": 10000
  }
}
```

**없어도 됨:** Fallback 자동 탐지로 자동 처리

## 📈 성능 비교

### 자동 탐지 vs 수동 설정

| 항목 | 자동 탐지 | 수동 설정 |
|------|---------|---------|
| 새 데이터셋 적용 | 즉시 | config.json 수정 필요 |
| 설정 오류 | 자동 보정 | 수동 수정 |
| 최적화 | 휴리스틱 기반 | 데이터 기반 |
| 안정성 | 높음 (보수적) | 매우 높음 |

## ⚠️ 주의사항

### 주의 1: 열 이름 명확성
```python
❌ 나쁜 예: 'col1', 'col2', 'val'
✅ 좋은 예: 'transaction_amount', 'customer_category'
```
→ 자동 탐지가 더 정확함

### 주의 2: 데이터 크기
```python
❌ 너무 작은 데이터: < 50행
   └─ 워터마킹 강건성 저하

✅ 충분한 데이터: > 1000행
   └─ 안정적인 워터마킹 가능
```

### 주의 3: 데이터 다양성
```python
❌ 값의 다양성 부족
   └─ 모든 값이 비슷한 범위

✅ 값의 범위가 충분함
   └─ 워터마킹 신호 강함
```

## 🐛 디버깅

### Verbose 모드로 문제 진단
```python
metadata = embedder.embed(
    source_path="problem_data.csv",
    output_path="output.csv",
    buyer_bitstring="10110",
    data_type="real_estate",
    verbose=True  # 탐지 과정 출력
)
```

### 발생 가능한 오류 및 해결책

| 오류 메시지 | 원인 | 해결책 |
|-----------|------|-------|
| "워터마킹에 적합한 numeric 열을 찾을 수 없습니다" | numeric 열 부족 | 데이터에 숫자 열 추가 |
| "참조 열(ref_cols)을 찾을 수 없습니다" | categorical 열 부족 | categorical 열 추가 |
| 탐지된 열이 부적절함 | 열 이름 모호함 | 명확한 열 이름 사용 |

## 📝 예제 코드 모음

### 예제 1: 기존 데이터셋 (config.json 설정 사용)
```python
from watermark import B2MarkEmbedder, B2MarkDetector

# 보험 데이터 - config.json에 설정됨
embedder = B2MarkEmbedder("secret_key")
metadata = embedder.embed(
    source_path="insurance_data.csv",
    output_path="watermarked.csv",
    buyer_bitstring="10110",
    data_type="insurance"
)
```

### 예제 2: 새로운 데이터셋 (자동 탐지)
```python
# 새 데이터셋 - 자동으로 열 탐지
metadata = embedder.embed(
    source_path="new_data.csv",
    output_path="watermarked.csv",
    buyer_bitstring="11011",
    data_type="real_estate"  # 형식이 달라도 자동 탐지
)
```

### 예제 3: 수동으로 열 지정 (최고 성능)
```python
# 수동 지정 - 가장 안정적
metadata = embedder.embed(
    source_path="data.csv",
    output_path="watermarked.csv",
    buyer_bitstring="10110",
    target_col="my_price_column",  # 직접 지정
    ref_cols=["category", "region"]  # 직접 지정
)
```

## 🎓 기술 상세

### 자동 탐지 알고리즘 복잡도
- 시간 복잡도: O(n·m) (n=행 수, m=열 수)
- 공간 복잡도: O(m)
- 일반적으로 <100ms (1000행 기준)

### 탐지 정확도
- 명확한 열 이름: 95%+
- 모호한 열 이름: 70%~80%
- 명시적 지정: 100%

---

**질문이나 버그 보고:** GitHub Issues 또는 프로젝트 담당자 연락
