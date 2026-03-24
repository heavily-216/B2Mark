'''
파일 번호: 1
파일명: watermak.py

'''
import pandas as pd
import numpy as np
import utils  # 위에서 만든 utils.py를 임포트(코랩 환경에서는 오류가 발생하므로 주석처리 함)

class B2MarkEmbedder:
    def __init__(self, secret_key="grad_project_key", k=10, g=3):
        self.secret_key = secret_key  # 보안 키 (워터마크 위치 결정)
        self.k = k                    # 전체 구간을 몇 개로 나눌지 (보통 10~20)
        self.g = g                    # 데이터 선별 비율 (g 값이 클수록 더 적은 데이터에 워터마킹 적용)

    def _get_composite_key(self, row, ref_cols):
        """참조 컬럼들의 값을 합쳐서 하나의 문자열 키 생성."""
        # 예: area=85, floor=10 -> "8510"
        features = [utils.get_feature_value(row[col]) for col in ref_cols]
        return "".join(features)

    def embed(self, source_path, output_path, buyer_bitstring, target_col, ref_cols):
        # 1. 워터마킹 할 데이터 로드
        df = pd.read_csv(source_path)
        
        # 2. 메타데이터 생성을 위한 범위 계산 (검출 시 필요)
        d_min = float(df[target_col].min())
        d_max = float(df[target_col].max())
        seed = 10000  # 고정 시드 사용 (일단 시드를 고정해 놓았음!)

        # 3. Green Zone 생성
        green_domains = utils.generate_green_domains(d_min, d_max, self.k, seed)
        
        # 4. 데이터 한 줄씩 처리
        num_bits = len(buyer_bitstring)
        
        for idx in df.index:
            # (1) 참조 키 생성 (변조되지 않는 컬럼들 사용)
            comp_key = self._get_composite_key(df.loc[idx], ref_cols)
            
            # (2) 이 행(Row)이 담당할 비트 위치 결정 (0 ~ num_bits-1)
            bit_idx = utils.hash_mod(self.secret_key, str(idx), num_bits)
            
            # (3) 선별: 해시 결과가 0인 경우에만 워터마킹 시도 (데이터 손상 최소화)
            if utils.hash_mod(self.secret_key, comp_key, self.g) != 0:
                continue

            # (4) 구매자 ID의 해당 비트가 '1'이면 값 변조 수행
            target_bit = buyer_bitstring[bit_idx]
            
            if target_bit == '1':
                original_val = df.loc[idx, target_col]
                
                # 현재 값이 Green Zone에 있는지 확인
                in_green = any(low <= original_val < high for low, high in green_domains)
                
                if not in_green:
                    # Red Zone이라면 가장 가까운 Green Zone으로 값 이동
                    # (간단하게 구현하기 위해 랜덤 함수 사용)
                    target_zone = green_domains[np.random.randint(len(green_domains))]
                    new_val = np.random.uniform(target_zone[0], target_zone[1])
                    df.loc[idx, target_col] = new_val

        # 5. 결과 저장 및 메타데이터 반환
        df.to_csv(output_path, index=False)
        return {"min": d_min, "max": d_max, "seed": seed}


class B2MarkDetector:
    """
    [워터마크 검출기]
    유출된 파일에서 통계적 분포를 분석해 구매자 ID를 복원
    """
    def __init__(self, secret_key="grad_project_key", k=10, g=3):
        self.secret_key = secret_key
        self.k = k
        self.g = g

    def _get_composite_key(self, row, ref_cols):
        features = [utils.get_feature_value(row[col]) for col in ref_cols]
        return "".join(features)

    def _collect_bit_stats(self, df, bit_length, target_col, ref_cols, green_domains):
        """비트별 Green/Total 카운트와 Z-score를 수집한다."""
        bit_stats = {i: {"green": 0, "total": 0} for i in range(bit_length)}

        for idx in df.index:
            comp_key = self._get_composite_key(df.loc[idx], ref_cols)
            bit_idx = utils.hash_mod(self.secret_key, str(idx), bit_length)

            if utils.hash_mod(self.secret_key, comp_key, self.g) != 0:
                continue

            val = df.loc[idx, target_col]
            bit_stats[bit_idx]["total"] += 1

            if any(low <= val < high for low, high in green_domains):
                bit_stats[bit_idx]["green"] += 1

        z_scores = {}
        for i in range(bit_length):
            g_cnt = bit_stats[i]["green"]
            t_cnt = bit_stats[i]["total"]
            z_scores[i] = None if t_cnt == 0 else utils.calculate_z_score(g_cnt, t_cnt)

        return bit_stats, z_scores

    def detect(self, suspect_path, meta_data, bit_length, target_col, ref_cols):
        # 1. 데이터 로드
        df = pd.read_csv(suspect_path)
        
        # 2. 메타데이터로 Green Zone 복원 (범인 잡을 정답지)
        d_min = meta_data['min']
        d_max = meta_data['max']
        seed = meta_data['seed']
        green_domains = utils.generate_green_domains(d_min, d_max, self.k, seed)

        # 3. 비트별 통계 수집
        bit_stats, z_scores = self._collect_bit_stats(
            df=df,
            bit_length=bit_length,
            target_col=target_col,
            ref_cols=ref_cols,
            green_domains=green_domains,
        )

        # 5. Z-Score 계산 및 비트 복원
        detected_id = ""
        print("\n--- [Detection Report] ---")
        
        for i in range(bit_length):
            g_cnt = bit_stats[i]['green']
            t_cnt = bit_stats[i]['total']
            
            if t_cnt == 0:
                detected_id += "?" # 데이터 부족
                continue
                
            z_score = z_scores[i]
            print(f"Bit {i}: Green={g_cnt}/{t_cnt}, Z-Score={z_score:.2f}")

            # 판정 (임계값 1.645는 95% 신뢰구간)
            if z_score > 1.645: 
                detected_id += "1"
            else:
                detected_id += "0"

        return detected_id

    def verify_ownership(
        self,
        suspect_path,
        meta_data,
        claimed_buyer_id,
        bit_length,
        target_col,
        ref_cols,
        z_threshold=1.645,
        min_match_ratio=0.8,
    ):
        """
        Data Ownership Verification(DOV):
        유출 파일이 특정 구매자(claimed_buyer_id)에게 판매된 파일인지 검증한다.
        """
        if len(claimed_buyer_id) != bit_length:
            raise ValueError("claimed_buyer_id 길이와 bit_length가 일치해야 합니다.")
        if any(ch not in ("0", "1") for ch in claimed_buyer_id):
            raise ValueError("claimed_buyer_id는 0/1 비트열이어야 합니다.")

        df = pd.read_csv(suspect_path)

        d_min = meta_data["min"]
        d_max = meta_data["max"]
        seed = meta_data["seed"]
        green_domains = utils.generate_green_domains(d_min, d_max, self.k, seed)

        bit_stats, z_scores = self._collect_bit_stats(
            df=df,
            bit_length=bit_length,
            target_col=target_col,
            ref_cols=ref_cols,
            green_domains=green_domains,
        )

        detected_id = ""
        known_bits = 0
        matched_bits = 0

        for i in range(bit_length):
            z = z_scores[i]
            if z is None:
                detected_id += "?"
                continue
            known_bits += 1
            bit = "1" if z > z_threshold else "0"
            detected_id += bit
            if bit == claimed_buyer_id[i]:
                matched_bits += 1

        match_ratio = 0.0 if known_bits == 0 else matched_bits / known_bits
        ownership_verified = known_bits > 0 and match_ratio >= min_match_ratio

        return {
            "claimed_buyer_id": claimed_buyer_id,
            "detected_id": detected_id,
            "bit_length": bit_length,
            "known_bits": known_bits,
            "matched_bits": matched_bits,
            "match_ratio": match_ratio,
            "z_threshold": z_threshold,
            "min_match_ratio": min_match_ratio,
            "ownership_verified": ownership_verified,
            "bit_stats": bit_stats,
            "z_scores": z_scores,
        }