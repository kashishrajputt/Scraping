from datetime import datetime

def parse_date(date_str):
    try:
        return datetime.strptime(date_str.strip(), "%d-%m-%Y").date()
    except Exception:
        return None
