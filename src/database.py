"""
数据库配置模块
"""
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate

db = SQLAlchemy()
migrate = Migrate()

def init_database(app):
    """初始化数据库"""
    db.init_app(app)
    migrate.init_app(app, db)

    # 创建数据库表（如果不存在）
    with app.app_context():
        db.create_all()