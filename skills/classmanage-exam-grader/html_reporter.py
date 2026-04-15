import json
from pathlib import Path

def generate_dashboard(graded_dir: str, output_dir: str) -> None:
    """채점된 JSON 파일들을 읽어 아름다운 HTML 대시보드를 생성합니다."""
    
    graded_path = Path(graded_dir)
    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)
    
    students = []
    
    for graded_file in graded_path.glob("*_graded.json"):
        with open(graded_file, "r", encoding="utf-8") as f:
            students.append(json.load(f))
            
    if not students:
        print("⚠️ 채점 데이터가 없어 대시보드를 생성할 수 없습니다.")
        return
        
    # 통계 계산
    students.sort(key=lambda x: x.get("total_score", 0), reverse=True)
    
    total_students = len(students)
    avg_score = round(sum(s.get("total_score", 0) for s in students) / total_students)
    hi_score = max(s.get("total_score", 0) for s in students)
    lo_score = min(s.get("total_score", 0) for s in students)
    max_score = students[0].get("total_points", 0) if students else 100
    
    html_template = f"""<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AI 채점 대시보드</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link href="https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;500;700&display=swap" rel="stylesheet">
    <style>
        body {{ font-family: 'Noto Sans KR', sans-serif; background-color: #F4F1EC; color: #1A2744; }}
        .glass-card {{ background: #FFFFFF; border-radius: 14px; box-shadow: 0 4px 20px rgba(26,39,68,0.05); }}
    </style>
</head>
<body class="p-8">
    <div class="max-w-6xl mx-auto">
        
        <header class="mb-10 flex items-center gap-4 bg-[#1A2744] text-white p-6 rounded-2xl shadow-lg">
            <span class="text-4xl">📊</span>
            <div>
                <h1 class="text-2xl font-bold">시험 채점 대시보드</h1>
                <p class="text-sm opacity-80 mt-1">exam-grader 자동 생성 결과 리포트</p>
            </div>
        </header>

        <!-- Stats Grid -->
        <div class="grid grid-cols-4 gap-6 mb-10">
            <div class="glass-card p-6 text-center border-t-4 border-[#1A2744]">
                <div class="text-4xl font-bold text-[#1A2744]">{total_students}명</div>
                <div class="text-sm text-gray-500 mt-2 font-medium">채점 인원</div>
            </div>
            <div class="glass-card p-6 text-center border-t-4 border-[#2E6B45]">
                <div class="text-4xl font-bold text-[#2E6B45]">{avg_score}점</div>
                <div class="text-sm text-gray-500 mt-2 font-medium">평균 점수</div>
            </div>
            <div class="glass-card p-6 text-center border-t-4 border-emerald-500">
                <div class="text-4xl font-bold text-emerald-500">{hi_score}점</div>
                <div class="text-sm text-gray-500 mt-2 font-medium">최고 점수</div>
            </div>
            <div class="glass-card p-6 text-center border-t-4 border-[#B83232]">
                <div class="text-4xl font-bold text-[#B83232]">{lo_score}점</div>
                <div class="text-sm text-gray-500 mt-2 font-medium">최저 점수</div>
            </div>
        </div>

        <!-- Student Table -->
        <div class="glass-card overflow-hidden">
            <table class="w-full text-left border-collapse">
                <thead>
                    <tr class="bg-[#1A2744] text-white">
                        <th class="py-4 px-6 font-semibold">이름 (학번)</th>
                        <th class="py-4 px-6 font-semibold">총점</th>
                        <th class="py-4 px-6 font-semibold">정답/오답/검토</th>
                        <th class="py-4 px-6 font-semibold">정답률</th>
                        <th class="py-4 px-6 font-semibold">문항별 결과</th>
                    </tr>
                </thead>
                <tbody class="divide-y divide-[#E2DBD0]">
"""
    for s in students:
        name = s.get("student_name", "Unknown")
        num = s.get("student_number", "")
        score = s.get("total_score", 0)
        c_cnt = s.get("correct_count", 0)
        w_cnt = s.get("wrong_count", 0)
        r_cnt = s.get("review_count", 0)
        acc = s.get("accuracy", 0)
        details = s.get("details", [])
        
        name_display = f"{name} ({num})" if num else name
        score_color = "text-[#2E6B45]" if score >= (max_score * 0.6) else "text-[#B83232]"
        
        # ProgressBar
        bar_color = "bg-[#2E6B45]" if score >= (max_score * 0.6) else "bg-[#B83232]"
        
        # OX Sequence
        ox_seq = ""
        for d in details:
            if d.get("correct") is True:
                ox_seq += '<span class="text-[#2E6B45] text-lg leading-none" title="{}번">●</span>'.format(d.get("q_num"))
            elif d.get("correct") is False:
                ox_seq += '<span class="text-[#B83232] text-lg leading-none" title="{}번">○</span>'.format(d.get("q_num"))
            else:
                ox_seq += '<span class="text-gray-400 text-lg leading-none" title="{}번">▲</span>'.format(d.get("q_num"))
        
        html_template += f"""
                    <tr class="hover:bg-[#FAFAF8] transition-colors">
                        <td class="py-4 px-6 font-medium text-lg">{name_display}</td>
                        <td class="py-4 px-6">
                            <span class="text-xl font-bold {score_color}">{score}</span>
                            <span class="text-sm text-gray-400 font-normal">/{max_score}</span>
                        </td>
                        <td class="py-4 px-6 text-gray-600 text-sm">
                            <span class="text-[#2E6B45] font-bold">{c_cnt}</span> / 
                            <span class="text-[#B83232] font-bold">{w_cnt}</span> / 
                            <span class="text-gray-500 font-bold">{r_cnt}</span>
                        </td>
                        <td class="py-4 px-6">
                            <div class="flex items-center gap-3">
                                <div class="w-full max-w-[100px] h-2 bg-gray-200 rounded-full overflow-hidden">
                                    <div class="h-full rounded-full {bar_color}" style="width: {acc}%;"></div>
                                </div>
                                <span class="text-sm text-gray-500 font-semibold">{acc}%</span>
                            </div>
                        </td>
                        <td class="py-4 px-6">
                            <div class="flex flex-wrap gap-1 bg-gray-50 p-2 rounded-lg border border-gray-100 inline-flex">
                                {ox_seq}
                            </div>
                        </td>
                    </tr>
"""
    
    html_template += """
                </tbody>
            </table>
        </div>
        
        <div class="mt-8 text-center text-gray-400 text-sm font-medium pb-8">
            Generated by CORTEX Exam Grader
        </div>
    </div>
</body>
</html>
"""

    dashboard_file = out_path / "dashboard.html"
    with open(dashboard_file, "w", encoding="utf-8") as f:
        f.write(html_template)
        
    print(f"  ✅ HTML 대시보드 리포트 생성 완료: {dashboard_file}")

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 2:
        generate_dashboard(sys.argv[1], sys.argv[2])
