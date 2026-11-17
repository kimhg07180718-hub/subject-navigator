"""고교학점제 과목 선택 내비게이터 (광주 광덕고)
희망 학과와 목표 대학을 고르면 2·3학년 선택과목 계획을 짜 주고, 선택 규칙을 검사한다.

실행 방법: 웹 앱은 streamlit run app.py, 테스트는 pytest

이 파일의 차례 (자료는 data 폴더의 CSV 5개에 따로 있다)
 1. 기준값
 2. 데이터 읽기
 3. 추천 [F1·F2]
 4. 계획 짜기 [F3]
 5. 규칙 검사 [F4·F5]
 6. 엑셀 저장 [F6]
 7. 화면 공통 (사이드바, 화면 머리, 다음 단계 버튼)
 8. 화면 1: 홈
 9. 화면 2: 추천 과목
10. 화면 3: 내 이수 계획
11. 시작
"""
import csv                                                # CSV 파일 읽기
import os                                                 # 파일 경로 만들기, 파일 고친 시각 알아보기
from io import BytesIO                                    # 메모리 안의 '가짜 파일' (엑셀을 파일 없이 내려보낸다)

import pandas as pd                                       # 화면에 표(st.dataframe)를 그릴 때 쓴다
import streamlit as st                                    # 웹 화면을 만든다
from openpyxl import Workbook                             # 엑셀 파일 만들기
from streamlit import runtime                             # streamlit run으로 켰는지 알아볼 때 쓴다


# ============================================================
# 1. 기준값: 앱 전체에서 쓰는 값을 이름을 붙여 한곳에 모아 둔다
# ============================================================

# 이 파일(app.py)이 있는 폴더 안의 data 폴더 경로. 어느 폴더에서 실행해도 같은 곳을 가리킨다
DATA_FOLDER = os.path.join(os.path.dirname(__file__), "data")

# data 폴더 안의 CSV 파일 5개 (dict의 키 → 파일 이름)
DATA_FILES = {
    "courses": "courses.csv",          # 전국 과목표 (2022 개정)
    "offerings": "offerings.csv",      # 우리 학교 개설표
    "groups": "groups.csv",            # 선택군
    "majors": "majors.csv",            # 계열·학과
    "recs": "recommendations.csv",     # 대학·학과별 권장 과목
}

# 정수로 바꿔야 하는 열. 빈칸이면 오류로 본다.
NUMBER_COLUMNS = {
    "courses": ["credits", "credits_min", "credits_max"],
    "offerings": ["grade", "semester", "school_credits"],
    "groups": ["grade", "semester", "pick_count"],
}

# 정수로 바꾸되 빈칸이면 0으로 두는 열
BLANK_AS_ZERO = {
    "offerings": ["applicants"],
    "recs": ["count"],
}

# 추천 점수
SCORE_CORE = 3        # 고른 대학·학과의 핵심 과목
SCORE_RECOMMEND = 2   # 고른 대학·학과의 권장 과목
SCORE_SAME_FIELD = 1  # 같은 계열 다른 학과의 권장 과목
SCORE_FIELD_AREA = 1  # 계열과 잘 맞는 교과의 과목 (권장 과목 자료가 적은 학과를 위해)
HINT_PENALTY = 1      # 계획을 짤 때: 보통 먼저 듣는 과목을 아직 안 들었으면 -1

# 권장 과목 자료가 없는 학과에서 대학 칸에 보여 줄 글자
NO_UNIVERSITY = "자료 없음"

# 계열마다 잘 맞는 교과 (courses.csv의 area 값)
FIELD_AREAS = {
    "공학": ["수학", "과학", "기술·가정/정보"],
    "자연": ["수학", "과학"],
    "의약": ["과학", "수학"],
    "사회": ["사회(역사/도덕 포함)", "수학"],
    "인문": ["국어", "사회(역사/도덕 포함)", "영어", "제2외국어/한문"],
    "교육": ["국어", "사회(역사/도덕 포함)", "교양"],
}

# 계획을 짜는 학기 순서 (학년, 학기)
PLAN_TERMS = [(2, 1), (2, 2), (3, 1), (3, 2)]

# 검사 결과 수준 (LEVELS에서 앞에 있을수록 중요하다)
ERROR = "오류"
WARNING = "주의"
INFO = "안내"
LEVELS = [ERROR, WARNING, INFO]

# 계획 엑셀 파일의 모양 (시트 이름 3개와 계획 시트의 열 이름)
PLAN_SHEET = "계획"
ISSUE_SHEET = "검사 결과"
CHOICE_SHEET = "선택"
PLAN_HEADER = ["학년", "학기", "과목"]

# 핵심·권장마다 배지 색을 하나로 정한다. 빨강은 오류에만 쓴다
LEVEL_COLOR = {"핵심": "violet", "권장": "blue"}


# ============================================================
# 2. 데이터 읽기: CSV 파일을 읽어 검사한 뒤 list·dict로 만든다
# ============================================================

def to_numbers(rows, columns, file_name, blank_as_zero=False):
    """rows(줄 dict의 list)에서 columns 열의 글자를 정수로 바꾼다. 숫자가 아니면 몇 번째 줄인지 알리는 ValueError를 낸다."""
    for row in rows:
        for col in columns:
            value = row.get(col)  # 그 열이 없거나 줄이 짧아 칸이 모자라면 None
            if blank_as_zero and (value is None or value.strip() == ""):
                value = "0"  # 빈칸을 0으로 보는 열이면 "0"으로 바꿔 둔다
            # int("3")은 3이 되지만 int("네")나 int(None)은 오류가 난다. 그 오류를 잡아 알아보기 쉬운 메시지로 바꾼다
            try:
                row[col] = int(value)
            except (TypeError, ValueError):
                raise ValueError(f"{file_name} {row['line']}번째 줄의 {col} 칸이 숫자가 아니에요: '{value}'")


def check_data(data):
    """읽은 자료에 과목 이름 오타, 없는 선택군, 두 번 들어간 줄이 있는지 보고, 있으면 줄 번호를 넣은 ValueError를 낸다."""
    # 개설표와 권장 과목의 과목 이름이 모두 과목표(courses.csv)에 있는지 본다 (오타를 일찍 찾는다)
    names = {c["name"] for c in data["courses"]}  # 과목 이름 set. 'in'으로 들어 있는지 빨리 확인할 수 있다
    for o in data["offerings"]:
        if o["name"] not in names:
            raise ValueError(f"offerings.csv {o['line']}번째 줄의 과목 '{o['name']}'이(가) courses.csv에 없어요.")
    for r in data["recs"]:
        for name in r["courses"].split("|"):  # "미적분Ⅱ|기하"처럼 |로 이어 적은 과목을 하나씩 본다
            if name != "" and name not in names:  # 칸이 비어 있으면 split 결과가 [""]라서 빈 글자는 건너뛴다
                raise ValueError(f"recommendations.csv {r['line']}번째 줄의 과목 '{name}'이(가) courses.csv에 없어요.")

    # 같은 선택군이 groups.csv에 두 번 들어가지 않았는지 본다
    group_ids = set()  # 지금까지 나온 선택군 이름
    for g in data["groups"]:
        if g["group_id"] in group_ids:
            raise ValueError(f"groups.csv {g['line']}번째 줄의 선택군 '{g['group_id']}'이(가) 앞에도 있어요.")
        group_ids.add(g["group_id"])

    # 개설표의 선택군 이름이 groups.csv에 있는지, 같은 (과목, 학년, 학기)가 두 번 나오지 않는지 본다
    seen = set()  # 지금까지 나온 (과목, 학년, 학기) 튜플
    for o in data["offerings"]:
        if o["group_id"] != "" and o["group_id"] not in group_ids:
            raise ValueError(f"offerings.csv {o['line']}번째 줄의 선택군 '{o['group_id']}'이(가) groups.csv에 없어요.")
        key = (o["name"], o["grade"], o["semester"])
        if key in seen:
            raise ValueError(f"offerings.csv {o['line']}번째 줄의 '{o['name']}'"
                             f"({o['grade']}학년 {o['semester']}학기)이(가) 앞에도 있어요.")
        seen.add(key)


def load_all(folder):
    """folder의 CSV 5개를 읽고 검사해 {"courses": [줄 dict, ...], "offerings": [...], ...} 모양의 dict로 돌려준다."""
    data = {}
    for key, file_name in DATA_FILES.items():
        # CSV 한 파일을 '줄마다 dict'인 list로 읽는다. 파일이 없거나 글자를 못 읽으면 알아보기 쉬운 메시지로 바꿔 낸다
        rows = []
        try:
            # with: 블록이 끝나면(오류가 나도) 파일을 저절로 닫는다
            # utf-8-sig: 엑셀이 'CSV UTF-8'로 저장할 때 맨 앞에 붙이는 표시(BOM)를 떼고 읽는다
            # newline="": 줄바꿈 처리는 csv 모듈에 맡긴다 (csv 파일을 열 때 파이썬 문서가 권하는 방법)
            with open(os.path.join(folder, file_name), encoding="utf-8-sig", newline="") as f:
                reader = csv.DictReader(f)  # 첫 줄을 열 이름으로 써서 줄마다 {열 이름: 글자} dict를 준다
                for row in reader:
                    row["line"] = reader.line_num  # 파일의 실제 줄 번호 (열 이름 줄이 1, 빈 줄도 센다). 오류 메시지에 쓴다
                    rows.append(row)
        except FileNotFoundError:
            raise FileNotFoundError(f"{file_name} 파일이 없어요. data 폴더를 확인해 주세요.")
        except UnicodeDecodeError:  # UTF-8이 아닌 방식으로 저장된 파일이면 글자를 읽다가 이 오류가 난다
            raise ValueError(f"{file_name}의 글자를 읽을 수 없어요. 엑셀에서 'CSV UTF-8' 형식으로 다시 저장해 주세요.")

        # 숫자 열을 정수로 바꾼다. 두 dict에 이 파일(key)이 없으면 .get이 기본값 빈 list를 돌려줘 아무것도 바꾸지 않는다
        to_numbers(rows, NUMBER_COLUMNS.get(key, []), file_name)
        to_numbers(rows, BLANK_AS_ZERO.get(key, []), file_name, blank_as_zero=True)
        data[key] = rows
    check_data(data)
    return data


def find_offering(name, grade, semester, offerings):
    """우리 학교 개설표에서 (과목, 학년, 학기)에 맞는 줄 dict를 찾아 돌려준다. 없으면 None."""
    for o in offerings:
        if o["name"] == name and o["grade"] == grade and o["semester"] == semester:
            return o
    return None


def offered_text(name, offerings):
    """과목이 우리 학교에서 열리는 때를 '2학년 1학기, 2학년 2학기'처럼, 열리지 않으면 '미개설'로 돌려준다."""
    # 개설표에서 그 과목의 줄만 골라 '2학년 1학기' 같은 글자 list를 만든다
    terms = [f"{o['grade']}학년 {o['semester']}학기" for o in offerings if o["name"] == name]
    if len(terms) == 0:
        return "미개설"
    return ", ".join(terms)  # 글자들 사이에 ", "를 넣어 한 줄로 잇는다


# ============================================================
# 3. 추천 [F1·F2]: 고른 대학·학과에 맞춰 과목마다 추천 점수를 매기고, 과목을 검색한다
# ============================================================

def split_courses(rule):
    """규칙(dict) 하나를 받아 courses 칸 'A|B|C'를 과목 이름 list ['A', 'B', 'C']로 나눠 돌려준다."""
    # list comprehension: '|'로 자른 조각을 하나씩 보며 빈 글자가 아닌 것만 모은다
    return [name for name in rule["courses"].split("|") if name != ""]


def need_count(rule):
    """규칙 하나를 받아 그 규칙을 지키려면 몇 과목이 필요한지 돌려준다."""
    if rule["rule"] == "none":  # 따로 정한 권장 과목 없음
        return 0
    if rule["rule"] == "at_least":  # 'N과목 이상': N은 count 칸에 있다
        return rule["count"]
    return 1  # single(한 과목), any_of(여럿 중 한 과목)


def rule_text(rule):
    """규칙 하나를 받아 사람이 읽기 쉬운 문장으로 바꿔 돌려준다."""
    names = split_courses(rule)
    if rule["rule"] == "none":
        return "따로 정한 권장 과목 없음"
    if rule["rule"] == "single":
        return names[0]
    if rule["rule"] == "any_of":  # 예: '화학 또는 생명과학 중 1과목'
        return " 또는 ".join(names) + " 중 1과목"  # join: list의 글자들 사이에 ' 또는 '을 넣어 하나로 잇는다
    # 남은 경우는 at_least. f-string은 {} 자리에 값을 넣는다 (예: '대수, 기하, 미적분Ⅱ 중 2과목 이상')
    return ", ".join(names) + f" 중 {rule['count']}과목 이상"


def find_rules(major, university, recs):
    """[F2] 학과·대학 이름과 권장 과목 자료(recs)를 받아 그 학과·대학의 규칙만 골라 list로 돌려준다."""
    return [rule for rule in recs if rule["major"] == major and rule["university"] == university]


def needed_rules(rules):
    """[F2] 규칙 list를 받아 '따로 정한 권장 과목 없음'(none) 규칙을 뺀 list를 돌려준다."""
    return [rule for rule in rules if need_count(rule) > 0]


def without_required(rules, required):
    """[F2] 규칙 list와 필수 과목 이름 set을 받아 (규칙, 남은 과목 list, 더 들어야 할 과목 수) list를 돌려준다."""
    # 필수 과목(required)은 모두 들으니 규칙에서 저절로 채워진다. 필수 과목만으로 채워지는 규칙은 통째로 뺀다
    # 예: '대수, 미적분Ⅰ, 기하, 미적분Ⅱ 중 3과목 이상' → (규칙, ['기하', '미적분Ⅱ'], 1)
    shown = []
    for rule in needed_rules(rules):
        names = split_courses(rule)
        rest = [n for n in names if n not in required]  # 필수가 아닌 과목만 남긴다
        need = need_count(rule) - (len(names) - len(rest))  # 빠진 필수 과목 수만큼 덜 들어도 된다
        if need > 0:
            shown.append((rule, rest, need))  # 세 값을 튜플 하나로 묶어 넣는다
    return shown


def field_names(majors):
    """[F1] 학과 list를 받아 계열 이름 list를 majors.csv에 나온 순서대로 돌려준다 (같은 이름은 한 번만)."""
    fields = []
    for m in majors:
        if m["field"] not in fields:  # 아직 안 넣은 계열만 넣는다
            fields.append(m["field"])
    return fields


def universities_for(major, recs):
    """[F1] 학과 이름과 recs를 받아 그 학과의 권장 과목 자료가 있는 대학 list(가나다순)를 돌려준다."""
    # {...}는 set이라 같은 대학이 여러 줄에 나와도 한 번만 남는다. sorted()는 가나다순 list로 바꾼다
    names = sorted({r["university"] for r in recs if r["major"] == major})
    if len(names) == 0:  # majors.csv에만 있고 권장 과목 자료가 없는 학과
        names = [NO_UNIVERSITY]
    return names


def score_courses(major, university, majors, recs, courses):
    """[F2] 고른 학과·대학과 자료를 받아 과목마다 추천 점수를 매긴 {과목 이름: 점수} dict를 돌려준다."""
    # scores.get(name, 0)은 아직 점수가 없는 과목이면 0을 돌려준다. 그래서 0점에서 시작해 더해 간다
    scores = {}

    # 1) 고른 대학·학과의 핵심 과목은 +3, 권장 과목은 +2
    for rule in find_rules(major, university, recs):
        point = SCORE_RECOMMEND
        if rule["level"] == "핵심":
            point = SCORE_CORE
        for name in split_courses(rule):
            scores[name] = scores.get(name, 0) + point

    # 2) 같은 계열 다른 학과의 권장 과목은 +1 (과목마다 한 번만)
    field = ""  # 고른 학과의 계열. majors.csv에 없는 학과면 빈 글자로 둔다
    for m in majors:
        if m["name"] == major:
            field = m["field"]
            break  # 처음 찾은 줄의 계열을 쓴다
    same_field = {m["name"] for m in majors if m["field"] == field and m["name"] != major}  # 같은 계열 다른 학과
    bonus = set()  # set에는 같은 과목이 한 번만 들어가므로 여러 학과에 나와도 +1은 한 번뿐이다
    for rule in recs:
        if rule["major"] in same_field:
            bonus.update(split_courses(rule))  # update: list의 과목들을 set에 한꺼번에 넣는다
    for name in bonus:
        scores[name] = scores.get(name, 0) + SCORE_SAME_FIELD

    # 3) 계열과 잘 맞는 교과의 과목은 +1 (예: 인문 계열 → 국어·사회·영어). FIELD_AREAS에 없는 계열이면 빈 list
    for c in courses:
        if c["area"] in FIELD_AREAS.get(field, []):
            scores[c["name"]] = scores.get(c["name"], 0) + SCORE_FIELD_AREA

    return scores


def score_word(score):
    """[F2] 추천 점수를 받아 3점 이상 '강력 추천', 2점 '추천', 1점 '참고', 그보다 낮으면 빈 글자를 돌려준다."""
    if score >= 3:
        return "강력 추천"
    if score >= 2:
        return "추천"
    if score >= 1:
        return "참고"
    return ""


def simple(text):
    """글자를 받아 띄어쓰기를 빼고 Ⅰ·Ⅱ를 1·2로 바꿔 돌려준다 (예: '미적분 Ⅱ' → '미적분2'). 검색할 때 쓴다."""
    return text.replace(" ", "").replace("Ⅰ", "1").replace("Ⅱ", "2")  # replace(찾을 글자, 바꿀 글자)를 이어 쓴다


def search_courses(keyword, courses):
    """[F2] 검색어와 과목 list를 받아 이름에 검색어가 들어간 과목 list를 돌려준다 (띄어쓰기, Ⅰ과 1의 차이는 무시)."""
    key = simple(keyword)
    if key == "":  # 빈칸만 쳤으면 아무것도 찾지 않는다
        return []
    return [c for c in courses if key in simple(c["name"])]  # 글자 in 글자: 앞 글자가 뒤 글자 안에 들어 있으면 True


# ============================================================
# 4. 계획 짜기 [F3]: 추천 점수로 2·3학년 선택과목 계획을 자동으로 짠다 (탐욕 알고리즘)
#    계획은 [(과목, 학년, 학기), ...] 모양의 list다
# ============================================================

def fixed_courses(offerings):
    """개설표를 받아 선택군이 없는 공통·지정 과목(모두 듣는 과목)을 계획 list로 만들어 돌려준다."""
    return [(o["name"], o["grade"], o["semester"]) for o in offerings if o["group_id"] == ""]


def required_names(offerings):
    """개설표를 받아 모두 듣는 공통·지정 과목(필수 과목)의 이름 set을 돌려준다. 예: 미적분Ⅰ, 화법과 언어"""
    # 계획의 줄마다 (과목, 학년, 학기)로 풀어서 과목 이름만 set에 모은다
    return {name for name, grade, semester in fixed_courses(offerings)}


def term_plan(plan, grade, semester):
    """계획과 학년·학기를 받아 그 한 학기에 든 줄만 골라 list로 돌려준다."""
    return [(name, g, s) for name, g, s in plan if g == grade and s == semester]


def group_options(group_id, offerings):
    """선택군 이름과 개설표를 받아 그 선택군에서 고를 수 있는 과목 이름 list를 돌려준다."""
    return [o["name"] for o in offerings if o["group_id"] == group_id]


def picked_in_group(plan, group, offerings):
    """계획과 선택군 하나를 받아, 계획에서 그 선택군(같은 학년·학기)에 들어간 과목 이름 list를 돌려준다."""
    options = group_options(group["group_id"], offerings)
    # 줄이 길어 두 줄로 나눠 쓴 list comprehension이다 (for 하나, if 하나)
    return [name for name, grade, semester in plan
            if name in options and grade == group["grade"] and semester == group["semester"]]


def taken_before(name, grade, semester, plan):
    """과목 이름·학년·학기와 계획을 받아, 계획에서 그 과목을 그보다 앞 학기에 들었으면 True를 돌려준다."""
    for n, g, s in plan:
        # 튜플 비교는 학년부터 하고, 학년이 같을 때만 학기를 비교한다 (예: (2, 2) < (3, 1)은 True)
        if n == name and (g, s) < (grade, semester):
            return True
    return False


def done_before(name, grade, semester, plan, offered):
    """먼저 들을 과목 이름을 받아, 막을 까닭이 없으면(빈 글자, 우리 학교에 없는 과목, 앞 학기에 들음) True를 돌려준다."""
    if name == "" or name not in offered:  # 우리 학교에 아예 없는 과목은 막지 않는다 (검사에서 안내만 한다)
        return True
    return taken_before(name, grade, semester, plan)


def build_plan(scores, courses, offerings, groups, taken=None):
    """[F3] 추천 점수와 자료를 받아, 점수가 높은 과목부터 선택군마다 pick_count만큼 골라 넣은 계획 list를 돌려준다."""
    # taken: 이미 고른 선택과목 [(과목, 학년, 학기), ...]. 그 선택군은 남은 자리만 채운다. 안 주면 None
    courses_by_name = {c["name"]: c for c in courses}  # {키: 값 for ...}: 과목 이름으로 과목 줄을 바로 찾는 dict
    offered = {o["name"] for o in offerings}  # 우리 학교에 열리는 과목 이름 set
    # 과목마다 신청 인원 (여러 학기에 열리면 가장 큰 값). 점수가 같을 때 폐강 위험이 적은 과목을 먼저 넣으려고 쓴다
    applicants = {}
    for o in offerings:
        applicants[o["name"]] = max(applicants.get(o["name"], 0), o["applicants"])

    # 모두 듣는 과목으로 시작하고, 이미 고른 과목이 있으면 덧붙인다
    plan = fixed_courses(offerings)
    if taken:  # None이나 빈 list면 거짓이라 건너뛴다
        plan = plan + list(taken)

    # 학기 순서대로, 그 학기의 선택군마다 남은 자리를 채운다 (탐욕: 지금 가장 좋아 보이는 과목부터 넣는다)
    for grade, semester in PLAN_TERMS:
        for group in groups:
            if group["grade"] != grade or group["semester"] != semester:
                continue
            need = group["pick_count"] - len(picked_in_group(plan, group, offerings))  # 남은 자리 수
            if need <= 0:
                continue

            # 후보 과목을 모으고, 후보마다 넣을 순서를 정하는 점수(priority)를 매긴다
            already = {n for n, g, s in plan}  # 계획에 이미 든 과목 이름 set
            candidates = []
            priority = {}
            for name in group_options(group["group_id"], offerings):
                # 이미 넣은 과목(같은 과목 두 번 금지)이거나, 학교에 열리는 선수 과목을 앞 학기에 안 들었으면 뺀다
                if name in already or not done_before(courses_by_name[name]["prereq"], grade, semester, plan, offered):
                    continue
                candidates.append(name)
                # 추천 점수에서 시작해, 보통 먼저 듣는 과목(before_hint)이 학교에 열리는데 앞 학기에 안 들었으면 조금 깎는다
                priority[name] = scores.get(name, 0)
                if not done_before(courses_by_name[name]["before_hint"], grade, semester, plan, offered):
                    priority[name] -= HINT_PENALTY

            # (순서 점수, 신청 인원) 튜플이 큰 과목부터 줄 세운다. lambda는 과목 이름 n을 받아 그 튜플을 돌려준다
            # reverse=True는 큰 것부터라는 뜻이다. 튜플은 앞 값부터 비교하고, 두 값이 모두 같은 과목끼리는 원래 순서를 지킨다
            candidates.sort(key=lambda n: (priority[n], applicants.get(n, 0)), reverse=True)
            for name in candidates[:need]:  # [:need]: 앞에서부터 남은 자리 수만큼만 넣는다
                plan.append((name, grade, semester))
    return plan


# ============================================================
# 5. 규칙 검사 [F4·F5]: 계획의 학점을 더하고, 규칙을 어긴 곳을 (수준, 메시지) 문장으로 알려 준다
# ============================================================

def josa(word, with_batchim, without_batchim):
    """낱말과 조사 두 개(받침 있을 때, 없을 때)를 받아 받침에 맞는 조사를 붙여 돌려준다. 예: 미적분Ⅰ → 미적분Ⅰ을"""
    # 마지막 글자가 Ⅰ·Ⅱ·1·2면 읽는 소리('일'·'이')로 바꿔서 본다. 표에 없는 글자는 get의 기본값으로 그대로 둔다
    last = {"Ⅰ": "일", "Ⅱ": "이", "1": "일", "2": "이"}.get(word[-1], word[-1])
    # "가" <= last <= "힣": 한글 글자인지 본다. ord()는 글자의 유니코드 번호를 돌려준다.
    # 한글은 '가'부터 받침 28가지(받침 없음 포함)씩 묶여 차례로 번호가 붙어 있어서, 28로 나눈 나머지가 0이면 받침이 없다
    if "가" <= last <= "힣" and (ord(last) - ord("가")) % 28 != 0:
        return word + with_batchim
    return word + without_batchim


def total_credits(plan, offerings):
    """[F4] 계획과 개설표를 받아 계획에 든 과목의 학점(우리 학교 기준) 합계를 돌려준다."""
    total = 0
    for name, grade, semester in plan:
        o = find_offering(name, grade, semester, offerings)  # 그 학기에 열리지 않으면 None
        if o is not None:
            total += o["school_credits"]
    return total


def check_groups(plan, offerings, groups):
    """계획, 개설표, 선택군 list를 받아 선택군마다 정해진 수만큼 골랐는지 검사해 [(수준, 메시지)] list를 돌려준다."""
    issues = []
    for g in groups:
        count = len(picked_in_group(plan, g, offerings))  # 이 선택군에서 고른 과목 수
        if count != g["pick_count"]:
            issues.append((ERROR, f"{g['group_id']}군({g['grade']}학년 {g['semester']}학기)에서는 "
                                  f"{g['pick_count']}과목을 골라야 해요. 지금 {count}과목이에요."))
    return issues


def check_duplicates(plan):
    """계획을 받아 같은 과목을 두 번 고른 곳을 찾아 [(수준, 메시지)] list로 돌려준다."""
    issues = []
    first_time = {}  # {과목 이름: (학년, 학기)} 과목을 처음 고른 학기를 기억한다
    for name, grade, semester in plan:
        if name in first_time:  # dict에 in을 쓰면 그 키가 있는지 본다
            g, s = first_time[name]  # 튜플 (학년, 학기)를 두 변수로 나눠 받는다
            issues.append((ERROR, f"{josa(name, '은', '는')} {g}학년 {s}학기에 이미 골랐어요."))
        else:
            first_time[name] = (grade, semester)
    return issues


def check_credits(plan, courses_by_name, offerings):
    """계획, {이름: 과목} dict, 개설표를 받아 학점이 허용 범위(예: 3~5학점) 밖인 곳을 [(수준, 메시지)] list로 돌려준다."""
    # 우리 학교 편성표에 학점을 잘못 적은 곳을 찾으려는 검사다
    issues = []
    for name, grade, semester in plan:
        o = find_offering(name, grade, semester, offerings)
        c = courses_by_name.get(name)  # get: 그런 키가 없으면 오류 대신 None을 돌려준다
        if o is None or c is None:  # 개설표나 과목 목록에 없으면 비교할 수 없으니 건너뛴다
            continue
        # a <= b <= c는 b가 a 이상 c 이하인지 한 번에 본다
        if not c["credits_min"] <= o["school_credits"] <= c["credits_max"]:  # 범위 안이 아니면
            issues.append((WARNING, f"{josa(name, '은', '는')} {c['credits_min']}~{c['credits_max']}학점이어야 해요. "
                                    "편성표를 다시 확인해 주세요."))
    return issues


def check_order(plan, courses_by_name, offered):
    """계획, {이름: 과목} dict, 열리는 과목 이름 set을 받아 듣는 순서가 어긋난 곳을 [(수준, 메시지)] list로 돌려준다."""
    # prereq: 꼭 먼저 들어야 하는 선수 과목, before_hint: 보통 먼저 듣는 과목 (빈 글자면 없음)
    issues = []
    for name, grade, semester in plan:
        c = courses_by_name.get(name)
        if c is None:
            continue

        # 1) 선수 과목을 앞 학기에 듣지 않았다: 우리 학교에 열리면 주의, 열리지 않으면 안내
        prereq = c["prereq"]
        if prereq != "" and not taken_before(prereq, grade, semester, plan):
            if prereq in offered:
                issues.append((WARNING, f"{name} 전에 {josa(prereq, '을', '를')} 들어야 해요."))
            else:
                issues.append((INFO, f"{josa(name, '은', '는')} {josa(prereq, '을', '를')} 먼저 들어야 하는데, "
                                     f"우리 학교 개설표에 {josa(prereq, '이', '가')} 없어요. 선생님께 확인해 보세요."))

        # 2) 보통 먼저 듣는 과목을 앞 학기에 듣지 않았다: 꼭 지킬 규칙은 아니라서 안내만 한다
        hint = c["before_hint"]
        if hint != "" and not taken_before(hint, grade, semester, plan):
            if hint in offered:
                issues.append((INFO, f"{josa(name, '은', '는')} 보통 {hint} 다음에 들어요. "
                                     "괜찮은지 선생님께 확인해 보세요."))
            else:
                issues.append((INFO, f"{josa(name, '은', '는')} 보통 {hint} 다음에 듣는데, "
                                     f"우리 학교 개설표에 {josa(hint, '이', '가')} 없어요. 선생님께 확인해 보세요."))
    return issues


def check_recommendations(plan, rules, offered):
    """[F2] 계획, 대학·학과 규칙 list, 열리는 과목 이름 set을 받아 권장 과목이 빠진 곳을 [(수준, 메시지)] list로 돌려준다."""
    issues = []
    plan_names = {name for name, grade, semester in plan}  # set comprehension: 계획에 든 과목 이름만 모은다
    for rule in rules:
        # 1) 들어야 할 과목이 없거나(need 0) 계획에 이미 충분히 넣은 규칙은 건너뛴다
        need = need_count(rule)
        if need == 0:
            continue
        names = split_courses(rule)
        have = [n for n in names if n in plan_names]  # 규칙의 과목 중 계획에 넣은 것
        if len(have) >= need:
            continue

        # 2) 메시지에 쓸 낱말을 준비한다. level 칸이 빈 글자면 거짓으로 보므로 or 뒤의 '권장'을 쓴다
        level = rule["level"] or "권장"
        who = f"{rule['university']} {rule['major']}"
        can_take = [n for n in names if n in offered]  # 규칙의 과목 중 우리 학교에 열리는 것
        if len(can_take) < need:
            # 3) 우리 학교에 열리는 과목만으로는 채울 수 없다: 학교 밖에서 들을 방법을 안내한다
            if rule["rule"] == "at_least" and len(can_take) > 0:
                text = f"{who}의 {level} 과목은 {need}과목 이상인데 우리 학교에는 {len(can_take)}과목만 열려요."
            else:
                text = f"{josa(' 또는 '.join(names), '은', '는')} 우리 학교에 열리지 않아요."
            issues.append((INFO, text + " 공동교육과정이나 온라인 강좌로 들을 수 있는지 선생님께 확인해 보세요."))
            # 다 채울 수는 없어도, 우리 학교에 열리는 과목은 계획에 넣었는지 따로 본다
            not_planned = [n for n in can_take if n not in plan_names]
            if len(not_planned) > 0:
                courses_text = josa(", ".join(not_planned), "을", "를")
                issues.append((WARNING, f"{who}의 {level} 과목 중 우리 학교에 열리는 {courses_text} 계획에 넣지 않았어요."))
        else:  # 4) 우리 학교에 열리는데 계획에 넣지 않음
            text = f"{josa(rule_text(rule), '은', '는')} {who}의 {level} 과목이에요."
            if rule["rule"] == "at_least":
                text += f" 지금 {len(have)}과목이에요."
            issues.append((WARNING, text))
    return issues


def validate(plan, courses, offerings, groups, rules):
    """[F5] 계획과 자료를 받아 모든 검사를 하고 [(수준, 메시지)] list를 오류 → 주의 → 안내 순서로 돌려준다."""
    # 여러 검사가 함께 쓰는 dict·set을 한 번만 만든다
    courses_by_name = {c["name"]: c for c in courses}  # dict comprehension: {과목 이름: 과목 dict}
    offered = {o["name"] for o in offerings}  # set이라 여러 학기에 열리는 과목도 이름은 한 번만 들어간다

    # list + list는 두 list를 이어 붙인다. 다섯 검사의 결과를 한 list로 모은다
    issues = check_groups(plan, offerings, groups) + check_duplicates(plan)
    issues += check_credits(plan, courses_by_name, offerings) + check_order(plan, courses_by_name, offered)
    issues += check_recommendations(plan, rules, offered)

    # LEVELS.index(수준)은 오류 0, 주의 1, 안내 2이므로 이 번호가 작은 것부터 앞에 온다.
    # key=lambda ...는 줄 세울 기준값을 정하는 작은 함수다. sort는 번호가 같은 것끼리는 원래 순서를 그대로 둔다
    issues.sort(key=lambda issue: LEVELS.index(issue[0]))
    return issues


# ============================================================
# 6. 엑셀 저장 [F6]: 계획을 엑셀 파일로 만든다. 서버에는 아무것도 남기지 않는다
# ============================================================

def save_plan(plan, issues, file, choice=None):
    """[F6] 계획, 검사 결과, 고른 계열·학과·대학 dict(choice, 없어도 됨)를 받아 엑셀 파일(file)로 저장한다."""
    # file은 파일 경로이거나 BytesIO(메모리 안에 만드는 파일)다. 학생 이름은 저장하지 않는다
    wb = Workbook()  # 새 엑셀 파일. 처음부터 빈 시트 하나(wb.active)가 들어 있다

    # 1) '계획' 시트: 첫 줄은 열 이름, 다음 줄부터 과목 하나에 한 줄
    sheet = wb.active
    sheet.title = PLAN_SHEET
    sheet.append(PLAN_HEADER)  # append: list 하나를 시트 맨 아래에 한 줄로 붙인다
    for name, grade, semester in plan:
        sheet.append([grade, semester, name])

    # 2) '검사 결과' 시트
    sheet = wb.create_sheet(ISSUE_SHEET)
    sheet.append(["수준", "메시지"])
    for level, message in issues:
        sheet.append([level, message])

    # 3) '선택' 시트: choice가 None이나 빈 dict면 거짓이라 만들지 않는다
    if choice:
        sheet = wb.create_sheet(CHOICE_SHEET)
        for key, value in choice.items():  # items(): dict의 (키, 값) 쌍을 하나씩 꺼낸다
            sheet.append([key, value])

    wb.save(file)


# ============================================================
# 7. 화면 공통: 여러 화면이 같이 쓰는 Streamlit 코드 (데이터 읽기, 사이드바, 화면 머리, 다음 단계 버튼)
# ============================================================
# Streamlit은 버튼을 누르거나 값을 고를 때마다 이 파일 전체를 위에서 아래로 다시 실행한다.
# 그래서 다음 실행까지 기억해야 하는 값은 st.session_state(dict처럼 쓰는 저장 공간)에 넣어 둔다.

PAGES = {}  # 화면 이름 → st.Page. 12. 시작에서 채운다 (다른 화면으로 가는 버튼·링크에 쓴다)


def load_data_or_stop():
    """CSV 5개를 읽은 data dict를 돌려준다. 파일이 없거나 숫자가 틀리면 화면에 오류를 보이고 멈춘다."""
    # 다시 실행될 때마다 CSV를 새로 읽지 않도록, 읽은 결과와 CSV 파일들을 고친 시각을 session_state에 같이 둔다.
    # 시각 list가 달라졌을 때(처음 열었거나 CSV를 고쳤을 때)만 다시 읽는다
    paths = [os.path.join(DATA_FOLDER, name) for name in DATA_FILES.values()]
    version = [os.path.getmtime(p) for p in paths if os.path.exists(p)]  # getmtime: 파일을 마지막으로 고친 시각
    if st.session_state.get("data_version") != version:  # get: 키가 없으면(처음 열었으면) None
        try:
            st.session_state["data"] = load_all(DATA_FOLDER)
        except (FileNotFoundError, ValueError) as error:  # 파일이 없거나 값이 틀리면 load_all이 내는 오류
            st.error(f"데이터를 읽지 못했어요. {error}")
            st.stop()  # 이번 실행을 여기서 멈춘다. 아래 코드는 실행하지 않는다
        st.session_state["data_version"] = version
    return st.session_state["data"]


def keep_in_options(key, options):
    """위젯 key와 목록을 받아, 저장된 값이 목록에 없으면(예: 계열을 바꿈) 첫 번째 항목으로 바꿔 둔다."""
    # 위젯을 그리기 전에 st.session_state[key]를 바꾸면 위젯이 그 값을 고른 채로 나타난다
    value = st.session_state.get(key)  # get: 처음 열어서 값이 없으면 None
    if value not in options:
        value = options[0]
    # 목록 안에 있던 값도 매번 다시 넣는다. 빼면 st.switch_page로 화면을 옮길 때 예전 값으로 돌아가는 일이 생긴다
    st.session_state[key] = value


def sidebar_choice(data):
    """[F1] data를 받아 사이드바에서 계열 → 학과 → 목표 대학을 고르게 하고, 고른 값을 dict로 돌려준다."""
    st.sidebar.header("1단계 · 내 진로 고르기")

    # 위젯의 key: 고른 값이 st.session_state[key]에 저장되어 다음 실행에도 남는다.
    # pills는 버튼 모양 선택지, required=True는 고른 것을 해제할 수 없게 한다
    fields = field_names(data["majors"])
    keep_in_options("field", fields)
    field = st.sidebar.pills("어떤 분야로 진학하고 싶나요?", fields, key="field", required=True)

    # 학과는 고른 계열의 학과만, 대학은 고른 학과의 권장 과목 자료가 있는 대학만 목록에 넣는다
    majors = [m["name"] for m in data["majors"] if m["field"] == field]
    keep_in_options("major", majors)
    major = st.sidebar.selectbox("학과", majors, key="major")

    universities = universities_for(major, data["recs"])
    keep_in_options("university", universities)
    university = st.sidebar.selectbox("목표 대학", universities, key="university")

    st.sidebar.caption("추천은 참고용이에요. 최종 선택은 선생님과 상의해서 정하세요.")
    return {"계열": field, "학과": major, "대학": university}


def current_choice():
    """run_web이 사이드바에서 받아 st.session_state["choice"]에 저장해 둔 계열·학과·대학 dict를 돌려준다."""
    return st.session_state["choice"]


def choice_badges(choice):
    """진로 dict를 받아 계열·학과·대학을 회색 배지 3개로 보여 줄 Markdown 글자를 돌려준다."""
    # ':gray-badge[글자]'는 Streamlit Markdown에서 회색 배지를 그리는 문법이다
    return f":gray-badge[{choice['계열']}] :gray-badge[{choice['학과']}] :gray-badge[{choice['대학']}]"


def page_top(step, title, icon, todo):
    """단계 번호·제목·아이콘·할 일을 받아 화면 맨 위(몇 단계, 제목, 지금 고른 진로, 할 일 한 줄)를 그린다."""
    st.caption(f"{step}단계 / 4단계")  # f-string: {} 자리에 변수 값이 들어간다 (예: '2단계 / 4단계')
    st.title(title, icon=icon)
    st.markdown(choice_badges(current_choice()))
    st.write(todo)


def next_step(page_name, label):
    """화면 이름과 버튼 글자를 받아 화면 끝에 '다음에 할 일' 버튼을 둔다. 누르면 그 화면으로 간다."""
    # 버튼을 누르면 파일이 다시 실행되고, st.button은 그 실행에서만 True를 돌려준다.
    # st.switch_page는 PAGES에 있는 그 화면으로 옮겨 다시 실행한다
    if st.button(label, type="primary", icon=":material/arrow_forward:"):
        st.switch_page(PAGES[page_name])


# ============================================================
# 8. 화면 1: 홈 (앱 소개, 지금 고른 진로, 사용 순서)
# ============================================================

def home_page():
    """홈 화면을 그린다: 앱 소개, 지금 고른 진로, 사용 순서 카드 4개, 데이터 출처."""
    data = load_data_or_stop()
    choice = current_choice()

    st.title("고교학점제 과목 선택 내비게이터", icon=":material/explore:")
    # 괄호 안에서 줄을 바꿔 이어 쓴 문자열 두 개는 하나로 붙는다
    st.write("희망 학과와 목표 대학을 고르면, 광주 광덕고 편성표 안에서 2·3학년 선택과목 계획을 "
             "짜 주고 선택 규칙도 검사해 줘요.")

    # 추천 과목 화면과 같은 수: 필수 과목만으로 채워지는 규칙은 세지 않는다
    rules = without_required(find_rules(choice["학과"], choice["대학"], data["recs"]),
                             required_names(data["offerings"]))
    st.markdown(f"**지금 고른 진로** {choice_badges(choice)} · 권장 과목 규칙 {len(rules)}개")

    # 사용 순서: 단계마다 카드 하나. page가 None이면 이 화면 밖(사이드바, 저장 칸)에서 하는 일이라 링크가 없다
    steps = [
        {"title": "진로 고르기", "text": "왼쪽에서 계열 → 학과 → 목표 대학을 골라요.", "page": None},
        {"title": "추천 과목 보기", "text": "대학이 권하는 과목이 우리 학교에 열리는지 봐요.", "page": "추천 과목"},
        {"title": "내 계획 고치기", "text": "추천대로 채운 계획을 보고 직접 고쳐요.", "page": "내 이수 계획"},
        {"title": "엑셀로 저장하기", "text": "3단계 화면 맨 아래에서 저장해 선생님께 보여 드려요.", "page": None},
    ]
    cards = st.columns(len(steps))  # 나란히 놓인 칸 4개의 list
    for i, step in enumerate(steps):  # enumerate: 번호 i(0부터)와 항목 step을 함께 꺼낸다
        # with 안에서 그린 것은 i번째 칸의 테두리 상자에 들어간다. height="stretch": 상자가 칸 높이를 꽉 채운다
        with cards[i].container(border=True, height="stretch"):
            st.markdown(f"**{i + 1}단계 · {step['title']}**")
            st.write(step["text"])
            if step["page"] is not None:
                st.page_link(PAGES[step["page"]], label="바로 가기", icon=":material/arrow_forward:")

    st.info("대학이 발표한 권장 과목 자료로 만든 추천이에요. 최종 선택은 담임·진로 선생님과 상의해서 정하세요.",
            title="추천은 참고용이에요", icon=":material/lightbulb:")

    next_step("추천 과목", "시작하기: 추천 과목 보러 가기")

    # 접었다 펼 수 있는 칸. 대학 수는 set으로 센다 (중괄호 comprehension은 set을 만들고, 같은 대학은 한 번만 들어간다)
    with st.expander("데이터 출처와 개인정보", icon=":material/info:"):
        universities = {r["university"] for r in data["recs"]}
        st.write("학생 이름이나 계획은 서버에 저장하지 않아요. 저장한 엑셀 파일은 내 기기에만 남아요.")
        st.write("데이터: 2022 개정 교육과정 과목표, 광덕고 2026학년도 시간표와 3학년 선택과목 안내문, "
                 f"{len(universities)}개 대학 권장 과목 자료(확인 날짜는 '추천 과목' 화면에 있어요).")


# ============================================================
# 9. 화면 2: 추천 과목 [F2] (대학 권장 과목과 개설 여부, 추천 점수 순위, 과목 검색)
# ============================================================

def open_mark(name, offerings):
    """과목 이름과 개설표를 받아, 열리면 '○ 열리는 때', 안 열리면 '× 우리 학교에 없어요'를 돌려준다."""
    text = offered_text(name, offerings)  # 예: '2학년 1학기, 2학년 2학기' 또는 '미개설'
    if text == "미개설":
        return "× 우리 학교에 없어요"
    return "○ " + text


def recommend_page():
    """추천 과목 화면을 그린다: 탭 3개(대학이 권하는 과목, 추천 점수 순위, 과목 찾기)와 다음 단계 버튼."""
    data = load_data_or_stop()
    choice = current_choice()
    major, university = choice["학과"], choice["대학"]  # 오른쪽 두 값을 왼쪽 두 변수에 차례로 넣는다
    offerings = data["offerings"]

    page_top(2, "추천 과목", ":material/star:", "대학이 권하는 과목을 보고, 우리 학교에서 언제 들을 수 있는지 확인해요.")
    scores = score_courses(major, university, data["majors"], data["recs"], data["courses"])  # {과목 이름: 점수}
    # 탭 3개를 만든다. 'with 탭:' 안에서 그린 것은 그 탭 안에 들어간다
    tab1, tab2, tab3 = st.tabs(["대학이 권하는 과목", "추천 점수 순위", "과목 찾기"])

    # 1) 대학이 발표한 권장 과목: 한 과목짜리 규칙은 표 하나로, 여러 과목 중 고르는 규칙은 카드로.
    #    모두 듣는 필수 과목(공통·지정)은 저절로 채워지므로 빼고 보여 준다
    with tab1:
        required = required_names(offerings)  # 필수 과목 이름 set
        all_rules = find_rules(major, university, data["recs"])
        shown = without_required(all_rules, required)  # [(규칙, 남은 과목 list, 더 들어야 할 수), ...]
        # 규칙에 나오지만 필수 과목이라 뺀 과목 (같은 이름은 한 번만, 나온 순서대로)
        hidden = []
        for rule in all_rules:
            for name in split_courses(rule):
                if name in required and name not in hidden:
                    hidden.append(name)

        # 맨 위 안내 하나: 권장 과목이 없음 / 모두 필수 과목 / 배지 뜻
        if len(needed_rules(all_rules)) == 0:  # '따로 정한 권장 과목 없음'만 있거나 자료가 없음
            title = "이 대학·학과는 따로 정한 권장 과목이 없어요"
            if university == NO_UNIVERSITY:  # majors.csv에만 있고 권장 과목 자료가 없는 학과
                title = "이 학과는 아직 권장 과목 자료가 없어요"
            st.info("대신 계열에 맞는 교과로 점수를 매겼어요. 대학 입학처 안내도 확인해 보세요.",
                    title=title, icon=":material/search_off:")
        elif len(shown) == 0:
            st.success("학교에서 모두 듣는 필수 과목만으로 채워져서, 따로 챙길 과목은 없어요.",
                       title="이 대학·학과가 권하는 과목은 모두 필수 과목이에요", icon=":material/check_circle:")
        else:
            st.markdown(":violet-badge[핵심] 꼭 듣기를 권하는 과목 · :blue-badge[권장] 되도록 듣기를 권하는 과목")
        if len(hidden) > 0:
            st.caption(f"모두 듣는 필수 과목({', '.join(hidden)})은 저절로 채워져서 목록에서 뺐어요.")

        # 한 과목짜리 규칙(필수 과목을 빼니 한 과목만 남은 규칙도)은 표 하나에 한 줄씩 모은다
        singles = []
        for rule, names, need in shown:  # 튜플 하나의 세 값을 세 변수로 나눠 받는다
            if len(names) == 1:
                singles.append({"과목": names[0], "구분": rule["level"], "우리 학교": open_mark(names[0], offerings),
                                "확인 날짜": rule["checked"], "원문": rule["source"], "메모": rule["note"]})
        if len(singles) > 0:
            st.markdown(f"**한 과목씩 정한 권장 과목 · {len(singles)}과목**")
            # height="content": 스크롤 없이 모든 줄을 보여 준다. column_config: 열마다 보이는 모양을 정한다
            st.dataframe(pd.DataFrame(singles), hide_index=True, height="content", column_config={
                "구분": st.column_config.TextColumn("구분", help="핵심: 꼭 듣기를 권해요. 권장: 되도록 들으면 좋아요."),
                "원문": st.column_config.LinkColumn("원문", display_text="보기")})  # 긴 주소 대신 '보기' 링크

        # 여러 과목 중 고르는 규칙은 카드 하나씩. 우리 학교에서 다 채울 수 없는 규칙 수(cannot)도 센다
        cannot = 0
        for rule, names, need in shown:
            missing = [n for n in names if offered_text(n, offerings) == "미개설"]  # 우리 학교에 없는 과목
            if len(names) - len(missing) < need:  # 열리는 과목을 다 들어도 모자란다
                cannot += 1
            if len(names) == 1:  # 한 과목짜리는 위 표에 이미 넣었다
                continue
            level = rule["level"]
            with st.container(border=True):  # 테두리 상자 하나 = 카드 하나
                # LEVEL_COLOR.get(level, 'gray'): 핵심은 보라, 권장은 파랑, dict에 없는 값이면 회색
                st.markdown(f":{LEVEL_COLOR.get(level, 'gray')}-badge[{level}] "
                            f"**아래 {len(names)}과목 중 {need}과목 이상**")
                # 열리는 과목은 열리는 때와 함께 한 줄씩, 없는 과목은 마지막 한 줄에 모은다
                lines = [f"- {n} · {open_mark(n, offerings)}" for n in names if n not in missing]
                if len(missing) > 0:
                    lines.append(f"- × 우리 학교에 없어요: {', '.join(missing)}")
                st.markdown("\n".join(lines))  # '- '로 시작하는 줄들은 글머리 기호 목록이 된다
                # [글자](주소)는 Markdown 링크. 메모가 빈 글자면 or가 None을 골라 도움말(?)을 달지 않는다
                st.caption(f"확인 날짜 {rule['checked']} · [입학처 원문 보기]({rule['source']})",
                           help=rule["note"] or None)

        if cannot > 0:
            st.info("공동교육과정이나 온라인 강좌로 들을 수 있는지 선생님께 확인해 보세요.",
                    title="우리 학교에서 다 채울 수 없는 규칙이 있어요", icon=":material/school:")
        st.caption("대학 자료는 바뀔 수 있어요. 지원하기 전에 대학 입학처 원문을 꼭 확인해요.")

    # 2) 추천 점수가 높은 우리 학교 선택과목
    with tab2:
        st.caption("점수가 높을수록 지금 고른 진로에 잘 맞아요. 강력 추천 = 3점 이상 · 추천 = 2점 · 참고 = 1점")
        st.caption(f"점수 매기는 법: 핵심 +{SCORE_CORE}, 권장 +{SCORE_RECOMMEND}, 같은 계열 다른 학과의 권장 "
                   f"+{SCORE_SAME_FIELD}, 계열과 맞는 교과 +{SCORE_FIELD_AREA}")
        rows = []
        for o in offerings:
            # 선택군이 있는(골라서 듣는) 과목 중 점수가 있는 것만. get(이름, 0): 점수가 없는 과목은 0점으로 본다
            if o["group_id"] != "" and scores.get(o["name"], 0) > 0:
                rows.append({"과목": o["name"], "열리는 때": f"{o['grade']}학년 {o['semester']}학기",
                             "추천": score_word(scores[o["name"]]), "점수": scores[o["name"]], "선택군": o["group_id"]})
        rows.sort(key=lambda r: r["점수"], reverse=True)  # key: 줄(r)마다 '점수' 값으로 비교, reverse=True: 큰 것부터
        top = 1  # 막대 끝 = 가장 높은 점수. 표가 비어 있으면 1
        if len(rows) > 0:
            top = rows[0]["점수"]  # 점수가 높은 순서로 정렬했으니 첫 줄이 가장 높다
        # ProgressColumn: 점수를 0~top 사이 막대로 그린다. format="%d점": 정수 뒤에 '점'을 붙여 보여 준다
        st.dataframe(pd.DataFrame(rows), hide_index=True, column_config={
            "점수": st.column_config.ProgressColumn("추천 점수", min_value=0, max_value=top, format="%d점")})

    # 3) 과목 이름 검색
    with tab3:
        keyword = st.text_input("과목 이름을 입력하세요", placeholder="예: 통계, 물리, 윤리")
        if keyword.strip() != "":  # strip(): 앞뒤 빈칸을 없앤다. 빈칸만 쳤거나 아무것도 안 쳤으면 찾지 않는다
            found = search_courses(keyword, data["courses"])
            if len(found) == 0:
                st.warning("더 짧은 말로 찾아보세요. 예: '확률통계' 대신 '확률'",
                           title=f"'{keyword}'이(가) 들어간 과목이 없어요")
            else:
                st.caption(f"{len(found)}개 과목을 찾았어요.")
                rows = []
                for c in found:
                    rows.append({"과목": c["name"], "교과": c["area"], "유형": c["type"],
                                 "우리 학교": open_mark(c["name"], offerings), "추천 점수": scores.get(c["name"], 0)})
                st.dataframe(pd.DataFrame(rows), hide_index=True)

    next_step("내 이수 계획", "다음: 내 이수 계획 짜러 가기")


# ============================================================
# 10. 화면 3: 내 이수 계획 [F3~F6] (자동 계획, 직접 수정, 규칙 검사, 엑셀 저장)
# ============================================================
# 선택군마다 고르기 칸(multiselect)을 하나씩 둔다. 칸의 key가 'pick_선택군'이라서
# 칸에서 고른 과목 list는 st.session_state['pick_G2-1A']처럼 저장되어 다음 실행에도 남는다.

def widget_key(group):
    """선택군 dict를 받아 그 선택군 고르기 칸의 key를 돌려준다. 예: 'pick_G2-1A'"""
    return f"pick_{group['group_id']}"


def show_plan_in_widgets(plan, groups, offerings):
    """계획 list를 받아 선택군마다 고르기 칸에 채워 넣고, 계획도 session_state에 저장한다."""
    # keep_in_options와 같은 방법: 칸을 그리기 전에 key 값을 바꿔 두면, 칸이 그 과목들을 고른 채로 나타난다
    for g in groups:
        st.session_state[widget_key(g)] = picked_in_group(plan, g, offerings)
    st.session_state["plan"] = plan


def plan_from_widgets(groups, offerings):
    """고르기 칸에 지금 들어 있는 과목에 모두 듣는 과목을 더해 계획 list로 돌려준다."""
    plan = fixed_courses(offerings)
    for g in groups:
        for name in st.session_state.get(widget_key(g), []):  # 칸 값이 아직 없으면 빈 list
            plan.append((name, g["grade"], g["semester"]))
    return plan


def plan_page():
    """[F3~F6] 화면 3: 계획을 칸에 채워 보여 주고, 직접 고치고, 검사하고, 엑셀로 저장하게 한다."""
    data = load_data_or_stop()
    choice = current_choice()
    courses, offerings, groups = data["courses"], data["offerings"], data["groups"]
    rules = find_rules(choice["학과"], choice["대학"], data["recs"])
    scores = score_courses(choice["학과"], choice["대학"], data["majors"], data["recs"], courses)
    target = (choice["학과"], choice["대학"])  # 지금 고른 진로. 튜플끼리 != 로 비교해 진로가 바뀌었는지 안다

    def course_label(name):
        """과목 이름을 받아 고르기 칸에 보일 글자를 돌려준다. 예: '기하 · 강력 추천'"""
        word = score_word(scores.get(name, 0))  # get: 점수가 없는 과목은 0점으로 본다
        if word == "":  # 붙일 말이 없으면(0점) 이름만
            return name
        return f"{name} · {word}"

    page_top(3, "내 이수 계획", ":material/event_note:", "추천대로 채워 둔 계획이에요. 칸마다 과목 수를 맞추고, 검사 결과를 본 뒤 저장해요.")

    # 고르기 칸을 무엇으로 채울지 정한다. 처음 열었으면 추천대로 짠 계획으로 채운다.
    # 다른 화면에 다녀오면 Streamlit이 칸 값을 지우고, 이 화면에서 진로를 바꾸면 칸 글자('기하 · 추천')가 바뀌어
    # 고른 과목이 사라진다. 두 경우 모두 저장해 둔 지난 계획으로 칸을 다시 채운다
    # 선택군마다 '칸 값이 없나?'(True/False)를 모은 list. any는 그 안에 True가 하나라도 있으면 True다
    left_page = any([widget_key(g) not in st.session_state for g in groups])
    changed = st.session_state.get("shown_for", target) != target  # 지난번에 칸을 그린 진로와 다르면 True (기록이 없으면 False)
    if "plan" not in st.session_state:
        show_plan_in_widgets(build_plan(scores, courses, offerings, groups), groups, offerings)
        st.session_state["plan_for"] = target  # 이 계획을 어느 진로에 맞춰 짰는지 기록
    elif left_page or changed:
        show_plan_in_widgets(st.session_state["plan"], groups, offerings)
    st.session_state["shown_for"] = target

    # 도구 줄: 지금 학년 · 추천대로 다시 짜기 (horizontal=True: 안의 위젯을 가로로 놓는다)
    with st.container(border=True, horizontal=True, vertical_alignment="center"):
        grade_now = st.radio("지금 학년", ["1학년", "2학년"], horizontal=True, key="grade_now",
                             captions=["모든 칸을 새로 채워요", "2학년 칸을 들은 과목으로 고친 뒤 눌러요"])
        # 값1 if 조건 else 값2: 조건이 참이면 값1, 거짓이면 값2가 된다
        label = "추천대로 다시 짜기" if grade_now == "1학년" else "2학년은 두고 빈자리 채우기"
        # clicked: 이번 실행이 이 버튼을 눌러서 시작됐으면 True (st.button은 7. 화면 공통의 next_step 참고)
        clicked = st.button(label, icon=":material/auto_fix_high:", help="2학년이면 먼저 아래 2학년 칸을 실제로 들은 과목으로 고친 뒤 눌러요.")

    # [F3] 추천대로 다시 짜기. 2학년이면 지금 칸에 고른 2학년 과목은 들은 과목으로 보고 두고, 빈자리와 3학년을 채운다
    if clicked:
        taken = []
        if grade_now == "2학년":
            fixed = fixed_courses(offerings)
            # p는 (과목, 학년, 학기). p[1]은 학년. 모두 듣는 과목은 build_plan이 알아서 넣으므로 뺀다
            taken = [p for p in plan_from_widgets(groups, offerings) if p[1] == 2 and p not in fixed]
        show_plan_in_widgets(build_plan(scores, courses, offerings, groups, taken), groups, offerings)
        st.session_state["plan_for"] = target
        st.toast("추천 점수대로 계획을 짰어요. 아래에서 직접 고칠 수 있어요.", icon=":material/check_circle:")
    elif st.session_state.get("plan_for", target) != target:  # 계획을 짠 뒤에 진로를 바꿨으면 알린다
        st.info(f"새 진로에 맞추려면 위의 '{label}'를 눌러요.", title="학과나 대학을 바꿨어요")

    # 고르기 칸의 값은 칸을 다시 그리기 전에 이미 session_state에 들어 있다.
    # 그래서 계획과 검사 결과를 먼저 만들고, 요약을 위에서부터 차례대로 그린다
    plan = plan_from_widgets(groups, offerings)
    st.session_state["plan"] = plan  # 다른 화면에 다녀와도 이 계획으로 칸을 다시 채운다
    issues = validate(plan, courses, offerings, groups, rules)
    by_level = {ERROR: [], WARNING: [], INFO: []}  # 수준 → '- 메시지' 줄 list. 아래에서 줄바꿈(\n)으로 이어 목록으로 보인다
    for level, message in issues:
        by_level[level].append("- " + message)
    n_error, n_warning, n_info = len(by_level[ERROR]), len(by_level[WARNING]), len(by_level[INFO])

    # 맨 위 요약에 쓸 수. done: 칸에 고른 과목 수가 정해진 수(pick_count)와 같은 선택군만 모아 센다
    done = len([g for g in groups if len(st.session_state.get(widget_key(g), [])) == g["pick_count"]])
    credits = 0  # 계획에는 1학년 공통 과목도 있으므로 2·3학년 학기만 더한다
    for grade, semester in PLAN_TERMS:
        credits += total_credits(term_plan(plan, grade, semester), offerings)
    # 우리 학교에 열리는데 아직 못 채운 대학 권장 과목 규칙 수 = 권장 과목 검사의 '주의' 수 (검사 함수를 다시 쓴다)
    rec_issues = check_recommendations(plan, rules, {o["name"] for o in offerings})  # set: 우리 학교에 열리는 과목 이름
    rec_missing = len([level for level, message in rec_issues if level == WARNING])

    # 맨 위 요약: 다 골랐나? 학점은? 빠진 권장 과목은? 고칠 것은? (columns(4): 가로로 4칸을 나눈다)
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("다 고른 선택군", f"{done} / {len(groups)}", border=True)
    c2.metric("2·3학년 학점", f"{credits}학점", border=True)
    c3.metric("못 채운 권장 규칙", f"{rec_missing}개", border=True, help="우리 학교에 열리는데 아직 못 채운 대학 권장 과목 규칙 수예요.")
    c4.metric("꼭 고칠 것 (오류)", f"{n_error}개", border=True)
    # 가장 급한 것 하나만 알린다: 오류 → 주의 → 모두 통과
    if n_error > 0:
        st.error(f"오류 {n_error}개를 고쳐야 해요. 맨 아래 '검사 결과'를 봐요.", title="계획에 고칠 곳이 있어요", icon=":material/error:")
    elif n_warning > 0:
        st.warning(f"주의 {n_warning}개를 확인해 보세요. 맨 아래 '검사 결과'에 있어요.", title="거의 다 됐어요", icon=":material/warning:")
    else:
        st.success("맨 아래에서 엑셀로 저장해요.", title="규칙을 모두 지켰어요", icon=":material/check_circle:")

    # [F4] 학기마다 테두리 상자 하나. 그 학기의 선택군마다 고르기 칸을 두고 과목을 바꾼다
    for grade, semester in PLAN_TERMS:
        term = term_plan(plan, grade, semester)
        with st.container(border=True):
            st.subheader(f"{grade}학년 {semester}학기 · {len(term)}과목 · {total_credits(term, offerings)}학점")
            for g in groups:
                if (g["grade"], g["semester"]) != (grade, semester):  # 이 학기의 선택군이 아니면 건너뛴다
                    continue
                # 칸 이름 끝에 몇 과목 더(덜) 고를지 붙인다. :green[...]은 초록 글자, :material/이름:은 아이콘
                need = g["pick_count"]
                picked = len(st.session_state.get(widget_key(g), []))
                if picked == need:
                    mark = ":green[:material/check_circle: 다 골랐어요]"
                elif picked < need:
                    mark = f":blue[:material/pending: {need - picked}과목 더 골라요]"
                else:
                    mark = f":red[:material/error: {picked - need}과목 빼요]"
                # format_func(course_label)는 칸에 보이는 글자만 바꾸고, 저장되는 값은 그대로 과목 이름이다
                st.multiselect(f"{g['group_id']}군 · {need}과목 중 {picked}과목 · {mark}",
                               group_options(g["group_id"], offerings), key=widget_key(g), help=g["memo"],
                               placeholder="과목을 골라 주세요", format_func=course_label, wrap=True,
                               select_all=False)  # 'Select all'(한꺼번에 고르기)을 숨긴다

    with st.expander("모두 듣는 공통·지정 과목 보기"):  # expander: 눌러야 펼쳐지는 접힌 상자
        fixed = [{"학년": g, "학기": s, "과목": n} for n, g, s in fixed_courses(offerings)]  # 과목마다 표의 한 줄
        st.dataframe(pd.DataFrame(fixed), hide_index=True)

    # [F5] 규칙 검사: 수준별로 한 상자씩. 안내는 꼭 고칠 필요가 없어서 접어 둔다
    st.subheader("검사 결과", anchor="check")  # anchor: 이 제목으로 바로 가는 주소 이름(#check)
    if len(issues) == 0:
        st.caption("고칠 것이 없어요.")
    if n_error > 0:
        st.error("\n".join(by_level[ERROR]), title=f"오류 {n_error}개 · 꼭 고쳐요", icon=":material/error:")
    if n_warning > 0:
        st.warning("\n".join(by_level[WARNING]), title=f"주의 {n_warning}개 · 확인해 보세요", icon=":material/warning:")
    if n_info > 0:
        with st.expander(f"안내 {n_info}개 · 꼭 고치지 않아도 돼요", icon=":material/info:"):
            st.markdown("\n".join(by_level[INFO]))

    # [F6] 엑셀 파일로 저장 (학생 기기에 내려받기, 서버에는 남지 않음)
    def excel_bytes():
        """이 화면의 plan·issues·choice로 엑셀 파일을 만들어 그 내용(bytes)을 돌려준다."""
        buffer = BytesIO()  # 디스크가 아니라 메모리에 만드는 빈 파일
        save_plan(plan, issues, buffer, choice)  # 안쪽 함수라서 plan_page의 변수를 그대로 쓸 수 있다
        return buffer.getvalue()

    with st.container(border=True):
        st.subheader("4단계 · 엑셀로 저장하기")
        st.write("저장한 파일을 담임·진로 선생님께 보여 드려요.")
        # 함수를 괄호 없이 넘기면 저장 버튼을 누를 때만 실행되어, 과목을 바꿀 때마다 파일을 만들지 않는다
        st.download_button("엑셀 파일로 저장", excel_bytes, file_name="내_이수계획.xlsx", type="primary",
                           icon=":material/download:",
                           mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        st.caption("파일은 내 기기에만 남고, 서버에는 저장하지 않아요.")

# ============================================================
# 11. 시작: 'streamlit run app.py'로 켠다
#     (테스트가 이 파일을 import할 때는 __name__이 "app"이라 아무것도 실행하지 않는다)
# ============================================================

def run_web():
    """사이드바(화면 목록과 진로 고르기)를 그리고, 고른 화면을 실행한다."""
    # 누르거나 고를 때마다 이 파일 전체가 다시 실행되므로(7. 화면 공통 참고) run_web도 매번 다시 불린다
    st.set_page_config(page_title="과목 선택 내비게이터", page_icon="🧭", layout="wide")  # 브라우저 탭 제목·아이콘, 넓은 화면

    # 화면 3개를 PAGES에 넣는다. st.Page(함수, ...): 그 화면을 열면 그 함수를 실행한다.
    # url_path는 주소 끝에 붙는 이름이다 (예: .../추천과목). default=True인 홈이 처음 여는 화면이다
    PAGES["홈"] = st.Page(home_page, title="홈", icon=":material/home:", default=True)
    PAGES["추천 과목"] = st.Page(recommend_page, title="추천 과목", icon=":material/star:", url_path="추천과목")
    PAGES["내 이수 계획"] = st.Page(plan_page, title="내 이수 계획", icon=":material/event_note:",
                                url_path="내_이수계획")
    page = st.navigation(list(PAGES.values()))  # 사이드바에 화면 목록을 그리고, 지금 열린 화면을 돌려준다

    # [F1] 모든 화면에서 같은 사이드바를 쓴다. 고른 진로는 session_state에 두어 각 화면이 꺼내 쓴다
    st.session_state["choice"] = sidebar_choice(load_data_or_stop())

    # Streamlit은 화면에 없는 위젯의 값을 지우므로, 다른 화면에 다녀와도 '지금 학년'을 기억하게 다시 저장한다
    # (위젯 값을 코드에서 직접 넣은 값으로 바꿔 두면 Streamlit이 지우지 않는다)
    if "grade_now" in st.session_state:
        st.session_state["grade_now"] = st.session_state["grade_now"]

    page.run()  # 사이드바에서 고른 화면의 함수(home_page, recommend_page, plan_page 가운데 하나)를 실행한다


if __name__ == "__main__":  # 이 파일을 직접 실행했을 때만 True다 (테스트가 import하면 False)
    if runtime.exists():  # streamlit run app.py로 켰을 때 (Streamlit 실행기 안에서 돌고 있으면 True)
        run_web()
    else:                 # python app.py로 켰을 때는 켜는 방법만 알려 준다
        print("이 앱은 웹 앱이에요. 'streamlit run app.py'로 켜 주세요.")
