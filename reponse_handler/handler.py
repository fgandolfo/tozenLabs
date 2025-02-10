from utils.logger import logger
import openai
from local_settings import OPENAI_API_KEY

class ResponseHandler:

    def __init__(self) -> None:
        self.client = openai.OpenAI(api_key=OPENAI_API_KEY)

        self.role_agent = {
            "role": "system",
            "content": """
            You are a helpful appointment booking assistant working for a barber business.
            The user normally has questions regarding their bookings, possibility to reschedule or cancel an appointment, and the address of the business.
            """
        }
        self.role_user = {
            "role": "user",
            "content": None
        }
        self.model = "gpt-4"

    def generate_response(self, message):
        self.role_user["content"] = message
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