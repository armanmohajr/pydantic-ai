import asyncio
from dataclasses import dataclass
from typing import List, Literal

from pydantic import BaseModel, Field
from pydantic_ai import Agent, RunContext
from dotenv import load_dotenv

load_dotenv()


# ------------------------
# Dependencies (Services)
# ------------------------

@dataclass
class DatabaseConn:
    """Mock database connection"""

    async def get_user_preferences(self, user_id: int) -> dict:
        return {
            "temperature_unit": "fahrenheit",
            "activity_preferences": ["hiking", "photography", "restaurants"],
        }

    async def log_recommendation(self, user_id: int, recommendation: str) -> None:
        print(
            f"[DB] Logged recommendation for user {user_id}: {recommendation}")


@dataclass
class WeatherDep:
    user_id: int
    db: DatabaseConn
    weather_api_key: str


# ------------------------
# Tool Response Models
# ------------------------

class WeatherToolData(BaseModel):
    temperature_f: float
    condition: str
    humidity_percent: int
    wind_mph: int


class UserPreferences(BaseModel):
    temperature_unit: Literal["fahrenheit", "celsius"]
    activity_preferences: List[str]


# ------------------------
# Final Agent Output Models
# ------------------------

class WeatherData(BaseModel):
    temperature: float
    condition: str
    humidity: int
    wind_speed: int


class PersonalizedWeatherResponse(BaseModel):
    weather: WeatherData
    personalized_recommendations: List[str] = Field(
        description="Actionable recommendations based on weather and user preferences"
    )
    safety_alerts: List[str] = Field(
        description="Weather-related safety warnings"
    )


# ------------------------
# Agent
# ------------------------

weather_agent = Agent(
    model="groq:llama-3.3-70b-versatile",
    deps_type=WeatherDep,
    output_type=PersonalizedWeatherResponse,
    system_prompt="""
You are an advanced weather assistant.

Rules:
- Use tools to fetch real data.
- Base recommendations on both weather and user preferences.
- Be concise, actionable, and practical.
- Always respect the output schema exactly.
""",
)


# ------------------------
# Tools
# ------------------------

@weather_agent.tool
async def get_current_weather(
    ctx: RunContext[WeatherDep],
    location: str,
) -> WeatherToolData:
    """Get structured weather data for a location."""

    mock_weather_db = {
        "san francisco": WeatherToolData(
            temperature_f=68,
            condition="partly cloudy",
            humidity_percent=65,
            wind_mph=12,
        ),
        "new york": WeatherToolData(
            temperature_f=84,
            condition="sunny",
            humidity_percent=70,
            wind_mph=8,
        ),
    }

    weather = mock_weather_db.get(location.lower())
    if not weather:
        raise ValueError(f"No weather data available for '{location}'")

    return weather


@weather_agent.tool
async def get_user_preferences(
    ctx: RunContext[WeatherDep],
) -> UserPreferences:
    """Fetch user preferences from database."""

    raw_prefs = await ctx.deps.db.get_user_preferences(ctx.deps.user_id)
    return UserPreferences(**raw_prefs)


@weather_agent.tool
async def log_interaction(
    ctx: RunContext[WeatherDep],
    recommendation: str,
) -> str:
    """Log recommendation for analytics."""

    await ctx.deps.db.log_recommendation(ctx.deps.user_id, recommendation)
    return "Logged successfully"


# ------------------------
# App Entry Point
# ------------------------

async def main() -> None:
    deps = WeatherDep(
        user_id=123,
        db=DatabaseConn(),
        weather_api_key="API_KEY",
    )

    result = await weather_agent.run(
        "I'm planning outdoor activities in San Francisco today. What do you recommend?",
        deps=deps,
    )

    print("=" * 50)
    print(f"Temperature: {result.output.weather.temperature}°F")
    print(f"Condition: {result.output.weather.condition}")
    print(f"Humidity: {result.output.weather.humidity}%")
    print(f"Wind Speed: {result.output.weather.wind_speed} mph")
    print("Recommendations:")
    for rec in result.output.personalized_recommendations:
        print(f" - {rec}")
    print("Safety Alerts:")
    for alert in result.output.safety_alerts:
        print(f" - {alert}")
    print("=" * 50)


if __name__ == "__main__":
    asyncio.run(main())
