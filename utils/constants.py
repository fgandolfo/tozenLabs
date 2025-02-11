

GOOGLE_AUTH_SCOPES = ['https://www.googleapis.com/auth/calendar']

RASA_VALIDATION_REGEX_EMAIL = r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$"
RASA_VALIDATION_REGEX_DATE = r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}$"

RASA_ACTION_VALIDATE_FORM = "validate_appointment_form"
RASA_ACTION_BOOK_APPOINTMENT = "action_book_appointment"
RASA_ACTION_CHAT_W_GPT = "action_chat_with_gpt"
RASA_ACTION_RESCHEDULE_APPOINTMENT = "action_reschedule_appointment"
RASA_ACTION_CANCEL_APPOINTMENT = "action_cancel_appointment"
RASA_ACTION_CHECK_EXISTING_APPOINTMENTS = "action_check_existing_appointments"
RASA_ACTION_GET_APPOINTMENTS = "action_get_appointments"
RASA_ACTION_PROCESS_OPTION = "action_process_option"

DB_STATUS_DONE = "DONE"
DB_STATUS_SCHEDULED = "SCHEDULED"
DB_STATUS_CANCELED = "CANCELED"
