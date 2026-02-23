'''
테스트를 위해 간단한 엑셀 데이터 파일을 만드는 코드입니다
cmd창에서 본 파일의 위치로 이동 후 python dummy.py를 실행하면 csv 파일이 생성됩니다
깃허브에 업로드된 test.csv 파일은 본 코드의 실행 결과입니다
매 실행시마다 다른 데이터 파일이 생성됩니다
'''
import pandas as pd
import numpy as np
import datetime

#=======================================================================================
# 데이터 파일 생성 함수
#=======================================================================================

def create_dummy_csv(filename = "default.csv", rows=1000):
    print("==============================================")
    print("생성할 파일 이름:", end=' ')
    filename = input() + ".csv"
    print("파일 데이터 개수(추천 개수 1000~5000):", end=' ')
    rows = int(input())
    print(f"\n~데이터셋 생성중~ \n파일명: {filename} (데이터 도합 {rows} 행)...\n")
    
    # 현재 시간을 랜덤 시드로 사용
    np.random.seed(42)
    
    data = {
        # 1. Target Column (워터마킹 당할 가격 정보)
        # 1억 ~ 20억 사이의 실수
        'price': np.random.uniform(100000, 2000000, rows),
        
        # 2. Reference Columns (해시 재료로 쓸 변하지 않는 정보)
        # 면적: 50~200 제곱미터
        'area': np.random.uniform(50, 200, rows),
        # 층수: 1~30층
        'floor': np.random.randint(1, 31, rows)
    }
    
    df = pd.DataFrame(data)
    
    # CSV 파일 저장
    df.to_csv(filename, index=False)
    print(f"{filename} 파일이 성공적으로 생성되었습니다")
    print("==============================================\n\n")

#=======================================================================================
# 메인 함수
#=======================================================================================

try:
    create_dummy_csv()
except:
    print("실행중 오류가 발생했습니다.")
