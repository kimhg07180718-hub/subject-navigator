"""[데이터] CSV 파일을 읽어 list·dict로 만든다."""
import csv
import os

from core.config import BLANK_AS_ZERO, DATA_FILES, NUMBER_COLUMNS


def load_csv(path):
    """CSV 파일 하나를 읽어 '줄마다 dict'인 list로 돌려준다. 각 줄에 파일의 줄 번호(line)도 적어 둔다."""
    rows = []
    with open(path, encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            row["line"] = reader.line_num  # 빈 줄이 있어도 실제 줄 번호
            rows.append(row)
    return rows


def to_numbers(rows, columns, file_name, blank_as_zero=False):
    """rows의 columns 열을 정수로 바꿔 돌려준다. 숫자가 아니면 몇 번째 줄인지 알려 준다."""
    for row in rows:
        for col in columns:
            value = row.get(col)
            if blank_as_zero and (value is None or value.strip() == ""):
                row[col] = 0
                continue
            try:
                row[col] = int(value)
            except (TypeError, ValueError):
                raise ValueError(f"{file_name} {row['line']}번째 줄의 {col} 칸이 숫자가 아니에요: '{value}'")
    return rows


def check_names(data):
    """개설표와 권장 과목의 과목 이름이 모두 과목표(courses.csv)에 있는지 확인한다. 오타를 일찍 찾기 위해서다."""
    names = {c["name"] for c in data["courses"]}
    for o in data["offerings"]:
        if o["name"] not in names:
            raise ValueError(f"offerings.csv {o['line']}번째 줄의 과목 '{o['name']}'이(가) courses.csv에 없어요.")
    for r in data["recs"]:
        for name in r["courses"].split("|"):
            if name != "" and name not in names:
                raise ValueError(f"recommendations.csv {r['line']}번째 줄의 과목 '{name}'이(가) courses.csv에 없어요.")


def check_repeats(data):
    """같은 선택군이나 같은 (과목, 학년, 학기)가 두 번 들어가지 않았는지, 선택군 이름이 맞는지 확인한다."""
    group_ids = set()
    for g in data["groups"]:
        if g["group_id"] in group_ids:
            raise ValueError(f"groups.csv {g['line']}번째 줄의 선택군 '{g['group_id']}'이(가) 앞에도 있어요.")
        group_ids.add(g["group_id"])

    seen = set()
    for o in data["offerings"]:
        if o["group_id"] != "" and o["group_id"] not in group_ids:
            raise ValueError(f"offerings.csv {o['line']}번째 줄의 선택군 '{o['group_id']}'이(가) groups.csv에 없어요.")
        key = (o["name"], o["grade"], o["semester"])
        if key in seen:
            raise ValueError(f"offerings.csv {o['line']}번째 줄의 '{o['name']}'"
                             f"({o['grade']}학년 {o['semester']}학기)이(가) 앞에도 있어요.")
        seen.add(key)


def load_all(folder):
    """data 폴더의 CSV 5개를 읽어 dict 하나에 담아 돌려준다."""
    data = {}
    for key, file_name in DATA_FILES.items():
        try:
            rows = load_csv(os.path.join(folder, file_name))
        except FileNotFoundError:
            raise FileNotFoundError(f"{file_name} 파일이 없어요. data 폴더를 확인해 주세요.")
        except UnicodeDecodeError:
            raise ValueError(f"{file_name}의 글자를 읽을 수 없어요. 엑셀에서 'CSV UTF-8' 형식으로 다시 저장해 주세요.")
        if key in NUMBER_COLUMNS:
            rows = to_numbers(rows, NUMBER_COLUMNS[key], file_name)
        if key in BLANK_AS_ZERO:
            rows = to_numbers(rows, BLANK_AS_ZERO[key], file_name, blank_as_zero=True)
        data[key] = rows
    check_names(data)
    check_repeats(data)
    return data


def find_offering(name, grade, semester, offerings):
    """우리 학교 개설표에서 (과목, 학년, 학기)에 맞는 줄을 찾는다. 없으면 None."""
    for o in offerings:
        if o["name"] == name and o["grade"] == grade and o["semester"] == semester:
            return o
    return None


def when_offered(name, offerings):
    """과목이 우리 학교에서 열리는 때를 '3학년 1학기'처럼 글자 list로 돌려준다."""
    terms = []
    for o in offerings:
        if o["name"] == name:
            terms.append(f"{o['grade']}학년 {o['semester']}학기")
    return terms


def offered_text(name, offerings):
    """열리는 때를 '2학년 1학기, 2학년 2학기'처럼, 열리지 않으면 '미개설'로 돌려준다."""
    terms = when_offered(name, offerings)
    if len(terms) == 0:
        return "미개설"
    return ", ".join(terms)
