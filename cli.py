"""키보드로 입력하는 콘솔 버전 (core 함수를 그대로 쓴다). 실행: python cli.py"""
import os

from core.config import NO_UNIVERSITY, PLAN_TERMS
from core.data import load_all, offered_text
from core.plan_io import load_plan, remove_unknown, save_plan
from core.planner import build_plan, fixed_courses, term_plan
from core.recommend import field_names, find_rules, score_courses, search_courses, universities_for
from core.validate import total_credits, validate

DATA_FOLDER = os.path.join(os.path.dirname(__file__), "data")


def choose(title, options):
    """번호 목록을 보여 주고, 키보드로 받은 번호에 맞는 항목을 돌려준다."""
    print(f"\n[{title}]")
    for i, option in enumerate(options, start=1):
        print(f"  {i}. {option}")
    while True:
        answer = input("번호를 입력하세요: ").strip()
        try:
            number = int(answer)
        except ValueError:
            print("숫자로 입력해 주세요.")
            continue
        if 1 <= number <= len(options):
            return options[number - 1]
        print("목록에 있는 번호를 입력해 주세요.")


def ask_file_name(question):
    """파일 이름을 입력받는다. 끝에 .xlsx가 없으면 붙인다."""
    name = input(question).strip()
    if name == "":
        name = "내_계획"
    if not name.endswith(".xlsx"):
        name = name + ".xlsx"
    return name


def print_plan(plan, offerings):
    """학기마다 과목과 학점 합계를 출력한다."""
    for grade, semester in PLAN_TERMS:
        term = term_plan(plan, grade, semester)
        names = ", ".join(name for name, g, s in term)
        print(f"\n{grade}학년 {semester}학기 ({total_credits(term, offerings)}학점): {names}")


def main():
    try:
        data = load_all(DATA_FOLDER)
    except (FileNotFoundError, ValueError) as error:
        print("데이터를 읽지 못했어요.", error)
        return

    field = choose("계열", field_names(data["majors"]))
    major = choose("학과", [m["name"] for m in data["majors"] if m["field"] == field])
    universities = universities_for(major, data["recs"])
    if universities == [NO_UNIVERSITY]:
        print("이 학과는 권장 과목 자료가 없어요. 계열에 맞는 과목으로만 추천할게요.")
    university = choose("목표 대학", universities)

    rules = find_rules(major, university, data["recs"])
    scores = score_courses(major, university, data["majors"], data["recs"], data["courses"])
    plan = build_plan(scores, data["courses"], data["offerings"], data["groups"])

    while True:
        print_plan(plan, data["offerings"])
        print("\n[검사 결과]")
        issues = validate(plan, data["courses"], data["offerings"], data["groups"], rules)
        for level, message in issues:
            print(f"  ({level}) {message}")
        if len(issues) == 0:
            print("  규칙을 모두 지켰어요.")

        menu = choose("다음에 할 일", ["과목 이름 검색", "엑셀 파일로 저장", "저장한 파일 불러오기", "끝내기"])
        if menu == "과목 이름 검색":
            found = search_courses(input("과목 이름: "), data["courses"])
            if len(found) == 0:
                print("  그런 과목이 없어요.")
            for c in found:
                print(f"  {c['name']} ({c['area']}) - {offered_text(c['name'], data['offerings'])}")
        elif menu == "엑셀 파일로 저장":
            file_name = ask_file_name("파일 이름(예: 내_계획): ")
            try:
                save_plan(plan, issues, file_name, {"계열": field, "학과": major, "대학": university})
                print(f"{file_name}에 저장했어요.")
            except OSError:
                print("저장하지 못했어요. 폴더 이름을 확인하고, 엑셀에서 그 파일을 열어 두었다면 닫아 주세요.")
        elif menu == "저장한 파일 불러오기":
            file_name = ask_file_name("불러올 파일 이름: ")
            try:
                loaded, warnings = remove_unknown(load_plan(file_name), data["offerings"])
            except FileNotFoundError:
                print("그런 파일이 없어요.")
                continue
            except ValueError as error:
                print(error)
                continue
            fixed = fixed_courses(data["offerings"])  # 모두 듣는 과목은 늘 넣는다
            plan = fixed + [p for p in loaded if p not in fixed]
            for warning in warnings:
                print(" ", warning)
        else:
            print("끝낼게요.")
            break


if __name__ == "__main__":
    try:
        main()
    except (KeyboardInterrupt, EOFError):  # Ctrl+C나 입력 끝으로 멈춰도 오류 화면 없이 끝낸다
        print("\n끝낼게요.")
