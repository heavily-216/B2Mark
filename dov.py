# =================================================================================
# 파일명:   dov.py
# 목적:     Taggants 기반 데이터 소유권 검증 (DOV) 시스템
# 설명:     표형 데이터에 OOD(Out-of-Distribution) 기반 비밀 키를 주입하고
#          블랙박스 모델 API를 통해 통계적으로 데이터 소유권을 검증
# =================================================================================

from __future__ import annotations

import json
import logging
from typing import Optional, Tuple, Dict, Callable, Any

import numpy as np
import pandas as pd
import torch
import torch.nn as nn
import torch.optim as optim
from scipy.stats import binom
from dataclasses import dataclass, asdict

# =================================================================================
# 로깅 설정
# =================================================================================

logging.basicConfig(
    level=logging.INFO,
    format="[%(levelname)s] %(asctime)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


# =================================================================================
# 대리 신경망 (Surrogate Model)
# =================================================================================


class SurrogateModel(nn.Module):
    """
    Gradient Matching을 위한 대리 신경망
    실제 모델을 모방하지 않고, 데이터 역공학에만 사용

    Architecture:
        Input -> Linear(hidden_dim) -> ReLU -> Dropout -> Linear(num_classes) -> Output
    """

    def __init__(self, num_features: int, num_classes: int, hidden_dim: int = 64):
        """
        Args:
            num_features: 입력 feature 수
            num_classes: 출력 클래스 수
            hidden_dim: 은닉층 차원 (기본값: 64)
        """
        super().__init__()
        self.num_features = num_features
        self.num_classes = num_classes

        # MLP 구조: 단순하지만 효과적
        self.fc1 = nn.Linear(num_features, hidden_dim)
        self.relu = nn.ReLU()
        self.dropout = nn.Dropout(p=0.2)
        self.fc2 = nn.Linear(hidden_dim, num_classes)

        # Xavier 초기화
        nn.init.xavier_uniform_(self.fc1.weight)
        nn.init.xavier_uniform_(self.fc2.weight)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """Forward pass

        Args:
            x: 입력 텐서 (shape: [batch_size, num_features])

        Returns:
            출력 로짓 (shape: [batch_size, num_classes])
        """
        x = self.fc1(x)
        x = self.relu(x)
        x = self.dropout(x)
        x = self.fc2(x)
        return x


# =================================================================================
# Taggants 엔진 (메인 클래스)
# =================================================================================


@dataclass
class TaggantsConfig:
    """Taggants 설정 정보

    Attributes:
        num_features: 입력 feature 수
        num_classes: 출력 클래스 수
        num_keys: 생성할 비밀 키 개수 (기본: 30)
        poison_ratio: 데이터 중독 비율 (기본: 0.01, 즉 1%)
        learning_rate: 대리 모델 학습률 (기본: 0.01)
        max_iterations: 대리 모델 학습 반복 횟수 (기본: 100)
        device: PyTorch 디바이스 "cpu" 또는 "cuda" (기본: "cpu")
        random_seed: 난수 시드 (기본: 42)
        alpha: 통계적 유의수준 (기본: 0.01, 즉 1%)
    """

    num_features: int
    num_classes: int
    num_keys: int = 30
    poison_ratio: float = 0.01
    learning_rate: float = 0.01
    max_iterations: int = 100
    device: str = "cpu"
    random_seed: int = 42
    alpha: float = 0.01

    def __post_init__(self):
        """설정 검증"""
        if self.num_features <= 0:
            raise ValueError("num_features must be positive")
        if self.num_classes <= 1:
            raise ValueError("num_classes must be > 1")
        if not (0 < self.poison_ratio <= 1):
            raise ValueError("poison_ratio must be in (0, 1]")
        if self.learning_rate <= 0:
            raise ValueError("learning_rate must be positive")
        if self.num_keys <= 0:
            raise ValueError("num_keys must be positive")
        if not (0 < self.alpha < 1):
            raise ValueError("alpha must be in (0, 1)")


class TabularTaggantEngine:
    """
    Taggants 기반 표형 데이터 소유권 검증 엔진

    주요 기능:
    1. OOD 비밀 키 생성 (Secret Keys)
    2. 대리 신경망을 이용한 Taggant 주입 (Gradient Matching)
    3. 블랙박스 모델에 대한 소유권 검증 (Statistical Verification)
    """

    def __init__(self, config: TaggantsConfig):
        """
        Taggants 엔진 초기화

        Args:
            config: TaggantsConfig 객체

        Raises:
            ValueError: 설정이 유효하지 않은 경우
        """
        if not isinstance(config, TaggantsConfig):
            raise TypeError("config must be TaggantsConfig instance")

        self.config = config
        self.device = torch.device(config.device)

        # 난수 시드 고정 (재현성 보장)
        np.random.seed(config.random_seed)
        torch.manual_seed(config.random_seed)
        if torch.cuda.is_available() and "cuda" in config.device:
            torch.cuda.manual_seed(config.random_seed)

        # 메타데이터 저장용
        self.metadata: Dict[str, Any] = {
            "config": asdict(config),
            "normalization_params": {},
            "secret_keys_info": {},
            "injection_info": {},
        }

        logger.info(
            f"TabularTaggantEngine initialized: "
            f"features={config.num_features}, classes={config.num_classes}, "
            f"keys={config.num_keys}, device={config.device}"
        )

    def generate_secret_keys(
        self,
        csv_data: Optional[pd.DataFrame] = None,
        ood_margin: float = 1.5,
        use_in_distribution: bool = True,
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        1단계: 비밀 키 생성

        Args:
            csv_data: 데이터셋 (범위 추정용, None이면 기본값 사용)
            ood_margin: OOD 방식에서 범위 외부 계수
            use_in_distribution: True면 In-Distribution, False면 OOD 방식

        Returns:
            secret_x: (num_keys, num_features) 비밀 입력 데이터
            secret_y: (num_keys,) 비밀 라벨 데이터
        """
        num_keys = self.config.num_keys
        num_features = self.config.num_features
        num_classes = self.config.num_classes

        # 데이터 범위 추정
        if csv_data is not None:
            numeric_data = csv_data.select_dtypes(include=[np.number])
            if len(numeric_data.columns) < num_features:
                raise ValueError(
                    f"CSV has {len(numeric_data.columns)} numeric columns "
                    f"but {num_features} features required"
                )

            numeric_data = numeric_data.iloc[:, :num_features]
            min_vals = numeric_data.min().values
            max_vals = numeric_data.max().values
            ranges = max_vals - min_vals
            mean_vals = numeric_data.mean().values
        else:
            # 기본값: [0, 1000] 범위 가정
            min_vals = np.zeros(num_features)
            max_vals = np.ones(num_features) * 1000
            ranges = max_vals - min_vals
            mean_vals = (min_vals + max_vals) / 2

        if use_in_distribution:
            logger.info(f"Generating {num_keys} secret keys (In-Distribution)...")
            secret_x_list = []

            for i in range(num_keys):
                direction = i % 3
                if direction == 0:
                    shift = ranges * 0.1
                    sample = np.maximum(min_vals - shift, min_vals - ranges * 0.5)
                elif direction == 1:
                    shift = ranges * 0.1
                    sample = np.minimum(max_vals + shift, max_vals + ranges * 0.5)
                else:
                    offset = (np.random.rand(num_features) - 0.5) * ranges * 0.3
                    sample = mean_vals + offset

                secret_x_list.append(sample)

            secret_x = np.array(secret_x_list)

            self.metadata["secret_keys_info"] = {
                "num_keys": num_keys,
                "strategy": "in_distribution",
                "data_range": {
                    "min": min_vals.tolist(),
                    "max": max_vals.tolist(),
                    "mean": mean_vals.tolist(),
                },
            }
        else:
            logger.info(f"Generating {num_keys} secret keys (OOD-based)...")
            ood_min = max_vals + ranges * 0.1
            ood_max = ood_min + ranges * ood_margin
            secret_x = np.random.uniform(
                ood_min, ood_max, size=(num_keys, num_features)
            )

            self.metadata["secret_keys_info"] = {
                "num_keys": num_keys,
                "strategy": "ood",
                "ood_range": {"min": ood_min.tolist(), "max": ood_max.tolist()},
            }

        secret_y = np.random.choice(num_classes, size=num_keys)

        logger.info(
            f"Secret keys generated (shape: {secret_x.shape}, "
            f"strategy={'in_distribution' if use_in_distribution else 'ood'})"
        )
        return secret_x, secret_y

    def inject_taggants(
        self,
        csv_data: pd.DataFrame,
        secret_x: np.ndarray,
        secret_y: np.ndarray,
        poison_ratio: Optional[float] = None,
    ) -> pd.DataFrame:
        """
        2단계: Gradient Matching을 통한 Taggant 주입

        Args:
            csv_data: 원본 CSV 데이터
            secret_x: 비밀 입력 데이터
            secret_y: 비밀 라벨
            poison_ratio: 중독 비율 (기본값: config.poison_ratio)

        Returns:
            수정된 CSV 데이터 (일부 행이 taggant로 교체됨)
        """
        if poison_ratio is None:
            poison_ratio = self.config.poison_ratio

        logger.info(f"Injecting taggants (poison_ratio={poison_ratio:.2%})...")

        poisoned_data = csv_data.copy()
        numeric_cols = poisoned_data.select_dtypes(include=[np.number]).columns.tolist()

        if len(numeric_cols) < self.config.num_features:
            raise ValueError(
                f"Not enough numeric columns: {len(numeric_cols)} < {self.config.num_features}"
            )

        target_cols = numeric_cols[: self.config.num_features]

        # 대리 신경망 초기화
        model = SurrogateModel(
            num_features=self.config.num_features, num_classes=self.config.num_classes
        ).to(self.device)

        # 대리 모델 학습
        self._train_surrogate_model(
            model, poisoned_data[target_cols].values, secret_x, secret_y
        )

        # 데이터 조정
        num_inject = max(1, int(len(poisoned_data) * poison_ratio))
        inject_indices = np.random.choice(
            len(poisoned_data), size=num_inject, replace=False
        )

        # Secret 데이터를 실제 데이터로 치환
        for idx, secret_idx in enumerate(inject_indices[: len(secret_x)]):
            poisoned_data.iloc[
                secret_idx, [poisoned_data.columns.get_loc(col) for col in target_cols]
            ] = secret_x[idx]

        logger.info(f"Taggants injected ({num_inject} samples modified)")
        return poisoned_data

    def _train_surrogate_model(
        self,
        model: SurrogateModel,
        train_data: np.ndarray,
        secret_x: np.ndarray,
        secret_y: np.ndarray,
    ) -> None:
        """대리 신경망을 실제 데이터 + 비밀 키로 학습"""
        optimizer = optim.Adam(model.parameters(), lr=self.config.learning_rate)
        criterion = nn.CrossEntropyLoss()

        train_x = torch.FloatTensor(train_data).to(self.device)
        train_y = torch.LongTensor(
            np.random.randint(0, self.config.num_classes, size=len(train_data))
        ).to(self.device)

        secret_x_tensor = torch.FloatTensor(secret_x).to(self.device)
        secret_y_tensor = torch.LongTensor(secret_y).to(self.device)

        model.train()

        for iteration in range(self.config.max_iterations):
            train_output = model(train_x)
            secret_output = model(secret_x_tensor)

            loss_train = criterion(train_output, train_y)
            loss_secret = criterion(secret_output, secret_y_tensor)
            total_loss = loss_train + loss_secret * 0.5

            optimizer.zero_grad()
            total_loss.backward()
            optimizer.step()

        logger.info(f"Surrogate model trained (final loss: {total_loss.item():.4f})")

    def verify_ownership(
        self,
        target_model_api_fn: Callable[[np.ndarray], int],
        secret_x: np.ndarray,
        secret_y: np.ndarray,
        alpha: Optional[float] = None,
        verbose: bool = True,
    ) -> Dict[str, Any]:
        """
        3단계: 블랙박스 모델 API를 이용한 통계적 소유권 검증

        Args:
            target_model_api_fn: 의심 모델의 예측 함수 (입력: numpy array, 출력: 클래스 인덱스)
            secret_x: 비밀 입력 데이터
            secret_y: 비밀 라벨
            alpha: 유의수준 (기본값: config.alpha)
            verbose: 상세 출력 여부

        Returns:
            검증 결과 딕셔너리
        """
        if alpha is None:
            alpha = self.config.alpha

        logger.info(f"Verifying data ownership (alpha={alpha})...")

        success_count = 0
        num_keys = len(secret_x)
        predictions = []

        # 블랙박스 모델 쿼리
        for i, (x, y_target) in enumerate(zip(secret_x, secret_y)):
            try:
                x_input = x.reshape(1, -1) if x.ndim == 1 else x
                pred_y = target_model_api_fn(x_input)

                if isinstance(pred_y, np.ndarray):
                    pred_y = pred_y.item() if pred_y.size == 1 else pred_y[0]
                pred_y = int(pred_y)

                predictions.append(pred_y)

                if pred_y == y_target:
                    success_count += 1

            except Exception as e:
                logger.warning(f"Error querying model for key {i}: {e}")
                predictions.append(-1)

        # 통계 검증
        p_base = 1.0 / self.config.num_classes
        p_value = 1 - binom.cdf(success_count - 1, num_keys, p_base)

        is_stolen = p_value < alpha
        confidence = 1 - p_value if is_stolen else p_value

        result = {
            "is_stolen": is_stolen,
            "p_value": float(p_value),
            "confidence": float(confidence),
            "matched": f"{success_count}/{num_keys}",
            "match_ratio": float(success_count / num_keys),
            "alpha": alpha,
            "p_base": float(p_base),
            "predictions": predictions,
        }

        if verbose:
            logger.info(
                f"Verification Result: Data {'STOLEN' if is_stolen else 'NOT STOLEN'} "
                f"(p-value={p_value:.6f}, confidence={confidence:.2%})"
            )

        return result

    def save_metadata(self, output_path: str) -> None:
        """메타데이터를 JSON 파일로 저장"""
        with open(output_path, "w") as f:
            json.dump(self.metadata, f, indent=2)
        logger.info(f"Metadata saved to {output_path}")

    def load_metadata(self, input_path: str) -> Dict[str, Any]:
        """메타데이터를 JSON 파일에서 로드"""
        with open(input_path, "r") as f:
            self.metadata = json.load(f)
        logger.info(f"Metadata loaded from {input_path}")
        return self.metadata


# =================================================================================
# 편의 함수
# =================================================================================


def create_taggants_engine(
    num_features: int,
    num_classes: int,
    num_keys: int = 30,
    poison_ratio: float = 0.01,
    device: str = "cpu",
    use_in_distribution: bool = True,
) -> TabularTaggantEngine:
    """
    Taggants 엔진 생성 헬퍼 함수

    Args:
        num_features: 입력 feature 수
        num_classes: 클래스 수
        num_keys: 비밀 키 수
        poison_ratio: 중독 비율
        device: PyTorch 장치
        use_in_distribution: True면 In-Distribution, False면 OOD

    Returns:
        TabularTaggantEngine 인스턴스
    """
    config = TaggantsConfig(
        num_features=num_features,
        num_classes=num_classes,
        num_keys=num_keys,
        poison_ratio=poison_ratio,
        device=device,
    )
    engine = TabularTaggantEngine(config)
    engine.use_in_distribution = use_in_distribution
    return engine
