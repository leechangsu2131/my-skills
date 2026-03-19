import sys
import os
import json
import requests
try:
    import fitz  # PyMuPDF
except ImportError:
    print("PyMuPDF (fitz) is not installed. Please install it using: pip install pymupdf")
    sys.exit(1)

# OpenRouter API Configuration
OPENROUTER_API_KEY = "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"
MODEL_NAME = "openrouter/hunter-alpha"

def extract_text_from_pdf(pdf_path):
    print(f"[{pdf_path}] 에서 텍스트 추출 중...")
    text = ""
    try:
        doc = fitz.open(pdf_path)
        for page_num in range(len(doc)):
            page = doc.load_page(page_num)
            text += page.get_text()
        return text
    except Exception as e:
        print(f"PDF 읽기 에러: {e}")
        return None

def summarize_text(text, lesson_topic):
    print(f"\n[{lesson_topic}] 에 대한 내용을 모델({MODEL_NAME})로 요약 중...")
    
    prompt = f"""
다음은 초등학교 음악 과목 지도서의 일부 텍스트입니다. 
이 중 '{lesson_topic}'와 관련된 내용을 찾아 교사가 수업 준비에 바로 활용할 수 있도록 핵심만 3~5줄로 요약해 주세요. 
만약 해당 내용이 없다면 '관련 내용을 찾을 수 없습니다.'라고 답변해 주세요.

텍스트:
{text[:5000]}
"""
    
    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://github.com/google-deepmind/antigravity",
        "X-Title": "Music Class Helper"
    }
    
    data = {
        "model": MODEL_NAME,
        "messages": [
            {"role": "user", "content": prompt}
        ],
        "reasoning": {"enabled": True}
    }
    
    try:
        import urllib3
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        
        # Add a timeout of 60 seconds to prevent hanging indefinitely
        response = requests.post(url, headers=headers, data=json.dumps(data), verify=False, timeout=60)
        response.raise_for_status() # Raise detailed exception for bad responses
        result = response.json()
        
        if 'choices' not in result:
            print(f"응답에 'choices'가 없습니다. 원본 응답:\n{json.dumps(result, indent=2, ensure_ascii=False)}")
            return "요약을 생성하는 데 문제가 발생했습니다 (예상치 못한 응답 포맷)."
            
        reply_content = result['choices'][0]['message']['content']
        
        # You can see reasoning tokens if present
        # if 'usage' in result and 'reasoningTokens' in result['usage']:
        #     print(f"(Reasoning Tokens: {result['usage']['reasoningTokens']})")
            
        return reply_content
        
    except requests.exceptions.HTTPError as e:
        print(f"API 호출 에러 (HTTP {e.response.status_code}): {e.response.text}")
        return f"요약을 생성하는 데 문제가 발생했습니다 (HTTP {e.response.status_code})."
    except Exception as e:
        print(f"예상치 못한 에러: {e}")
        return "알 수 없는 에러로 요약에 실패했습니다."

def main():
    if len(sys.argv) < 3:
        print("Usage: python summarize_pdf.py <pdf_path> <lesson_topic>")
        sys.exit(1)
        
    pdf_path = sys.argv[1]
    lesson_topic = sys.argv[2]
    
    if not os.path.exists(pdf_path):
        print(f"\n[!] 파일을 찾을 수 없습니다: {pdf_path}")
        sys.exit(1)
        
    text = extract_text_from_pdf(pdf_path)
    if text:
        summary = summarize_text(text, lesson_topic)
        print("\n" + "="*60)
        print(f" [ {lesson_topic} ] 지도서 핵심 요약")
        print("="*60)
        
        # Windows cp949 terminal print fixes
        try:
            print(summary)
        except UnicodeEncodeError:
            print(summary.encode('cp949', errors='replace').decode('cp949'))
            
        print("="*60)
        print("\n")

if __name__ == "__main__":
    main()
