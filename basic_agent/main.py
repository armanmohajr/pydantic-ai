from pydantic import BaseModel
from pydantic_ai import Agent
from dotenv import load_dotenv

load_dotenv()

# Define the our response structure


class WeatherResponse(BaseModel):
    location: str
    temperature: str
    condition: str
    recommendation: str


weather_agent = Agent(
    model="groq:llama-3.3-70b-versatile",
    output_type=WeatherResponse,
    system_prompt=(
        "You are a helpful weather forecast agent. "
        "Provide a weather forecast, always give temperature in Fahrenheit, "
        "and always include a recommendation on what to wear."
    ),
)


# Run the agent

if __name__ == "__main__":
    result = weather_agent.run_sync(
        "What is the weather in the San Francisco").output
    # print the result
    print(f"location: {result.location}")
    print(f"temperature: {result.temperature}")
    print(f"condition: {result.condition}")
    print(f"recommendation: {result.recommendation}")
