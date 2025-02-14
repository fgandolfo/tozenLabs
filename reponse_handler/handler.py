from utils.logger import logger
import openai
from local_settings import OPENAI_API_KEY
from datetime import datetime

class ResponseHandler:

    def __init__(self) -> None:
        self.client = openai.OpenAI(api_key=OPENAI_API_KEY)
        
        self.role_user = {
            "role": "user",
            "content": None
        }
        self.model = "gpt-4"

    def generate_response(self, message):
        self.role_user["content"] = message
        
        self.role_agent = {
            "role": "system",
            "content": """
            You are a helpful appointment booking assistant working for a barber business.
            The user normally has questions regarding their bookings, possibility to reschedule or cancel an appointment, and the address of the business.
            """
        }
        
        generated_response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                self.role_agent,
                self.role_user    
            ],
        )

        response = generated_response.choices[0].message.content
        logger.info(generated_response.json())
        return response
    
    def validate_user_input(self, user_input, validation_type):
        
        slot_validation = {
            "date": {
                "user_example": "For this wednesday, Next Wednesday at 12pm, Thursday 13 at 9am",
                "format_example": "2025-02-15 15:00"
            },
            "name": {
                "user_example": "My name is John Doe, John Doe, Sure, my name is John Doe.",
                "format_example": "John Doe"
            },
            "email": {
                "user_example": "Sure, my email is test@email.com, My email is test@email.com",
                "format_example": "test@email.com"
            },
        }
        self.role_agent = {
            "role": "system",
            "content":f"""
            You are a data validator. The user inputs a message and
            your job is to parse the message and return the data that you
            are validating in a format that the agent can then use. The validation
            type is {validation_type}
            Below are some user examples and some format examples so that you understand what is expected:
            - User example: {slot_validation.get(validation_type).get("user_example")}
            - Format example: {slot_validation.get(validation_type).get("format_example")}
            
            You should only return a response that follows the format example since it will be used later
            as a variable. For the date validation, please take into account the current date and time for the
            user input parsing. Current date is {datetime.strftime(datetime.today().date(), "%A %d %B %Y at %H:%M")}
            """   
        }

        self.role_user["content"] = user_input

        generated_response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                self.role_agent,
                self.role_user    
            ],
        )

        response = generated_response.choices[0].message.content
        return response