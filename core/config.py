"""앱 전체에서 쓰는 기준값을 이름을 붙여 한곳에 모아 둔다."""

# data 폴더 안의 CSV 파일 5개 (dict의 키 → 파일 이름)
DATA_FILES = {
    "courses": "courses.csv",          # 전국 과목표 (2022 개정)
    "offerings": "offerings.csv",      # 우리 학교 개설표
    "groups": "groups.csv",            # 선택군
    "majors": "majors.csv",            # 계열·학과
    "recs": "recommendations.csv",     # 대학·학과별 권장 과목
}

# 정수로 바꿔야 하는 열. 빈칸이면 오류로 본다.
NUMBER_COLUMNS = {
    "courses": ["credits", "credits_min", "credits_max"],
    "offerings": ["grade", "semester", "school_credits"],
    "groups": ["grade", "semester", "pick_count"],
}

# 정수로 바꾸되 빈칸이면 0으로 두는 열
BLANK_AS_ZERO = {
    "offerings": ["applicants"],
    "recs": ["count"],
}

# [1단계] 추천 점수
SCORE_CORE = 3        # 고른 대학·학과의 핵심 과목
SCORE_RECOMMEND = 2   # 고른 대학·학과의 권장 과목
SCORE_SAME_FIELD = 1  # 같은 계열 다른 학과의 권장 과목
SCORE_FIELD_AREA = 1  # 계열과 잘 맞는 교과의 과목 (권장 과목 자료가 적은 학과를 위해)
HINT_PENALTY = 1      # 계획을 짤 때: 보통 먼저 듣는 과목을 아직 안 들었으면 -1

# 권장 과목 자료가 없는 학과에서 대학 칸에 보여 줄 글자
NO_UNIVERSITY = "자료 없음"

# 계열마다 잘 맞는 교과 (courses.csv의 area 값)
FIELD_AREAS = {
    "공학": ["수학", "과학", "기술·가정/정보"],
    "자연": ["수학", "과학"],
    "의약": ["과학", "수학"],
    "사회": ["사회(역사/도덕 포함)", "수학"],
    "인문": ["국어", "사회(역사/도덕 포함)", "영어", "제2외국어/한문"],
    "교육": ["국어", "사회(역사/도덕 포함)", "교양"],
}

# 계획을 짜는 학기 순서 (학년, 학기)
PLAN_TERMS = [(2, 1), (2, 2), (3, 1), (3, 2)]

# 검사 결과 수준 (앞에 있을수록 중요)
ERROR = "오류"
WARNING = "주의"
INFO = "안내"
LEVELS = [ERROR, WARNING, INFO]

# 계획 엑셀 파일의 모양
PLAN_SHEET = "계획"
ISSUE_SHEET = "검사 결과"
CHOICE_SHEET = "선택"
PLAN_HEADER = ["학년", "학기", "과목"]
