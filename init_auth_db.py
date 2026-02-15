#!/usr/bin/env python3
"""
Initialize PostgreSQL database and create default admin user

Run this script after starting PostgreSQL to:
1. Create database tables
2. Create default admin user
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from src.database import init_db, SessionLocal
from src.crud.user import create_user, get_user_by_email
from src.data_models import UserCreate, UserRole
from src.config import Config


def create_default_admin():
    """Create default admin user if not exists"""
    db = SessionLocal()

    try:
        # Check if admin already exists
        existing_admin = get_user_by_email(db, "admin@hr-automation.com")
        if existing_admin:
            print("✅ Admin user already exists")
            print(f"   Email: admin@hr-automation.com")
            return

        # Create default admin
        admin_user = UserCreate(
            email="admin@hr-automation.com",
            name="System Administrator",
            password="admin123",  # CHANGE THIS AFTER FIRST LOGIN!
            role=UserRole.ADMIN,
            is_active=True,
            is_superuser=True
        )

        created_admin = create_user(db, admin_user)
        print("✅ Default admin user created successfully")
        print(f"   Email: {created_admin.email}")
        print(f"   Name: {created_admin.name}")
        print(f"   Role: {created_admin.role}")
        print(f"   Password: admin123 (CHANGE THIS AFTER FIRST LOGIN!)")
        print(f"\n   Login at: http://localhost:8000/docs")
        print(f"   Use POST /api/auth/token with username=admin@hr-automation.com and password=admin123")

    except Exception as e:
        print(f"❌ Error creating admin user: {e}")
        raise
    finally:
        db.close()


def main():
    """Main initialization function"""
    print("=" * 80)
    print("INITIALIZING AUTHENTICATION DATABASE")
    print("=" * 80)
    print()

    # Check configuration
    print(f"PostgreSQL Server: {Config.POSTGRES_SERVER}")
    print(f"Database: {Config.POSTGRES_DB}")
    print()

    try:
        # Initialize database tables
        print("🔧 Creating database tables...")
        init_db()
        print("✅ Database tables created successfully")
        print()

        # Create default admin
        print("👤 Creating default admin user...")
        create_default_admin()
        print()

        print("=" * 80)
        print("✅ DATABASE INITIALIZATION COMPLETED")
        print("=" * 80)
        print()
        print("Next steps:")
        print("1. Start the application: docker-compose up or python -m src.fastapi_api")
        print("2. Access API docs: http://localhost:8000/docs")
        print("3. Login with admin credentials")
        print("4. CHANGE THE ADMIN PASSWORD IMMEDIATELY!")
        print()

    except Exception as e:
        print()
        print("=" * 80)
        print("❌ INITIALIZATION FAILED")
        print("=" * 80)
        print(f"Error: {e}")
        print()
        print("Troubleshooting:")
        print("1. Make sure PostgreSQL is running")
        print("2. Check database credentials in .env file")
        print("3. Verify POSTGRES_SERVER, POSTGRES_USER, POSTGRES_PASSWORD, POSTGRES_DB")
        print()
        sys.exit(1)


if __name__ == "__main__":
    main()
