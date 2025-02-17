from datetime import datetime

def format_appointment_date(date_str) -> str:
    """Format date string into human-readable format."""
    return date_str.strftime("%A %d %B %Y at %H:%M")