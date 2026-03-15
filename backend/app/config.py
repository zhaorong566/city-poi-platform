from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    database_url: str = "postgresql://poi:poipass@localhost:5432/poiplatform"
    redis_url: str = "redis://localhost:6379"

    class Config:
        env_file = ".env"

settings = Settings()