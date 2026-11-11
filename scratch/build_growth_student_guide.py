from pathlib import Path
from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_CELL_VERTICAL_ALIGNMENT
from docx.oxml import OxmlElement
from docx.oxml.ns import qn

OUT = Path(r"C:\Users\user\.gemini\antigravity\scratch\repos\my-skills\skills\teacherlesson-aiep-courseware\output\2026-11-11-growth-presentation\학생용_성장발표회_준비안내.docx")
OUT.parent.mkdir(parents=True, exist_ok=True)

doc = Document()
sec = doc.sections[0]
sec.top_margin = Inches(0.68)
sec.bottom_margin = Inches(0.68)
sec.left_margin = Inches(0.78)
sec.right_margin = Inches(0.78)

styles = doc.styles
normal = styles["Normal"]
normal.font.name = "Malgun Gothic"
normal.font.size = Pt(12)
normal.font.color.rgb = RGBColor(25, 45, 42)
normal._element.rPr.rFonts.set(qn("w:eastAsia"), "Malgun Gothic")
normal.paragraph_format.space_after = Pt(5)
normal.paragraph_format.line_spacing = 1.18
for name, size in [("Title", 25), ("Heading 1", 18), ("Heading 2", 14)]:
    st = styles[name]
    st.font.name = "Malgun Gothic"
    st._element.rPr.rFonts.set(qn("w:eastAsia"), "Malgun Gothic")
    st.font.size = Pt(size)
    st.font.bold = True
    st.font.color.rgb = RGBColor(0, 0, 0)
    st.paragraph_format.space_before = Pt(10)
    st.paragraph_format.space_after = Pt(5)

def shade(cell, fill):
    tc_pr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:fill"), fill)
    tc_pr.append(shd)

def cell_text(cell, text, bold=False):
    cell.text = ""
    p = cell.paragraphs[0]
    p.paragraph_format.space_after = Pt(2)
    r = p.add_run(text)
    r.bold = bold
    r.font.name = "Malgun Gothic"
    r._element.rPr.rFonts.set(qn("w:eastAsia"), "Malgun Gothic")
    r.font.size = Pt(10.5)
    cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER

def add_bullet(text):
    p = doc.add_paragraph(style="List Bullet")
    p.paragraph_format.space_after = Pt(3)
    p.add_run(text)
    return p

def add_number(text):
    p = doc.add_paragraph(style="List Number")
    p.paragraph_format.space_after = Pt(3)
    p.add_run(text)
    return p

p = doc.add_paragraph()
p.style = "Title"
p.alignment = WD_ALIGN_PARAGRAPH.CENTER
p.add_run("나의 성장 발표회 준비")
p = doc.add_paragraph()
p.alignment = WD_ALIGN_PARAGRAPH.CENTER
r = p.add_run("처음의 나와 지금의 나를 돌아보며 내 이야기를 준비해요")
r.font.size = Pt(13)
r.font.color.rgb = RGBColor(54, 87, 77)

doc.add_paragraph("성장 발표회는 누가 더 잘했는지 겨루는 시간이 아니에요. 한 해 동안 내가 어떻게 달라졌는지 내 말로 들려주는 시간이에요. 천천히 생각하고, 나에게 맞는 방법을 골라요.")

doc.add_heading("준비 순서", level=1)
for item in [
    "한 해의 활동을 돌아보고 기억에 남는 세 가지를 찾아요.",
    "그중 하나를 골라 왜 이야기하고 싶은지 생각해요.",
    "처음의 나부터 지금의 나까지 이야기의 흐름을 짜요.",
    "내가 달라진 모습을 보여 주는 자료를 찾아요.",
    "발표 방법과 연습 계획을 정해요.",
]:
    add_number(item)

doc.add_heading("1차시 · 기억에 남는 활동 세 가지 찾기", level=1)
doc.add_paragraph("교과서 차례나 학급에서 본 자료를 3월부터 차례로 떠올려요. 교과 이름만 쓰지 말고, 그 시간에 한 활동까지 적어요.")
p = doc.add_paragraph()
p.add_run("활동 이름 예시 틀  ").bold = True
p.add_run("○○ 시간에 ○○ 하기")
for n in range(1, 4):
    doc.add_paragraph(f"{n}. ______________________________________________________________")
p = doc.add_paragraph()
p.add_run("생각을 돕는 질문  ").bold = True
p.add_run("올해 가장 기억에 남는 활동은? 내가 가장 달라진 점은? 힘들었지만 해낸 일은?")

doc.add_heading("가족과 이야기해 보기", level=1)
doc.add_paragraph("집에서 가족에게 물어봐요. “올해 내가 즐거워 보였던 일은 뭐였어?” 가족의 답을 그대로 주제로 정하는 것이 아니라, 내 이야기를 떠올리는 데 참고해요.")

doc.add_heading("2차시 · 성장 이야기 하나 고르기", level=1)
doc.add_paragraph("기억에 남는 활동 세 가지 중 하나를 골라요. 처음의 나와 지금의 나를 생각하고, 왜 이 이야기를 고르고 싶은지 짝에게 말한 뒤 적어요.")
for label, line in [("내가 고른 성장 이야기", ""), ("이 이야기를 고른 까닭", "")]:
    p = doc.add_paragraph()
    p.add_run(label + "  ").bold = True
    p.add_run("______________________________________________________________")
    doc.add_paragraph("________________________________________________________________________")
p = doc.add_paragraph()
p.add_run("말하기 틀  ").bold = True
p.add_run("나는 ○○ 시간에 ○○를 한 것이 기억에 남아요. 왜냐하면 ○○ 때문이에요.")

doc.add_heading("생각이 잘 떠오르지 않을 때", level=2)
add_bullet("내가 보는 나를 먼저 생각해요.")
add_bullet("선생님이나 가족이 보는 내 모습을 떠올려요.")
add_bullet("친구가 찾은 이야기 중 나와 닮은 것이 있는지 들어 봐요.")

doc.add_heading("가정 활동 · 내 성장을 보여 주는 자료 찾기", level=1)
doc.add_paragraph("가족과 함께 내 성장을 보여 주는 자료를 세 개 정도 찾아요. 사진이나 영상이 아니어도 괜찮아요. 공책 글, 그림, 작품, 일기, 연습 메모, 내가 쓰던 물건도 좋은 자료예요.")
add_bullet("자료마다 언제 만들거나 찍었는지 날짜를 적어요.")
add_bullet("‘변화’를 보여 주려면 예전 모습과 지금 모습처럼 날짜가 다른 자료가 필요해요.")
add_bullet("같은 날 한 번의 활동 영상은 노력한 모습을 보여 주는 자료로 쓸 수 있어요.")
add_bullet("사진과 영상에는 나만 나오게 골라요. 다른 친구가 나오면 다른 자료를 찾아요.")

tbl = doc.add_table(rows=1, cols=4)
tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
tbl.style = "Table Grid"
headers = ["번호", "자료 이름", "언제 만들거나 찍었나요?", "어떤 이야기를 보여 주나요?"]
for c, h in zip(tbl.rows[0].cells, headers):
    cell_text(c, h, True)
    shade(c, "E5EFE8")
for num in ["①", "②", "③"]:
    cells = tbl.add_row().cells
    for c, value in zip(cells, [num, "", "", ""]):
        cell_text(c, value)

doc.add_heading("이야기의 얼개 짜기", level=1)
doc.add_paragraph("친구에게 먼저 말해 본 뒤 짧게 적어요. 모든 칸을 다 채우지 않아도 돼요. 계획서에는 자료 번호를 연결해요.")
outline = [
    ("처음의 나", "처음에는 어땠나요?"),
    ("어려움", "어려웠던 점은 무엇이었나요?"),
    ("계기", "시작하게 된 일이나 기억에 남는 일은 무엇인가요?"),
    ("노력", "무엇을 연습했나요? 어떻게 노력했나요?"),
    ("변화", "무엇이 달라졌나요?"),
    ("지금의 나", "이제 할 수 있게 된 것은 무엇인가요?"),
    ("내가 얻은 배움", "이 경험으로 무엇을 알게 되었나요?"),
]
tbl2 = doc.add_table(rows=1, cols=3)
tbl2.alignment = WD_TABLE_ALIGNMENT.CENTER
tbl2.style = "Table Grid"
for c, h in zip(tbl2.rows[0].cells, ["이야기 단계", "생각을 돕는 질문", "내가 말하거나 적을 내용 · 증거 번호"]):
    cell_text(c, h, True)
    shade(c, "E5EFE8")
for stage, prompt in outline:
    cells = tbl2.add_row().cells
    cell_text(cells[0], stage, True)
    cell_text(cells[1], prompt)
    cell_text(cells[2], "\n\n")

doc.add_heading("발표 방법과 연습 계획", level=1)
doc.add_paragraph("처음과 지금의 모습을 가장 잘 보여 주는 방법을 골라요.")
doc.add_paragraph("[ ] 사진·그림을 곁들인 발표    [ ] 역할극    [ ] 직접 보여 주기    [ ] 그림    [ ] 영상    [ ] 다른 방법")
doc.add_paragraph("이 방법을 고른 까닭: __________________________________________________")
doc.add_paragraph("준비물: ______________________________________________________________")
doc.add_paragraph("연습 방법: [ ] 메모하며    [ ] 거울을 보며    [ ] 친구 앞에서    [ ] 가족 앞에서")
doc.add_paragraph("연습할 날짜: ____________________    발표 시간: 교사의 안내를 확인해요.")

doc.add_heading("마지막으로 기억해요", level=1)
add_bullet("내 이야기는 내 경험에서 골라요. 예시를 그대로 따라 쓰지 않아요.")
add_bullet("자료는 많이 모으기보다 내 변화를 잘 보여 주는 것을 골라요.")
add_bullet("대본을 외우기보다 내 말로 이야기해요. 완벽하지 않아도 괜찮아요.")

for table in doc.tables:
    for row in table.rows:
        for cell in row.cells:
            for p in cell.paragraphs:
                p.paragraph_format.space_after = Pt(2)
                p.paragraph_format.line_spacing = 1.05

doc.save(OUT)
print(OUT)
