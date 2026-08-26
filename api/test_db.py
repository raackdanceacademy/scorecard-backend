from .database import SessionLocal, engine   # ✅ Added dot
from .models import Branch                  # ✅ Added dot

def test_connection():
    try:
        db = SessionLocal()
        print("✅ Successfully connected to MySQL!")
        db.close()
        return True
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == "__main__":
    test_connection()