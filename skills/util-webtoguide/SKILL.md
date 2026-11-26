---
name: util-webtoguide
description: Converting Naver blog post with images to a markdown guide
metadata:
  category: 공통 유틸
  status: 운영
  summary: 웹페이지, 특히 네이버 블로그의 글·이미지를 추출해 출처 링크가 포함된 Markdown 가이드로 변환한다.
---
# util-webtoguide
이 스킬은 웹사이트(특히 네이버 블로그) 등의 링크에서 글과 이미지를 추출하여,
이미지가 올바른 설명 사이에 들어간 마크다운(Markdown) 형태의 가이드 문서로 변환해주는 파이썬 스크립트입니다.

## 스크립트 실행 방법
`python webtoguide.py [네이버_블로그_URL]`
을 실행하면 **저장소 밖 데이터 폴더**(`내 문서\my-skills-data\util-webtoguide\output\<블로그아이디>_<글번호>\`)에 마크다운 가이드 파일(`guide_output.md`)과 `images` 폴더가 생성됩니다. 글마다 폴더가 따로라서 다음 글을 변환해도 앞 글 결과가 덮어써지지 않습니다(같은 글을 다시 변환하면 그 폴더를 다시 씁니다). 다른 사람 블로그의 그림이 저장소에 올라가지 않도록 결과는 저장소 안에 두지 않습니다(위치는 끝나면 화면에 표시됩니다). 
가이드 파일의 최상단에는 작성자가 잊지 않도록 **원본 게시물의 출처 링크가 자동으로 표기**됩니다.
