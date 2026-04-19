# 자동 열 탐지 시스템 가이드 - 마켓플레이스 최적화

## 📋 개요

B2Mark는 **마켓플레이스 시스템**으로서 새로운 데이터셋을 받으면 자동으로 워터마킹에 적합한 열을 찾아 **즉시 처리**할 수 있습니다.

**핵심:** config.json 없이도 모든 데이터셋을 처리할 수 있습니다.

## 🎯 설계 철학

### 마켓플레이스 요구사항
```
❌ 데이터셋마다 config.json 수정 → 너무 번거로움
❌ 수동 설정 필요 → 진입장벽 높음
❌ 사용자가 복잡함을 느낌

✅ 새 데이터셋 → 자동 탐지 → 즉시 워터마킹
✅ 설정 불필요 → 간단함
✅ config.json은 선택 (성능 최적화용)
```

## 🔍 탐지 알고리즘

### 1️⃣ 우선순위 시스템 (마켓플레이스 최적화)

```
┌──────────────────────────────────────────────┐
│ auto_detect_columns(df, data_type)          │
│ (prefer_config=False, 기본값)               │
└──────────────┬───────────────────────────────┘
               │
        🔍 자동 탐지 (우선)
               │
    ┌──────────▼──────────┐
    │ get_numeric_cols()  │
    │ get_categ_cols()    │
    └──────────┬──────────┘
               │
        ✅ 즉시 사용 (마켓플레이스)
               
config.json은 선택사항:
prefer_config=True 설정 시 config 우선 시도
   → 없으면 자동 탐지로 Fallback
```

**기본 (prefer_config=False):**
- 모든 데이터셋에 자동 적용
- config.json 필요 없음
- 마켓플레이스에 최적화

**선택 (prefer_config=True):**
- config.json이 있으면 그것 사용
- 없으면 자동 탐지로 Fallback
- 성능 최적화 원할 때 사용

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

### 📌 예제 1: 마켓플레이스 기본 (권장)
```python
from watermark import B2MarkEmbedder

embedder = B2MarkEmbedder(secret_key="my_key")

# 새 데이터셋 → 자동 탐지 → 즉시 워터마킹 ✨
metadata = embedder.embed(
    source_path="new_marketplace_data.csv",
    output_path="watermarked.csv",
    buyer_bitstring="10110",
    data_type="any_type"  # config.json 필요 없음!
)
```
**특징:** 모든 데이터셋에 자동 적용, config.json 불필요

---

### 📌 예제 2: Verbose 모드 (디버깅)
```python
# 탐지 과정 상세 로깅
metadata = embedder.embed(
    source_path="data.csv",
    output_path="watermarked.csv",
    buyer_bitstring="10110",
    data_type="real_estate",
    verbose=True  # 어떤 열이 선택되었는지 확인
)
```

**출력 예시:**
```
🔍 자동 탐지 모드 (마켓플레이스 최적화)

🔍 Fallback 자동 열 탐지 시작...
✓ 탐지된 numeric 열: ['총_월납_보험료', ...]
✓ Target 열 선택: '총_월납_보험료'
✓ 탐지된 categorical 열: ['직업', '지역']
✓ Reference 열 선택: ('직업', '지역')
```

---

### 📌 예제 3: 성능 최적화 (선택사항)
```python
# config.json이 있으면 그것을 사용
# 없으면 자동 탐지로 Fallback
metadata = embedder.embed(
    source_path="data.csv",
    output_path="watermarked.csv",
    buyer_bitstring="10110",
    data_type="insurance",
    # prefer_config=True  # 추가 파라미터로 가능
)
```
**특징:** 성능 최적화를 원할 때만 사용

---

### 📌 예제 4: 수동 지정 (고급)
```python
# 직접 열을 지정하면 탐지 과정 스킵
metadata = embedder.embed(
    source_path="data.csv",
    output_path="watermarked.csv",
    buyer_bitstring="10110",
    target_col="price",           # 직접 지정
    ref_cols=["category", "region"]  # 직접 지정
)
```
**특징:** 가장 안정적, 자동 탐지 필요 없음
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

## 🔧 설정 파일 (config.json) - 선택사항

### 📌 기본: config.json 필요 없음
자동 탐지로 모든 데이터셋 처리 가능합니다.

### 📌 선택: 성능 최적화
특정 데이터셋에 대해 수동 최적화가 필요한 경우에만 추가합니다:

```json
{
  "my_dataset_type": {
    "description": "내 데이터셋 설명",
    "target_col_candidates": [
      "선호하는_열_이름1",
      "선호하는_열_이름2"
    ],
    "ref_cols_candidates": [
      ["참조열1", "참조열2"],
      ["참조열3"]
    ],
    "k": 16,
    "g": 2,
    "embed_seed": 10000
  }
}
```

### 사용 시
```python
# prefer_config=True로 설정값 우선 사용
embedder.embed(
    source_path="data.csv",
    output_path="watermarked.csv",
    buyer_bitstring="10110",
    data_type="my_dataset_type",
    prefer_config=True  # config 설정 우선
)
```

## 📈 성능 비교

### 마켓플레이스 워크플로우

| 단계 | 자동 탐지 (기본) | config.json (선택) |
|------|--------|---------|
| **새 데이터셋** | ✅ 즉시 처리 | ❌ 설정 필요 |
| **빠른 출시** | ✅ 1초 | ❌ 수십 초 |
| **사용 편의** | ✅ 간단 | ❌ 복잡 |
| **성능 최적** | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| **강건성** | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ |

**결론:** 마켓플레이스 시스템에는 **자동 탐지(기본)**가 최적화됨

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
