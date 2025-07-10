class Settings:
    prod = {
        "secret_key": "your-secret-key-here",
        "algorithm": "HS256",
        "access_token_expire_minutes": 30,
        "api_v1_str": "/api/v1",
        "project_name": "FastAPI Advanced",
        "default_page_size": 10,
        "max_page_size": 100
    }

    test = {
        "secret_key": "your-secret-key-here",
        "algorithm": "HS256",
        "access_token_expire_minutes": 30,
        "api_v1_str": "/api/v1",
        "project_name": "FastAPI Advanced",
        "default_page_size": 10,
        "max_page_size": 100
    }