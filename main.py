import argparse
import json
import os
from watermark import B2MarkEmbedder, B2MarkDetector

# --- 설정값 (추후 config 파일로 분리해 데이터별로 다른 값을 받을 예정) ---
SECRET_KEY = "grad_project_key"
TARGET_COL = "price"         # 워터마킹할 컬럼 (가격 등)
REF_COLS = ["area", "floor"] # 참조할 컬럼 (면적, 층수 등)

def run_embed(args):
    """삽입 모드 실행"""
    print(f"[*] 워터마크를 삽입합니다... 구매자 정보: {args.buyer_id}")
    
    embedder = B2MarkEmbedder(secret_key=SECRET_KEY)
    
    # 워터마킹 수행
    meta_data = embedder.embed(
        source_path=args.input,
        output_path=args.output,
        buyer_bitstring=args.buyer_id,
        target_col=TARGET_COL,
        ref_cols=REF_COLS
    )
    
    # 메타데이터 저장 (중요: 이게 있어야 검출 가능)
    meta_path = args.output + ".meta.json"
    with open(meta_path, "w") as f:
        json.dump(meta_data, f)
        
    print(f"[+] 워터마크가 성공적으로 삽입되었습니다 (파일명: {args.output})")
    print(f"[+] 워터마크 메타데이터가 저장되었습니다 (파일명: {meta_path})")

def run_detect(args):
    """검출 모드 실행"""
    print(f"[*] 워터마크를 검출합니다... 대상 파일: {args.input}")
    
    # 메타데이터 로드
    if not os.path.exists(args.meta):
        print(f"[-] 해당 파일의 워터마크 메타데이터 파일을 찾을 수 없습니다 ({args.meta})")
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
        ref_cols=REF_COLS
    )
    
    print(f"\n[!!!] 구매자 ID: [{detected_id}]")

if __name__ == "__main__":
    # 명령어 파서 설정 (CLI)
    parser = argparse.ArgumentParser(description="B2Mark Watermarking Tool")
    subparsers = parser.add_subparsers(dest="mode", help="Select mode (embed/detect)")

    # 1. Embed 명령어 설정
    # 사용법: python main.py embed --input original.csv --output sold.csv --buyer_id 10110
    embed_parser = subparsers.add_parser("embed", help="Embed watermark")
    embed_parser.add_argument("--input", required=True, help="Original CSV file path")
    embed_parser.add_argument("--output", required=True, help="Output CSV file path")
    embed_parser.add_argument("--buyer_id", required=True, help="Buyer ID (Bitstring, e.g., 10110)")

    # 2. Detect 명령어 설정
    # 사용법: python main.py detect --input leaked.csv --meta sold.csv.meta.json --bit_len 5
    detect_parser = subparsers.add_parser("detect", help="Detect watermark")
    detect_parser.add_argument("--input", required=True, help="Suspect CSV file path")
    detect_parser.add_argument("--meta", required=True, help="Meta-data JSON file path")
    detect_parser.add_argument("--bit_len", type=int, required=True, help="Length of Buyer ID")

    args = parser.parse_args()

    if args.mode == "embed":
        run_embed(args)
    elif args.mode == "detect":
        run_detect(args)
    else:
        parser.print_help()