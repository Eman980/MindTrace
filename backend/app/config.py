import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    PROJECT_NAME: str = "MindTrace"
    PROJECT_TAGLINE: str = "Understand What You Understand"
    API_V1_PREFIX: str = "/api/v1"

    # Database
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./mindtrace.db")

    # Security & Auth
    SECRET_KEY: str = os.getenv("SECRET_KEY", "mindtrace_fyp_university_secret_key_change_in_prod_2026")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days

    # External APIs
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")

    # Storage
    UPLOAD_DIR: str = os.getenv("UPLOAD_DIR", os.path.join(os.path.dirname(os.path.dirname(__file__)), "uploads"))
    MAX_FILE_SIZE_MB: int = 250

    # Behavioural tracking & Misconception scoring
    REPLAY_THRESHOLD: int = 3

    # Signal Weights
    POINT_INCORRECT_CHECKPOINT: int = 2
    POINT_VAGUE_CHECKPOINT: int = 1
    POINT_REPLAY_EXCEEDED: int = 2
    POINT_MARKED_UNRESOLVED: int = 3
    POINT_REPEATED_CONFUSION: int = 2

    # Severity Levels
    SEVERITY_LOW_MAX: int = 2
    SEVERITY_MED_MAX: int = 5
    # >= 6 is High

    # ── Evidence-Based Resolution Thresholds ───────────────────────────────────
    # All configurable via .env so E4 sensitivity analysis can vary them without
    # touching code. Defaults match the brief.
    #
    # N_PASS: how many correct passes (on reworded/transfer items, each with
    #   explanation_verdict=valid and confidence >= CONFIDENCE_FLOOR) are needed
    #   before a misconception can be marked Resolved.
    N_PASS: int = int(os.getenv("N_PASS", "2"))

    # MIN_DELAY_HOURS: at least one of the N_PASS passes must arrive this many
    #   hours AFTER the intervention was shown, to count toward resolution.
    #   Set DEMO_DELAY_HOURS in .env for short in-lab demos.
    MIN_DELAY_HOURS: float = float(os.getenv("MIN_DELAY_HOURS", "72"))    # 3 days
    DEMO_DELAY_HOURS: float = float(os.getenv("DEMO_DELAY_HOURS", "1"))   # 1 hr for demo

    # CONFIDENCE_FLOOR: minimum student-reported confidence (1-3) that counts
    #   toward a pass. Answers below this are recorded but not counted.
    CONFIDENCE_FLOOR: int = int(os.getenv("CONFIDENCE_FLOOR", "2"))

    # Use demo delay instead of full delay? Toggle via .env (1=yes, 0=no)
    USE_DEMO_DELAY: bool = bool(int(os.getenv("USE_DEMO_DELAY", "0")))

    class Config:
        env_file = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")
        extra = "allow"

    @property
    def effective_delay_hours(self) -> float:
        """Return whichever delay threshold is active."""
        return self.DEMO_DELAY_HOURS if self.USE_DEMO_DELAY else self.MIN_DELAY_HOURS

settings = Settings()

# Ensure uploads directory exists
os.makedirs(settings.UPLOAD_DIR, exist_ok=True)

