from encryption import password_decrypt

password = input("Please write the password: ")

with open(".credentials", "r") as f:
    DISCORD_TOKEN = password_decrypt(f.readline().encode(), password).decode()

    DATABASE_STRING = password_decrypt(f.readline().encode(), password).decode()
