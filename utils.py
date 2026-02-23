# utils.py
import hashlib
import numpy as np
import math

def hash_mod(secret_key, key_value, mod_value):
    """
    [해시 함수]
    데이터의 값(key_value)과 비밀키(secret_key)를 결합하여
    0부터 mod_value-1 사이의 랜덤한 정수 인덱스를 반환합니다.
    """
    combined = f"{secret_key}{key_value}"
    hash_value = int(hashlib.sha256(combined.encode()).hexdigest(), 16)
    return hash_value % mod_value

def get_feature_value(val, n=2):
    """
    [특징 추출 함수]
    숫자형 데이터의 앞 n자리를 문자열로 추출합니다.
    """
    if val == 0:
        return "0" * n
    # 소수점 제거 및 앞 n자리 추출
    digits = str(val).replace('.', '').lstrip('0')
    if len(digits) < n:
        return digits + "0" * (n - len(digits))
    return digits[:n]

def generate_green_domains(min_val, max_val, k, seed):
    """
    [Green Zone 생성 함수]
    데이터의 최소~최대 범위를 k개 구간으로 나누고,
    그중 절반을 '안전 구역(Green Zone)'으로 선정하여 반환합니다.
    """
    np.random.seed(seed)
    
    # 1. 구간 생성
    intervals = np.linspace(min_val, max_val, k + 1)
    segments = [(intervals[i], intervals[i + 1]) for i in range(k)]
    
    # 2. 섞어서 절반 선택
    np.random.shuffle(segments)
    half_k = k // 2
    green_domains = segments[:half_k]
    
    return green_domains

def calculate_z_score(green_cnt, total_cnt):
    """
    [통계 검정 함수]
    Green Zone에 포함된 비율을 바탕으로 Z-Score를 계산합니다.
    """
    if total_cnt == 0:
        return 0.0
    return (green_cnt - total_cnt/2) / math.sqrt(total_cnt/4)