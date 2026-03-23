# -*- coding: utf-8 -*-
"""
基金持仓管理系统 - 主应用
"""
import os
from flask import Flask, render_template
from config import config

def create_app(config_name='default'):
    """应用工厂函数"""
    app = Flask(__name__)

    # 加载配置
    app.config.from_object(config[config_name])

    # 确保实例文件夹存在
    os.makedirs(app.instance_path, exist_ok=True)

    # 初始化扩展
    from src.database import init_database
    from src.auth.utils import init_login_manager

    init_database(app)
    init_login_manager(app)

    # 注册蓝图
    from src.auth.routes import auth_bp
    from src.fund.routes import fund_bp
    from src.fund.api import fund_api_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(fund_bp)
    app.register_blueprint(fund_api_bp, url_prefix='/api/v1')

    # 错误处理
    @app.errorhandler(404)
    def not_found_error(error):
        return render_template('errors/404.html'), 404

    @app.errorhandler(500)
    def internal_error(error):
        from src.database import db
        db.session.rollback()
        return render_template('errors/500.html'), 500

    # 迁移旧版用户数据（仅开发环境）
    @app.before_request
    def migrate_legacy_users():
        if app.config.get('DEBUG', False):
            from src.auth.utils import migrate_legacy_users
            from src.database import db

            # 旧版内存用户数据（从原app.py复制）
            legacy_users_db = {
                "admin": {
                    "username": "admin",
                    "password": "pbkdf2:sha256:260000$XcW6pB3v$8c5a9c7e8f9a0b1c2d3e4f5a6b7c8d9e0f1a2b3c4d5e6f7a8b9c0d1e2f3a4b5c6",
                    "email": "admin@example.com"
                }
            }

            try:
                migrated = migrate_legacy_users(legacy_users_db)
                if migrated > 0:
                    print(f"✅ 迁移了 {migrated} 个旧版用户到数据库")
            except Exception as e:
                print(f"⚠️  用户迁移失败: {e}")

    return app


# 创建应用实例
app = create_app()

if __name__ == '__main__':
    print("🚀 基金持仓管理系统已启动...")
    print("📍 访问地址: http://127.0.0.1:5000")
    print("默认账号: admin / admin123")
    print("📊 功能模块:")
    print("  - 用户认证系统")
    print("  - 基金持仓管理")
    print("  - 交易记录管理")
    print("  - 盈亏计算")
    print("  - 数据可视化")

    app.run(
        debug=app.config.get('DEBUG', True),
        host=app.config.get('HOST', '0.0.0.0'),
        port=app.config.get('PORT', 5000)
    )