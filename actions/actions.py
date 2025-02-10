from utils.constants import RASA_VALIDATION_REGEX_DATE, RASA_VALIDATION_REGEX_EMAIL, RASA_ACTION_BOOK_APPOINTMENT, RASA_ACTION_VALIDATE_FORM
from rasa_sdk.executor import CollectingDispatcher
from booking_handler.handler import GoogleHandler
from utils.exceptions import AuthenticationFailed
from rasa_sdk.forms import FormValidationAction
from rasa_sdk import Action, Tracker
import re


booking_handler = GoogleHandler()


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
            event_link = booking_handler.book_appointment(
                appointment_date,
                user_email,
                "tozenlabs@gmail.com", #client's email
                "Testing new module", #description
                "Module tester" #title
            )

        except AuthenticationFailed:
            dispatcher.utter_message(text="Authentication failed. Please try again.")
            return []

        if event_link:
            dispatcher.utter_message(text=f"Your appointment is scheduled! 📅 Invitation sent to {user_email}. \n[View event]({event_link})")
        else:
            dispatcher.utter_message(text="There was an issue scheduling your appointment. Please try again later.")

        return []