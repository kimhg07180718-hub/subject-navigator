# 고교학점제 과목 선택 내비게이터

희망 학과와 목표 대학을 고르면, 광주 광덕고 편성표 안에서 2·3학년 선택과목 계획을 짜 주고 선택 규칙을 검사해 주는 Python 웹앱입니다. 추천은 참고용이고, 학생 정보와 계획은 서버에 저장하지 않습니다.

## 실행 방법

### 더블클릭으로 실행하기

- 윈도우는 `실행_윈도우.bat`, 맥은 `실행_맥.command`를 더블클릭합니다. 맥에서 처음에 막히면 오른쪽 클릭 → 열기를 누릅니다.
- 처음 한 번은 이 폴더 안에 `.venv`(가상환경)를 만들고 필요한 라이브러리를 설치합니다. 인터넷이 필요하고 3~5분쯤 걸립니다. 그다음부터는 바로 실행됩니다.
- 메뉴에서 1은 웹 앱(브라우저가 열림), 2는 테스트입니다. 웹 앱을 끝내려면 검은 창을 닫습니다.
- Python 3.11 이상이 있어야 합니다. 없으면 python.org에서 설치하고, 설치 첫 화면의 "Add python.exe to PATH"에 체크합니다.
- `.streamlit/config.toml`은 Streamlit 설정입니다. 첫 실행 때 이메일을 묻지 않게 하고, 파란 강조색과 맑은 고딕 글꼴(컴퓨터에 깔린 글꼴이라 인터넷 없이 됨)을 쓰고, 오른쪽 위 Deploy 같은 개발자 버튼을 숨깁니다(`toolbarMode = "viewer"`). 개발하다가 Rerun·Clear cache 버튼이 필요하면 `toolbarMode`를 `"auto"`로 바꿉니다.

## 화면 구성

다른 사이트의 좋은 화면을 참고해 고쳤습니다.

| 참고한 곳 | 가져온 점 | 우리 앱 |
|---|---|---|
| 고교학점제 지원센터(hscredit.kr) 진로·학업 설계 | 번호를 붙인 단계 안내 | 홈의 단계 카드 4개, 화면마다 'N단계 / 4단계' |
| 정부 디지털 서비스 디자인 시스템(KRDS) | 파란 강조색, 빨강은 위험에만, 색만으로 뜻을 전하지 않기, 배지 | 테마 색, 핵심·권장 배지, 상태마다 아이콘과 글자를 함께 표시 |
| GOV.UK 디자인 시스템 | 오류 요약을 맨 위에, 알림은 하나만 | 계획 화면 맨 위 상태 상자 하나, 검사 결과를 오류·주의·안내로 묶기 |
| 대학 학업 관리 도구(Degree Works, Stellic) | 진행 상황 숫자를 위에, 요건마다 '몇 개 중 몇 개' | 요약 숫자 4개, 선택군마다 '4과목 중 3과목 · 1과목 더 골라요' |
| 닐슨 노먼 그룹(NN/g) 글 | 같은 종류는 표, 섞인 것은 카드, 자주 안 쓰는 것은 접어 두기 | 한 과목 규칙은 표, 여러 과목 규칙은 카드, 안내와 출처는 접어 둠 |

### 명령어로 실행하기

Python 3.11 이상이 필요합니다.

```bash
pip install -r requirements.txt
streamlit run app.py      # 웹 화면 (브라우저가 열림)
pytest                    # 테스트 실행
```

## 폴더 구조

코드는 모두 `app.py` 한 파일에 있습니다. 과목·대학 자료는 코드와 따로 `data` 폴더의 CSV에 두어서, 자료를 고칠 때 코드를 건드리지 않아도 됩니다.

```
subject-navigator/
├── app.py                 # 앱 코드 전체 (웹 화면, 계산 함수). 맨 위 설명에 차례가 있음
├── data/                  # CSV 5개 (설명은 data/README.md)
├── tests/                 # pytest 테스트 23개 (app.py의 함수를 불러와 확인)
├── 실행_윈도우.bat         # 더블클릭 실행 (윈도우): 처음엔 설치, 그다음엔 메뉴
├── 실행_맥.command         # 더블클릭 실행 (맥)
├── .streamlit/config.toml # Streamlit 설정 (이메일 질문 끄기, 테마 색·글꼴, 개발자 버튼 숨기기)
├── pytest.ini             # 테스트 설정
└── requirements.txt       # 설치할 라이브러리
```

### app.py의 차례

코드 곳곳에 한 줄씩 설명 주석을 달아 두었습니다. 1~6은 Streamlit 없이 순수 Python(list·dict·set, csv 모듈)이라 웹 화면과 테스트가 같이 씁니다.

| 차례 | 하는 일 | 함수 |
|---|---|---|
| 1. 기준값 | 점수, 학기 순서, 시트 이름 같은 상수 | (상수만 있음) |
| 2. 데이터 읽기 | CSV를 읽고 숫자·과목 이름·중복을 확인 | `to_numbers`, `check_data`, `load_all`, `find_offering`, `offered_text` |
| 3. 추천 [F1·F2] | 계열·학과·대학 목록, 권장 과목 규칙, 추천 점수, 검색 | `field_names`, `universities_for`, `find_rules`, `needed_rules`, `without_required`, `score_courses`, `score_word`, `search_courses` |
| 4. 계획 짜기 [F3] | 필수 과목과 선택군으로 계획을 자동으로 짬 | `fixed_courses`, `required_names`, `term_plan`, `taken_before`, `done_before`, `build_plan` |
| 5. 규칙 검사 [F4·F5] | 학점 합계와 규칙 검사 | `total_credits`, `check_*` 5개 (`check_recommendations`는 화면 요약에도 씀), `validate` |
| 6. 엑셀 저장 [F6] | 계획을 엑셀 파일로 씀 | `save_plan` |
| 7. 화면 공통 | 데이터 읽기, 사이드바 진로 고르기, 화면 머리, 다음 단계 버튼 | `load_data_or_stop`, `sidebar_choice`, `page_top`, `next_step` |
| 8~10. 화면 3개 | 홈, 추천 과목(탭 3개), 내 이수 계획 | `home_page`, `recommend_page`, `plan_page` |
| 11. 시작 | 화면 3개를 등록하고 사이드바를 그린 뒤 고른 화면을 실행 | `run_web` |

## 처리 흐름

```
CSV 5개 → load_all → score_courses → build_plan → (학생이 직접 수정) → validate → 화면 표시
                                                                                    ↓
                                                                      save_plan → 엑셀 파일
```

1. `load_all`이 CSV를 읽어 `{"courses": [...], "offerings": [...], ...}` dict로 만든다. 숫자 칸을 숫자로 바꾸고, 개설표와 권장 과목의 과목 이름이 과목표에 있는지, 같은 줄이 두 번 들어가지 않았는지 확인한다. 웹 화면은 CSV를 고친 시각이 바뀔 때만 다시 읽는다.
2. `score_courses`가 고른 대학·학과의 권장 과목에 점수를 매긴다 (핵심 +3, 권장 +2, 같은 계열 다른 학과 권장 +1, 계열과 맞는 교과 +1).
3. `build_plan`이 2학년 1학기부터 3학년 2학기까지 선택군마다 점수가 높은 과목을 `pick_count`만큼 고른다 (탐욕 알고리즘). 같은 과목은 두 번 고르지 않고, 선수 과목을 아직 안 들은 과목은 빼고, 점수가 같으면 신청 인원이 많은 과목을 먼저 고른다.
4. `validate`가 선택군 개수, 같은 과목 중복, 학점 범위, 과목 순서, 권장 과목 누락을 검사해 `[(수준, 메시지)]`를 돌려준다. 우리 학교에서 다 채울 수 없는 권장 규칙도, 열리는 과목을 빼먹었으면 주의를 띄운다.
5. `save_plan`이 계획, 검사 결과, 고른 진로를 엑셀 파일에 써서 학생 기기로 내려보낸다. 서버에는 파일을 남기지 않는다.

## 설계서-구현 대응표

| 기능 | 파일·함수 | 화면 | 테스트 |
|---|---|---|---|
| F1 계열·학과 선택 | `sidebar_choice`, `field_names`, `universities_for` | 모든 화면의 사이드바 | (화면에서 확인) |
| F2 권장 과목 매칭 | `find_rules`, `needed_rules`, `without_required`, `required_names`, `score_courses`, `score_word`, `search_courses` | 추천 과목의 탭 3개(모두 듣는 필수 과목은 '대학이 권하는 과목'에서 뺌), 홈의 '권장 과목 규칙 N개', 계획 칸의 '강력 추천/추천/참고' | `test_score_core_higher_than_recommend`, `test_search_ignores_spaces`, `test_needed_rules_drops_none`, `test_required_names`, `test_without_required`, `test_score_word` |
| F3 이수 계획 자동 생성 | `fixed_courses`, `build_plan` | 내 이수 계획의 '추천대로 다시 짜기' (2학년이면 '2학년은 두고 빈자리 채우기') | `test_good_plan_has_no_errors`, `test_taken_courses_are_kept` |
| F4 계획 직접 수정 | 선택군별 고르기 칸, `term_plan`, `total_credits` | 내 이수 계획의 학기별 상자와 '4과목 중 N과목' 표시, 맨 위 요약 숫자 | `test_total_credits` |
| F5 규칙 검사와 경고 | `validate`와 `check_*` 함수 5개 | 내 이수 계획 맨 위 상태 상자, '못 채운 권장 규칙'·'오류' 숫자, '검사 결과' (오류·주의 상자, 안내는 접어 둠) | `test_group_too_many`, `test_group_too_few`, `test_duplicate_course`, `test_prereq_order`, `test_missing_core_recommendation`, `test_not_offered_recommendation_is_info`, `test_unmeetable_rule_still_checks_offered_courses`, `test_rule_with_no_offered_course_names_courses` |
| F6 엑셀 저장 | `save_plan` | 내 이수 계획의 '4단계 · 엑셀로 저장하기' 상자(누를 때만 파일을 만듦) | `test_save_plan` |
| 데이터 읽기와 예외 처리 | `to_numbers`, `check_data`, `load_all`, `load_data_or_stop` | 모든 화면 (실패하면 오류 안내 후 멈춤) | `test_missing_data_file`, `test_number_error_shows_line`, `test_offering_name_typo`, `test_recommendation_name_typo`, `test_repeated_group_row` |

## 예외 처리

| 상황 | 처리 |
|---|---|
| 데이터 CSV 파일이 없음 | `load_all`이 FileNotFoundError("courses.csv 파일이 없어요")를 내고, 화면은 오류를 보여 주고 멈춤 |
| 학점 칸이 숫자가 아님 | `to_numbers`가 ValueError("groups.csv 3번째 줄의 pick_count 칸이 숫자가 아니에요")로 몇 번째 줄인지 알려 줌 |
| 개설표에 과목표에 없는 이름(오타)이 있음 | `check_data`가 ValueError("offerings.csv 58번째 줄의 과목 '미적분 2'이(가) courses.csv에 없어요")를 냄 |
| 권장 과목 이름에 오타가 있음 | `check_data`가 ValueError("recommendations.csv 2번째 줄의 과목 '기하학'이(가) courses.csv에 없어요")를 냄. 그냥 두면 '열리지 않아요'로 잘못 안내함 |
| 같은 선택군이나 같은 개설 과목 줄이 두 번 있음, 없는 선택군 이름을 씀 | `check_data`가 ValueError("groups.csv 10번째 줄의 선택군 'G2-1A'이(가) 앞에도 있어요")로 알려 줌. 그냥 두면 화면이 멈추거나 과목이 두 번 추천됨 |
| 앱을 켠 채로 CSV를 고침 | `load_data_or_stop`이 CSV 파일을 고친 시각이 바뀌었으면 다시 읽어서, 새로고침하면 고친 내용(또는 오류 안내)이 바로 보임 |
| CSV를 엑셀에서 다른 형식(CP949)으로 저장함 | `load_all`이 UnicodeDecodeError를 "'CSV UTF-8' 형식으로 다시 저장해 주세요"로 바꿔 알려 줌 |
| 계획 화면에서 학과·대학을 바꿈 | 고르기 칸 글자('기하 · 추천')가 바뀌어도 고른 과목이 사라지지 않게, 지난 계획으로 칸을 다시 채움(`shown_for`) |
| majors.csv에만 있고 권장 과목 자료가 없는 학과 | 대학 칸에 '자료 없음'(`NO_UNIVERSITY`)을 보여 주고, 추천 과목 화면에서 "이 학과는 아직 권장 과목 자료가 없어요"로 안내. |

## 알려진 한계와 개선 아이디어

- 탐욕 알고리즘이라 앞 학기 선택 때문에 뒤 학기에 '보통 먼저 듣는 과목' 안내가 나올 수 있습니다 (예: 생명과학 없이 세포와 물질대사). 핵심 과목의 선수 과목에 점수를 물려주는 개선을 해 보고 전후를 비교하면 보고서 소재가 됩니다.
- 3학년 선택과목 학점은 안내문에 없어 3학점으로 추정했습니다. 화면의 학점 합계에만 쓰입니다.
- 대학 권장 과목은 29개 대학 20개 학과만 들어 있고, 일부 대학은 기사나 옮긴 자료로만 확인했습니다. `data/recommendations.csv`에 줄을 더하면 코드를 고치지 않고 늘릴 수 있습니다.
