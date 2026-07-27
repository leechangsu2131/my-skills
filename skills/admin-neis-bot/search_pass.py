import json, os, sys

log_path1 = r"C:\Users\lee21\.gemini\antigravity\brain\d8a868cf-ab02-44e0-92b1-68bd3ae1045a\.system_generated\logs\transcript.jsonl"
log_path2 = r"C:\Users\lee21\.gemini\antigravity\brain\b857c57b-5e64-4b7d-bb6c-7a63cf5605b2\.system_generated\logs\transcript.jsonl"

def search_file(path, keywords):
    if not os.path.exists(path):
        print(f"Path does not exist: {path}")
        return
    print(f"Searching in {path}...")
    with open(path, "r", encoding="utf-8") as f:
        for idx, line in enumerate(f):
            try:
                data = json.loads(line)
                content = str(data.get("content", ""))
                # tool_calls 도 포함해서 검색
                tc = str(data.get("tool_calls", ""))
                combined = content + " " + tc
                for kw in keywords:
                    if kw in combined:
                        print(f"Line {idx+1} matches '{kw}':")
                        # 텍스트가 너무 길면 잘라서 출력
                        snippet = combined if len(combined) < 250 else combined[:250] + "..."
                        print(f"  {snippet}")
            except Exception as e:
                pass

search_file(log_path1, ["비밀번호", "password", "결재", "neis", "나이스"])
search_file(log_path2, ["비밀번호", "password", "결재", "neis", "나이스"])
