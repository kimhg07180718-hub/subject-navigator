#!/bin/bash
# 과목 선택 내비게이터 실행 파일 (맥·리눅스)
# 처음 한 번은 필요한 라이브러리를 설치하고, 그다음부터는 바로 실행한다.
cd "$(dirname "$0")" || exit 1

# 1) 파이썬 3.11 이상 찾기
if ! command -v python3 >/dev/null 2>&1; then
    echo "파이썬을 찾지 못했어요. https://www.python.org/downloads/ 에서 3.11 이상을 설치해 주세요."
    read -r -p "Enter를 누르면 닫혀요."
    exit 1
fi
if ! python3 -c "import sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)"; then
    echo "파이썬 버전이 낮아요. 3.11 이상이 필요해요. (지금: $(python3 --version))"
    read -r -p "Enter를 누르면 닫혀요."
    exit 1
fi

# 2) 처음 한 번만: 이 폴더 안에 가상환경(.venv)을 만들고 라이브러리 설치
if [ ! -f .venv/ready.txt ]; then
    echo "처음 실행이라 필요한 라이브러리를 설치해요. 인터넷이 필요하고 3~5분쯤 걸려요."
    if ! { python3 -m venv .venv && .venv/bin/python -m pip install --disable-pip-version-check -r requirements.txt; }; then
        echo "설치하다가 문제가 생겼어요. 인터넷 연결을 확인하고 다시 실행해 주세요."
        read -r -p "Enter를 누르면 닫혀요."
        exit 1
    fi
    echo ok > .venv/ready.txt
fi

# 3) 메뉴
echo
echo "===== 과목 선택 내비게이터 ====="
echo " 1. 웹 앱 열기 (추천)"
echo " 2. 테스트 돌리기"
read -r -p "번호를 고르세요 (그냥 Enter는 1): " choice
case "$choice" in
    2) .venv/bin/python -m pytest -q ;;
    *) echo "잠시 뒤 브라우저에 앱이 열려요. 끝내려면 이 창을 닫거나 Ctrl+C를 누르세요."
       .venv/bin/python -m streamlit run app.py ;;
esac
read -r -p "Enter를 누르면 닫혀요."
