# -*- coding: utf-8 -*-
"""
짝수 K값만 테스트 - 정확한 Green/Red 50:50 분할
K와 G 파라미터 신뢰도 점수 비교 (최종 버전)

주의: 홀수 k값은 Green Zone과 Red Zone이 불균형이 되므로 사용 금지
짝수 k값만 사용하여 정확한 50:50 분할을 보장함
"""

import json
import tempfile
from pathlib import Path
from watermark import insert, detect, WatermarkOptions

# 테스트 설정
SECRET_KEY = "grad_project_key"
TARGET_COL = "price"
REF_COLS = ("area", "floor")
BUYER_ID = "10110"
INPUT_FILE = "variants_watermark.csv"

def test_even_k_values():
    """짝수 k값만 테스트"""
    
    print("=" * 80)
    print("짝수 K값만 테스트 (정확한 Green/Red 50:50 분할)")
    print("=" * 80)
    print()
    
    results = []
    
    # 짝수 k값만 테스트
    k_values = [8, 10, 12, 14, 16, 18, 20, 22, 24]
    g_values = [3, 4, 5, 6, 7]
    
    for k in k_values:
        for g in g_values:
            try:
                print(f"[테스트] k={k}, g={g}")
                
                with tempfile.TemporaryDirectory() as tmpdir:
                    output_file = Path(tmpdir) / "watermarked.csv"
                    
                    options = WatermarkOptions(
                        secret_key=SECRET_KEY,
                        buyer_bitstring=BUYER_ID,
                        target_col=TARGET_COL,
                        ref_cols=REF_COLS,
                        k=k,
                        g=g,
                    )
                    
                    embed_result = insert(INPUT_FILE, output_file, options)
                    metadata = embed_result.metadata
                    
                    detection_result = detect(
                        output_file, 
                        options, 
                        embed_metadata=metadata
                    )
                    
                    score = detection_result.score
                    detected_id = detection_result.detected_bitstring
                    success = (detected_id == BUYER_ID)
                    
                    results.append({
                        'k': k,
                        'g': g,
                        'score': score,
                        'detected_id': detected_id,
                        'original_id': BUYER_ID,
                        'success': success
                    })
                    
                    status = "✅" if success else "❌"
                    print(f"  {status} 신뢰도: {score:.4f}, 검출: {detected_id}")
                    print()
                    
            except Exception as e:
                print(f"  ✗ 오류: {str(e)}")
                print()
                results.append({
                    'k': k,
                    'g': g,
                    'score': None,
                    'error': str(e)
                })
    
    # 결과 요약
    print("=" * 80)
    print("결과 요약")
    print("=" * 80)
    
    successful = [r for r in results if r['success']]
    failed = [r for r in results if 'error' not in r and not r['success']]
    
    print(f"\n✅ 검출 성공: {len(successful)}/{len(results)} ({len(successful)/len(results)*100:.1f}%)")
    print(f"❌ 검출 실패: {len(failed)}/{len(results)} ({len(failed)/len(results)*100:.1f}%)")
    
    if failed:
        print("\n검출 실패 목록:")
        for r in failed:
            print(f"  k={r['k']}, g={r['g']}: 원본={r['original_id']}, 검출={r['detected_id']}")
    
    # 신뢰도 기준 상위 10개
    valid_results = [r for r in results if r['success']]
    valid_results.sort(key=lambda x: x['score'], reverse=True)
    
    print("\n상위 10개 설정 (검출 성공만):")
    print(f"{'k':<4} {'g':<4} {'신뢰도':<12} {'상태'}")
    print("-" * 30)
    for r in valid_results[:10]:
        print(f"{r['k']:<4} {r['g']:<4} {r['score']:<12.4f} ✅")
    
    # 최적 설정
    if valid_results:
        best = valid_results[0]
        print(f"\n🏆 최적 설정: k={best['k']}, g={best['g']}")
        print(f"   신뢰도: {best['score']:.4f}")
    
    return results

if __name__ == "__main__":
    results = test_even_k_values()
    
    # 결과 저장
    output_file = "test_results_even_k.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    print(f"\n결과 저장: {output_file}")
