from app.db.database import init_db

if __name__ == "__main__":
    print("Initialising database...")
    init_db()
    print("Database initialised.")
