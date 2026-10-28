import os
from dotenv import dotenv_values

config = dotenv_values(".env")
print(f"Parsed SUBNURI_PW: '{config.get('SUBNURI_PW')}'")
