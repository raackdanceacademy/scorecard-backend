from sqlalchemy import create_engine, text
import os
from dotenv import load_dotenv

load_dotenv()

DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "3306")
DB_USER = os.getenv("DB_USER", "root")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")
DB_NAME = os.getenv("DB_NAME", "dance_studio_scorecard")

DATABASE_URL = f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
engine = create_engine(DATABASE_URL, pool_pre_ping=True)

def add_columns():
    print("🔄 Running database migration...")
    print("=" * 50)
    
    with engine.connect() as conn:
        # ============================================
        # Update monthly_scores table
        # ============================================
        print("\n📊 Updating monthly_scores...")
        
        monthly_columns = [
            ("base_score", "FLOAT DEFAULT 0"),
            ("penalty", "FLOAT DEFAULT 0"),
            ("action", "VARCHAR(50) DEFAULT 'No data submitted'"),
        ]
        
        for column, datatype in monthly_columns:
            try:
                conn.execute(text(f"ALTER TABLE monthly_scores ADD COLUMN {column} {datatype}"))
                conn.commit()
                print(f"  ✅ Added {column} to monthly_scores")
            except Exception as e:
                if "Duplicate column" in str(e) or "already exists" in str(e):
                    print(f"  ℹ️  Column {column} already exists in monthly_scores")
                else:
                    print(f"  ❌ Error adding {column}: {e}")
        
        # ============================================
        # Update it_submissions table
        # ============================================
        print("\n📝 Updating it_submissions...")
        
        it_columns = [
            # Financial Health
            ("revenue_target", "FLOAT DEFAULT 0"),
            ("revenue_actual", "FLOAT DEFAULT 0"),
            ("tshirt_due", "FLOAT DEFAULT 0"),
            ("tshirt_paid", "FLOAT DEFAULT 0"),
            ("salary_due", "FLOAT DEFAULT 0"),
            ("salary_paid", "FLOAT DEFAULT 0"),
            ("hotel_due", "FLOAT DEFAULT 0"),
            ("hotel_paid", "FLOAT DEFAULT 0"),
            ("merch_due", "FLOAT DEFAULT 0"),
            ("merch_paid", "FLOAT DEFAULT 0"),
            ("fee_collection_rate", "FLOAT DEFAULT 0"),
            ("operating_margin", "FLOAT DEFAULT 0"),
            
            # Student Growth
            ("opening_students", "INT DEFAULT 0"),
            ("new_student_target", "INT DEFAULT 0"),
            ("new_enrollments", "INT DEFAULT 0"),
            ("dropouts", "INT DEFAULT 0"),
            ("closing_students", "INT DEFAULT 0"),
            ("batch_utilization", "FLOAT DEFAULT 0"),
            ("trials_conducted", "INT DEFAULT 0"),
            ("trial_conversions", "INT DEFAULT 0"),
            
            # Local Marketing
            ("marketing_activities", "INT DEFAULT 0"),
            ("partnerships", "INT DEFAULT 0"),
            ("social_media_posts", "INT DEFAULT 0"),
            ("events_workshops", "INT DEFAULT 0"),
            
            # Penalty Flags
            ("unauthorized_discount", "VARCHAR(10) DEFAULT 'No'"),
            ("false_reporting", "VARCHAR(10) DEFAULT 'No'"),
            ("trainer_misconduct", "VARCHAR(10) DEFAULT 'No'"),
            ("comments", "VARCHAR(500) DEFAULT ''"),
        ]
        
        for column, datatype in it_columns:
            try:
                conn.execute(text(f"ALTER TABLE it_submissions ADD COLUMN {column} {datatype}"))
                conn.commit()
                print(f"  ✅ Added {column} to it_submissions")
            except Exception as e:
                if "Duplicate column" in str(e) or "already exists" in str(e):
                    print(f"  ℹ️  Column {column} already exists in it_submissions")
                else:
                    print(f"  ❌ Error adding {column} to it_submissions: {e}")
        
        # ============================================
        # Verify changes
        # ============================================
        print("\n" + "=" * 50)
        print("✅ Migration complete!")
        
        print("\n📋 Current columns in monthly_scores:")
        try:
            result = conn.execute(text("DESCRIBE monthly_scores"))
            for row in result:
                print(f"  - {row[0]}")
        except:
            print("  ⚠️ Table monthly_scores not found")
        
        print("\n📋 Current columns in it_submissions:")
        try:
            result = conn.execute(text("DESCRIBE it_submissions"))
            for row in result:
                print(f"  - {row[0]}")
        except:
            print("  ⚠️ Table it_submissions not found")

if __name__ == "__main__":
    try:
        add_columns()
    except Exception as e:
        print(f"\n❌ Error connecting to database: {e}")
        print("Make sure MySQL is running and your .env file has the correct password")