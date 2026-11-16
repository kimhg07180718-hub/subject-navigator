"""[F2] 고른 대학·학과에 맞춰 과목마다 추천 점수를 매기고, 과목을 검색한다."""
from core.config import (FIELD_AREAS, NO_UNIVERSITY, SCORE_CORE, SCORE_FIELD_AREA, SCORE_RECOMMEND,
                         SCORE_SAME_FIELD)


def split_courses(rule):
    """규칙의 courses 칸('A|B|C')을 과목 이름 list로 나눈다."""
    return [name for name in rule["courses"].split("|") if name != ""]


def need_count(rule):
    """규칙을 지키려면 몇 과목이 필요한지 돌려준다. 'none'은 0과목."""
    if rule["rule"] == "none":
        return 0
    if rule["rule"] == "at_least":
        return rule["count"]
    return 1  # single, any_of


def rule_text(rule):
    """규칙을 사람이 읽기 쉬운 문장으로 바꾼다."""
    names = split_courses(rule)
    if rule["rule"] == "none":
        return "따로 정한 권장 과목 없음"
    if rule["rule"] == "single":
        return names[0]
    if rule["rule"] == "any_of":
        return " 또는 ".join(names) + " 중 1과목"
    return ", ".join(names) + f" 중 {rule['count']}과목 이상"


def find_rules(major, university, recs):
    """[F2] 고른 학과·대학의 권장 과목 규칙만 골라 돌려준다."""
    rules = []
    for rule in recs:
        if rule["major"] == major and rule["university"] == university:
            rules.append(rule)
    return rules


def needed_rules(rules):
    """[F2] '따로 정한 권장 과목 없음'(none) 규칙을 뺀 list. 홈과 추천 과목 화면이 같은 수를 보여 주게 한다."""
    kept = []
    for rule in rules:
        if need_count(rule) > 0:
            kept.append(rule)
    return kept


def without_required(rules, required):
    """[F2] 규칙에서 모두 듣는 필수 과목(required)을 뺀다. 필수 과목만으로 채워지는 규칙은 통째로 빼고,
    남은 규칙은 (규칙, 남은 과목 list, 더 들어야 할 과목 수)로 돌려준다.
    예: '대수, 미적분Ⅰ, 기하, 미적분Ⅱ 중 3과목 이상' → (규칙, ['기하', '미적분Ⅱ'], 1)"""
    shown = []
    for rule in needed_rules(rules):
        names = split_courses(rule)
        rest = [n for n in names if n not in required]
        need = need_count(rule) - (len(names) - len(rest))  # 필수 과목은 저절로 채워진다
        if need > 0:
            shown.append((rule, rest, need))
    return shown


def field_names(majors):
    """[F1] majors.csv에 나온 순서대로 계열 이름 list를 만든다 (같은 이름은 한 번만)."""
    fields = []
    for m in majors:
        if m["field"] not in fields:
            fields.append(m["field"])
    return fields


def universities_for(major, recs):
    """[F1] 그 학과의 권장 과목 자료가 있는 대학 list (가나다순). 하나도 없으면 [NO_UNIVERSITY]."""
    names = sorted({r["university"] for r in recs if r["major"] == major})
    if len(names) == 0:  # majors.csv에만 있고 권장 과목 자료가 없는 학과
        names = [NO_UNIVERSITY]
    return names


def field_of(major, majors):
    """학과 이름으로 계열을 찾는다. 없으면 빈 글자."""
    for m in majors:
        if m["name"] == major:
            return m["field"]
    return ""


def score_courses(major, university, majors, recs, courses):
    """[F2] 과목마다 추천 점수를 매겨 {과목 이름: 점수} dict로 돌려준다."""
    scores = {}

    # 1) 고른 대학·학과의 핵심 과목은 +3, 권장 과목은 +2
    for rule in find_rules(major, university, recs):
        if rule["level"] == "핵심":
            point = SCORE_CORE
        else:
            point = SCORE_RECOMMEND
        for name in split_courses(rule):
            scores[name] = scores.get(name, 0) + point

    # 2) 같은 계열 다른 학과의 권장 과목은 +1 (과목마다 한 번만)
    field = field_of(major, majors)
    same_field = set()
    for m in majors:
        if m["field"] == field and m["name"] != major:
            same_field.add(m["name"])
    bonus = set()
    for rule in recs:
        if rule["major"] in same_field:
            bonus.update(split_courses(rule))
    for name in bonus:
        scores[name] = scores.get(name, 0) + SCORE_SAME_FIELD

    # 3) 계열과 잘 맞는 교과의 과목은 +1 (예: 인문 계열 → 국어·사회·영어)
    areas = FIELD_AREAS.get(field, [])
    for c in courses:
        if c["area"] in areas:
            scores[c["name"]] = scores.get(c["name"], 0) + SCORE_FIELD_AREA

    return scores


def score_word(score):
    """[F2] 추천 점수를 말로 바꾼다. 3점 이상 '강력 추천', 2점 '추천', 1점 '참고', 0점은 빈 글자."""
    if score >= 3:
        return "강력 추천"
    if score >= 2:
        return "추천"
    if score >= 1:
        return "참고"
    return ""


def simple(text):
    """검색하기 쉽게 띄어쓰기를 빼고 Ⅰ·Ⅱ를 1·2로 바꾼다 (예: '미적분 Ⅱ' → '미적분2')."""
    return text.replace(" ", "").replace("Ⅰ", "1").replace("Ⅱ", "2")


def search_courses(keyword, courses):
    """[F2] 이름에 keyword가 들어간 과목을 찾는다. 띄어쓰기와 Ⅰ·1의 차이는 무시한다."""
    key = simple(keyword)
    if key == "":
        return []
    found = []
    for c in courses:
        if key in simple(c["name"]):
            found.append(c)
    return found
