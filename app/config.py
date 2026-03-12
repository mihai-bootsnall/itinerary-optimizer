from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    anthropic_api_key: str = ""
    ai_model: str = "claude-sonnet-4-6"
    ai_max_tokens: int = 8192
    max_legs_per_search: int = 6
    recommended_max_legs: int = 4

    model_config = {"env_prefix": "ITINERARY_", "env_file": ".env"}


settings = Settings()
