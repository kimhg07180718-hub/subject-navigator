"""[F6] 계획을 엑셀 파일로 저장하고 다시 읽는다. 서버에는 아무것도 남기지 않는다."""
import zlib
from xml.etree.ElementTree import ParseError
from zipfile import BadZipFile

from openpyxl import Workbook, load_workbook
from openpyxl.utils.exceptions import InvalidFileException

from core.config import CHOICE_SHEET, ISSUE_SHEET, PLAN_HEADER, PLAN_SHEET

# 엑셀이 아니거나 손상된 파일을 열 때 생길 수 있는 오류들
BAD_FILE_ERRORS = (BadZipFile, InvalidFileException, KeyError, OSError, ParseError, zlib.error, EOFError)


def save_plan(plan, issues, file, choice=None):
    """[F6] 계획과 검사 결과를 엑셀 파일(file)에 쓴다. file은 파일 경로나 BytesIO.
    choice: 고른 계열·학과·대학 dict. 학생 이름은 저장하지 않는다."""
    wb = Workbook()

    sheet = wb.active
    sheet.title = PLAN_SHEET
    sheet.append(PLAN_HEADER)
    for name, grade, semester in plan:
        sheet.append([grade, semester, name])

    sheet = wb.create_sheet(ISSUE_SHEET)
    sheet.append(["수준", "메시지"])
    for level, message in issues:
        sheet.append([level, message])

    if choice:
        sheet = wb.create_sheet(CHOICE_SHEET)
        for key, value in choice.items():
            sheet.append([key, value])

    wb.save(file)


def open_workbook(file):
    """엑셀 파일을 연다. 엑셀이 아니면 알아듣기 쉬운 ValueError로 바꾼다."""
    try:
        return load_workbook(file, read_only=True)
    except FileNotFoundError:
        raise  # 파일이 없는 것은 그대로 알린다
    except BAD_FILE_ERRORS:
        raise ValueError("엑셀 파일을 읽을 수 없어요. 앱에서 저장한 .xlsx 파일을 올려 주세요.")


def read_rows(file, sheet_name):
    """엑셀 파일에서 시트 하나의 모든 줄을 list로 읽는다. 그 시트가 없으면 None.
    파일은 무슨 일이 있어도 닫고(finally), 손상된 파일은 알아듣기 쉬운 ValueError로 바꾼다."""
    wb = open_workbook(file)
    try:
        if sheet_name not in wb.sheetnames:
            return None
        return list(wb[sheet_name].iter_rows(values_only=True))
    except BAD_FILE_ERRORS:
        raise ValueError("엑셀 파일이 손상돼서 읽을 수 없어요. 앱에서 다시 저장해 주세요.")
    finally:
        wb.close()


def load_plan(file):
    """[F6] save_plan으로 저장한 엑셀 파일을 읽어 계획 [(과목, 학년, 학기)] list로 돌려준다."""
    rows = read_rows(file, PLAN_SHEET)
    if rows is None:
        raise ValueError(f"'{PLAN_SHEET}' 시트가 없어요. 앱에서 저장한 파일을 올려 주세요.")
    if len(rows) == 0 or list(rows[0][:3]) != PLAN_HEADER:
        raise ValueError("열 이름이 달라요. 앱에서 저장한 파일을 올려 주세요.")

    plan = []
    for line, row in enumerate(rows[1:], start=2):
        name = ""
        if len(row) >= 3 and row[2] is not None:
            name = str(row[2]).strip()
        if name == "":  # 과목 칸이 빈 줄은 건너뜀
            continue
        try:
            plan.append((name, int(row[0]), int(row[1])))
        except (TypeError, ValueError):
            raise ValueError(f"{line}번째 줄의 학년·학기가 숫자가 아니에요.")
    return plan


def load_choice(file):
    """저장할 때 고른 계열·학과·대학을 dict로 돌려준다. 없으면 빈 dict."""
    rows = read_rows(file, CHOICE_SHEET)
    choice = {}
    if rows is None:  # 예전에 저장한 파일에는 이 시트가 없을 수 있다
        return choice
    for row in rows:
        if len(row) >= 2 and row[0] is not None and row[1] is not None:
            choice[str(row[0])] = str(row[1])
    return choice


def remove_unknown(plan, offerings):
    """[F6] 우리 학교 개설표에 없는 (과목, 학년, 학기)는 빼고, 뺀 줄을 경고 문장 list로 돌려준다."""
    known = set()
    for o in offerings:
        known.add((o["name"], o["grade"], o["semester"]))

    kept = []
    warnings = []
    for name, grade, semester in plan:
        if (name, grade, semester) in known:
            kept.append((name, grade, semester))
        else:
            warnings.append(f"{grade}학년 {semester}학기 '{name}'은(는) 우리 학교 개설표에 없어서 뺐어요.")
    return kept, warnings
