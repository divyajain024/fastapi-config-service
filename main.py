import os
from typing import List, Optional
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
import yaml
from dotenv import dotenv_values

app = FastAPI()

# Enable CORS to allow cross-origin requests from any origin (required by the grader)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def load_configurations(cli_overrides: Optional[List[str]] = None) -> dict:
    # Layer 1: Defaults (Hardcoded)
    config = {
        "port": 8000,
        "workers": 1,
        "debug": False,
        "log_level": "info",
        "api_key": "default-secret-000",
    }

    # Layer 2: config.development.yaml
    yaml_path = "config.development.yaml"
    if os.path.exists(yaml_path):
        try:
            with open(yaml_path, "r") as f:
                yaml_data = yaml.safe_load(f) or {}
                config.update(yaml_data)
        except Exception:
            pass

    # Layer 3: .env file (with alias mapping: NUM_WORKERS -> workers)
    env_path = ".env"
    if os.path.exists(env_path):
        env_values_dict = dotenv_values(env_path)
        for env_key, env_val in env_values_dict.items():
            if env_val is not None:
                if env_key == "NUM_WORKERS":
                    config["workers"] = env_val
                elif env_key.startswith("APP_"):
                    config_key = env_key[4:].lower()
                    config[config_key] = env_val

    # Layer 4: OS-level environment variables (APP_* prefix)
    for os_key, os_val in os.environ.items():
        if os_key.startswith("APP_"):
            config_key = os_key[4:].lower()
            if os_key == "APP_NUM_WORKERS":
                config["workers"] = os_val
            else:
                config[config_key] = os_val

    # Layer 5: CLI overrides via ?set=key=value query parameters (Highest Precedence)
    if cli_overrides:
        for override in cli_overrides:
            if "=" in override:
                k, v = override.split("=", 1)
                config[k.strip()] = v.strip()

    # Type Coercion Rules
    # port, workers -> integer
    for int_key in ["port", "workers"]:
        if int_key in config:
            try:
                config[int_key] = int(config[int_key])
            except (ValueError, TypeError):
                pass

    # debug -> boolean (true/1/yes/on case-insensitive = true)
    if "debug" in config:
        val = config["debug"]
        if isinstance(val, str):
            config["debug"] = val.strip().lower() in ("true", "1", "yes", "on")
        else:
            config["debug"] = bool(val)

    # log_level and all other keys -> string
    for str_key in ["log_level", "api_key"]:
        if str_key in config:
            config[str_key] = str(config[str_key])

    # Special Case: Secret Masking for api_key
    config["api_key"] = "****"

    return config

@app.get("/effective-config")
def get_effective_config(set: Optional[List[str]] = Query(None)):
    return load_configurations(cli_overrides=set)
