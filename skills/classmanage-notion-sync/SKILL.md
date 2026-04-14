---
name: Notion to Supabase Migrator
description: 노션(Notion) 데이터베이스의 자료를 읽어와서 Supabase 테이블로 자동 이관해주는 스크립트입니다.
---

# Notion to Supabase Migrator

노션 데이터베이스에 쌓여있는 레코드들을 추출하여 Supabase의 특정 테이블로 이관(Migration)하는 도구입니다.

## 기능 설명
- **노션 DB 연동**: Notion API를 활용해 지정된 Database ID의 모든 페이지(Row) 데이터를 가져옵니다.
- **자동 데이터 매핑**: 노션의 프로퍼티(Text, Number, Date, Select 등)를 JSON 형태로 파싱하여 Supabase 테이블 컬럼에 맞게 변환합니다.
- **Supabase 업로드**: 추출된 JSON 데이터를 Supabase REST API를 통해 일괄 업로드(Insert/Upsert)합니다.

## 설정 방법

### 1. 환경 변수 설정
`my-skills/skills/notion-to-supabase/.env` 파일을 생성하고 다음 정보를 입력하세요.

```env
NOTION_API_KEY=secret_...
NOTION_DATABASE_ID=...
SUPABASE_URL=https://<your-project>.supabase.co
SUPABASE_KEY=eyJhbG...
SUPABASE_TABLE_NAME=my_table
```

### 2. 패키지 설치
```powershell
pip install -r requirements.txt
```

## 사용법
터미널에서 이 폴더로 이동한 뒤 파이썬 스크립트를 실행합니다.

```powershell
# 옵션 1) 환경변수의 기본 설정대로 바로 이관
python migrate.py

# 옵션 2) 특정 노션 DB와 특정 수퍼베이스 테이블을 임시 지정해서 이관
python migrate.py --notion-db [DATABASE_ID] --table [TABLE_NAME]
```

## 참고 사항
- 노션 프로퍼티의 이름이 Supabase의 컬럼명과 완전히 일치해야 값이 정상적으로 들어갑니다. (예: 노션의 'title' -> Supabase의 'title')
- SSL 인증서 체인 오류(윈도우 보안 문제)를 피하기 위해 `urllib3.disable_warnings()`를 적용하고 REST API를 사용해 데이터를 전송합니다.
