"""앱 시작 파일. 실행: streamlit run app.py
사이드바(화면 목록과 진로 고르기)를 그리고, 고른 화면을 실행한다."""
import streamlit as st

from common import load_data_or_stop, sidebar_choice

st.set_page_config(page_title="과목 선택 내비게이터", page_icon="🧭", layout="wide")

page = st.navigation([
    st.Page("views/0_홈.py", title="홈", icon=":material/home:", default=True),
    st.Page("views/1_추천과목.py", title="추천 과목", icon=":material/star:"),
    st.Page("views/2_내_이수계획.py", title="내 이수 계획", icon=":material/event_note:"),
])

data = load_data_or_stop()
st.session_state["choice"] = sidebar_choice(data)  # [F1] 모든 화면에서 같은 사이드바를 쓴다

# Streamlit은 화면에 없는 위젯의 값을 지우므로, 다른 화면에 다녀와도 '지금 학년'을 기억하게 다시 저장한다
if "grade_now" in st.session_state:
    st.session_state["grade_now"] = st.session_state["grade_now"]

page.run()
