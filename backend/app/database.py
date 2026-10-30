from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from app.config import settings

# Configure SQLite or PostgreSQL
if settings.DATABASE_URL.startswith("sqlite"):
    engine = create_engine(
        settings.DATABASE_URL,
        connect_args={"check_same_thread": False}
    )
else:
    engine = create_engine(
        settings.DATABASE_URL,
        pool_pre_ping=True
    )

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def ensure_schema_compatibility():
    """Ensure optional columns exist in existing SQLite databases."""
    try:
        from sqlalchemy import text
        with engine.connect() as conn:
            # Concepts columns
            res = conn.execute(text("PRAGMA table_info(concepts)"))
            concept_cols = {row[1] for row in res.fetchall()}
            if concept_cols and "core_concepts" not in concept_cols:
                conn.execute(text("ALTER TABLE concepts ADD COLUMN core_concepts TEXT DEFAULT '[]'"))
                conn.commit()
            if concept_cols and "confusing_topics" not in concept_cols:
                conn.execute(text("ALTER TABLE concepts ADD COLUMN confusing_topics TEXT DEFAULT '[]'"))
                conn.commit()

            # Checkpoint Attempts columns
            res_att = conn.execute(text("PRAGMA table_info(checkpoint_attempts)"))
            att_cols = {row[1] for row in res_att.fetchall()}
            if att_cols and "attempt_number" not in att_cols:
                conn.execute(text("ALTER TABLE checkpoint_attempts ADD COLUMN attempt_number INTEGER DEFAULT 1"))
                conn.commit()

            # Checkpoints columns
            res_chk = conn.execute(text("PRAGMA table_info(checkpoints)"))
            chk_cols = {row[1] for row in res_chk.fetchall()}
            if chk_cols and "source_excerpt" not in chk_cols:
                conn.execute(text("ALTER TABLE checkpoints ADD COLUMN source_excerpt TEXT DEFAULT NULL"))
                conn.commit()
            if chk_cols and "source_timestamp" not in chk_cols:
                conn.execute(text("ALTER TABLE checkpoints ADD COLUMN source_timestamp FLOAT DEFAULT NULL"))
                conn.commit()

            # Lectures columns
            res_lec = conn.execute(text("PRAGMA table_info(lectures)"))
            lec_cols = {row[1] for row in res_lec.fetchall()}
            if lec_cols and "transcription_status" not in lec_cols:
                conn.execute(text("ALTER TABLE lectures ADD COLUMN transcription_status VARCHAR(50) DEFAULT 'ready'"))
                conn.commit()
            if lec_cols and "processing_error" not in lec_cols:
                conn.execute(text("ALTER TABLE lectures ADD COLUMN processing_error TEXT DEFAULT NULL"))
                conn.commit()
    except Exception as e:
        print(f"[Database] Schema compatibility warning: {e}")

ensure_schema_compatibility()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
