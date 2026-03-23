"""
配置文件
"""
import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    """基础配置"""
    # 安全密钥
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'

    # 数据库配置
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'sqlite:///fund_management.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Flask-Login配置
    REMEMBER_COOKIE_DURATION = 3600  # 1小时

    # 外部API配置
    EASTMONEY_API_BASE = 'https://fund.eastmoney.com'

    # 缓存配置
    CACHE_TYPE = 'simple'  # 简单内存缓存
    CACHE_DEFAULT_TIMEOUT = 300  # 5分钟

    # 应用配置
    HOST = os.environ.get('HOST', '0.0.0.0')
    PORT = int(os.environ.get('PORT', 5000))


class DevelopmentConfig(Config):
    """开发环境配置"""
    DEBUG = True
    SQLALCHEMY_ECHO = True  # 输出SQL语句


class TestingConfig(Config):
    """测试环境配置"""
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'  # 内存数据库
    WTF_CSRF_ENABLED = False


class ProductionConfig(Config):
    """生产环境配置"""
    DEBUG = False
    # 生产环境应该从环境变量获取
    SECRET_KEY = os.environ.get('SECRET_KEY')
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL')


# 配置映射
config = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}