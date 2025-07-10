# -*- coding: utf-8 -*-
import os
from conf.async_mysql import *
from conf.async_redis import *
from conf.config import *
__all__ = ["my_config"]


class Con:
    def __init__(self, obj, env):
        self.dict = getattr(obj, env)
        self.prod = getattr(obj, "prod")
        self.test = getattr(obj, "test")

    def __getattr__(self, item):
        return self.dict.get(item)


class Config:
    def __init__(self):
        env = os.environ.get("ENV", "test").lower()
        if env != "prod":
            env = "test"
        self.env = env
        print("环境", env)
        self.async_mysql = Con(AsyncMySql, env)               # mysql配置
        self.async_redis = Con(AsyncRedis, env)               # redis配置
        self.settings = Con(Settings, env)               # common配置

my_config = Config()
