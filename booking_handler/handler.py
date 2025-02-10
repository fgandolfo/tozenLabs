from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
import pickle
import os
from utils.constants import GOOGLE_AUTH_SCOPES
from utils.logger import logger
from googleapiclient.discovery import build
from datetime import datetime, timedelta
from utils.exceptions import AuthenticationFailed

class GoogleHandler:

    def __init__(self) -> None: 
        self.creds = None
        self.__TOKEN_PICKLE__ = "token.pickle"

    def authenticate(self):
        """
        Authenticate user via OAuth
        and save credentials
        """
        current_dir = os.path.dirname(os.path.abspath(__file__))  # Get actions.py's directory
        credentials_path = os.path.join(current_dir, "credentials.json")
        
        if not os.path.exists(credentials_path):
            raise FileNotFoundError(f"❌ credentials.json file not found at {credentials_path}")

        if os.path.exists(self.__TOKEN_PICKLE__):
            with open(self.__TOKEN_PICKLE__, "rb") as token:
                self.creds = pickle.load(token)

        if not self.creds or not self.creds.valid:
            if self.creds and self.creds.expired and self.creds.refresh_token:
                self.creds.refresh(Request())
            
            else:
                flow = InstalledAppFlow.from_client_secrets_file(credentials_path, GOOGLE_AUTH_SCOPES)
                self.creds = flow.run_local_server(port=0)

            with open(self.__TOKEN_PICKLE__, "wb") as token:
                pickle.dump(self.creds, token)
        
        if not self.creds:
            raise AuthenticationFailed

    def book_appointment(self, start_time, email_attendee, email_client, description, title, address=None, duration_mins=60):
        """
        Creates an event with the user as an attendee
        """
        try:
            self.authenticate()
        except AuthenticationFailed:
            raise
        
        try:
            service = build(
                "calendar",
                "v3",
                credentials=self.creds
                )

            start_datetime = datetime.strptime(start_time, "%Y-%m-%d %H:%M")
            end_datetime = start_datetime + timedelta(minutes=duration_mins)

            event = {
                "summary": title,
                "description": description,
                "start": {
                    "dateTime": start_datetime.isoformat(),
                    "timeZone": "UTC"
                },
                "end": {
                    "dateTime": end_datetime.isoformat(),
                    "timeZone": "UTC"
                },
                "attendees": [
                    {
                        "email": email_attendee
                    },
                    {
                        "email": email_client
                    }
                ],
                "reminders": {
                    "useDefault": True
                },
            }

            event_result = service.events().insert(calendarId="primary", body=event).execute()
            logger.info(f"{event_result}")
            # {
            #     'kind': 'calendar#event', 
            #     'etag': '"3478400032724000"', 
            #     'id': '9v324isvn89v7afgso2oohefac', 
            #     'status': 'confirmed', 
            #     'htmlLink': 'https://www.google.com/calendar/event?eid=OXYzMjRpc3ZuODl2N2FmZ3NvMm9vaGVmYWMgZmFjdS5nYW5kb2xmb0Bt', 
            #     'created': '2025-02-10T15:06:56.000Z', 
            #     'updated': '2025-02-10T15:06:56.362Z', 
            #     'summary': 'Module tester', 
            #     'description': 'Testing new module', 
            #     'creator': {
            #         'email': 'facu.gandolfo@gmail.com',
            #         'self': True
            #     }, 
            #     'organizer': {
            #         'email': 'facu.gandolfo@gmail.com', 
            #         'self': True
            #     }, 
            #     'start': {
            #         'dateTime': '2025-02-10T18:00:00+01:00', 
            #         'timeZone': 'UTC'
            #     }, 
            #     'end': {
            #         'dateTime': '2025-02-10T19:00:00+01:00',
            #         'timeZone': 'UTC'
            #     }, 
            #     'iCalUID': '9v324isvn89v7afgso2oohefac@google.com',
            #     'sequence': 0, 
            #     'attendees': [
            #             {
            #                 'email': 'facu.gandolfo@gmail.com', 'organizer': True, 'self': True, 'responseStatus': 'needsAction'
            #             },
            #             {
            #                 'email': 'tozenlabs@gmail.com', 'responseStatus': 'needsAction'
            #             }
            #         ],
            #     'reminders': {
            #         'useDefault': True
            #     }, 
            #     'eventType': 'default'
            # }
            return event_result.get("id")

        except Exception as e:
            print(f"Error creating calendar event: {e}")
            return None

    def reschedule_appointment(self, start_time, event_id, duration_mins=60, calendar_id="primary"):
        """
        Reschedules an existing event
        """
        try:
            self.authenticate()
        except AuthenticationFailed:
            raise
        
        try:
            service = build(
                "calendar",
                "v3",
                credentials=self.creds
                )

            start_datetime = datetime.strptime(start_time, "%Y-%m-%d %H:%M")
            end_datetime = start_datetime + timedelta(minutes=duration_mins)
            
            event = service.events().get(calendarId=calendar_id, eventId=event_id).execute()
            event["start"] = {
                "dateTime": start_datetime.isoformat(),
                "timeZone": "UTC"
            }
            event["end"] = {
                "dateTime": end_datetime.isoformat(),
                "timeZone": "UTC"
            }

            updated_appointment =  service.events().update(calendarId=calendar_id, eventId=event_id, body=event).execute()

            return updated_appointment

        except Exception as e:
            logger.error(f"Error rescheduling event: {e}")
            return None

    def cancel_appointment(self, event_id, calendar_id="primary"):
        """
        Deletes an existing event
        """
        try:
            self.authenticate()
        except AuthenticationFailed:
            raise
        
        try:
            service = build(
                "calendar",
                "v3",
                credentials=self.creds
                )
            
            service.events().delete(calendarId=calendar_id, eventId=event_id).execute()

        except Exception as e:
            logger.error(f"Error rescheduling event: {e}")
            return None