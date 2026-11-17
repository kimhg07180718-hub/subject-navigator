"""[F6]·[데이터] 엑셀 저장과 CSV 읽기 예외 처리를 확인한다."""
import os
import shutil

import pytest
from openpyxl import load_workbook

from app import load_all, save_plan


def test_save_plan(tmp_path):
    """저장한 엑셀 파일에 계획, 검사 결과, 고른 진로가 시트마다 들어 있어야 한다."""
    plan = [("미적분Ⅰ", 2, 2), ("미적분Ⅱ", 3, 1)]
    path = tmp_path / "plan.xlsx"
    save_plan(plan, [("주의", "예시 메시지")], path, {"학과": "컴퓨터공학", "대학": "연세대"})
    wb = load_workbook(path)
    assert list(wb["계획"].iter_rows(values_only=True)) == [("학년", "학기", "과목"), (2, 2, "미적분Ⅰ"), (3, 1, "미적분Ⅱ")]
    assert list(wb["검사 결과"].iter_rows(values_only=True)) == [("수준", "메시지"), ("주의", "예시 메시지")]
    assert list(wb["선택"].iter_rows(values_only=True)) == [("학과", "컴퓨터공학"), ("대학", "연세대")]


def test_missing_data_file(tmp_path):
    """data 폴더에 CSV가 없으면 파일 이름을 알려 주는 FileNotFoundError."""
    with pytest.raises(FileNotFoundError, match="courses.csv"):
        load_all(tmp_path)


def copy_data(tmp_path):
    """실제 data 폴더의 CSV 5개를 임시 폴더에 복사한다."""
    folder = os.path.join(os.path.dirname(__file__), "..", "data")
    for name in ["courses.csv", "offerings.csv", "groups.csv", "majors.csv", "recommendations.csv"]:
        shutil.copy(os.path.join(folder, name), tmp_path / name)


def test_number_error_shows_line(tmp_path):
    """학점 칸에 글자가 있으면 몇 번째 줄인지 알려 주는 ValueError."""
    copy_data(tmp_path)
    lines = (tmp_path / "groups.csv").read_text(encoding="utf-8-sig").splitlines()
    lines[2] = lines[2].replace(",4,", ",네,", 1)  # 3번째 줄의 pick_count를 글자로
    (tmp_path / "groups.csv").write_text("\n".join(lines), encoding="utf-8-sig")
    with pytest.raises(ValueError, match="groups.csv 3번째 줄"):
        load_all(tmp_path)


def test_offering_name_typo(tmp_path):
    """개설표에 courses.csv에 없는 과목 이름(오타)이 있으면 줄 번호와 함께 알려 준다."""
    copy_data(tmp_path)
    text = (tmp_path / "offerings.csv").read_text(encoding="utf-8-sig")
    (tmp_path / "offerings.csv").write_text(text.replace("미적분Ⅱ", "미적분 2", 1), encoding="utf-8-sig")
    with pytest.raises(ValueError, match="offerings.csv"):
        load_all(tmp_path)


def test_repeated_group_row(tmp_path):
    """groups.csv에 같은 선택군 줄이 두 번 있으면 알려 준다."""
    copy_data(tmp_path)
    lines = (tmp_path / "groups.csv").read_text(encoding="utf-8-sig").splitlines()
    lines.append(lines[1])  # 첫 선택군 줄을 한 번 더
    (tmp_path / "groups.csv").write_text("\n".join(lines), encoding="utf-8-sig")
    with pytest.raises(ValueError, match="앞에도 있어요"):
        load_all(tmp_path)


def test_recommendation_name_typo(tmp_path):
    """권장 과목 이름에 오타가 있으면 '열리지 않아요'로 잘못 안내하지 않고 줄 번호를 알려 준다."""
    copy_data(tmp_path)
    text = (tmp_path / "recommendations.csv").read_text(encoding="utf-8-sig")
    (tmp_path / "recommendations.csv").write_text(text.replace("기하", "기하학", 1), encoding="utf-8-sig")
    with pytest.raises(ValueError, match="recommendations.csv .*기하학"):
        load_all(tmp_path)
