from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    PROJECT_NAME: str = "VibeFlow ML Backend"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"
    DATABASE_URL: str = "sqlite:///./vibeflow_ml.db"

    class Config:
        env_file = ".env"

settings = Settings()
