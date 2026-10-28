"""수업나누리 검색결과 디버그 스크립트"""
import os, time
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

def main():
    options = Options()
    options.add_argument("--window-size=1280,900")
    driver = webdriver.Chrome(options=options)
    
    try:
        # 1. 로그인 창 띄우기
        driver.get("http://nanuri.gyo6.net/login/login.tc")
        print("\n로그인하신 뒤 터미널에서 Enter를 쳐주세요.")
        input("> ")
        
        # 2. 감각적 표현 파라미터 넣어서 검색 결과 페이지 접근
        print("\n검색결과 페이지 진입...")
        driver.get("http://nanuri.gyo6.net/board/list.tc?mn=1042&mngNo=6&searchKeyword=감각적 표현&pageIndex=1")
        time.sleep(3)
        
        # 3. HTML 파싱해서 실제 검색 form이 요구하는 name 속성 확인
        soup = BeautifulSoup(driver.page_source, "html.parser")
        print("\n--- [form 리스트] ---")
        for f in soup.find_all("form"):
            print(f"Form ID: {f.get('id')}, Action: {f.get('action')}")
            for inp in f.find_all("input"):
                print(f"  Input name={inp.get('name')}, type={inp.get('type')}, value={inp.get('value')}")
            print("---------------------")
            
        # 화면에 보이는 게시글 개수와 제목 샘플
        count = driver.page_source.count("selectBoardDetail")
        print(f"\n현재 화면의 게시물 개수 (selectBoardDetail 기준): {count}")
        print("첫번째 게시글 텍스트 샘플:")
        try:
            sample = soup.find("a", onclick=lambda x: x and "selectBoardDetail" in x).get_text(strip=True)
            print(" ->", sample)
        except:
            pass
            
    finally:
        driver.quit()

if __name__ == "__main__":
    main()
