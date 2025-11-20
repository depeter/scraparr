"""Script to add authentication to all API endpoints"""
import re
from pathlib import Path

# Files to protect
api_files = [
    "app/api/jobs.py",
    "app/api/executions.py",
    "app/api/database.py",
    "app/api/proxy.py",
]

for file_path in api_files:
    path = Path(file_path)
    if not path.exists():
        print(f"Skipping {file_path} - not found")
        continue

    content = path.read_text()

    # Add import if not present
    if "from app.core.security import get_current_active_user" not in content:
        # Find the imports section and add our import
        import_pattern = r"(from app\.core\.database import[^\n]+)"
        replacement = r"\1\nfrom app.core.security import get_current_active_user"
        content = re.sub(import_pattern, replacement, content)

        # Also add User to imports if not present
        if "from app.models import" in content and "User" not in content:
            content = re.sub(
                r"(from app\.models import [^User\n]+)",
                r"\1, User",
                content
            )

    # Add current_user parameter to all async def functions that have db: AsyncSession
    # Pattern: find functions with db parameter but no current_user parameter
    def add_auth_param(match):
        func_def = match.group(0)
        # Check if already has current_user
        if "current_user" in func_def:
            return func_def
        # Add current_user parameter before the closing parenthesis
        func_def = func_def.rstrip(")\n:")
        func_def += ",\n    current_user: User = Depends(get_current_active_user)\n):"
        return func_def

    # Match async function definitions with db parameter
    pattern = r"async def \w+\([^)]*db: AsyncSession[^)]*\):"
    content = re.sub(pattern, add_auth_param, content)

    # Write back
    path.write_text(content)
    print(f"✓ Protected {file_path}")

print("\nDone! All endpoints protected with authentication.")
