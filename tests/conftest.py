"""테스트마다 실제 data 폴더의 CSV를 읽어 쓴다."""
import os

import pytest

from app import load_all

DATA_FOLDER = os.path.join(os.path.dirname(__file__), "..", "data")


@pytest.fixture
def data():
    return load_all(DATA_FOLDER)
