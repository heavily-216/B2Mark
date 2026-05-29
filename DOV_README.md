# Taggants 기반 데이터 소유권 검증 (DOV) 시스템

B2Mark 프로젝트에 통합된 **Taggants 기반 DOV(Data Ownership Verification)** 시스템에 대한 문서입니다.

## 📋 목차

1. [개요](#개요)
2. [아키텍처](#아키텍처)
3. [설치](#설치)
4. [사용 방법](#사용-방법)
5. [API 문서](#api-문서)
6. [예제](#예제)
7. [통계적 검증 원리](#통계적-검증-원리)
8. [핵심 구성 요소](#핵심-구성-요소)
9. [문제 해결](#문제-해결)

---

## 개요

### Taggants란?

**Taggants**는 표형 데이터의 소유권을 검증하기 위한 고급 기법입니다:

- **비밀 키(Secret Keys)**: In-Distribution 또는 Out-of-Distribution(OOD) 범위에서 생성되는 숨겨진 입력값
- **중독(Poisoning)**: 대리 신경망을 이용하여 원본 데이터에 비밀 키를 소량 주입
- **검증(Verification)**: 블랙박스 모델 API에 비밀 키를 쿼리하여 소유권 여부를 통계적으로 판단

### 핵심 특징

✅ **블랙박스 검증**: 모델의 내부 구조를 몰라도 API 호출로 검증 가능  
✅ **통계적 근거**: 이항분포 기반 p-value로 결과의 신뢰성 평가  
✅ **저탐지율**: OOD 기반 비밀 키로 데이터 조작 감지 어려움  
✅ **유연한 전략**: In-Distribution 또는 OOD 모드 선택 가능  

---

## 아키텍처

### 3단계 파이프라인

```
┌─────────────────────────┐
│  1. 비밀 키 생성         │  generate_secret_keys()
│  (In-Dist 또는 OOD)    │
└────────────┬────────────┘
             │
             ▼
┌─────────────────────────┐
│  2. Taggants 주입       │  inject_taggants()
│  (Gradient Matching)   │
└────────────┬────────────┘
             │
             ▼
┌─────────────────────────┐
│  3. 소유권 검증         │  verify_ownership()
│  (통계적 검증)         │
└─────────────────────────┘
```

### 핵심 클래스

```python
# 설정
TaggantsConfig
  - num_features: 입력 feature 수
  - num_classes: 출력 클래스 수
  - num_keys: 비밀 키 개수 (기본: 30)
  - poison_ratio: 중독 비율 (기본: 0.01)
  - learning_rate: 학습률 (기본: 0.01)
  - max_iterations: 최대 반복 (기본: 100)
  - alpha: 통계적 유의수준 (기본: 0.01)

# 메인 엔진
TabularTaggantEngine
  - generate_secret_keys(): 비밀 키 생성
  - inject_taggants(): 데이터에 taggants 주입
  - verify_ownership(): 블랙박스 모델 검증
  - save_metadata(): 메타데이터 저장
  - load_metadata(): 메타데이터 로드
```

---

## 설치

```bash
# 의존성 설치
pip install -r requirements.txt

# 또는 개별 설치
pip install torch scipy numpy pandas
```

---

## 사용 방법

### 기본 사용법

#### 1단계: Taggants 엔진 초기화

```python
from dov import create_taggants_engine
import pandas as pd

# 데이터 로드
data = pd.read_csv("original.csv")

# 엔진 생성
engine = create_taggants_engine(
    num_features=5,        # 입력 feature 수
    num_classes=3,         # 클래스 수
    num_keys=30,          # 비밀 키 개수
    poison_ratio=0.01,    # 중독 비율
    device="cpu"          # "cpu" 또는 "cuda"
)
```

#### 2단계: 비밀 키 생성

```python
# 데이터 범위를 고려하여 비밀 키 생성
secret_x, secret_y = engine.generate_secret_keys(
    csv_data=data,
    use_in_distribution=True  # In-Distribution 모드 사용
)

print(f"Secret keys shape: {secret_x.shape}")  # (30, 5)
print(f"Secret labels shape: {secret_y.shape}")  # (30,)
```

#### 3단계: Taggants 주입

```python
# 원본 데이터에 taggants 주입
poisoned_data = engine.inject_taggants(
    csv_data=data,
    secret_x=secret_x,
    secret_y=secret_y,
    poison_ratio=0.01  # 1% 데이터 수정
)

# 중독된 데이터 저장
poisoned_data.to_csv("poisoned.csv", index=False)
```

#### 4단계: 소유권 검증

```python
# 블랙박스 모델의 예측 함수 정의
def model_api(x):
    """외부 모델 API 호출
    
    Args:
        x: numpy array (1D or 2D)
        
    Returns:
        클래스 인덱스 (int)
    """
    # 실제로는 외부 서비스 호출
    return external_model.predict(x)

# 소유권 검증
result = engine.verify_ownership(
    target_model_api_fn=model_api,
    secret_x=secret_x,
    secret_y=secret_y,
    alpha=0.01,
    verbose=True
)

print(result)
# {
#   'is_stolen': True,
#   'p_value': 0.000123,
#   'confidence': 99.99%,
#   'matched': '28/30',
#   'match_ratio': 0.933,
#   ...
# }
```

---

## API 문서

### `create_taggants_engine()`

**간편한 엔진 생성 함수**

```python
def create_taggants_engine(
    num_features: int,
    num_classes: int,
    num_keys: int = 30,
    poison_ratio: float = 0.01,
    device: str = "cpu",
    use_in_distribution: bool = True
) -> TabularTaggantEngine
```

**매개변수**:
- `num_features`: 입력 feature 개수 (필수)
- `num_classes`: 분류할 클래스 개수 (필수)
- `num_keys`: 생성할 비밀 키 개수 (기본: 30)
- `poison_ratio`: 데이터 중독 비율 0~1 (기본: 0.01)
- `device`: "cpu" 또는 "cuda" (기본: "cpu")
- `use_in_distribution`: True면 In-Distribution, False면 OOD (기본: True)

**반환값**: `TabularTaggantEngine` 인스턴스

---

### `TabularTaggantEngine.generate_secret_keys()`

**비밀 키 생성 (In-Distribution 또는 OOD 방식)**

```python
def generate_secret_keys(
    csv_data: Optional[pd.DataFrame] = None,
    ood_margin: float = 1.5,
    use_in_distribution: bool = True
) -> Tuple[np.ndarray, np.ndarray]
```

**매개변수**:
- `csv_data`: 범위 추정용 데이터 (None이면 [0, 1000] 가정)
- `ood_margin`: OOD 범위 외부 계수 (기본: 1.5)
- `use_in_distribution`: True면 In-Distribution, False면 OOD (기본: True)

**반환값**:
- `secret_x`: 비밀 입력 (shape: [num_keys, num_features])
- `secret_y`: 비밀 라벨 (shape: [num_keys])

**동작**:

**In-Distribution 모드** (use_in_distribution=True):
- 데이터 범위 내의 corner cases 생성
- 3가지 방향: min 방향, max 방향, mean 방향
- 모델이 학습 가능하고 탐지 성능 높음

**OOD 모드** (use_in_distribution=False):
- 데이터 범위 밖에서 균등분포로 샘플링
- 데이터 조작 감지 어려움

---

### `TabularTaggantEngine.inject_taggants()`

**데이터에 Taggants 주입 (Gradient Matching)**

```python
def inject_taggants(
    csv_data: pd.DataFrame,
    secret_x: np.ndarray,
    secret_y: np.ndarray,
    poison_ratio: Optional[float] = None
) -> pd.DataFrame
```

**매개변수**:
- `csv_data`: 원본 CSV 데이터 (필수)
- `secret_x`: 비밀 입력 데이터 (필수)
- `secret_y`: 비밀 라벨 (필수)
- `poison_ratio`: 중독 비율 (None이면 config 값 사용)

**반환값**: 중독된 CSV 데이터 (pandas DataFrame)

**동작**:
1. 대리 신경망(SurrogateModel) 생성
2. 실제 데이터 + 비밀 키로 신경망 학습
3. 원본 데이터의 일부를 비밀 키로 치환
4. 치환된 개수: `int(len(data) * poison_ratio)`

---

### `TabularTaggantEngine.verify_ownership()`

**블랙박스 모델에 대한 소유권 검증**

```python
def verify_ownership(
    target_model_api_fn: Callable[[np.ndarray], int],
    secret_x: np.ndarray,
    secret_y: np.ndarray,
    alpha: Optional[float] = None,
    verbose: bool = True
) -> Dict[str, Any]
```

**매개변수**:
- `target_model_api_fn`: 모델 API 함수 (입력: array, 출력: 클래스 인덱스)
- `secret_x`: 비밀 입력 (필수)
- `secret_y`: 비밀 라벨 (필수)
- `alpha`: 통계적 유의수준 (기본: 0.01)
- `verbose`: 상세 출력 여부 (기본: True)

**반환값**: 검증 결과 딕셔너리

```python
{
    'is_stolen': bool,           # 소유권 침해 여부
    'p_value': float,            # 통계적 p-value
    'confidence': float,         # 신뢰도
    'matched': str,              # "성공/전체" 형식
    'match_ratio': float,        # 성공률
    'alpha': float,              # 유의수준
    'p_base': float,             # 기초 확률
    'predictions': List[int]     # 각 키별 예측값
}
```

**동작**:
1. 모든 비밀 키를 모델 API에 쿼리
2. 예측값과 비밀 라벨 비교 (정답/오답 계산)
3. 이항분포로 p-value 계산
4. p-value < alpha이면 소유권 침해로 판정

---

## 예제

### 예제 1: 기본 사용법

```python
import numpy as np
import pandas as pd
from dov import create_taggants_engine

# 더미 데이터 생성
n_samples = 100
n_features = 5
data = pd.DataFrame(np.random.randn(n_samples, n_features))

# 엔진 생성
engine = create_taggants_engine(
    num_features=5,
    num_classes=3,
    num_keys=30,
    use_in_distribution=True  # In-Distribution 모드
)

# 1. 비밀 키 생성
secret_x, secret_y = engine.generate_secret_keys(data)
print(f"Secret X shape: {secret_x.shape}, Secret Y shape: {secret_y.shape}")

# 2. Taggants 주입
poisoned_data = engine.inject_taggants(data, secret_x, secret_y)

# 3. 모의 모델 API
def mock_model(x):
    # 실제로는 외부 모델 호출
    return int(np.random.random() * 3)

# 4. 소유권 검증
result = engine.verify_ownership(mock_model, secret_x, secret_y)
print(f"Stolen: {result['is_stolen']}, p-value: {result['p_value']:.6f}")
```

### 예제 2: 메타데이터 저장/로드

```python
# 메타데이터 저장 (JSON 형식)
engine.save_metadata("dov_metadata.json")

# 나중에 로드
metadata = engine.load_metadata("dov_metadata.json")
print(f"Strategy: {metadata['secret_keys_info']['strategy']}")
print(f"Data range: {metadata['secret_keys_info']['data_range']}")
```

### 예제 3: In-Distribution vs OOD 비교

```python
import pandas as pd
from dov import create_taggants_engine

data = pd.read_csv("real_estate_data.csv")

# OOD 모드
engine_ood = create_taggants_engine(
    num_features=5,
    num_classes=3,
    num_keys=30,
    use_in_distribution=False  # OOD 모드
)
secret_x_ood, secret_y_ood = engine_ood.generate_secret_keys(data)

# In-Distribution 모드
engine_id = create_taggants_engine(
    num_features=5,
    num_classes=3,
    num_keys=30,
    use_in_distribution=True  # In-Distribution 모드
)
secret_x_id, secret_y_id = engine_id.generate_secret_keys(data)

# 메타데이터 확인
print("OOD Strategy:", engine_ood.metadata["secret_keys_info"]["strategy"])
print("ID Strategy:", engine_id.metadata["secret_keys_info"]["strategy"])
```

---

## 통계적 검증 원리

### 이항분포 기반 검증

**문제**: 블랙박스 모델이 우연히 정답을 맞출 수도 있습니다.

**해결**: 이항분포로 통계적 유의성 검증

#### 계산 과정

1. **기초 확률 계산**
   ```
   p_base = 1 / num_classes
   예: 3-클래스 분류면 p_base = 0.333
   ```

2. **성공 개수 계산**
   ```
   success_count = 모델이 정답을 맞춘 비밀 키 개수
   예: 30개 중 28개 정답
   ```

3. **p-value 계산 (우측 단측 검정)**
   ```
   p_value = P(X ≥ success_count | p=p_base, n=num_keys)
   = 1 - binom.cdf(success_count - 1, num_keys, p_base)
   ```

4. **유의성 판정**
   ```
   is_stolen = (p_value < alpha)
   alpha 기본값: 0.01 (1% 유의수준)
   ```

### 해석

| p_value | 해석 | 판정 |
|---------|------|------|
| < 0.01 | 1% 이하 우연 가능성 | **소유권 침해** ✓ |
| 0.01~0.05 | 1~5% 우연 가능성 | 경계 필요 |
| > 0.05 | 5% 이상 우연 가능성 | **소유권 없음** ✗ |

### 예시 계산

```
num_keys = 30
num_classes = 3
p_base = 1/3 ≈ 0.333

케이스 1: success_count = 28
  p-value ≈ 0.0001  →  p_value < 0.01  →  is_stolen = True

케이스 2: success_count = 15
  p-value ≈ 0.5  →  p_value > 0.01  →  is_stolen = False

케이스 3: success_count = 20
  p-value ≈ 0.02  →  p_value > 0.01  →  is_stolen = False
```

---

## 핵심 구성 요소

### SurrogateModel (대리 신경망)

대리 신경망은 Taggant 주입 과정에서 자동으로 생성되며, 직접 사용할 필요는 없습니다.

```python
# 내부적으로 사용되는 구조
# Input (num_features)
#   ↓
# Linear(num_features, 64)
#   ↓
# ReLU
#   ↓
# Dropout(0.2)
#   ↓
# Linear(64, num_classes)
#   ↓
# Output (logits)
```

### TaggantsConfig (설정)

엔진의 모든 설정을 관리합니다.

```python
@dataclass
class TaggantsConfig:
    num_features: int              # 필수: 입력 feature 수
    num_classes: int               # 필수: 클래스 수
    num_keys: int = 30             # 비밀 키 개수
    poison_ratio: float = 0.01     # 데이터 중독 비율 (1%)
    learning_rate: float = 0.01    # 신경망 학습률
    max_iterations: int = 100      # 신경망 학습 반복 횟수
    device: str = "cpu"            # "cpu" 또는 "cuda"
    random_seed: int = 42          # 재현성을 위한 난수 시드
    alpha: float = 0.01            # 통계적 유의수준 (1%)
```

---

## 성능 및 보안 고려사항

### ✅ 강점

- **높은 탐지율**: 소유권 침해 모델 정확하게 탐지
- **낮은 탐지율**: OOD 기반으로 데이터 조작 감지 어려움
- **블랙박스 호환**: API 호출만으로 검증 가능
- **통계적 근거**: p-value로 신뢰성 검증

### ⚠️ 제한사항

- **쿼리 의존성**: 모델 API에 대한 충분한 접근 필요
- **데이터 특성**: 고차원 데이터에선 효과 감소 가능
- **계산 비용**: 대규모 비밀 키 생성 시 시간 소요

### 🔒 보안 권장사항

1. **비밀 키 보호**: secret_x, secret_y를 안전하게 관리
2. **메타데이터 암호화**: 메타데이터 파일 암호화 저장
3. **쿼리 제한**: API 쿼리 수 제한으로 공격 방어
4. **정기 검증**: 정기적으로 소유권 검증 수행

---

## 문제 해결

### Q: "ModuleNotFoundError: No module named 'torch'"

**답변**:
```bash
pip install torch scipy numpy pandas
```

### Q: "Data has X columns but model expects Y features"

**답변**: num_features를 CSV 파일의 수치형 열 개수로 설정하세요:
```python
numeric_cols = data.select_dtypes(include=[np.number]).shape[1]
engine = create_taggants_engine(num_features=numeric_cols, num_classes=3)
```

### Q: 검증 결과가 항상 is_stolen=False?

**답변**: 
- 모델 API 함수가 올바르게 작동하는지 확인
- alpha 값을 조정해보기 (기본: 0.01, 더 큰 값 시도)
- 비밀 키 개수 증가 (num_keys를 30 이상으로 설정)
- 포이즌 비율 조정 (poison_ratio 증가)

### Q: In-Distribution vs OOD 어떤 것을 선택해야 하나?

**답변**:
- **In-Distribution** (권장): 모델 학습이 잘되고 탐지 성능이 높음
- **OOD**: 더 숨겨진 느낌이지만, 때로 탐지 성능이 낮을 수 있음

```python
# In-Distribution 권장
engine = create_taggants_engine(
    num_features=5,
    num_classes=3,
    use_in_distribution=True  # 기본값
)
```

---

**마지막 업데이트**: 2026-05-29
**버전**: 2.0.0
