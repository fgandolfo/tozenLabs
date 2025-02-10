

GOOGLE_AUTH_SCOPES = ['https://www.googleapis.com/auth/calendar']

RASA_VALIDATION_REGEX_EMAIL = r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$"
RASA_VALIDATION_REGEX_DATE = r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}$"

RASA_ACTION_VALIDATE_FORM = "validate_appointment_form"
RASA_ACTION_BOOK_APPOINTMENT = "action_book_appointment"
RASA_ACTION_RESCHEDULE_APPOINTMENT = ""
RASA_ACTION_CANCEL_APPOINTMENT = ""
