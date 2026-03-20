import argparse
import contextlib
import io
import json
import os
from dataclasses import dataclass
from typing import Callable, Dict, List, Tuple

import numpy as np
import pandas as pd

from watermark import B2MarkDetector, B2MarkEmbedder


SECRET_KEY = "grad_project_key"
TARGET_COL = "price"
REF_COLS = ["area", "floor"]


@dataclass(frozen=True)
class VariantResult:
    name: str
    path: str
    detected_id: str
    ok: bool


def _ensure_dir(path: str) -> None:
    os.makedirs(path, exist_ok=True)


def _write_json(path: str, obj) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)


def _make_base_dummy(rows: int, seed: int) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    return pd.DataFrame(
        {
            "price": rng.uniform(100000, 2000000, rows),
            "area": rng.uniform(50, 200, rows),
            "floor": rng.integers(1, 31, rows),
        }
    )


def _attack_round(df: pd.DataFrame, decimals: int) -> pd.DataFrame:
    out = df.copy()
    out[TARGET_COL] = out[TARGET_COL].round(decimals)
    return out


def _attack_gaussian_noise(
    df: pd.DataFrame,
    std: float,
    ratio: float,
    seed: int,
) -> pd.DataFrame:
    out = df.copy()
    rng = np.random.default_rng(seed)
    n = len(out)
    mask = rng.random(n) < ratio
    noise = rng.normal(0.0, std, n)
    out.loc[mask, TARGET_COL] = out.loc[mask, TARGET_COL] + noise[mask]
    return out


def _attack_uniform_jitter(
    df: pd.DataFrame,
    width: float,
    ratio: float,
    seed: int,
) -> pd.DataFrame:
    out = df.copy()
    rng = np.random.default_rng(seed)
    n = len(out)
    mask = rng.random(n) < ratio
    jitter = rng.uniform(-width, width, n)
    out.loc[mask, TARGET_COL] = out.loc[mask, TARGET_COL] + jitter[mask]
    return out


def _attack_clip_outliers(
    df: pd.DataFrame,
    low_q: float,
    high_q: float,
) -> pd.DataFrame:
    out = df.copy()
    lo = float(out[TARGET_COL].quantile(low_q))
    hi = float(out[TARGET_COL].quantile(high_q))
    out[TARGET_COL] = out[TARGET_COL].clip(lo, hi)
    return out


def _attack_scale_and_shift(
    df: pd.DataFrame,
    scale: float,
    shift: float,
) -> pd.DataFrame:
    out = df.copy()
    out[TARGET_COL] = out[TARGET_COL] * scale + shift
    return out


def _attack_decimal_string_format(
    df: pd.DataFrame,
    fmt: str,
) -> pd.DataFrame:
    out = df.copy()
    # CSV로 다시 쓸 때 숫자->문자->숫자 파싱이 일어나도록 의도적으로 문자열로 변환
    out[TARGET_COL] = out[TARGET_COL].map(lambda x: fmt.format(float(x)))
    return out


def _postprocess_numeric(df: pd.DataFrame) -> pd.DataFrame:
    """
    detector는 수치 비교를 하므로, 공격 과정에서 price가 문자열이 될 수 있어
    저장 전에 확실히 float로 정규화한다.
    """
    out = df.copy()
    out[TARGET_COL] = pd.to_numeric(out[TARGET_COL], errors="coerce")
    # NaN이 생기면 검출 자체가 깨지므로, 해당 경우는 원본값으로 복구
    if out[TARGET_COL].isna().any():
        out[TARGET_COL] = out[TARGET_COL].fillna(df[TARGET_COL].astype(float))
    return out


def build_variants(
    watermarked_df: pd.DataFrame,
    meta_data: Dict,
    seed: int,
) -> List[Tuple[str, pd.DataFrame]]:
    d_min = float(meta_data["min"])
    d_max = float(meta_data["max"])
    seg = (d_max - d_min) / 10.0  # k=10 기본 가정(프로젝트 기본값)

    variants: List[Tuple[str, pd.DataFrame]] = []
    variants.append(("wm_clean", watermarked_df))
    variants.append(("round_int", _attack_round(watermarked_df, decimals=0)))
    variants.append(("round_2dp", _attack_round(watermarked_df, decimals=2)))

    # 작은 노이즈(구간 폭 대비 작게): 대부분 green-zone 판정이 유지되도록 설계
    variants.append(
        (
            "gaussian_noise_10pct_small",
            _attack_gaussian_noise(watermarked_df, std=seg * 0.03, ratio=0.10, seed=seed + 1),
        )
    )
    variants.append(
        (
            "gaussian_noise_30pct_small",
            _attack_gaussian_noise(watermarked_df, std=seg * 0.03, ratio=0.30, seed=seed + 2),
        )
    )
    variants.append(
        (
            "uniform_jitter_20pct",
            _attack_uniform_jitter(watermarked_df, width=seg * 0.04, ratio=0.20, seed=seed + 3),
        )
    )

    # 가격 이상치 클리핑(상/하위 극단값 손상 가정)
    variants.append(("clip_1_99", _attack_clip_outliers(watermarked_df, low_q=0.01, high_q=0.99)))

    # 단위 변환/정규화 같은 스케일 변화(다만 너무 크면 green zone 경계가 흔들릴 수 있어 약하게)
    variants.append(("scale_shift_small", _attack_scale_and_shift(watermarked_df, scale=1.01, shift=-seg * 0.02)))

    # 문자열 포맷 손상(저장/전달 과정에서 소수점 자리수 강제 등)
    variants.append(("string_format_1dp", _attack_decimal_string_format(watermarked_df, fmt="{:.1f}")))

    return [(name, _postprocess_numeric(df)) for name, df in variants]


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate robustness dataset for B2Mark.")
    parser.add_argument("--out_dir", default="robustness_dataset", help="Output directory")
    parser.add_argument("--rows", type=int, default=3000, help="Number of rows in dummy dataset")
    parser.add_argument("--seed", type=int, default=42, help="Random seed")
    parser.add_argument("--buyer_id", default="10110", help="Buyer ID bitstring")
    parser.add_argument("--bit_len", type=int, default=5, help="Buyer ID length")
    parser.add_argument(
        "--save_detection_logs",
        action="store_true",
        help="Save per-variant detector stdout (Z-score report) to files",
    )
    args = parser.parse_args()

    out_dir = os.path.abspath(args.out_dir)
    _ensure_dir(out_dir)
    variants_dir = os.path.join(out_dir, "variants")
    _ensure_dir(variants_dir)
    logs_dir = os.path.join(out_dir, "detection_logs")
    if args.save_detection_logs:
        _ensure_dir(logs_dir)

    base_path = os.path.join(out_dir, "base.csv")
    wm_path = os.path.join(out_dir, "watermarked.csv")
    meta_path = wm_path + ".meta.json"

    # 1) base dummy
    base_df = _make_base_dummy(rows=args.rows, seed=args.seed)
    base_df.to_csv(base_path, index=False)

    # 2) embed watermark (uses project engine)
    embedder = B2MarkEmbedder(secret_key=SECRET_KEY)
    meta_data = embedder.embed(
        source_path=base_path,
        output_path=wm_path,
        buyer_bitstring=args.buyer_id,
        target_col=TARGET_COL,
        ref_cols=REF_COLS,
    )
    _write_json(meta_path, meta_data)

    # 3) load watermarked as df (to ensure consistent types)
    wm_df = pd.read_csv(wm_path)

    # 4) build & write variants
    variants = build_variants(wm_df, meta_data=meta_data, seed=args.seed)
    variant_paths: Dict[str, str] = {}
    for name, df in variants:
        path = os.path.join(variants_dir, f"{name}.csv")
        df.to_csv(path, index=False)
        variant_paths[name] = path

    # 5) detect watermark for each variant
    detector = B2MarkDetector(secret_key=SECRET_KEY)
    results: List[VariantResult] = []
    for name, path in variant_paths.items():
        stdout_buf = io.StringIO()
        with contextlib.redirect_stdout(stdout_buf):
            detected = detector.detect(
                suspect_path=path,
                meta_data=meta_data,
                bit_length=args.bit_len,
                target_col=TARGET_COL,
                ref_cols=REF_COLS,
            )
        detection_log = stdout_buf.getvalue()
        if args.save_detection_logs:
            log_path = os.path.join(logs_dir, f"{name}.txt")
            with open(log_path, "w", encoding="utf-8") as f:
                f.write(detection_log)
        ok = detected == args.buyer_id
        results.append(VariantResult(name=name, path=path, detected_id=detected, ok=ok))

    # 6) report
    report = {
        "buyer_id_expected": args.buyer_id,
        "bit_len": args.bit_len,
        "base_csv": base_path,
        "watermarked_csv": wm_path,
        "meta_json": meta_path,
        "variants": [
            {"name": r.name, "path": r.path, "detected_id": r.detected_id, "ok": r.ok}
            for r in results
        ],
        "summary": {
            "total": len(results),
            "ok": sum(1 for r in results if r.ok),
            "fail": sum(1 for r in results if not r.ok),
        },
    }
    _write_json(os.path.join(out_dir, "report.json"), report)

    pd.DataFrame([r.__dict__ for r in results]).to_csv(os.path.join(out_dir, "report.csv"), index=False)

    print(f"[+] Done. Dataset written to: {out_dir}")
    print(f"[+] Report: {os.path.join(out_dir, 'report.json')}")


if __name__ == "__main__":
    main()

