"""Plain Python logic, kept out of notebooks so CI can unit test it."""


def clean_amount(value):
    """Turn strings like '$1,200.50' into 1200.5. Returns None for blanks."""
    if value is None or str(value).strip() == "":
        return None
    return float(str(value).replace("$", "").replace(",", ""))
