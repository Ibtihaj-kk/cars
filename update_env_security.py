#!/usr/bin/env python
"""
Script to update .env file with secure SECRET_KEY
Run this once to set up your environment properly
"""
import os
import shutil
from pathlib import Path

# Generated secure SECRET_KEY
NEW_SECRET_KEY = "na6c_b=o_7vlsocp=-s48r39i=%x$l_eo-@ivu%i65#oywk8b4"

# Generate a strong password recommendation
RECOMMENDED_DB_PASSWORD = "YM2025$SecureDb!P@ssw0rd#2025"

def update_env_file():
    """Update .env file with secure values"""
    env_path = Path(__file__).parent / '.env'
    env_example_path = Path(__file__).parent / '.env.example'
    
    # Create .env from .env.example if it doesn't exist
    if not env_path.exists() and env_example_path.exists():
        shutil.copy(env_example_path, env_path)
        print("✅ Created .env from .env.example")
    
    if not env_path.exists():
        print("❌ .env file not found!")
        return
    
    # Read current .env
    with open(env_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    # Update values
    updated_lines = []
    for line in lines:
        if line.startswith('SECRET_KEY='):
            updated_lines.append(f'SECRET_KEY={NEW_SECRET_KEY}\n')
            print(f"✅ Updated SECRET_KEY")
        elif line.startswith('DB_PASSWORD=Kh@n+555'):
            updated_lines.append(f'DB_PASSWORD={RECOMMENDED_DB_PASSWORD}\n')
            print(f"⚠️  Updated DB_PASSWORD (REMEMBER TO UPDATE YOUR DATABASE!)")
        else:
            updated_lines.append(line)
    
    # Write back
    with open(env_path, 'w', encoding='utf-8') as f:
        f.writelines(updated_lines)
    
    print("\n✅ .env file updated successfully!")
    print("\n⚠️  IMPORTANT NEXT STEPS:")
    print("1. Update your PostgreSQL database password to match:")
    print(f"   ALTER USER postgres WITH PASSWORD '{RECOMMENDED_DB_PASSWORD}';")
    print("2. Configure your SMTP settings in .env for email")
    print("3. Never commit .env to version control!")

if __name__ == '__main__':
    update_env_file()
