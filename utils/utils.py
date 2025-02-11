from datetime import datetime

def format_appointment_date(date_str: str) -> str:
    """Format date string into human-readable format."""
    return datetime.strptime(date_str, "%Y-%m-%d %H:%M").strftime("%A %d %B %Y at %H:%M")