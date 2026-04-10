import argparse
import json
import os
from watermark import B2MarkEmbedder, B2MarkDetector, load_config_by_datatype

# --- 설정값 ---
SECRET_KEY = "grad_project_key"


def run_embed(args):
    """삽입 모드 실행"""
    # config에서 설정 로드
    config = load_config_by_datatype(args.data_type)
    TARGET_COL = config["target_col"]
    REF_COLS = config["ref_cols"]
    K = config["k"]
    G = config["g"]
    EMBED_SEED = config["embed_seed"]

    print(
        f"[*] 워터마크를 삽입합니다... 구매자 정보: {args.buyer_id}, 데이터타입: {args.data_type}"
    )
    print(f"    (k={K}, g={G}, embed_seed={EMBED_SEED})")

    embedder = B2MarkEmbedder(secret_key=SECRET_KEY)

    # 워터마킹 수행 - 별도의 WatermarkOptions 전달 방식으로 수정 필요
    meta_data = embedder.embed(
        source_path=args.input,
        output_path=args.output,
        buyer_bitstring=args.buyer_id,
        target_col=TARGET_COL,
        ref_cols=REF_COLS,
        k=K,
        g=G,
        embed_seed=EMBED_SEED,
        verbose=args.verbose if hasattr(args, "verbose") else False,
    )

    # 메타데이터 저장 (중요: 이게 있어야 검출 가능)
    meta_path = args.output + ".meta.json"
    with open(meta_path, "w") as f:
        json.dump(meta_data, f)

    print(f"[+] 워터마크가 성공적으로 삽입되었습니다 (파일명: {args.output})")
    print(f"[+] 워터마크 메타데이터가 저장되었습니다 (파일명: {meta_path})")


def run_detect(args):
    """검출 모드 실행"""
    # config에서 설정 로드
    config = load_config_by_datatype(args.data_type)
    TARGET_COL = config["target_col"]
    REF_COLS = config["ref_cols"]

    print(
        f"[*] 워터마크를 검출합니다... 대상 파일: {args.input}, 데이터타입: {args.data_type}"
    )

    # 메타데이터 로드
    if not os.path.exists(args.meta):
        print(
            f"[-] 해당 파일의 워터마크 메타데이터 파일을 찾을 수 없습니다 ({args.meta})"
        )
        return

    with open(args.meta, "r") as f:
        meta_data = json.load(f)

    detector = B2MarkDetector(secret_key=SECRET_KEY)

    # 검출 수행
    detected_id = detector.detect(
        suspect_path=args.input,
        meta_data=meta_data,
        bit_length=args.bit_len,
        target_col=TARGET_COL,
        ref_cols=REF_COLS,
        verbose=args.verbose if hasattr(args, "verbose") else False,
    )

    print(f"\n[!!!] 구매자 ID: [{detected_id}]")


def run_dov(args):
    """Data Ownership Verification 모드 실행"""
    # config에서 설정 로드
    config = load_config_by_datatype(args.data_type)
    TARGET_COL = config["target_col"]
    REF_COLS = config["ref_cols"]

    print(
        f"[*] DOV(소유권 검증)를 수행합니다... 대상 파일: {args.input}, 데이터타입: {args.data_type}"
    )

    if not os.path.exists(args.meta):
        print(f"[-] 메타데이터 파일을 찾을 수 없습니다 ({args.meta})")
        return

    with open(args.meta, "r") as f:
        meta_data = json.load(f)

    detector = B2MarkDetector(secret_key=SECRET_KEY)
    result = detector.verify_ownership(
        suspect_path=args.input,
        meta_data=meta_data,
        claimed_buyer_id=args.claimed_id,
        bit_length=args.bit_len,
        target_col=TARGET_COL,
        ref_cols=REF_COLS,
        z_threshold=args.z_threshold,
        min_match_ratio=args.min_match_ratio,
    )

    print("\n--- [DOV Report] ---")
    print(f"Claimed ID : {result['claimed_buyer_id']}")
    print(f"Detected ID: {result['detected_id']}")
    print(f"Matched    : {result['matched_bits']}/{result['known_bits']}")
    print(f"Match Ratio: {result['match_ratio']:.2%}")
    print(
        f"Decision   : {'OWNERSHIP VERIFIED' if result['ownership_verified'] else 'NOT VERIFIED'} "
        f"(threshold={result['min_match_ratio']:.0%})"
    )


if __name__ == "__main__":
    # 명령어 파서 설정 (CLI)
    parser = argparse.ArgumentParser(description="B2Mark Watermarking Tool")
    subparsers = parser.add_subparsers(dest="mode", help="Select mode (embed/detect)")

    # 1. Embed 명령어 설정
    # 사용법: python main.py embed --input original.csv --output sold.csv --buyer_id 10110 --data_type real_estate --verbose
    embed_parser = subparsers.add_parser("embed", help="Embed watermark")
    embed_parser.add_argument("--input", required=True, help="Original CSV file path")
    embed_parser.add_argument("--output", required=True, help="Output CSV file path")
    embed_parser.add_argument(
        "--buyer_id", required=True, help="Buyer ID (Bitstring, e.g., 10110)"
    )
    embed_parser.add_argument(
        "--data_type",
        default="real_estate",
        choices=["real_estate", "insurance", "credit_card"],
        help="Data type: real_estate, insurance, credit_card",
    )
    embed_parser.add_argument(
        "--verbose",
        action="store_true",
        help="Print detailed embedding information",
    )

    # 2. Detect 명령어 설정
    # 사용법: python main.py detect --input leaked.csv --meta sold.csv.meta.json --bit_len 5 --data_type real_estate
    detect_parser = subparsers.add_parser("detect", help="Detect watermark")
    detect_parser.add_argument("--input", required=True, help="Suspect CSV file path")
    detect_parser.add_argument("--meta", required=True, help="Meta-data JSON file path")
    detect_parser.add_argument(
        "--bit_len", type=int, required=True, help="Length of Buyer ID"
    )
    detect_parser.add_argument(
        "--data_type",
        default="real_estate",
        choices=["real_estate", "insurance", "credit_card"],
        help="Data type: real_estate, insurance, credit_card",
    )
    detect_parser.add_argument(
        "--verbose",
        action="store_true",
        help="Print detailed bit-by-bit detection results",
    )

    # 3. DOV 명령어 설정
    # 사용법: python main.py dov --input leaked.csv --meta sold.csv.meta.json --claimed_id 10110 --bit_len 5 --data_type real_estate
    dov_parser = subparsers.add_parser("dov", help="Verify data ownership")
    dov_parser.add_argument("--input", required=True, help="Suspect CSV file path")
    dov_parser.add_argument("--meta", required=True, help="Meta-data JSON file path")
    dov_parser.add_argument(
        "--claimed_id", required=True, help="Claimed Buyer ID bitstring"
    )
    dov_parser.add_argument(
        "--bit_len", type=int, required=True, help="Length of Buyer ID"
    )
    dov_parser.add_argument(
        "--data_type",
        default="real_estate",
        choices=["real_estate", "insurance", "credit_card"],
        help="Data type: real_estate, insurance, credit_card",
    )
    dov_parser.add_argument(
        "--z_threshold",
        type=float,
        default=1.645,
        help="Z-score threshold for decoding bit=1 (default: 1.645)",
    )
    dov_parser.add_argument(
        "--min_match_ratio",
        type=float,
        default=0.8,
        help="Minimum match ratio for ownership verification (default: 0.8)",
    )

    args = parser.parse_args()

    if args.mode == "embed":
        run_embed(args)
    elif args.mode == "detect":
        run_detect(args)
    elif args.mode == "dov":
        run_dov(args)
    else:
        parser.print_help()
