from pydantic_ai import Agent
from dotenv import load_dotenv
load_dotenv()

agent = Agent(
    model="gateway/groq:llama-3.3-70b-versatile"
)
