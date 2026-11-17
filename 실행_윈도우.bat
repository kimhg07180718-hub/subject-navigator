@echo off
rem 과목 선택 내비게이터 실행 파일 (윈도우)
rem 처음 한 번은 필요한 라이브러리를 설치하고, 그다음부터는 바로 실행한다.
cd /d "%~dp0"
title 과목 선택 내비게이터

rem 1) 파이썬 찾기: py 런처가 있으면 쓰고, 없으면 python을 쓴다
set "PY="
py -3 --version >nul 2>nul
if not errorlevel 1 set "PY=py -3"
if not defined PY (
    python --version >nul 2>nul
    if not errorlevel 1 set "PY=python"
)
if not defined PY goto no_python

rem 2) 파이썬 3.11 이상인지 확인 (pandas 3에 필요)
%PY% -c "import sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)" >nul 2>nul
if errorlevel 1 goto old_python

rem 3) 처음 한 번만: 이 폴더 안에 가상환경(.venv)을 만들고 라이브러리 설치
if exist ".venv\ready.txt" goto menu
echo.
echo 처음 실행이라 필요한 라이브러리를 설치해요.
echo 인터넷이 필요하고 3~5분쯤 걸려요. 창을 닫지 말고 기다려 주세요.
echo.
if not exist ".venv\Scripts\python.exe" (
    %PY% -m venv .venv
    if errorlevel 1 goto fail
)
".venv\Scripts\python.exe" -m pip install --disable-pip-version-check -r requirements.txt
if errorlevel 1 goto fail
echo ok> ".venv\ready.txt"

:menu
echo.
echo ===== 과목 선택 내비게이터 =====
echo  1. 웹 앱 열기 (추천)
echo  2. 테스트 돌리기
echo.
set "CHOICE=1"
set /p "CHOICE=번호를 고르세요 (그냥 Enter는 1): "
if "%CHOICE%"=="2" goto test

echo.
echo 잠시 뒤 브라우저에 앱이 열려요. 끝내려면 이 창을 닫으세요.
".venv\Scripts\python.exe" -m streamlit run app.py
goto end

:test
".venv\Scripts\python.exe" -m pytest -q
goto end

:no_python
echo.
echo 파이썬을 찾지 못했어요.
echo https://www.python.org/downloads/ 에서 파이썬 3.11 이상을 설치해 주세요.
echo 설치 첫 화면에서 "Add python.exe to PATH"에 꼭 체크하세요.
goto end

:old_python
echo.
echo 파이썬 버전이 낮아요. 3.11 이상이 필요해요.
%PY% --version
echo https://www.python.org/downloads/ 에서 새 버전을 설치해 주세요.
goto end

:fail
echo.
echo 설치하다가 문제가 생겼어요. 인터넷 연결을 확인하고 다시 실행해 주세요.
echo 계속 안 되면 이 폴더의 .venv 폴더를 지우고 다시 실행해 보세요.
goto end

:end
echo.
pause
