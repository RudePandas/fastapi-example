class AsyncMySql:
    prod = {
        "host": "localhost",
        "port": 3306,
        "user": "root",
        "passwd": "123456",
        "db": "fastapi_db",
        "charset": "utf8mb4",
        "autocommit": True,
        "maxsize": 100,
        "minsize": 1
    }

    test = {
        "host": "localhost",
        "port": 3306,
        "user": "root",
        "passwd": "123456",
        "db": "fastapi_db",
        "charset": "utf8mb4",
        "autocommit": True,
        "maxsize": 100,
        "minsize": 1
    }