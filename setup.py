import os
import secrets
import getpass
from cryptography.fernet import Fernet

def generate_secret_key():
    """Generate a secure secret key"""
    return secrets.token_hex(32)

def generate_encryption_key():
    """Generate a Fernet encryption key"""
    return Fernet.generate_key().decode()

def setup_env_file():
    """Set up the .env file with user input"""
    if os.path.exists('.env'):
        overwrite = input('.env file already exists. Overwrite? (y/n): ')
        if overwrite.lower() != 'y':
            print('Setup cancelled.')
            return
    
    print("\n=== PDF Processing API Setup ===\n")
    
    # Database settings
    print("\n--- Database Settings ---")
    db_user = input("Database user [postgres]: ") or "postgres"
    db_password = getpass.getpass("Database password [postgres]: ") or "postgres"
    db_host = input("Database host [localhost]: ") or "localhost"
    db_port = input("Database port [5432]: ") or "5432"
    db_name = input("Database name [pdf_processing]: ") or "pdf_processing"
    
    database_url = f"postgresql+asyncpg://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
    
    # Security settings
    print("\n--- Security Settings ---")
    secret_key = input(f"Secret key [auto-generate]: ") or generate_secret_key()
    encryption_key = input(f"Encryption key [auto-generate]: ") or generate_encryption_key()
    
    # API settings
    print("\n--- API Settings ---")
    api_host = input("API host [0.0.0.0]: ") or "0.0.0.0"
    api_port = input("API port [8000]: ") or "8000"
    
    # Admin user
    print("\n--- Admin User ---")
    admin_email = input("Admin email [admin@example.com]: ") or "admin@example.com"
    admin_password = getpass.getpass("Admin password [changeme]: ") or "changeme"
    
    # Write to .env file
    with open('.env', 'w') as f:
        f.write(f"# Database settings\n")
        f.write(f"DATABASE_URL={database_url}\n\n")
        
        f.write(f"# Security settings\n")
        f.write(f"SECRET_KEY={secret_key}\n")
        f.write(f"ENCRYPTION_KEY={encryption_key}\n\n")
        
        f.write(f"# API settings\n")
        f.write(f"API_HOST={api_host}\n")
        f.write(f"API_PORT={api_port}\n\n")
        
        f.write(f"# Default admin user\n")
        f.write(f"ADMIN_EMAIL={admin_email}\n")
        f.write(f"ADMIN_PASSWORD={admin_password}\n")
    
    print("\n.env file created successfully!")
    print("You can now run the application with: ./start.sh")

if __name__ == "__main__":
    setup_env_file()
