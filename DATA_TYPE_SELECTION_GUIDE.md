# 데이터 타입별 구분 기능 구현 가이드

**작성일**: 2026-04-10  
**작업 대상**: real_estate, insurance, credit_card 데이터 타입 선택 기능

---

## 📋 개요

B2Mark 시스템은 **세 가지 데이터 타입**을 지원하며, 각 데이터 타입별로 최적화된 설정값을 제공합니다.
사용자는 GUI 또는 CLI를 통해 데이터 타입을 선택하여 작업할 수 있습니다.

---

## 🎯 지원 데이터 타입

### 1️⃣ Real Estate (부동산)
- **식별자**: `real_estate`
- **대상 열**: `본건 단위면적당 실거래가` (가격)
- **참고 열**: `대지면적`, `지상 층수`
- **기본 설정**:
  - k = 32 (구간 분할 개수)
  - g = 2 (워터마킹 비율의 역수 = 50%)
  - embed_seed = 1

### 2️⃣ Insurance (보험)
- **식별자**: `insurance`
- **대상 열**: `premium` (보험료)
- **참고 열**: `age`, `policy_type`
- **기본 설정**:
  - k = 24
  - g = 3 (워터마킹 비율 = 33.3%)
  - embed_seed = 20000

### 3️⃣ Credit Card (신용카드)
- **식별자**: `credit_card`
- **대상 열**: `transaction_amount` (거래금액)
- **참고 열**: `card_id`, `merchant_category`
- **기본 설정**:
  - k = 20
  - g = 4 (워터마킹 비율 = 25%)
  - embed_seed = 30000

---

## 📁 설정 파일: config.json

모든 데이터 타입의 설정은 `config.json`에 저장됩니다.

```json
{
  "real_estate": {
    "description": "부동산 데이터",
    "target_col": "본건 단위면적당 실거래가",
    "ref_cols": ["대지면적", "지상 층수"],
    "k": 32,
    "g": 2,
    "embed_seed": 1,
    "selection_strategy": "hash_mod",
    "selection_params": {"g_value": 2}
  },
  "insurance": {
    "description": "보험 데이터",
    "target_col": "premium",
    "ref_cols": ["age", "policy_type"],
    "k": 24,
    "g": 3,
    "embed_seed": 20000,
    "selection_strategy": "hash_mod",
    "selection_params": {"g_value": 3}
  },
  "credit_card": {
    "description": "카드 데이터",
    "target_col": "transaction_amount",
    "ref_cols": ["card_id", "merchant_category"],
    "k": 20,
    "g": 4,
    "embed_seed": 30000,
    "selection_strategy": "hash_mod",
    "selection_params": {"g_value": 4}
  }
}
```

---

## 🛠 구현 위치

### 1. watermark.py (코어 함수)

**config 로드 함수** (watermark.py:367)

```python
def load_config_by_datatype(data_type: str = "real_estate") -> dict:
    """config.json에서 데이터 타입별 설정을 로드"""
    try:
        config_path = Path(__file__).parent / "config.json"
        with open(config_path, "r", encoding="utf-8") as f:
            config = json.load(f)
        if data_type not in config:
            raise ValueError(f"설정에서 '{data_type}' 데이터 타입을 찾을 수 없습니다.")
        return config[data_type]
    except FileNotFoundError:
        raise FileNotFoundError("config.json 파일을 찾을 수 없습니다.")
```

**사용 방법**:
```python
# 데이터 타입별 설정 로드
config = load_config_by_datatype("real_estate")
target_col = config["target_col"]      # "본건 단위면적당 실거래가"
ref_cols = config["ref_cols"]          # ["대지면적", "지상 층수"]
k = config["k"]                        # 32
g = config["g"]                        # 2
```

---

## 🖥 GUI 구현 (gui.py)

### 1. Embed Tab (워터마크 삽입)

**데이터 타입 선택** (gui.py:92-99)

```python
# 데이터 타입
ttk.Label(frame, text="데이터 타입:").pack(anchor="w", pady=(5, 0))
self.embed_datatype_var = tk.StringVar(value="real_estate")
datatype_combo = ttk.Combobox(
    frame,
    textvariable=self.embed_datatype_var,
    values=["real_estate", "insurance", "credit_card"],
    state="readonly",
    width=47,
)
```

**워터마킹 실행** (gui.py:119-147)

```python
def embed_watermark(self):
    ...
    data_type = self.embed_datatype_var.get()  # 선택된 데이터 타입
    
    # 데이터 타입에 맞는 설정 로드
    config = load_config_by_datatype(data_type)
    
    # 설정값 추출
    target_col = config["target_col"]
    ref_cols = tuple(config["ref_cols"])
    k = config["k"]
    g = config["g"]
    
    # 워터마킹 실행
    embedder = B2MarkEmbedder(secret_key=SECRET_KEY)
    meta_data = embedder.embed(
        input_path,
        output_path,
        buyer_id,
        target_col,
        ref_cols,
        k=k,
        g=g,
    )
```

### 2. Detect Tab (워터마크 검출)

**데이터 타입 선택** (gui.py:228-235)

```python
self.detect_datatype_var = tk.StringVar(value="real_estate")
datatype_combo = ttk.Combobox(
    frame,
    textvariable=self.detect_datatype_var,
    values=["real_estate", "insurance", "credit_card"],
    state="readonly",
    width=47,
)
```

**워터마크 검출** (gui.py:254-303)

```python
def detect_watermark(self):
    ...
    data_type = self.detect_datatype_var.get()  # 선택된 데이터 타입
    
    # 데이터 타입에 맞는 설정 로드
    config = load_config_by_datatype(data_type)
    target_col = config["target_col"]
    ref_cols = tuple(config["ref_cols"])
    
    # 워터마크 검출
    detector = B2MarkDetector(secret_key=SECRET_KEY)
    detected_id = detector.detect(
        input_path,
        meta_data,
        int(bit_len),
        target_col,
        ref_cols,
    )
```

### 3. DOV Tab (소유권 검증)

**데이터 타입 선택** (gui.py:369-376)

```python
self.dov_datatype_var = tk.StringVar(value="real_estate")
datatype_combo = ttk.Combobox(
    frame,
    textvariable=self.dov_datatype_var,
    values=["real_estate", "insurance", "credit_card"],
    state="readonly",
    width=47,
)
```

**소유권 검증** (gui.py:397-445)

```python
def verify_ownership(self):
    ...
    data_type = self.dov_datatype_var.get()  # 선택된 데이터 타입
    
    # 데이터 타입에 맞는 설정 로드
    config = load_config_by_datatype(data_type)
    target_col = config["target_col"]
    ref_cols = tuple(config["ref_cols"])
    
    # 소유권 검증 실행
    detector = B2MarkDetector(secret_key=SECRET_KEY)
    result = detector.verify_ownership(
        suspect_path=input_path,
        meta_data=meta_data,
        claimed_buyer_id=claimed_id,
        bit_length=int(bit_len),
        target_col=target_col,
        ref_cols=ref_cols,
        z_threshold=float(z_threshold),
        min_match_ratio=float(min_ratio),
    )
```

---

## 💻 CLI 구현 (main.py)

### 1. Embed 명령어

**사용법**:
```bash
python main.py embed \
  --input original.csv \
  --output sold.csv \
  --buyer_id 10110 \
  --data_type real_estate \
  --verbose
```

**구현** (main.py:4, 140-145):

```python
from watermark import load_config_by_datatype

# 명령어 정의
parser_embed.add_argument(
    "--data_type",
    default="real_estate",
    choices=["real_estate", "insurance", "credit_card"],
    help="Data type: real_estate, insurance, credit_card",
)

# 실행 시
config = load_config_by_datatype(args.data_type)
target_col = config["target_col"]
ref_cols = tuple(config["ref_cols"])
k = config["k"]
g = config["g"]
```

### 2. Detect 명령어

**사용법**:
```bash
python main.py detect \
  --input leaked.csv \
  --meta sold.csv.meta.json \
  --bit_len 5 \
  --data_type real_estate
```

### 3. DOV 명령어

**사용법**:
```bash
python main.py dov \
  --input leaked.csv \
  --meta sold.csv.meta.json \
  --claimed_id 10110 \
  --bit_len 5 \
  --data_type real_estate
```

---

## 🔄 워크플로우

### 사용자 관점

```
┌─────────────────────────────────┐
│  1. 데이터 타입 선택              │
│  (real_estate / insurance /      │
│   credit_card)                   │
└────────────┬────────────────────┘
             │
┌────────────▼────────────────────┐
│  2. config.json 로드             │
│  - 타입별 최적 설정값 추출        │
└────────────┬────────────────────┘
             │
┌────────────▼────────────────────┐
│  3. 워터마크 작업 실행            │
│  - embed / detect / dov          │
│  - 적절한 열(column) 사용         │
│  - 최적화된 k, g 값 적용          │
└────────────┬────────────────────┘
             │
┌────────────▼────────────────────┐
│  4. 결과 반환                    │
│  - 메타데이터 저장               │
│  - 검출 결과 표시                │
└─────────────────────────────────┘
```

---

## 📊 설정값 비교

| 파라미터 | Real Estate | Insurance | Credit Card |
|---------|------------|-----------|------------|
| **target_col** | 본건 단위면적당 실거래가 | premium | transaction_amount |
| **ref_cols** | 대지면적, 지상층수 | age, policy_type | card_id, merchant_category |
| **k** | 32 | 24 | 20 |
| **g** | 2 (50%) | 3 (33.3%) | 4 (25%) |
| **embed_seed** | 1 | 20000 | 30000 |
| **특징** | 높은 워터마킹율 | 중간 워터마킹율 | 낮은 워터마킹율 |

### 설정값 의미

- **k**: 구간 분할 개수 (Green/Red 존 개수)
- **g**: 워터마킹 적용 비율의 역수 (1/g가 워터마킹 비율)
- **embed_seed**: 난수 생성 시드값

---

## 💡 각 데이터 타입별 특징

### Real Estate (부동산) - 높은 강도
- **특징**: g=2 (50% 워터마킹) - 가장 높은 워터마킹율
- **용도**: 고가 부동산 거래에서 강력한 보호 필요
- **강점**: 매우 견고한 워터마크, 높은 신뢰도
- **주의**: 데이터 변조가 클 수 있음

### Insurance (보험) - 중간 강도
- **특징**: g=3 (33.3% 워터마킹)
- **용도**: 일반적인 보험 데이터 보호
- **강점**: 강건성과 데이터 품질의 균형
- **주의**: 대부분의 상황에 적절

### Credit Card (신용카드) - 낮은 강도
- **특징**: g=4 (25% 워터마킹) - 가장 낮은 워터마킹율
- **용도**: 실시간 거래 데이터, 데이터 품질 중요
- **강점**: 최소한의 데이터 변조
- **주의**: 약간 낮은 신뢰도 (충분함)

---

## 🔧 설정 커스터마이징

만약 특정 데이터 타입의 설정을 변경하려면 `config.json`을 수정하세요:

```json
{
  "real_estate": {
    "description": "부동산 데이터",
    "target_col": "본건 단위면적당 실거래가",
    "ref_cols": ["대지면적", "지상 층수"],
    "k": 28,        # ← 32에서 28로 변경
    "g": 3,         # ← 2에서 3으로 변경 (워터마킹율 감소)
    "embed_seed": 1,
    "selection_strategy": "hash_mod",
    "selection_params": {"g_value": 3}
  },
  ...
}
```

변경 후 재실행하면 새로운 설정이 자동으로 적용됩니다.

---

## 🎯 사용 시나리오

### 시나리오 1: 부동산 매매 데이터 보호

```bash
# GUI 사용
1. GUI 실행
2. Embed 탭 선택
3. 데이터 타입: "real_estate" 선택
4. 원본 파일: 부동산_매매.csv
5. 구매자 ID: 12345
6. 워터마크 삽입 실행
→ 설정: k=32, g=2 (50% 워터마킹)
→ 매우 강력한 보호
```

### 시나리오 2: 보험료 데이터 워터마킹

```bash
# CLI 사용
python main.py embed \
  --input insurance_data.csv \
  --output insurance_watermarked.csv \
  --buyer_id 67890 \
  --data_type insurance
→ 설정: k=24, g=3 (33.3% 워터마킹)
→ 균형잡힌 보호
```

### 시나리오 3: 신용카드 거래 데이터 검증

```bash
# CLI 사용 (검출)
python main.py detect \
  --input suspected_card_data.csv \
  --meta original.meta.json \
  --bit_len 8 \
  --data_type credit_card
→ 설정: k=20, g=4 (25% 워터마킹)
→ 최소 데이터 변조
```

---

## ✅ 체크리스트

- [x] config.json에 3가지 데이터 타입 설정 정의
- [x] load_config_by_datatype() 함수 구현
- [x] GUI의 3가지 탭(Embed, Detect, DOV)에 데이터 타입 선택 추가
- [x] CLI의 embed, detect, dov 명령어에 --data_type 옵션 추가
- [x] 각 데이터 타입별 최적화된 파라미터 설정
- [x] 오류 처리 (타입 미지정, config 파일 미존재 등)

---

## 📞 예시 코드

### Python에서 프로그래밍적 사용

```python
from watermark import load_config_by_datatype, B2MarkEmbedder

# 1. 설정 로드
config = load_config_by_datatype("insurance")
print(f"Target Column: {config['target_col']}")
print(f"Reference Columns: {config['ref_cols']}")
print(f"Parameters: k={config['k']}, g={config['g']}")

# 2. 워터마크 삽입
embedder = B2MarkEmbedder(secret_key="my_secret")
metadata = embedder.embed(
    source_path="input.csv",
    output_path="output.csv",
    buyer_bitstring="11010",
    target_col=config["target_col"],
    ref_cols=tuple(config["ref_cols"]),
    k=config["k"],
    g=config["g"],
    embed_seed=config["embed_seed"]
)
print(f"워터마킹 완료: {metadata}")
```

---

## 📌 요약

| 항목 | 설명 |
|------|------|
| **지원 타입** | real_estate, insurance, credit_card |
| **설정 파일** | config.json |
| **로드 함수** | load_config_by_datatype(data_type) |
| **GUI 적용** | Embed, Detect, DOV 탭에 드롭다운 선택기 추가 |
| **CLI 적용** | --data_type 옵션으로 선택 |
| **특징** | 타입별 최적화된 파라미터 자동 적용 |

---

**참고자료**:
- `config.json` - 설정 파일
- `watermark.py` - 코어 구현
- `gui.py` - GUI 구현
- `main.py` - CLI 구현
