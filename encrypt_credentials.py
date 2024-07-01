from encryption import password_encrypt

DISCORD_TOKEN = input("Paste your discord token please: ")

DATABASE_STRING = input("Paste your database string please: ")

key = input("Please set your key: ")


encrypted_token = password_encrypt(DISCORD_TOKEN.encode(), key)
encrypted_database_string = password_encrypt(DATABASE_STRING.encode(), key)

with open(".credentials", "w") as f:
    f.write(encrypted_token.decode() + "\n")
    f.write(encrypted_database_string.decode() + "\n")
