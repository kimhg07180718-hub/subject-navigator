"""여러 화면이 같이 쓰는 Streamlit 코드 (데이터 불러오기, 사이드바의 진로 고르기, 화면 머리, 다음 단계 버튼)."""
import os

import streamlit as st

from core.config import DATA_FILES
from core.data import load_all
from core.recommend import field_names, universities_for

DATA_FOLDER = os.path.join(os.path.dirname(__file__), "data")


def data_version():
    """CSV 파일들을 마지막으로 고친 시각 list. 파일을 고치면 값이 바뀐다."""
    times = []
    for file_name in DATA_FILES.values():
        path = os.path.join(DATA_FOLDER, file_name)
        if os.path.exists(path):
            times.append(os.path.getmtime(path))
    return times


@st.cache_data(max_entries=1)
def get_data(version):  # version은 캐시 열쇠로만 쓴다. CSV를 고치면 값이 바뀌어 다시 읽는다
    """CSV 5개를 읽는다. 파일을 고치지 않았으면 저장해 둔 결과를 쓴다."""
    return load_all(DATA_FOLDER)


def load_data_or_stop():
    """데이터를 읽는다. 파일이 없거나 숫자가 틀리면 화면에 알리고 멈춘다."""
    try:
        return get_data(data_version())
    except (FileNotFoundError, ValueError) as error:
        st.error(f"데이터를 읽지 못했어요. {error}")
        st.stop()


def keep_in_options(key, options):
    """목록에 없는 값이면(예: 계열을 바꿈) 첫 번째 항목으로 바꾼다."""
    value = st.session_state.get(key)
    if value not in options:
        value = options[0]
    st.session_state[key] = value


def sidebar_choice(data):
    """[F1] 사이드바에서 계열 → 학과 → 목표 대학을 고르고 dict로 돌려준다."""
    # 불러온 계획 파일에 들어 있던 선택이 있으면 먼저 적용한다
    pending = st.session_state.pop("pending_choice", None)
    if pending:
        for key, name in [("field", "계열"), ("major", "학과"), ("university", "대학")]:
            if pending.get(name):
                st.session_state[key] = pending[name]

    st.sidebar.header("1단계 · 내 진로 고르기")

    fields = field_names(data["majors"])
    keep_in_options("field", fields)
    field = st.sidebar.pills("어떤 분야로 진학하고 싶나요?", fields, key="field", required=True)

    majors = [m["name"] for m in data["majors"] if m["field"] == field]
    keep_in_options("major", majors)
    major = st.sidebar.selectbox("학과", majors, key="major")

    universities = universities_for(major, data["recs"])
    keep_in_options("university", universities)
    university = st.sidebar.selectbox("목표 대학", universities, key="university")

    st.sidebar.caption("추천은 참고용이에요. 최종 선택은 선생님과 상의해서 정하세요.")
    return {"계열": field, "학과": major, "대학": university}


def current_choice():
    """app.py가 사이드바에서 받아 저장해 둔 계열·학과·대학 dict를 돌려준다."""
    return st.session_state["choice"]


def choice_badges(choice):
    """지금 고른 계열·학과·대학을 회색 배지 3개로 보여 줄 글자를 만든다."""
    return f":gray-badge[{choice['계열']}] :gray-badge[{choice['학과']}] :gray-badge[{choice['대학']}]"


def page_top(step, title, icon, todo):
    """화면 맨 위: 몇 단계인지, 제목, 지금 고른 진로, 이 화면에서 할 일 한 줄."""
    st.caption(f"{step}단계 / 4단계")
    st.title(title, icon=icon)
    st.markdown(choice_badges(current_choice()))
    st.write(todo)


def next_step(page, label):
    """화면 끝에 '다음에 할 일' 버튼을 하나 둔다. 누르면 그 화면으로 간다."""
    if st.button(label, type="primary", icon=":material/arrow_forward:"):
        st.switch_page(page)
