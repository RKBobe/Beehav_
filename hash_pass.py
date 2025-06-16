# hash_pass.py
import bcrypt

# This script will prompt you for a password and securely hash it.
try:
    password = input("Enter password to hash: ")
    password_bytes = password.encode('utf-8')
    salt = bcrypt.gensalt()
    hashed_password_bytes = bcrypt.hashpw(password_bytes, salt)
    hashed_password_str = hashed_password_bytes.decode('utf-8')

    print("\n✅--- COPY YOUR HASHED PASSWORD BELOW ---✅")
    print(hashed_password_str)
    print("✅---------------------------------------✅\n")

except Exception as e:
    print(f"\nAn error occurred: {e}")