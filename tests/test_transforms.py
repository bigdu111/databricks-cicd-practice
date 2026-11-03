import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from transforms import clean_amount


def test_clean_amount_handles_currency():
    assert clean_amount("$1,200.50") == 1200.5


def test_clean_amount_handles_blank():
    assert clean_amount("  ") is None
