"""[F3~F6] 계획 자동 생성, 직접 수정, 규칙 검사, 엑셀 저장·불러오기."""
from io import BytesIO

import pandas as pd
import streamlit as st

from common import current_choice, load_data_or_stop, page_top
from core.config import ERROR, INFO, NO_UNIVERSITY, PLAN_TERMS, WARNING
from core.plan_io import load_choice, load_plan, remove_unknown, save_plan
from core.planner import build_plan, fixed_courses, group_options, picked_in_group, term_plan
from core.recommend import find_rules, score_courses, score_word
from core.validate import check_recommendations, total_credits, validate

data = load_data_or_stop()
choice = current_choice()
courses, offerings, groups = data["courses"], data["offerings"], data["groups"]
rules = find_rules(choice["학과"], choice["대학"], data["recs"])
scores = score_courses(choice["학과"], choice["대학"], data["majors"], data["recs"], courses)
target = (choice["학과"], choice["대학"])  # 지금 고른 진로


def widget_key(group):
    return f"pick_{group['group_id']}"


def show_plan_in_widgets(plan):
    """계획을 선택군별 고르기 칸(multiselect)에 채워 넣는다."""
    for g in groups:
        st.session_state[widget_key(g)] = picked_in_group(plan, g, offerings)
    st.session_state["plan"] = plan


def plan_from_widgets():
    """고르기 칸에 지금 들어 있는 과목으로 계획 list를 만든다."""
    plan = fixed_courses(offerings)
    for g in groups:
        for name in st.session_state.get(widget_key(g), []):
            plan.append((name, g["grade"], g["semester"]))
    return plan


def course_label(name):
    """고르기 칸에 '기하 · 강력 추천'처럼 추천 정도를 붙여 보여 준다."""
    word = score_word(scores.get(name, 0))
    if word == "":
        return name
    return f"{name} · {word}"


page_top(3, "내 이수 계획", ":material/event_note:",
         "추천대로 채워 둔 계획이에요. 칸마다 과목 수를 맞추고, 검사 결과를 본 뒤 저장해요.")

# 처음 열었을 때: 추천대로 짠 계획. 다른 화면에 다녀왔으면 저장해 둔 계획으로 칸을 다시 채운다.
if "plan" not in st.session_state:
    show_plan_in_widgets(build_plan(scores, courses, offerings, groups))
    st.session_state["plan_for"] = target
elif any(widget_key(g) not in st.session_state for g in groups):
    show_plan_in_widgets(st.session_state["plan"])
elif st.session_state.get("shown_for", target) != target:
    # 이 화면에서 진로를 바꾸면 칸 글자('기하 · 추천')가 바뀌어 고른 과목이 사라지므로, 지난 계획으로 칸을 다시 채운다
    show_plan_in_widgets(st.session_state["plan"])
st.session_state["shown_for"] = target

# 도구 줄: 지금 학년 · 추천대로 다시 짜기 · 저장한 계획 불러오기
with st.container(border=True, horizontal=True, vertical_alignment="center"):
    grade_now = st.radio("지금 학년", ["1학년", "2학년"], horizontal=True, key="grade_now",
                         captions=["모든 칸을 새로 채워요", "2학년 칸을 들은 과목으로 고친 뒤 눌러요"])
    label = "추천대로 다시 짜기" if grade_now == "1학년" else "2학년은 두고 빈자리 채우기"
    clicked = st.button(label, icon=":material/auto_fix_high:",
                        help="2학년이면 먼저 아래 2학년 칸을 실제로 들은 과목으로 고친 뒤 눌러요.")
    with st.popover("저장한 계획 불러오기", icon=":material/upload_file:"):
        uploaded = st.file_uploader("앱에서 저장한 엑셀 파일(.xlsx)을 올려 주세요", type=["xlsx"])

# [F6] 저장해 둔 계획 파일 불러오기
if uploaded is not None and st.session_state.get("loaded_file") != uploaded.file_id:
    try:
        loaded = load_plan(BytesIO(uploaded.getvalue()))
        saved_choice = load_choice(BytesIO(uploaded.getvalue()))
        loaded, warnings = remove_unknown(loaded, offerings)
        show_plan_in_widgets(loaded)

        major = saved_choice.get("학과", choice["학과"])
        university = saved_choice.get("대학", choice["대학"])
        if university != NO_UNIVERSITY and len(find_rules(major, university, data["recs"])) == 0:
            warnings.append(f"파일에 적힌 '{major} · {university}'이(가) 지금 목록에 없어요. 왼쪽에서 다시 골라 주세요.")
        st.session_state["pending_choice"] = saved_choice
        st.session_state["plan_for"] = (major, university)
        st.session_state["load_messages"] = [f"'{uploaded.name}'에서 계획을 불러왔어요."] + warnings
        st.session_state["loaded_file"] = uploaded.file_id  # 이 파일은 처리했다고 기록
        st.rerun()  # 파일에 적힌 학과·대학을 사이드바에 반영하려고 한 번 더 그린다
    except ValueError as error:
        st.error(str(error), title="파일을 읽지 못했어요")
        st.session_state["loaded_file"] = uploaded.file_id  # 같은 파일로 오류를 계속 보여 주지 않는다
messages = st.session_state.pop("load_messages", [])
if len(messages) > 0:
    st.toast(messages[0], icon=":material/check_circle:")
if len(messages) > 1:
    st.warning("\n".join("- " + m for m in messages[1:]), title="불러온 파일에서 확인할 것이 있어요")

# [F3] 추천대로 다시 짜기. 2학년이면 지금 고른 2학년 과목은 그대로 두고, 빈자리와 3학년을 채운다.
if clicked:
    taken = []
    if grade_now == "2학년":
        fixed = fixed_courses(offerings)
        for name, grade, semester in plan_from_widgets():
            if grade == 2 and (name, grade, semester) not in fixed:
                taken.append((name, grade, semester))
    show_plan_in_widgets(build_plan(scores, courses, offerings, groups, taken))
    st.session_state["plan_for"] = target
    st.toast("추천 점수대로 계획을 짰어요. 아래에서 직접 고칠 수 있어요.", icon=":material/check_circle:")
elif st.session_state.get("plan_for", target) != target:
    st.info(f"새 진로에 맞추려면 위의 '{label}'를 눌러요.", title="학과나 대학을 바꿨어요")

# 고르기 칸의 값은 칸을 다시 그리기 전에 이미 session_state에 들어 있다.
# 그래서 계획과 검사 결과를 먼저 만들고, 요약을 위에서부터 차례대로 그린다.
plan = plan_from_widgets()
st.session_state["plan"] = plan
issues = validate(plan, courses, offerings, groups, rules)
by_level = {ERROR: [], WARNING: [], INFO: []}
for level, message in issues:
    by_level[level].append("- " + message)
n_error, n_warning, n_info = len(by_level[ERROR]), len(by_level[WARNING]), len(by_level[INFO])

# 맨 위 요약: 다 골랐나? 학점은? 빠진 권장 과목은? 고칠 것은?
done = 0
for g in groups:
    if len(st.session_state.get(widget_key(g), [])) == g["pick_count"]:
        done += 1
credits = 0
for grade, semester in PLAN_TERMS:
    credits += total_credits(term_plan(plan, grade, semester), offerings)
offered = {o["name"] for o in offerings}
rec_missing = 0  # 우리 학교에 열리는데 아직 못 채운 대학 권장 과목 규칙 수 (검사 함수를 그대로 다시 씀)
for level, message in check_recommendations(plan, rules, offered):
    if level == WARNING:
        rec_missing += 1

c1, c2, c3, c4 = st.columns(4)
c1.metric("다 고른 선택군", f"{done} / {len(groups)}", border=True)
c2.metric("2·3학년 학점", f"{credits}학점", border=True)
c3.metric("못 채운 권장 규칙", f"{rec_missing}개", border=True,
          help="우리 학교에 열리는데 아직 못 채운 대학 권장 과목 규칙 수예요.")
c4.metric("꼭 고칠 것 (오류)", f"{n_error}개", border=True)
if n_error > 0:
    st.error(f"오류 {n_error}개를 고쳐야 해요. 맨 아래 '검사 결과'를 봐요.", title="계획에 고칠 곳이 있어요",
             icon=":material/error:")
elif n_warning > 0:
    st.warning(f"주의 {n_warning}개를 확인해 보세요. 맨 아래 '검사 결과'에 있어요.", title="거의 다 됐어요",
               icon=":material/warning:")
else:
    st.success("맨 아래에서 엑셀로 저장해요.", title="규칙을 모두 지켰어요", icon=":material/check_circle:")

# [F4] 학기마다 선택군 칸에서 과목 바꾸기. 학기마다 테두리 상자 하나
for grade, semester in PLAN_TERMS:
    term = term_plan(plan, grade, semester)
    with st.container(border=True):
        st.subheader(f"{grade}학년 {semester}학기 · {len(term)}과목 · {total_credits(term, offerings)}학점")
        for g in groups:
            if (g["grade"], g["semester"]) != (grade, semester):
                continue
            need = g["pick_count"]
            picked = len(st.session_state.get(widget_key(g), []))
            if picked == need:
                mark = ":green[:material/check_circle: 다 골랐어요]"
            elif picked < need:
                mark = f":blue[:material/pending: {need - picked}과목 더 골라요]"
            else:
                mark = f":red[:material/error: {picked - need}과목 빼요]"
            st.multiselect(
                f"{g['group_id']}군 · {need}과목 중 {picked}과목 · {mark}",
                group_options(g["group_id"], offerings),
                key=widget_key(g),
                help=g["memo"],
                placeholder="과목을 골라 주세요",
                format_func=course_label,
                wrap=True,
                select_all=False,  # 'Select all'(한꺼번에 고르기)을 숨긴다
            )

with st.expander("모두 듣는 공통·지정 과목 보기"):
    fixed = [{"학년": g, "학기": s, "과목": n} for n, g, s in fixed_courses(offerings)]
    st.dataframe(pd.DataFrame(fixed), hide_index=True)

# [F5] 규칙 검사: 수준별로 한 상자씩. 안내는 접어 둔다
st.subheader("검사 결과", anchor="check")
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
    """이 화면의 plan·issues·choice로 엑셀 파일을 만든다.
    download_button에 함수를 넘기면 저장 버튼을 누를 때만 실행되어, 과목을 바꿀 때마다 만들지 않는다."""
    buffer = BytesIO()
    save_plan(plan, issues, buffer, choice)
    return buffer.getvalue()


with st.container(border=True):
    st.subheader("4단계 · 엑셀로 저장하기")
    st.write("저장한 파일을 담임·진로 선생님께 보여 드려요. 다음에 위의 '저장한 계획 불러오기'로 올리면 이어서 고칠 수 있어요.")
    st.download_button("엑셀 파일로 저장", excel_bytes, file_name="내_이수계획.xlsx", type="primary",
                       icon=":material/download:",
                       mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    st.caption("파일은 내 기기에만 남고, 서버에는 저장하지 않아요.")
