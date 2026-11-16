"""[F4·F5] 계획의 학점을 더하고, 규칙을 어긴 곳을 문장으로 알려 준다."""
from core.config import ERROR, INFO, LEVELS, WARNING
from core.data import find_offering
from core.planner import picked_in_group, taken_before
from core.recommend import need_count, rule_text, split_courses


def josa(word, with_batchim, without_batchim):
    """'미적분Ⅰ' + 을/를처럼 마지막 글자의 받침에 맞는 조사를 붙인다."""
    last = word[-1]
    last = {"Ⅰ": "일", "Ⅱ": "이", "1": "일", "2": "이"}.get(last, last)
    if "가" <= last <= "힣" and (ord(last) - ord("가")) % 28 != 0:
        return word + with_batchim
    return word + without_batchim


def total_credits(plan, offerings):
    """[F4] 계획에 든 과목의 학점(우리 학교 기준)을 모두 더한다."""
    total = 0
    for name, grade, semester in plan:
        o = find_offering(name, grade, semester, offerings)
        if o is not None:
            total += o["school_credits"]
    return total


def check_groups(plan, offerings, groups):
    """선택군마다 정해진 수만큼 골랐는지 검사한다."""
    issues = []
    for g in groups:
        count = len(picked_in_group(plan, g, offerings))
        if count != g["pick_count"]:
            issues.append((ERROR, f"{g['group_id']}군({g['grade']}학년 {g['semester']}학기)에서는 "
                                  f"{g['pick_count']}과목을 골라야 해요. 지금 {count}과목이에요."))
    return issues


def check_duplicates(plan):
    """같은 과목을 두 번 고르지 않았는지 검사한다."""
    issues = []
    first_time = {}
    for name, grade, semester in plan:
        if name in first_time:
            g, s = first_time[name]
            issues.append((ERROR, f"{josa(name, '은', '는')} {g}학년 {s}학기에 이미 골랐어요."))
        else:
            first_time[name] = (grade, semester)
    return issues


def check_credits(plan, courses_by_name, offerings):
    """우리 학교 학점이 과목의 허용 범위(예: 3~5학점) 안인지 검사한다 (편성표 입력 실수 찾기)."""
    issues = []
    for name, grade, semester in plan:
        o = find_offering(name, grade, semester, offerings)
        c = courses_by_name.get(name)
        if o is None or c is None:
            continue
        if not c["credits_min"] <= o["school_credits"] <= c["credits_max"]:
            issues.append((WARNING, f"{josa(name, '은', '는')} {c['credits_min']}~{c['credits_max']}학점이어야 해요. "
                                    "편성표를 다시 확인해 주세요."))
    return issues


def check_order(plan, courses_by_name, offered):
    """선수 과목(꼭 먼저)과 보통 먼저 듣는 과목을 앞 학기에 들었는지 검사한다."""
    issues = []
    for name, grade, semester in plan:
        c = courses_by_name.get(name)
        if c is None:
            continue

        prereq = c["prereq"]
        if prereq != "" and not taken_before(prereq, grade, semester, plan):
            if prereq in offered:
                issues.append((WARNING, f"{name} 전에 {josa(prereq, '을', '를')} 들어야 해요."))
            else:
                issues.append((INFO, f"{josa(name, '은', '는')} {josa(prereq, '을', '를')} 먼저 들어야 하는데, "
                                     f"우리 학교 개설표에 {josa(prereq, '이', '가')} 없어요. 선생님께 확인해 보세요."))

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
    """[F2] 고른 대학·학과의 권장 과목을 계획에 넣었는지 검사한다."""
    issues = []
    plan_names = {name for name, grade, semester in plan}
    for rule in rules:
        need = need_count(rule)
        if need == 0:
            continue
        names = split_courses(rule)
        have = [n for n in names if n in plan_names]
        if len(have) >= need:
            continue

        level = rule["level"] or "권장"
        who = f"{rule['university']} {rule['major']}"
        can_take = [n for n in names if n in offered]
        if len(can_take) < need:
            if rule["rule"] == "at_least":
                text = f"{who}의 {level} 과목은 {need}과목 이상인데 우리 학교에는 {len(can_take)}과목만 열려요."
            else:
                text = f"{josa(' 또는 '.join(names), '은', '는')} 우리 학교에 열리지 않아요."
            issues.append((INFO, text + " 공동교육과정이나 온라인 강좌로 들을 수 있는지 선생님께 확인해 보세요."))
            # 다 채울 수는 없어도, 우리 학교에 열리는 과목은 계획에 넣었는지 따로 본다
            not_planned = [n for n in can_take if n not in plan_names]
            if len(not_planned) > 0:
                courses_text = josa(", ".join(not_planned), "을", "를")
                issues.append((WARNING, f"{who}의 {level} 과목 중 우리 학교에 열리는 {courses_text} 계획에 넣지 않았어요."))
        else:  # 우리 학교에 열리는데 계획에 넣지 않음
            text = f"{josa(rule_text(rule), '은', '는')} {who}의 {level} 과목이에요."
            if rule["rule"] == "at_least":
                text += f" 지금 {len(have)}과목이에요."
            issues.append((WARNING, text))
    return issues


def validate(plan, courses, offerings, groups, rules):
    """[F5] 모든 검사를 해서 [(수준, 메시지)] list로 돌려준다. 오류 → 주의 → 안내 순서."""
    courses_by_name = {c["name"]: c for c in courses}
    offered = {o["name"] for o in offerings}

    issues = []
    issues += check_groups(plan, offerings, groups)
    issues += check_duplicates(plan)
    issues += check_credits(plan, courses_by_name, offerings)
    issues += check_order(plan, courses_by_name, offered)
    issues += check_recommendations(plan, rules, offered)

    issues.sort(key=lambda issue: LEVELS.index(issue[0]))  # 정렬해도 같은 수준끼리는 순서 유지
    return issues
