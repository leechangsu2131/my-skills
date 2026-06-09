"""Flask 서버를 거치지 않고 직접 s2b_cart_scraper를 호출하여 테스트"""
import asyncio
import sys
import io

# stdout encoding fix
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

import importlib
import s2b_cart_scraper
importlib.reload(s2b_cart_scraper)

async def main():
    print("=== S2B 장바구니 불러오기 테스트 ===")
    try:
        items = await s2b_cart_scraper.get_s2b_cart_items()
        if items:
            print(f"\n[성공] 총 {len(items)}개 품목:")
            for i, item in enumerate(items):
                print(f"  {i+1}. {item['name']} (수량: {item['quantity']}, 단가: {item['unit_price']})")
            
            # TSV 포맷 출력 (실제 웹 UI에 표시될 형태)
            print("\n=== TSV 포맷 (웹 UI 출력) ===")
            tsv = "".join([f"{item['name']}\t\t{item['quantity']}\t\t{item['unit_price']}\n" for item in items])
            print(tsv)
        else:
            print("\n[실패] 빈 리스트 반환됨")
    except Exception as e:
        print(f"\n[오류] {e}")
        import traceback
        traceback.print_exc()

asyncio.run(main())
