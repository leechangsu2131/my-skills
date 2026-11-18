import os
import sys as _sys, pathlib as _pl; _sys.path.insert(0, str(next(p / "_shared" for p in _pl.Path(__file__).resolve().parents if (p / "_shared" / "skill_env.py").is_file())))
from skill_env import env_values

config = env_values()
print(f"Parsed SUBNURI_PW: '{config.get('SUBNURI_PW')}'")
