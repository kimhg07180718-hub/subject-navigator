"""[홈] 앱 소개, 지금 고른 진로, 사용 순서(단계 카드)."""
import streamlit as st

from common import choice_badges, current_choice, load_data_or_stop, next_step
from core.planner import required_names
from core.recommend import find_rules, without_required

data = load_data_or_stop()
choice = current_choice()

st.title("고교학점제 과목 선택 내비게이터", icon=":material/explore:")
st.write("희망 학과와 목표 대학을 고르면, 광주 광덕고 편성표 안에서 2·3학년 선택과목 계획을 "
         "짜 주고 선택 규칙도 검사해 줘요.")

# 추천 과목 화면과 같은 수: 필수 과목만으로 채워지는 규칙은 세지 않는다
rules = without_required(find_rules(choice["학과"], choice["대학"], data["recs"]), required_names(data["offerings"]))
st.markdown(f"**지금 고른 진로** {choice_badges(choice)} · 권장 과목 규칙 {len(rules)}개")

# 사용 순서: 단계마다 카드 하나. page가 None이면 이 화면 밖(사이드바, 저장 칸)에서 하는 일이다
STEPS = [
    {"title": "진로 고르기", "text": "왼쪽에서 계열 → 학과 → 목표 대학을 골라요.", "page": None},
    {"title": "추천 과목 보기", "text": "대학이 권하는 과목이 우리 학교에 열리는지 봐요.",
     "page": "views/1_추천과목.py"},
    {"title": "내 계획 고치기", "text": "추천대로 채운 계획을 보고 직접 고쳐요.",
     "page": "views/2_내_이수계획.py"},
    {"title": "엑셀로 저장하기", "text": "3단계 화면 맨 아래에서 저장해 선생님께 보여 드려요.", "page": None},
]
cards = st.columns(len(STEPS))
for i in range(len(STEPS)):
    step = STEPS[i]
    with cards[i].container(border=True, height="stretch"):
        st.markdown(f"**{i + 1}단계 · {step['title']}**")
        st.write(step["text"])
        if step["page"] is not None:
            st.page_link(step["page"], label="바로 가기", icon=":material/arrow_forward:")

st.info("대학이 발표한 권장 과목 자료로 만든 추천이에요. 최종 선택은 담임·진로 선생님과 상의해서 정하세요.",
        title="추천은 참고용이에요", icon=":material/lightbulb:")

next_step("views/1_추천과목.py", "시작하기: 추천 과목 보러 가기")

with st.expander("데이터 출처와 개인정보", icon=":material/info:"):
    universities = {r["university"] for r in data["recs"]}
    st.write("학생 이름이나 계획은 서버에 저장하지 않아요. 저장한 엑셀 파일은 내 기기에만 남아요.")
    st.write("데이터: 2022 개정 교육과정 과목표, 광덕고 2026학년도 시간표와 3학년 선택과목 안내문, "
             f"{len(universities)}개 대학 권장 과목 자료(확인 날짜는 '추천 과목' 화면에 있어요).")
