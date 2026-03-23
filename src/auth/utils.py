"""
认证工具函数
"""
from flask_login import LoginManager
from src.auth.models import User

login_manager = LoginManager()

@login_manager.user_loader
def load_user(user_id):
    """加载用户回调函数"""
    return User.query.get(int(user_id))

def init_login_manager(app):
    """初始化登录管理器"""
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    login_manager.login_message = '请先登录以访问此页面'
    login_manager.login_message_category = 'info'

def migrate_legacy_users(legacy_users_db):
    """
    迁移旧版内存用户到数据库
    legacy_users_db: 旧版内存用户字典
    返回: 迁移成功的用户数量
    """
    migrated_count = 0

    for username, user_data in legacy_users_db.items():
        # 检查用户是否已存在
        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            continue

        # 创建新用户
        try:
            user = User(
                username=username,
                email=user_data.get('email', f'{username}@example.com')
            )
            # 注意：旧版密码已经是哈希值，需要直接使用
            user.password_hash = user_data['password']
            from src.database import db
            db.session.add(user)
            migrated_count += 1
        except Exception as e:
            print(f"迁移用户 {username} 失败: {e}")
            continue

    if migrated_count > 0:
        from src.database import db
        db.session.commit()

    return migrated_count