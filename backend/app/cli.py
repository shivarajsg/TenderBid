import argparse
import asyncio
import getpass
import sys
from app.core.security import hash_password, UserRole
from app.db.session import AsyncSessionLocal
from app.db.repositories.users import UserRepository


async def create_admin_user(email: str, full_name: str, password: str):
    """Securely provision a platform administrator account."""
    async with AsyncSessionLocal() as session:
        user_repo = UserRepository(session)
        existing = await user_repo.get_by_email(email)
        if existing:
            print(f"[ERROR] User with email '{email}' already exists.")
            sys.exit(1)

        hashed_pw = hash_password(password)
        user = await user_repo.create(
            email=email,
            hashed_password=hashed_pw,
            full_name=full_name,
            role=UserRole.ADMIN.value,
        )
        await session.commit()
        print(f"[SUCCESS] Admin account created successfully: {user.email} (ID: {user.id})")


def main():
    parser = argparse.ArgumentParser(description="Tender Platform Administrative CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    admin_parser = subparsers.add_parser("create-admin", help="Provision a new platform administrator")
    admin_parser.add_argument("--email", required=True, help="Administrator email address")
    admin_parser.add_argument("--full-name", required=True, help="Administrator full display name")
    admin_parser.add_argument("--password", required=False, help="Password (if omitted, will prompt securely)")

    args = parser.parse_args()

    if args.command == "create-admin":
        password = args.password
        if not password:
            password = getpass.getpass("Enter administrator password (min 8 chars): ")
            confirm = getpass.getpass("Confirm administrator password: ")
            if password != confirm:
                print("[ERROR] Passwords do not match.")
                sys.exit(1)
        if len(password) < 8:
            print("[ERROR] Password must be at least 8 characters long.")
            sys.exit(1)

        asyncio.run(create_admin_user(args.email, args.full_name, password))


if __name__ == "__main__":
    main()
