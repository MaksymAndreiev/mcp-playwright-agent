def get_current_date() -> str:
    """Returns today's date in YYYY/MM/DD format."""
    from datetime import datetime
    return datetime.now().strftime("%Y/%m/%d")