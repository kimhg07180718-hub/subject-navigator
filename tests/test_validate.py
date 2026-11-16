"""[F2·F3·F5] 일부러 틀린 계획을 만들어 경고가 나오는지 확인한다. 실행: pytest"""
from core.planner import build_plan, fixed_courses, required_names, term_plan
from core.recommend import find_rules, needed_rules, score_courses, score_word, search_courses, without_required
from core.validate import check_recommendations, total_credits, validate


def make_plan(data, major="컴퓨터공학", university="연세대"):
    """테스트용: 추천대로 짠 계획과 그 학과의 규칙을 돌려준다."""
    rules = find_rules(major, university, data["recs"])
    scores = score_courses(major, university, data["majors"], data["recs"], data["courses"])
    plan = build_plan(scores, data["courses"], data["offerings"], data["groups"])
    return plan, rules


def run_validate(plan, data, rules=None):
    return validate(plan, data["courses"], data["offerings"], data["groups"], rules or [])


def messages(issues, level):
    return [msg for lv, msg in issues if lv == level]


def test_good_plan_has_no_errors(data):
    """추천대로 짠 계획은 오류와 주의가 없어야 한다."""
    plan, rules = make_plan(data)
    issues = run_validate(plan, data, rules)
    assert messages(issues, "오류") == []
    assert messages(issues, "주의") == []


def test_group_too_many(data):
    """선택군에서 정해진 수보다 많이 고르면 오류."""
    plan, rules = make_plan(data)
    plan.append(("경제", 3, 1))  # G3-1A는 4과목인데 5번째 과목
    issues = run_validate(plan, data, rules)
    assert any("G3-1A" in msg and "지금 5과목" in msg for msg in messages(issues, "오류"))


def test_group_too_few(data):
    """선택군에서 정해진 수보다 적게 고르면 오류."""
    plan, rules = make_plan(data)
    plan = [p for p in plan if not (p[1] == 3 and p[2] == 2)]  # 3학년 2학기를 모두 비움
    issues = run_validate(plan, data, rules)
    errors = messages(issues, "오류")
    assert any("G3-2A" in msg and "지금 0과목" in msg for msg in errors)
    assert any("G3-2C" in msg for msg in errors)


def test_duplicate_course(data):
    """1·2학기에 모두 열리는 과목을 두 번 고르면 오류."""
    plan = fixed_courses(data["offerings"]) + [("생명과학", 2, 1), ("생명과학", 2, 2)]
    issues = run_validate(plan, data)
    assert "생명과학은 2학년 1학기에 이미 골랐어요." in messages(issues, "오류")


def test_prereq_order():
    """미적분Ⅰ 없이 미적분Ⅱ만 들으면 주의. (데이터 파일 대신 작은 표로 확인)"""
    courses = [
        {"name": "미적분Ⅰ", "prereq": "", "before_hint": "", "credits_min": 3, "credits_max": 5},
        {"name": "미적분Ⅱ", "prereq": "미적분Ⅰ", "before_hint": "", "credits_min": 3, "credits_max": 5},
    ]
    offerings = [
        {"name": "미적분Ⅰ", "grade": 2, "semester": 2, "school_credits": 4, "group_id": ""},
        {"name": "미적분Ⅱ", "grade": 3, "semester": 1, "school_credits": 3, "group_id": "G3-1A"},
    ]
    plan = [("미적분Ⅱ", 3, 1)]
    issues = validate(plan, courses, offerings, [], [])
    assert ("주의", "미적분Ⅱ 전에 미적분Ⅰ을 들어야 해요.") in issues


def test_missing_core_recommendation(data):
    """경희대 컴퓨터공학의 핵심 과목인 기하를 빼면 주의."""
    plan, rules = make_plan(data, "컴퓨터공학", "경희대")
    plan = [p for p in plan if p[0] != "기하"]
    plan.append(("세계사", 2, 1))  # 선택군 수는 맞춰 둠
    issues = run_validate(plan, data, rules)
    assert any(msg.startswith("기하는 경희대 컴퓨터공학의 핵심") for msg in messages(issues, "주의"))


def test_not_offered_recommendation_is_info(data):
    """우리 학교에 없는 권장 과목(인공지능 수학)은 오류가 아니라 안내."""
    plan, rules = make_plan(data, "컴퓨터공학", "경희대")
    issues = run_validate(plan, data, rules)
    assert any(msg.startswith("인공지능 수학은 우리 학교에 열리지 않아요") for msg in messages(issues, "안내"))


def test_unmeetable_rule_still_checks_offered_courses():
    """다 채울 수 없는 규칙(4과목 중 2과목만 열림)이어도, 열리는 과목을 계획에 안 넣었으면 주의."""
    rule = {"university": "가상대", "major": "가상학", "rule": "at_least", "courses": "기하|미적분Ⅱ|없는 과목|또 없는 과목",
            "count": 4, "level": "핵심"}
    issues = check_recommendations([("기하", 2, 1)], [rule], {"기하", "미적분Ⅱ"})
    assert ("안내", "가상대 가상학의 핵심 과목은 4과목 이상인데 우리 학교에는 2과목만 열려요. "
            "공동교육과정이나 온라인 강좌로 들을 수 있는지 선생님께 확인해 보세요.") in issues
    assert ("주의", "가상대 가상학의 핵심 과목 중 우리 학교에 열리는 미적분Ⅱ를 계획에 넣지 않았어요.") in issues


def test_needed_rules_drops_none(data):
    """'따로 정한 권장 과목 없음' 규칙만 있는 학과(연세대 간호학)는 남는 규칙이 없다."""
    assert len(find_rules("간호학", "연세대", data["recs"])) == 1
    assert needed_rules(find_rules("간호학", "연세대", data["recs"])) == []
    assert len(needed_rules(find_rules("컴퓨터공학", "연세대", data["recs"]))) == 3


def test_required_names(data):
    """모두 듣는 공통·지정 과목만 필수 과목이다. 선택군에서 고르는 기하는 아니다."""
    required = required_names(data["offerings"])
    assert "미적분Ⅰ" in required
    assert "화법과 언어" in required
    assert "기하" not in required


def test_without_required():
    """[F2] 필수 과목만으로 채워지는 규칙은 빼고, 섞인 규칙은 남은 과목과 남은 개수만 남긴다."""
    rules = [{"rule": "single", "courses": "미적분Ⅰ", "count": 0},
             {"rule": "any_of", "courses": "물리학|화학", "count": 0},
             {"rule": "any_of", "courses": "확률과 통계|기하", "count": 0},
             {"rule": "at_least", "courses": "대수|미적분Ⅰ|기하|미적분Ⅱ", "count": 3},
             {"rule": "none", "courses": "", "count": 0}]
    shown = without_required(rules, {"대수", "미적분Ⅰ", "확률과 통계"})
    result = [(names, need) for rule, names, need in shown]
    assert result == [(["물리학", "화학"], 1), (["기하", "미적분Ⅱ"], 1)]


def test_score_word():
    """추천 점수를 말로 바꾼다: 3점 이상 강력 추천, 2점 추천, 1점 참고, 0점 빈 글자."""
    assert score_word(5) == "강력 추천"
    assert score_word(3) == "강력 추천"
    assert score_word(2) == "추천"
    assert score_word(1) == "참고"
    assert score_word(0) == ""


def test_score_core_higher_than_recommend(data):
    """경희대 컴퓨터공학: 핵심 과목 기하(+3)가 권장 과목 인공지능 수학(+2)보다 점수가 높다."""
    scores = score_courses("컴퓨터공학", "경희대", data["majors"], data["recs"], data["courses"])
    assert scores["기하"] > scores["인공지능 수학"]


def test_taken_courses_are_kept(data):
    """2학년 학생이 이미 들은 과목은 그대로 두고, 나머지 선택군을 채워 오류 없는 계획을 만든다."""
    taken = [("세계사", 2, 1), ("사회와 문화", 2, 1), ("지구과학", 2, 1), ("생명과학", 2, 1)]
    scores = score_courses("컴퓨터공학", "연세대", data["majors"], data["recs"], data["courses"])
    plan = build_plan(scores, data["courses"], data["offerings"], data["groups"], taken)
    picked_2_1 = [n for n, g, s in plan if (g, s) == (2, 1) and n in {"세계사", "사회와 문화", "지구과학", "생명과학", "기하"}]
    assert sorted(picked_2_1) == sorted(["세계사", "사회와 문화", "지구과학", "생명과학"])
    issues = run_validate(plan, data)
    assert messages(issues, "오류") == []  # 3학년 선택군까지 모두 알맞게 채워졌다


def test_total_credits(data):
    """3학년 1학기: 지정 과목(확률과 통계, 화법과 언어) 4학점씩 + 선택 6과목 × 3학점 = 26학점."""
    plan, rules = make_plan(data)
    assert total_credits(term_plan(plan, 3, 1), data["offerings"]) == 26


def test_search_ignores_spaces(data):
    """띄어쓰기와 Ⅰ·1의 차이를 무시하고 찾는다. 빈 검색어는 빈 결과."""
    names = [c["name"] for c in search_courses("확률과통계", data["courses"])]
    assert names == ["확률과 통계"]
    names = [c["name"] for c in search_courses("미적분2", data["courses"])]
    assert names == ["미적분Ⅱ"]
    assert search_courses("   ", data["courses"]) == []
