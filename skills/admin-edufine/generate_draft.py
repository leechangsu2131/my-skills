import os
import json
import google.generativeai as genai
from dotenv import load_dotenv

def generate_draft_from_items(items):
    """
    S2B 물품 목록을 기반으로 에듀파인 기안문 제목과 개요를 생성합니다.
    """
    load_dotenv(r'C:\Users\user\.gemini\antigravity\scratch\repos\my-skills\skills\admin-edufine\.env')
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise Exception("GEMINI_API_KEY가 .env 파일에 없습니다.")
        
    genai.configure(api_key=api_key)
    
    # 모델 선택 (빠르고 저렴한 flash 모델 권장)
    model = genai.GenerativeModel('gemini-1.5-flash')
    
    item_list_str = "\n".join([f"- {item['name']} (수량: {item['quantity']}, 단가: {item['unit_price']}원)" for item in items])
    
    prompt = f"""
다음은 학교장터(S2B)에서 구매할 물품 목록입니다:
{item_list_str}

위 물품들을 구매하기 위한 학교 품의 기안문의 적절한 '제목'과 '내용(개요)'을 작성해주세요.
기안문 내용 작성 가이드라인:
1. 제목은 간결하고 명확하게 작성합니다. (예: 2024학년도 체육수업 교구 구입 품의)
2. 내용은 "관련: 2024학년도 학교회계 예산편성 기본지침" 등 상투적인 문구를 포함하여 공문서 양식에 맞게 격식있게 작성합니다.
3. 구매 목적과 물품 총괄 내용을 간단히 요약합니다.

결과물은 반드시 다음 형태의 순수 JSON 문자열로만 응답해 주세요. 마크다운 기호(```json 등)를 붙이지 마세요:
{{
    "title": "기안문 제목",
    "summary": "기안문 내용(줄바꿈은 \\n 사용)"
}}
"""
    
    print("[LLM] 기안문 생성 요청 중...")
    response = model.generate_content(prompt)
    
    try:
        text = response.text.strip()
        if text.startswith('```json'):
            text = text[7:]
        if text.endswith('```'):
            text = text[:-3]
        text = text.strip()
        data = json.loads(text)
        return data
    except Exception as e:
        print(f"[LLM] JSON 파싱 오류: {e}")
        # 기본값 반환
        return {
            "title": "물품 구입 품의",
            "summary": "다음과 같이 물품을 구입하고자 합니다."
        }

if __name__ == "__main__":
    sample_items = [
        {"name": "다우리 뉴좌전굴 허리 유연성 측정기", "quantity": "2", "unit_price": "170500"},
        {"name": "아이워너 초시계 스톱워치", "quantity": "2", "unit_price": "32500"}
    ]
    res = generate_draft_from_items(sample_items)
    print("생성된 제목:", res.get("title"))
    print("생성된 내용:")
    print(res.get("summary"))
