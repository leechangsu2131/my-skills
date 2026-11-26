import urllib.request
import urllib.parse
import hashlib
import re
import os
import sys
import pathlib
from html.parser import HTMLParser

sys.path.insert(0, str(next(p / "_shared" for p in pathlib.Path(__file__).resolve().parents if (p / "_shared" / "skill_env.py").is_file())))
from skill_env import data_dir

class NaverParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.in_main = False
        self.img_count = 0
        self.record = []
        self.current_text = ''
        self.main_div_depth = 0
        self.current_depth = 0
        self.img_urls = []

    def handle_starttag(self, tag, attrs):
        self.current_depth += 1
        attr_dict = dict(attrs)
        
        if tag == 'div' and 'se-main-container' in attr_dict.get('class', ''):
            self.in_main = True
            self.main_div_depth = self.current_depth

        if self.in_main:
            if tag == 'img' and 'se-image-resource' in attr_dict.get('class', ''):
                if self.current_text.strip():
                    self.record.append(('TEXT', self.current_text.strip()))
                    self.current_text = ''
                
                src = attr_dict.get('data-lazy-src') or attr_dict.get('src')
                if src:
                    src = src.replace('&amp;', '&')
                    self.img_urls.append(src)
                    self.img_count += 1
                    self.record.append(('IMG', self.img_count, src))

    def handle_endtag(self, tag):
        if self.in_main and self.current_depth == self.main_div_depth:
            self.in_main = False
        self.current_depth -= 1

    def handle_data(self, data):
        if self.in_main:
            data = data.replace('\n', '').replace('\r', '').strip()
            if data:
                self.current_text += data + ' '

def article_folder_name(url):
    """글마다 따로 저장할 하위 폴더 이름. 네이버 글이면 '<블로그아이디>_<글번호>', 아니면 주소 해시.
    파일 이름에 쓸 수 없는 글자는 '_' 로 바꿔 경로가 밖으로 새지 않게 한다."""
    parsed = urllib.parse.urlparse(url)
    query = urllib.parse.parse_qs(parsed.query)
    blog_id = (query.get('blogId') or [''])[0]
    log_no = (query.get('logNo') or [''])[0]
    if blog_id and log_no:
        name = re.sub(r'[^0-9A-Za-z_-]+', '_', f"{blog_id}_{log_no}").strip('_')
        if name:
            return name
    return 'url_' + hashlib.sha1(url.encode('utf-8')).hexdigest()[:10]


def main():
    if len(sys.argv) < 2:
        print("사용법: python webtoguide.py [네이버_블로그_URL]")
        sys.exit(1)
        
    url = sys.argv[1]
    
    if 'PostView.naver' not in url and 'blog.naver.com' in url:
        parts = url.split('/')
        if len(parts) >= 5:
            blog_id = parts[3]
            log_no = parts[4]
            url = f'https://blog.naver.com/PostView.naver?blogId={blog_id}&logNo={log_no}'
    
    print(f"다운로드 중: {url}")
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    try:
        html = urllib.request.urlopen(req).read().decode('utf-8')
    except Exception as e:
        print(f"웹페이지를 가져오는 중 오류가 발생했습니다: {e}")
        sys.exit(1)

    parser = NaverParser()
    parser.feed(html)
    if parser.current_text.strip():
        parser.record.append(('TEXT', parser.current_text.strip()))

    # 결과(가이드 .md + 그림)는 저장소 밖 data_dir() 에만 저장한다 (다른 사람 블로그 그림·화면 덤프가 저장소에 올라가지 않게)
    # 글마다 하위 폴더를 써서 다음 글이 앞 글의 가이드·그림을 덮어쓰지 않게 한다 (T80)
    out_dir = data_dir("util-webtoguide", "output", article_folder_name(url))
    os.makedirs(out_dir / 'images', exist_ok=True)
    
    md_content = f"# 블로그 가이드 변환 결과\n\n> **원본 게시글 출처:** [{url}]({url})\n\n"
    
    print(f"총 {parser.img_count}개의 이미지를 찾았습니다.")
    
    for item in parser.record:
        if item[0] == 'TEXT':
            md_content += f"{item[1]}\n\n"
        elif item[0] == 'IMG':
            idx = item[1]
            src = item[2]
            ext = 'png'
            if '.jpg' in src.lower(): ext = 'jpg'
            elif '.jpeg' in src.lower(): ext = 'jpeg'
            
            filename = f"images/img_{idx}.{ext}"  # 가이드 .md 기준 상대 경로
            print(f"이미지 다운로드 중: {filename}")
            try:
                urllib.request.urlretrieve(src, str(out_dir / filename))
                md_content += f"![참고 이미지 {idx}]({filename})\n\n"
            except Exception as e:
                print(f"이미지 {idx} 다운로드 실패: {e}")
                
    with open(out_dir / 'guide_output.md', 'w', encoding='utf-8') as f:
        f.write(md_content)
        
    print(f"완료되었습니다! 이 폴더에서 guide_output.md 파일과 images 폴더를 확인하세요: {out_dir}")

if __name__ == '__main__':
    main()
