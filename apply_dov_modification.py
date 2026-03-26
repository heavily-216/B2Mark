import pandas as pd
import argparse

def apply_1dp_round(input_path, output_path, target_col='price'):
    df = pd.read_csv(input_path)
    df[target_col] = df[target_col].round(1)
    df.to_csv(output_path, index=False)
    print(f"변형 완료: {output_path}")

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('input', help='입력 CSV 파일 경로')
    parser.add_argument('output', help='출력 CSV 파일 경로')
    parser.add_argument('--col', default='price', help='대상 컬럼명')
    args = parser.parse_args()
    
    apply_1dp_round(args.input, args.output, args.col)