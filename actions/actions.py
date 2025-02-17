from utils.constants import *
from rasa_sdk.events import SlotSet, FollowupAction, UserUtteranceReverted
from infrastructure.database.database import Database
from reponse_handler.handler import ResponseHandler
from rasa_sdk.executor import CollectingDispatcher
from utils.exceptions import AuthenticationFailed
from booking_handler.handler import GoogleHandler
from rasa_sdk.forms import FormValidationAction
from utils.utils import format_appointment_date
from typing import Dict, Text, Any, List
from datetime import datetime, timedelta
from local_settings import BUSINESS_ID
from rasa_sdk import Action, Tracker
from utils.logger import logger
import json
import re
# ------------------------------------
# --------- WORKING HOURS & ----------
# --------   SLOT DURATION -----------
# ------------------------------------
WORK_HOURS_START = 9  # Opening
WORK_HOURS_END = 18  # Closing
SLOT_DURATION = timedelta(minutes=30)  # X-minute slots
DAYS_AHEAD = 7  # Check availability for the next X days
# ------------------------------------

# ------------------------------------
# ----------- HANDLERS ---------------
# ------------------------------------
booking_handler = GoogleHandler()
db = Database()
# ------------------------------------

# ---------------------------------------
# ----------- VALIDATIONS ---------------
# ---------------------------------------
class ValidateAppointmentForm(FormValidationAction):
    def name(self) -> str:
        self.ai_assistant = ResponseHandler()
        return RASA_ACTION_VALIDATE_FORM

    def validate_user_name(self, slot_value: str, dispatcher: CollectingDispatcher, tracker: Tracker, domain: dict) -> dict:
        if not slot_value:
            return {"appointment_date": None}
        
        curated_value = self.ai_assistant.validate_user_input(slot_value, "name")

        if len(curated_value) < 2:
            dispatcher.utter_message(text="Name must be at least 2 characters long.")
            return { "user_name": None }
        
        return { "user_name": curated_value }

    def validate_user_email(self, slot_value: str, dispatcher: CollectingDispatcher, tracker: Tracker, domain: dict) -> dict:
        if not slot_value:
            return {"appointment_date": None}
        
        curated_value = self.ai_assistant.validate_user_input(slot_value, "email")

        if not re.match(RASA_VALIDATION_REGEX_EMAIL, curated_value):
            dispatcher.utter_message(text="Invalid email format. Please enter a valid email.")
            return { "user_email": None }
        
        return { "user_email": curated_value }

    def validate_appointment_date(self, slot_value: str, dispatcher: CollectingDispatcher, tracker: Tracker, domain: dict) -> dict:
        if not slot_value:
            return {"appointment_date": None}
        
        curated_value = self.ai_assistant.validate_user_input(slot_value, "date")

        if not re.match(RASA_VALIDATION_REGEX_DATE, curated_value):
            dispatcher.utter_message(text="Invalid date format! Please use YYYY-MM-DD HH:MM (e.g., 2025-02-10 14:30).")
            return {"appointment_date": None}
        
        try:
            date_obj = datetime.strptime(curated_value, "%Y-%m-%d %H:%M")
            if date_obj < datetime.now():
                dispatcher.utter_message(text="Please select a future date and time.")
                return {"appointment_date": None}
        except ValueError:
            dispatcher.utter_message(text="Invalid date. Please provide a valid date and time.")
            return {"appointment_date": None}
        
        return {"appointment_date": curated_value}

class ValidateEmailForm(FormValidationAction):
    def name(self) -> str:
        self.ai_assistant = ResponseHandler()
        return RASA_ACTION_VALIDATE_EMAIL

    def validate_user_email(self, slot_value: str, dispatcher: CollectingDispatcher, tracker: Tracker, domain: dict) -> dict:
        if not slot_value:
            return {"appointment_date": None}
        
        curated_value = self.ai_assistant.validate_user_input(slot_value, "email")

        if not re.match(RASA_VALIDATION_REGEX_EMAIL, curated_value):
            dispatcher.utter_message(text="Invalid email format. Please enter a valid email.")
            return { "user_email": None }
        
        return { "user_email": curated_value }

class ValidateRescheduleForm(FormValidationAction):
    def name(self) -> str:
        self.ai_assistant = ResponseHandler()
        return RASA_ACTION_VALIDATE_RESCHEDULE

    def validate_user_email(self, slot_value: str, dispatcher: CollectingDispatcher, tracker: Tracker, domain: dict) -> dict:
        if not slot_value:
            return {"appointment_date": None}
        
        curated_value = self.ai_assistant.validate_user_input(slot_value, "email")

        if not re.match(RASA_VALIDATION_REGEX_EMAIL, curated_value):
            dispatcher.utter_message(text="Invalid email format. Please enter a valid email.")
            return { "user_email": None }
        
        return { "user_email": curated_value }

    def validate_appointment_date(self, slot_value: str, dispatcher: CollectingDispatcher, tracker: Tracker, domain: dict) -> dict:
        if not slot_value:
            return {"appointment_date": None}
        
        curated_value = self.ai_assistant.validate_user_input(slot_value, "date")

        if not re.match(RASA_VALIDATION_REGEX_DATE, curated_value):
            dispatcher.utter_message(text="Invalid date format! Please use YYYY-MM-DD HH:MM (e.g., 2025-02-10 14:30).")
            return {"appointment_date": None}
        
        try:
            date_obj = datetime.strptime(curated_value, "%Y-%m-%d %H:%M")
            if date_obj < datetime.now():
                dispatcher.utter_message(text="Please select a future date and time.")
                return {"appointment_date": None}
        except ValueError:
            dispatcher.utter_message(text="Invalid date. Please provide a valid date and time.")
            return {"appointment_date": None}
        
        return {"appointment_date": curated_value}
    
# ---------------------------------------

# -----------------------------------
# ----------- ACTIONS ---------------
# -----------------------------------
class ActionCheckExistingAppointments(Action):
    """
    This action checks if a user has any existing appointments and provides options
    to manage them. If appointments exist, it displays them and offers options to:
    1. Reschedule
    2. Cancel
    3. Book a new appointment

    If no appointments exist, it starts the appointment booking flow.

    Returns:
        List[Dict]: A list containing slot updates for appointment_status and
                   potentially a followup action to start the appointment form
    """
    def name(self) -> str:
        return RASA_ACTION_CHECK_EXISTING_APPOINTMENTS

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain):

        user_email = tracker.get_slot("user_email")

        existing_appointments = db.get_appointment_by_email(user_email, only_scheduled=True)

        if existing_appointments:
            logger.info(existing_appointments)
            existing_appointments = [
                appt for appt in existing_appointments
                if appt["appointment_date"] >= datetime.today()
            ]

            dispatcher.utter_message(text="I see that you have the following appointments:")
            
            for appt in existing_appointments:
                formatted_date = format_appointment_date(appt["appointment_date"])
                dispatcher.utter_message(text=f"📅 {formatted_date}")

            dispatcher.utter_message(
                text="What would you like to do?",
                buttons=[
                    {"title": "📅 Reschedule", "payload": "/request_reschedule"},
                    {"title": "❌ Cancel", "payload": "/request_cancel"},
                    {"title": "➕ Book New", "payload": "/request_booking"}
                ]
            )
        
            logger.info(f"Existing appointments for {user_email}: {existing_appointments}")
            return [SlotSet("appointment_status", "pending_action")]

        logger.info(f"No existing appointments for {user_email}")
        dispatcher.utter_message(text="Great! You don't have any scheduled appointments so let's get you one! 😄")
        return [SlotSet("appointment_status", "booking_new"), FollowupAction("appointment_form")]

class ActionBookAppointment(Action):
    """
    This action books a new appointment for a user.

    Returns:
        List[Dict]: A list containing slot updates for appointment_status and
                   potentially a followup action to start the appointment form
    """
    def name(self) -> str:
        return RASA_ACTION_BOOK_APPOINTMENT

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain):
        try:
            client_email = tracker.get_slot("user_email")
            client_name = tracker.get_slot("user_name")
            appointment_date = tracker.get_slot("appointment_date")

            if not all([client_email, client_name, appointment_date]):
                dispatcher.utter_message(text="Missing required information. Please provide email and appointment date.")
                return []

            business_id = "JOO000"
            business_name = "TheBarberShop"
            business_service = "Standard Haircut"
            business_email = "tozenlabs@gmail.com"
            business_assignee_id = "John Doe"
            business_address = "Evergreen 123, Springfield"
            appointment_title = f"{business_name} - {business_service} appointment with {business_assignee_id}"
            appointment_description = "This is a test for a booking AI agent"


            event_id = booking_handler.book_appointment(
                appointment_date,
                client_email,
                business_email, #client's email
                appointment_description, #description
                appointment_title #title
            )

            db.insert_appointment(
                client_email,
                client_name,
                appointment_date,
                event_id,
                business_id,
                business_assignee_id
            )

            logger.info(f"Appointment booked {client_email}, {client_name}, {appointment_date}, {business_id}, {DB_STATUS_SCHEDULED}")

            if event_id:
                dispatcher.utter_message(text=f"Your appointment for {appointment_date} is scheduled! 📅 Invitation sent to {client_email}.")
            else:
                dispatcher.utter_message(text="There was an issue scheduling your appointment. Please try again later.")

            return [
                SlotSet("appointment_date", None),
                SlotSet("requested_slot", None),
                SlotSet("appointment_status", "pending_action"),
                FollowupAction("action_end_flow")
            ]

        except Exception as e:
            logger.error(f"Error booking appointment: {str(e)}")
            dispatcher.utter_message(text="An unexpected error occurred. Please try again later.")
            return [
                SlotSet("appointment_date", None),
                SlotSet("requested_slot", None),
                SlotSet("appointment_status", "pending_action")
            ]

class ActionRescheduleAppointment(Action):
    """
    This action reschedules an existing appointment for a user.

    Returns:
        List[Dict]: A list containing slot updates for appointment_status and
                   potentially a followup action to start the appointment form
    """
    def name(self) -> str:
        return RASA_ACTION_RESCHEDULE_APPOINTMENT

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain):
        user_email = tracker.get_slot("user_email")
        appointment_date = tracker.get_slot("appointment_date")

        if not user_email or not appointment_date:
            dispatcher.utter_message(text="I couldn't retrieve your email or new appointment date.")
            return []

        existing_appointment = db.get_appointment_by_email(user_email, only_scheduled=True)

        try:
            latest_appointment_id = existing_appointment[0].get("appointment_id")
        except IndexError:
            dispatcher.utter_message(f"I couldn't find any existing scheduled appointments for the email {user_email}")
            return []
        
        if not existing_appointment:
            dispatcher.utter_message(text="I couldn't find any existing appointment for your email.")
            return []

        try:
            event_id = booking_handler.reschedule_appointment(
                appointment_date,
                latest_appointment_id,
            )

            db.update_appointment_status(
                event_id,
                appointment_status=DB_STATUS_SCHEDULED,
                updated_date=appointment_date
            )

        except AuthenticationFailed:
            dispatcher.utter_message(text="Authentication failed. Please try again.")
            return [
                SlotSet("appointment_date", None),
                SlotSet("requested_slot", None),
                SlotSet("appointment_status", "pending_action")
            ]
        except Exception as e:
            dispatcher.utter_message(text="There was an error rescheduling your appointment.")
            logger.error(f"Error rescheduling appointment: {str(e)}")
            return [
                SlotSet("appointment_date", None),
                SlotSet("requested_slot", None),
                SlotSet("appointment_status", "pending_action")
            ]

        logger.info(f"Appointment rescheduled. {user_email}, {appointment_date}")
        dispatcher.utter_message(text=f"Your appointment has been rescheduled! 📅 Updated invitation sent to {user_email}.")
        return [
            SlotSet("appointment_date", None),
            SlotSet("requested_slot", None),
            SlotSet("appointment_status", "pending_action")
        ]


class ActionCancelAppointment(Action):
    """
    This action reschedules an existing appointment for a user.

    Returns:
        List[Dict]: A list containing slot updates for appointment_status and
                   potentially a followup action to start the appointment form
    """
    def name(self) -> str:
        return RASA_ACTION_CANCEL_APPOINTMENT

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain):
        user_email = tracker.get_slot("user_email")

        if not user_email:
            dispatcher.utter_message(text="I couldn't retrieve your email or new appointment date.")
            return [
                SlotSet("requested_slot", None),
                SlotSet("appointment_status", "pending_action")
            ]

        
        existing_appointment = db.get_appointment_by_email(user_email, only_scheduled=True)

        try:
            appointment_id = existing_appointment[0].get("appointment_id")
        except IndexError:
            dispatcher.utter_message(text=f"I couldn't find any existing scheduled appointments for the email {user_email}")
            return [
                SlotSet("requested_slot", None),
                SlotSet("appointment_status", "pending_action")
            ]

        try:
            booking_handler.cancel_appointment(
                appointment_id
            )
            db.update_appointment_status(
                appointment_id,
                DB_STATUS_CANCELED
            )

        except AuthenticationFailed:
            dispatcher.utter_message(text="Authentication failed. Please try again.")
            return [
                SlotSet("requested_slot", None),
                SlotSet("appointment_status", "pending_action")
            ]
        except Exception as e:
            dispatcher.utter_message(text="There was an error canceling your appointment.")
            logger.error(f"Error canceling appointment: {str(e)}")
            return [
                SlotSet("requested_slot", None),
                SlotSet("appointment_status", "pending_action")
            ]

        return [
            SlotSet("requested_slot", None),
            SlotSet("appointment_status", "pending_action")
        ]

#ok
class ActionChatWithGPT(Action):
    """
    This action allows the user to chat with the GPT model.

    Returns:
        List[Dict]: A list containing slot updates for appointment_status and
                   potentially a followup action to start the appointment form
    """
    def name(self) -> str:
        self.ai_assistant = ResponseHandler()
        return RASA_ACTION_CHAT_W_GPT

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain):

        user_message = tracker.latest_message.get("text")
        logger.info(tracker.latest_message)
        
        response = self.ai_assistant.generate_response(
            user_message
        )

        dispatcher.utter_message(text=response)

        return []

class ActionGetAppointments(Action):
    """
    This action displays the user's upcoming appointments.

    Returns:
        List[Dict]: A list containing slot updates for appointment_status and
                   potentially a followup action to start the appointment form
    """
    def name(self) -> str:
        return RASA_ACTION_GET_APPOINTMENTS

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain):
        user_email = tracker.get_slot("user_email")

        appointments = db.get_appointment_by_email(user_email, only_scheduled=True)

        if not appointments:
            dispatcher.utter_message(text="No appointments found for this email.")
            return []
        
        appointments = [
            appt for appt in appointments
            if appt["appointment_date"] >= datetime.today()
        ]

        
        sorted_appointments = sorted(appointments, key=lambda appt: appt["appointment_date"])
        mapped_dates = list(map(lambda x: x["appointment_date"], sorted_appointments))

        response_message = "📅 Your Upcoming Appointments:\n\n"

        for date in mapped_dates:
            formatted_date = format_appointment_date(date)
            response_message += f"🔹 {formatted_date}\n"
        
        logger.info(f"Retrieved all appointments for {user_email}")

        dispatcher.utter_message(text=response_message)

        dispatcher.utter_message(
            text="What would you like to do?",
            buttons=[
                {"title": "📅 Reschedule", "payload": "/request_reschedule"},
                {"title": "❌ Cancel", "payload": "/request_cancel"},
                {"title": "➕ Book New", "payload": "/request_booking"}
            ]
        )

        return [
            SlotSet("requested_slot", None),
            SlotSet("appointment_status", "pending_action")
        ]

#ok
class ActionProcessOption(Action):
    """
    This action processes the user's choice from the list of options.

    Returns:
        List[Dict]: A list containing slot updates for appointment_status and
                   potentially a followup action to start the appointment form
    """
    def name(self):
        return RASA_ACTION_PROCESS_OPTION

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]):
        user_choice = tracker.latest_message.get("text")

        if user_choice == "1":
            dispatcher.utter_message(text="Let's reschedule your appointment.")
            return [SlotSet("appointment_status", "reschedule"), FollowupAction("reschedule_form")]

        elif user_choice == "2":
            return [SlotSet("appointment_status", "canceled"), FollowupAction("action_cancel_appointment")]

        elif user_choice == "3":
            dispatcher.utter_message(text="Alright! Let's book a new appointment.")
            return [SlotSet("appointment_status", "booking_new"), FollowupAction("appointment_form")]

        else:
            dispatcher.utter_message(text="I didn't understand that. Please enter any of the 3 options.")
            return []

class ActionGetAvailableAppointments(Action):
    def name(self) -> str:
        return "action_get_available_appointments"

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict) -> List[Dict]:
        user_email = tracker.get_slot("user_email")

        # Fetch existing appointments from the database
        existing_appointments = db.get_appointment_by_email(user_email, only_scheduled=True)
        
        if not existing_appointments: 
            existing_appointments = []
        
        logger.info(f"\nHERE!!\n{existing_appointments}\n\n")
        # Convert existing appointments to a dictionary for quick lookup
        booked_slots = self.process_booked_slots(existing_appointments)

        # Generate available slots
        available_slots = self.get_available_slots(booked_slots)

        if available_slots:
            message = "Here are the available appointment slots:\n"
            for day, times in available_slots.items():
                formatted_times = ", ".join(times)
                message += f"📅 {day}: {formatted_times}\n"
        else:
            message = "No available slots found in the next 7 days. 😞"

        dispatcher.utter_message(text=message)
        return []
    
    def process_booked_slots(self, appointments) -> Dict[str, List[str]]:
        """
        Process the booked slots and return a dictionary {date: [booked_times]}.
        Filters out past appointments.
        """
        booked_slots = {}

        now = datetime.now()

        for appt in appointments:
            date_str = appt["appointment_date"].strftime("%Y-%m-%d")
            time_str = appt["appointment_date"].strftime("%H:%M")

            # Convert appointment date and time to a datetime object
            appt_datetime = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M")

            # Ignore past appointments
            if appt_datetime < now:
                continue

            if date_str not in booked_slots:
                booked_slots[date_str] = []

            booked_slots[date_str].append(time_str)

        return booked_slots
    
    def get_available_slots(self, booked_slots: Dict[str, List[str]]) -> Dict[str, List[str]]:
        """
        Generates all possible slots for the next 7 days and filters out the booked ones.
        Returns available slots as a dictionary {date: [available_times]}.
        """
        today = datetime.today()
        available_slots = {}

        for day_offset in range(DAYS_AHEAD):
            current_day = today + timedelta(days=day_offset)

            # Skip weekends
            if current_day.weekday() >= 5:
                continue

            date_str = current_day.strftime("%Y-%m-%d")
            available_slots[date_str] = []

            start_time = datetime(current_day.year, current_day.month, current_day.day, WORK_HOURS_START, 0)
            end_time = datetime(current_day.year, current_day.month, current_day.day, WORK_HOURS_END, 0)

            current_time = start_time
            while current_time < end_time:
                time_str = current_time.strftime("%H:%M")

                # Ensure slots are in future
                if current_time > datetime.now():

                    # Check if the slot is available (does not overlap with booked slots)
                    if date_str not in booked_slots or not self.is_overlapping(time_str, booked_slots.get(date_str)):
                        available_slots[date_str].append(time_str)

                current_time += SLOT_DURATION  # Move to the next 30-minute slot

            if not available_slots[date_str]:
                del available_slots[date_str]  # Remove empty days

        return available_slots

    def is_overlapping(self, slot: str, booked_times: List[str]) -> bool:
        """
        Checks if a given time slot overlaps with any existing booked slots.
        Ensures a 30-minute gap after any booking.
        """
        slot_time = datetime.strptime(slot, "%H:%M")

        for booked_time in booked_times:
            booked_time_dt = datetime.strptime(booked_time, "%H:%M")

            # If the slot is within 30 minutes after an existing booking, it is not available
            #   14:00   14:30   15:00
            if booked_time_dt - (SLOT_DURATION*0.75) <= slot_time < booked_time_dt + SLOT_DURATION:
                logger.info(f"Booked_time: {booked_time_dt}")
                logger.info(f"Checking slot: {slot_time}")
                logger.info(f"End booked_time: {booked_time_dt + SLOT_DURATION}\n")
                return True

        return False

#ok
class ActionEndFlow(Action):
    """
    This action checks if a user has any existing appointments and provides options
    to manage them. If appointments exist, it displays them and offers options to:
    1. Reschedule
    2. Cancel
    3. Book a new appointment

    If no appointments exist, it starts the appointment booking flow.

    Returns:
        List[Dict]: A list containing slot updates for appointment_status and
                   potentially a followup action to start the appointment form
    """
    def name(self) -> str:
        return "action_end_flow"

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain):

        dispatcher.utter_message(
            text="Thank you for using our AI asistant for managing your appointments.\nI'll leave some useful links below 👇🏼\n",
            buttons=[
                {"title": "📅 See my appointment details", "payload": "/get_existing_appointments"},
                {"title": "🌐 Visit website", "url": "https://www.example.com", "type": "web_url"},
                {"title": "ℹ️ Appointment pre-requisites", "payload": "/request_pre_requisites"}
            ]
        )
    
        return [SlotSet("appointment_status", None)]

#ok
class ActionTest(Action):
    """
    Testing list
    """
    def name(self) -> str:
        return "action_test_func"

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain):
        
        response = db.get_business("HEN000")
        logger.info(response.get("id"))
        logger.info(response.get("business_name"))
        for x in json.loads(response.get("employees")):
            logger.info(x.get("name"))
            logger.info(bool(x.get("available")))
            logger.info("\n")
            
        logger.info(response.get("services"))
        dispatcher.utter_message(
            text=f"{response}",
        )
    
        return [SlotSet("appointment_status", None)]
# -----------------------------------