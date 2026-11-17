from sqlalchemy import create_engine, event
from sqlalchemy.orm import declarative_base, sessionmaker
from app.config import settings

# Configure SQLite or PostgreSQL
db_url = getattr(settings, "DATABASE_URL_NORMALIZED", settings.DATABASE_URL)
if db_url.startswith("sqlite"):
    engine = create_engine(
        db_url,
        connect_args={"check_same_thread": False}
    )

    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()
else:
    engine = create_engine(
        db_url,
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
            if lec_cols and "processing_status" not in lec_cols:
                conn.execute(text("ALTER TABLE lectures ADD COLUMN processing_status VARCHAR(50) DEFAULT 'ready'"))
                conn.commit()
            if lec_cols and "progress" not in lec_cols:
                conn.execute(text("ALTER TABLE lectures ADD COLUMN progress INTEGER DEFAULT 100"))
                conn.commit()
            if lec_cols and "error_message" not in lec_cols:
                conn.execute(text("ALTER TABLE lectures ADD COLUMN error_message TEXT DEFAULT NULL"))
                conn.commit()
            if lec_cols and "processing_error" not in lec_cols:
                conn.execute(text("ALTER TABLE lectures ADD COLUMN processing_error TEXT DEFAULT NULL"))
                conn.commit()
            if lec_cols and "file_hash" not in lec_cols:
                conn.execute(text("ALTER TABLE lectures ADD COLUMN file_hash VARCHAR(64) DEFAULT NULL"))
                conn.commit()
            if lec_cols:
                conn.execute(text("DROP INDEX IF EXISTS idx_lectures_file_hash"))
                conn.execute(text("CREATE UNIQUE INDEX IF NOT EXISTS uq_lectures_user_file_hash ON lectures(user_id, file_hash)"))
                conn.execute(text("""
                    UPDATE lectures 
                    SET processing_status = 'ready', progress = 100 
                    WHERE (processing_status IS NULL OR processing_status = '' OR processing_status = 'uploaded')
                      AND (status = 'ready' OR status = 'completed' OR id IN (SELECT DISTINCT lecture_id FROM concepts))
                """))
                conn.commit()

            # Misconceptions lifecycle columns
            res_misc = conn.execute(text("PRAGMA table_info(misconceptions)"))
            misc_cols = {row[1] for row in res_misc.fetchall()}
            if misc_cols and "improving_at" not in misc_cols:
                conn.execute(text("ALTER TABLE misconceptions ADD COLUMN improving_at DATE DEFAULT NULL"))
                conn.commit()
            if misc_cols and "recheck_due" not in misc_cols:
                conn.execute(text("ALTER TABLE misconceptions ADD COLUMN recheck_due DATE DEFAULT NULL"))
                conn.commit()
            if misc_cols and "relapse_count" not in misc_cols:
                conn.execute(text("ALTER TABLE misconceptions ADD COLUMN relapse_count INTEGER DEFAULT 0"))
                conn.commit()
            if misc_cols and "lecture_title" not in misc_cols:
                conn.execute(text("ALTER TABLE misconceptions ADD COLUMN lecture_title VARCHAR(255) DEFAULT NULL"))
                conn.commit()
            if misc_cols and "is_archived" not in misc_cols:
                conn.execute(text("ALTER TABLE misconceptions ADD COLUMN is_archived INTEGER DEFAULT 0"))
                conn.commit()

            # Media files columns
            res_mf = conn.execute(text("PRAGMA table_info(media_files)"))
            mf_cols = {row[1] for row in res_mf.fetchall()}
            if mf_cols and "file_hash" not in mf_cols:
                conn.execute(text("ALTER TABLE media_files ADD COLUMN file_hash VARCHAR(64) DEFAULT NULL"))
                conn.commit()
            if mf_cols:
                conn.execute(text("CREATE INDEX IF NOT EXISTS idx_media_files_file_hash ON media_files(file_hash)"))
                conn.commit()

            # Courses table (Teacher Insights Phase 2)
            res_c = conn.execute(text("SELECT name FROM sqlite_master WHERE type='table' AND name='courses'")).fetchone()
            if not res_c:
                conn.execute(text("""
                    CREATE TABLE IF NOT EXISTS courses (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        teacher_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                        title VARCHAR(255) NOT NULL,
                        course_code VARCHAR(100),
                        description TEXT,
                        join_code VARCHAR(32) NOT NULL UNIQUE,
                        created_at DATETIME,
                        updated_at DATETIME
                    )
                """))
                conn.execute(text("CREATE INDEX IF NOT EXISTS idx_courses_teacher_id ON courses(teacher_id)"))
                conn.execute(text("CREATE UNIQUE INDEX IF NOT EXISTS uq_courses_join_code ON courses(join_code)"))
                conn.commit()

            # Course enrollments table (Teacher Insights Phase 3)
            res_ce = conn.execute(text("SELECT name FROM sqlite_master WHERE type='table' AND name='course_enrollments'")).fetchone()
            if not res_ce:
                conn.execute(text("""
                    CREATE TABLE IF NOT EXISTS course_enrollments (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        course_id INTEGER NOT NULL REFERENCES courses(id) ON DELETE CASCADE,
                        student_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                        consent_granted BOOLEAN NOT NULL DEFAULT 0,
                        status VARCHAR(50) NOT NULL DEFAULT 'active',
                        consent_at DATETIME,
                        created_at DATETIME,
                        updated_at DATETIME,
                        CONSTRAINT uq_course_student_enrollment UNIQUE (course_id, student_id)
                    )
                """))
                conn.execute(text("CREATE INDEX IF NOT EXISTS idx_enrollments_course_id ON course_enrollments(course_id)"))
                conn.execute(text("CREATE INDEX IF NOT EXISTS idx_enrollments_student_id ON course_enrollments(student_id)"))
                conn.commit()

            # Lectures table course_id column (Phase 3 Security Remediation)
            res_lec = conn.execute(text("PRAGMA table_info(lectures)"))
            lec_cols = {row[1] for row in res_lec.fetchall()}
            if lec_cols and "course_id" not in lec_cols:
                conn.execute(text("ALTER TABLE lectures ADD COLUMN course_id INTEGER REFERENCES courses(id) ON DELETE SET NULL DEFAULT NULL"))
                conn.execute(text("CREATE INDEX IF NOT EXISTS idx_lectures_course_id ON lectures(course_id)"))
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
