import fitz
from pathlib import Path

def create_fake_pdfs():
    base_dir = Path("c:/Users/lee21/.gemini/antigravity/scratch/my-skills/skills/classmanage-exam-grader/data/input")
    
    ans_dir = base_dir / "answer_key"
    stu_dir = base_dir / "students"
    
    ans_dir.mkdir(parents=True, exist_ok=True)
    stu_dir.mkdir(parents=True, exist_ok=True)
    
    # 1. 정답지 PDF 생성
    doc_ans = fitz.open()
    page_ans = doc_ans.new_page()
    content_ans = """
[Answer Key]
Exam: Science Test

1. objective / answer: 3 / points: 10
2. short_answer / answer: 24 / points: 10
3. descriptive / answer: Since photosynthesis produces oxygen and glucose. / points: 20
Rubric for 3: Must include oxygen and glucose. 10 points if only one is included.
"""
    page_ans.insert_text(fitz.Point(50, 50), content_ans, fontname="helv", fontsize=12)
    doc_ans.save(str(ans_dir / "answer_key.pdf"))
    doc_ans.close()
    
    # 2. 학생 시험지 PDF 생성
    doc_stu = fitz.open()
    page_stu = doc_stu.new_page()
    content_stu = """
[Science Test]
Name: HongGilDong
Number: 1

1. 3
2. 24
3. It produces oxygen.
"""
    page_stu.insert_text(fitz.Point(50, 50), content_stu, fontname="helv", fontsize=12)
    doc_stu.save(str(stu_dir / "HongGilDong.pdf"))
    doc_stu.close()

    print("Fake PDFs generated successfully.")

if __name__ == "__main__":
    create_fake_pdfs()
