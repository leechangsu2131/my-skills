import os
import pandas as pd
from datetime import datetime

def save_report(results: list, output_path: str = None) -> str:
    """처리 결과 리스트를 Excel 파일로 저장합니다."""
    if not results:
        return ""
        
    df = pd.DataFrame(results)
    
    # 보기 편하게 컬럼명 한글로 매핑
    cols_mapping = {
        'filepath': '파일 경로',
        'sihaeng_no': '시행번호',
        'title': '제목',
        'status': '상태',
        'fail_reason': '실패 사유',
        'processed_at': '처리 일시'
    }
    
    df = df.rename(columns={k: v for k, v in cols_mapping.items() if k in df.columns})
    
    if not output_path:
        os.makedirs('result', exist_ok=True)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_path = os.path.join('result', f'edufine_report_{timestamp}.xlsx')
        
    # Excel 저장
    df.to_excel(output_path, index=False)
    return output_path
