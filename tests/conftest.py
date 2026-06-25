from collections.abc import Iterator
from pathlib import Path
import shutil
import uuid

import pytest


@pytest.fixture
def tmp_path() -> Iterator[Path]:
    base_path = Path(".test-tmp")
    base_path.mkdir(exist_ok=True)
    test_path = base_path / uuid.uuid4().hex
    test_path.mkdir()

    yield test_path

    shutil.rmtree(test_path, ignore_errors=True)
