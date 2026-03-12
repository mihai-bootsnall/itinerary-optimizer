from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    ai_provider: str = "anthropic"
    anthropic_api_key: str = ""
    openai_api_key: str = ""
    google_api_key: str = ""
    ai_model: str = ""
    ai_max_tokens: int = 8192
    max_legs_per_search: int = 6
    recommended_max_legs: int = 4
    default_strategies: str = ""

    model_config = {"env_prefix": "ITINERARY_", "env_file": ".env"}


settings = Settings()
