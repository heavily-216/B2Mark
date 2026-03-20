# watermark
졸업프로젝트
## 📂 프로젝트 파일 구조 및 역할

프로젝트는 크게 4개의 핵심 파이썬 파일로 구성되어 있습니다.

* **`utils.py` (공통 도구)**
  * **역할:** 해시 계산(`hash_mod`), 구간 분할(`generate_green_domains`), Z-Score 계산 등 상태(State)를 가지지 않는 순수 통계/수학 함수들의 모음입니다.
  * **주의:** 워터마크 삽입과 검출 시 **정확히 동일한 기준**을 적용해야 하므로, 이 파일의 로직이 변경되면 시스템 전체의 무결성이 깨집니다!
* **`watermark.py` (핵심 엔진)**
  * **역할:** B²Mark 논문에서 제시된 알고리즘의 핵심 로직을 담당하는 파일로, 아래의 2개 클래스로 구성됩니다 ▼
  * **`B2MarkEmbedder`:** 원본 데이터에 구매자의 고유 ID(다중비트열)를 은밀하게 삽입합니다.
  * **`B2MarkDetector`:** 유출된 파일의 통계적 분포(Z-Test)를 분석하여 구매자 ID를 복원합니다.
* **`main.py` (CLI 실행기)**
  * **역할:** 터미널(명령 프롬프트) 환경에서 엔진을 구동하는 진입점입니다. 프론트엔드/서버에서 파이썬 스크립트를 직접 호출할 때 사용합니다.
* **`gui.py` (사용자 인터페이스)**
  * **역할:** GUI 환경에서 워터마킹 및 검출을 수행할 수 있도록 만듭니다.
* **(추가)`dummy.py` (테스트용 더미 데이터 생성기)**
  * **역할:** 워터마킹 테스트를 위해 간단한 엑셀 데이터셋 파일을 만드는 코드입니다.

## 🚀 사용 방법 (How to Run)

### 1. 필수 라이브러리 설치

깃허브에 업로드된 모든 파일을 다운로드 합니다.
cmd창에서 pip install -r requirements.txt 명령어를 실행하면 프로젝트 실행을 위한 필수 라이브러리 설치가 완료됩니다.

### 2. 테스트용 더미 데이터 준비

cmd창에서 python make_dummy.py 명령어를 실행하여 워터마킹 테스트를 수행할 csv 파일을 준비합니다.

### (추가) 워터마킹 강인성(손상 내성) 데이터셋 생성

워터마킹된 CSV를 여러 방식으로 “약간 손상”시킨 변형(노이즈/반올림/클리핑/스케일 변화 등)을 만들고, 각 변형에서 `detect` 결과가 원래 구매자 ID로 복원되는지 `report.json`, `report.csv`로 요약합니다.

```bash
# (WSL/Ubuntu 계열 예시) pip/venv가 없으면 먼저 설치
sudo apt update
sudo apt install -y python3-pip python3-venv

pip3 install -r requirements.txt

# 강인성 데이터셋 생성
python3 make_robustness_dataset.py \
  --out_dir robustness_dataset \
  --rows 3000 \
  --seed 42 \
  --buyer_id 10110 \
  --bit_len 5
```

생성 결과:

- `robustness_dataset/base.csv`: 더미 원본
- `robustness_dataset/watermarked.csv`: 워터마킹 적용본 (+ `watermarked.csv.meta.json`)
- `robustness_dataset/variants/*.csv`: 손상(변형) 버전들
- `robustness_dataset/report.json`, `robustness_dataset/report.csv`: 변형별 검출 성공/실패 요약

### 3. GUI 모드로 실행 (추천)

cmd창에서 python gui.py 명령어를 실행하면 애플리케이션 창이 열리며, 파일 선택 및 버튼 클릭으로 모든 작업을 수행할 수 있습니다.

### 4. CLI 모드로 실행(서버용)

서버와 연동을 위해 CLI 모드로 실행 가능합니다. cmd창에 아래의 명령어를 순서대로 입력합니다:

**워터마크 삽입:** python main.py embed --input {워터마킹을 적용할 파일명.csv} --output {워터마킹 적용 후 생성할 파일명.csv} --buyer_id {삽입할 다중비트 5자리}

즉 cmd창에 아래와 같이 명령어를 입력하시면 됩니다

*예: python main.py embed --input test_260223.csv --output sold_userA.csv --buyer_id 10110*

명령어 실행 결과 워터마킹이 적용된 데이터셋과, 추후 워터마킹 검출을 위해 사용되는 메타데이터(즉 NFT의 정보) json 파일이 생성됩니다.

**워터마크 검출:** python main.py detect --input {워터마킹을 검출할 파일명.csv} --meta {앞서 생성된 메타데이터 파일명.json} --bit_len 5
