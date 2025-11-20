"""Initialize authentication - create users table and admin user"""
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select

from app.core.config import settings
from app.core.security import hash_password
from app.models.user import User
from app.core.database import Base

async def init_auth():
    """Initialize authentication system"""
    # Create engine
    engine = create_async_engine(settings.DATABASE_URL, echo=True)

    # Create users table
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    print("✓ Users table created")

    # Create async session
    async_session = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )

    # Create admin user if not exists
    async with async_session() as session:
        # Check if admin user exists
        result = await session.execute(
            select(User).where(User.username == "admin")
        )
        existing_user = result.scalar_one_or_none()

        if existing_user:
            print("⚠ Admin user already exists")
        else:
            # Create admin user with default password
            admin_user = User(
                username="admin",
                email="admin@example.com",
                hashed_password=hash_password("admin123"),  # Change this!
                is_active=True,
                is_admin=True
            )
            session.add(admin_user)
            await session.commit()
            print("✓ Admin user created")
            print("  Username: admin")
            print("  Password: admin123")
            print("  ⚠ IMPORTANT: Change the password immediately after first login!")

    await engine.dispose()
    print("\n✓ Authentication initialization complete")

if __name__ == "__main__":
    asyncio.run(init_auth())
