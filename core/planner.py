"""[F3] 추천 점수로 2·3학년 선택과목 계획을 자동으로 짠다 (탐욕 알고리즘)."""
from core.config import HINT_PENALTY, PLAN_TERMS


def fixed_courses(offerings):
    """선택군이 없는 공통·지정 과목(모두 듣는 과목)을 계획 list로 만든다."""
    plan = []
    for o in offerings:
        if o["group_id"] == "":
            plan.append((o["name"], o["grade"], o["semester"]))
    return plan


def required_names(offerings):
    """모두 듣는 공통·지정 과목(필수 과목)의 이름 set. 예: 미적분Ⅰ, 화법과 언어"""
    names = set()
    for name, grade, semester in fixed_courses(offerings):
        names.add(name)
    return names


def term_plan(plan, grade, semester):
    """계획에서 한 학기(grade, semester)에 든 줄만 골라 돌려준다."""
    term = []
    for name, g, s in plan:
        if g == grade and s == semester:
            term.append((name, g, s))
    return term


def group_options(group_id, offerings):
    """선택군 하나에서 고를 수 있는 과목 이름 list."""
    names = []
    for o in offerings:
        if o["group_id"] == group_id:
            names.append(o["name"])
    return names


def picked_in_group(plan, group, offerings):
    """계획에서 그 선택군(같은 학년·학기)에 들어간 과목 이름 list."""
    options = group_options(group["group_id"], offerings)
    picked = []
    for name, grade, semester in plan:
        if name in options and grade == group["grade"] and semester == group["semester"]:
            picked.append(name)
    return picked


def taken_before(name, grade, semester, plan):
    """계획에서 name을 (grade, semester)보다 앞 학기에 들었으면 True."""
    for n, g, s in plan:
        if n == name and (g, s) < (grade, semester):  # 튜플은 학년부터 비교한다
            return True
    return False


def prereq_done(name, grade, semester, plan, courses_by_name, offered):
    """선수 과목을 앞 학기에 들었으면 True.
    선수 과목이 우리 학교에 아예 없으면 막지 않는다 (검사에서 안내만 한다)."""
    prereq = courses_by_name[name]["prereq"]
    if prereq == "" or prereq not in offered:
        return True
    return taken_before(prereq, grade, semester, plan)


def priority(name, grade, semester, plan, scores, courses_by_name, offered):
    """계획에 넣을 순서를 정하는 점수. 보통 먼저 듣는 과목(before_hint)을 아직 안 들었으면 조금 깎는다."""
    point = scores.get(name, 0)
    hint = courses_by_name[name]["before_hint"]
    if hint != "" and hint in offered and not taken_before(hint, grade, semester, plan):
        point -= HINT_PENALTY
    return point


def build_plan(scores, courses, offerings, groups, taken=None):
    """[F3] 점수가 높은 과목부터 선택군마다 pick_count만큼 골라 계획 list를 돌려준다.
    taken: 이미 고른 선택과목 [(과목, 학년, 학기)]. 그 선택군은 남은 자리만 채운다."""
    courses_by_name = {c["name"]: c for c in courses}
    offered = {o["name"] for o in offerings}
    applicants = {}  # 점수가 같을 때 신청 인원이 많은(폐강 위험이 적은) 과목 먼저
    for o in offerings:
        applicants[o["name"]] = max(applicants.get(o["name"], 0), o["applicants"])

    plan = fixed_courses(offerings)
    if taken:
        plan = plan + list(taken)

    for grade, semester in PLAN_TERMS:
        for group in groups:
            if group["grade"] != grade or group["semester"] != semester:
                continue
            need = group["pick_count"] - len(picked_in_group(plan, group, offerings))
            if need <= 0:
                continue

            already = {n for n, g, s in plan}
            candidates = []
            for name in group_options(group["group_id"], offerings):
                if name in already:  # 같은 과목 두 번 금지
                    continue
                if not prereq_done(name, grade, semester, plan, courses_by_name, offered):
                    continue
                candidates.append(name)

            candidates.sort(key=lambda n: (priority(n, grade, semester, plan, scores, courses_by_name, offered),
                                           applicants.get(n, 0)), reverse=True)
            for name in candidates[:need]:
                plan.append((name, grade, semester))
    return plan
