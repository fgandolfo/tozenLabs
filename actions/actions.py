from utils.constants import RASA_VALIDATION_REGEX_DATE, RASA_VALIDATION_REGEX_EMAIL, RASA_ACTION_BOOK_APPOINTMENT, RASA_ACTION_VALIDATE_FORM, RASA_ACTION_CHAT_W_GPT, RASA_ACTION_RESCHEDULE_APPOINTMENT
from rasa_sdk.executor import CollectingDispatcher
from booking_handler.handler import GoogleHandler
from utils.exceptions import AuthenticationFailed
from rasa_sdk.forms import FormValidationAction
from rasa_sdk import Action, Tracker
from reponse_handler.handler import ResponseHandler
from utils.logger import logger
import re
from infrastructure.database.database import Database

booking_handler = GoogleHandler()
db = Database()

class ValidateAppointmentForm(FormValidationAction):
    def name(self) -> str:
        return RASA_ACTION_VALIDATE_FORM

    def validate_user_name(self, slot_value: str, dispatcher: CollectingDispatcher, tracker: Tracker, domain: dict) -> dict:
        if len(slot_value) < 2:
            dispatcher.utter_message(text="Name must be at least 2 characters long.")
            return { "user_name": None }
        
        return { "user_name": slot_value }

    def validate_user_email(self, slot_value: str, dispatcher: CollectingDispatcher, tracker: Tracker, domain: dict) -> dict:
        if not re.match(RASA_VALIDATION_REGEX_EMAIL, slot_value):
            dispatcher.utter_message(text="Invalid email format. Please enter a valid email.")
            return { "user_email": None }
        
        return { "user_email": slot_value }

    def validate_appointment_date(self, slot_value: str, dispatcher: CollectingDispatcher, tracker: Tracker, domain: dict) -> dict:
        if not re.match(RASA_VALIDATION_REGEX_DATE, slot_value):
            dispatcher.utter_message(text="Invalid date format! Please use YYYY-MM-DD HH:MM (e.g., 2025-02-10 14:30).")
            return { "appointment_date": None }
        
        return { "appointment_date": slot_value }

class ActionBookAppointment(Action):
    
    def name(self) -> str:
        return RASA_ACTION_BOOK_APPOINTMENT

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain):
        
        user_email = tracker.get_slot("user_email")
        user_name = tracker.get_slot("user_name")
        appointment_date = tracker.get_slot("appointment_date")

        if not user_email or not appointment_date:
            dispatcher.utter_message(text="I couldn't retrieve your email or appointment date.")
            return []

        try:
            event_id = booking_handler.book_appointment(
                appointment_date,
                user_email,
                "tozenlabs@gmail.com", #client's email
                "Testing new module", #description
                "Module tester" #title
            )

            db.insert_appointment(
                user_email,
                appointment_date,
                "scheduled",
                event_id
            )

            logger.info(db.get_all_appointments())

        except AuthenticationFailed:
            dispatcher.utter_message(text="Authentication failed. Please try again.")
            return []

        if event_id:
            dispatcher.utter_message(text=f"Your appointment for {appointment_date} is scheduled! 📅 Invitation sent to {user_email}.")
        else:
            dispatcher.utter_message(text="There was an issue scheduling your appointment. Please try again later.")

        return []

class ActionRescheduleAppointment(Action):
    def name(self) -> str:
        return RASA_ACTION_RESCHEDULE_APPOINTMENT

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain):
        user_email = tracker.get_slot("user_email")
        appointment_date = tracker.get_slot("appointment_date")

        if not user_email or not appointment_date:
            dispatcher.utter_message(text="I couldn't retrieve your email or new appointment date.")
            return []

        existing_appointment = db.get_appointment_by_email(user_email)
        if not existing_appointment:
            dispatcher.utter_message(text="I couldn't find any existing appointment for your email.")
            return []

        try:
            event_id = booking_handler.reschedule_appointment(
                appointment_date,
                existing_appointment["event_id"],
            )

            # Update the appointment in the database
            db.update_appointment(
                existing_appointment["event_id"],
                appointment_date
            )

        except AuthenticationFailed:
            dispatcher.utter_message(text="Authentication failed. Please try again.")
            return []
        except Exception as e:
            dispatcher.utter_message(text="There was an error rescheduling your appointment.")
            logger.error(f"Error rescheduling appointment: {str(e)}")
            return []

        dispatcher.utter_message(text=f"Your appointment has been rescheduled! 📅 Updated invitation sent to {user_email}.")
        return []

class ActionChatWithGPT(Action):

    def name(self) -> str:
        return RASA_ACTION_CHAT_W_GPT

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain):

        user_message = tracker.latest_message.get("text")
        logger.info(tracker.latest_message)

        response = ResponseHandler().generate_response(
            user_message
        )

        dispatcher.utter_message(text=response)

        return []