"""[F2] 고른 대학·학과의 권장 과목, 우리 학교 개설 여부, 추천 점수 순위, 과목 검색."""
import pandas as pd
import streamlit as st

from common import current_choice, load_data_or_stop, next_step, page_top
from core.config import NO_UNIVERSITY, SCORE_CORE, SCORE_FIELD_AREA, SCORE_RECOMMEND, SCORE_SAME_FIELD
from core.data import offered_text
from core.planner import required_names
from core.recommend import (find_rules, needed_rules, score_courses, score_word, search_courses, split_courses,
                            without_required)

data = load_data_or_stop()
choice = current_choice()
major, university = choice["학과"], choice["대학"]
offerings = data["offerings"]

LEVEL_COLOR = {"핵심": "violet", "권장": "blue"}  # 핵심·권장마다 배지 색을 하나로 정한다. 빨강은 오류에만 쓴다


def open_mark(name):
    """우리 학교에 열리면 '○ 열리는 때', 안 열리면 '× 우리 학교에 없어요'."""
    text = offered_text(name, offerings)
    if text == "미개설":
        return "× 우리 학교에 없어요"
    return "○ " + text


page_top(2, "추천 과목", ":material/star:", "대학이 권하는 과목을 보고, 우리 학교에서 언제 들을 수 있는지 확인해요.")
scores = score_courses(major, university, data["majors"], data["recs"], data["courses"])
tab1, tab2, tab3 = st.tabs(["대학이 권하는 과목", "추천 점수 순위", "과목 찾기"])

# 1) 대학이 발표한 권장 과목: 한 과목짜리 규칙은 표 하나로, 여러 과목 중 고르는 규칙은 카드로.
#    모두 듣는 필수 과목(공통·지정)은 저절로 채워지므로 빼고 보여 준다
with tab1:
    required = required_names(offerings)
    all_rules = find_rules(major, university, data["recs"])
    shown = without_required(all_rules, required)  # [(규칙, 남은 과목 list, 더 들어야 할 수)]
    hidden = []  # 규칙에 나오지만 필수 과목이라 뺀 과목
    for rule in all_rules:
        for name in split_courses(rule):
            if name in required and name not in hidden:
                hidden.append(name)

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

    singles = []  # 한 과목짜리 규칙 → 표의 한 줄
    choices = []  # 여러 과목 중 고르는 규칙 → 카드 하나
    cannot = 0    # 우리 학교에 열리는 과목이 모자라서 다 채울 수 없는 규칙 수
    for rule, names, need in shown:
        offered = [n for n in names if offered_text(n, offerings) != "미개설"]
        if len(offered) < need:
            cannot += 1
        if len(names) == 1:  # 한 과목짜리 규칙, 또는 필수 과목을 빼니 한 과목만 남은 규칙
            singles.append({"과목": names[0], "구분": rule["level"], "우리 학교": open_mark(names[0]),
                            "확인 날짜": rule["checked"], "원문": rule["source"], "메모": rule["note"]})
        else:
            choices.append((rule, names, need))

    if len(singles) > 0:
        st.markdown(f"**한 과목씩 정한 권장 과목 · {len(singles)}과목**")
        st.dataframe(pd.DataFrame(singles), hide_index=True, height="content", column_config={  # 모든 줄을 다 보여 준다
            "구분": st.column_config.TextColumn("구분", help="핵심: 꼭 듣기를 권해요. 권장: 되도록 들으면 좋아요."),
            "원문": st.column_config.LinkColumn("원문", display_text="보기")})

    for rule, names, need in choices:
        level = rule["level"]
        with st.container(border=True):
            st.markdown(f":{LEVEL_COLOR.get(level, 'gray')}-badge[{level}] "
                        f"**아래 {len(names)}과목 중 {need}과목 이상**")
            lines = []
            missing = []
            for name in names:
                if offered_text(name, offerings) == "미개설":
                    missing.append(name)
                else:
                    lines.append(f"- {name} · {open_mark(name)}")
            if len(missing) > 0:
                lines.append(f"- × 우리 학교에 없어요: {', '.join(missing)}")
            st.markdown("\n".join(lines))
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
        if o["group_id"] != "" and scores.get(o["name"], 0) > 0:
            rows.append({"과목": o["name"], "열리는 때": f"{o['grade']}학년 {o['semester']}학기",
                         "추천": score_word(scores[o["name"]]), "점수": scores[o["name"]], "선택군": o["group_id"]})
    rows.sort(key=lambda r: r["점수"], reverse=True)
    top = 1  # 막대 끝 = 가장 높은 점수. 표가 비어 있으면 1
    if len(rows) > 0:
        top = rows[0]["점수"]  # 점수가 높은 순서로 정렬했으니 첫 줄이 가장 높다
    st.dataframe(pd.DataFrame(rows), hide_index=True, column_config={
        "점수": st.column_config.ProgressColumn("추천 점수", min_value=0, max_value=top, format="%d점")})

# 3) 과목 이름 검색
with tab3:
    keyword = st.text_input("과목 이름을 입력하세요", placeholder="예: 통계, 물리, 윤리")
    if keyword.strip() != "":
        found = search_courses(keyword, data["courses"])
        if len(found) == 0:
            st.warning("더 짧은 말로 찾아보세요. 예: '확률통계' 대신 '확률'",
                       title=f"'{keyword}'이(가) 들어간 과목이 없어요")
        else:
            st.caption(f"{len(found)}개 과목을 찾았어요.")
            rows = []
            for c in found:
                rows.append({"과목": c["name"], "교과": c["area"], "유형": c["type"],
                             "우리 학교": open_mark(c["name"]), "추천 점수": scores.get(c["name"], 0)})
            st.dataframe(pd.DataFrame(rows), hide_index=True)

next_step("views/2_내_이수계획.py", "다음: 내 이수 계획 짜러 가기")
