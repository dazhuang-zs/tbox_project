"""
用户认证路由
"""
from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from src.auth.models import User
from src.database import db

auth_bp = Blueprint('auth', __name__, url_prefix='/auth')

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    """用户注册"""
    if current_user.is_authenticated:
        return redirect(url_for('fund.dashboard'))

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '').strip()
        confirm_password = request.form.get('confirm_password', '').strip()

        # 验证输入
        errors = []
        if not username or not email or not password:
            errors.append('所有字段都是必填的')

        if len(password) < 6:
            errors.append('密码长度至少6位')

        if password != confirm_password:
            errors.append('两次输入的密码不一致')

        # 检查用户名和邮箱是否已存在
        if User.query.filter_by(username=username).first():
            errors.append('用户名已存在')

        if User.query.filter_by(email=email).first():
            errors.append('邮箱已存在')

        if errors:
            for error in errors:
                flash(error, 'error')
            return render_template('auth/register.html')

        # 创建新用户
        try:
            user = User(username=username, email=email)
            user.set_password(password)
            db.session.add(user)
            db.session.commit()
            flash('注册成功！请登录', 'success')
            return redirect(url_for('auth.login'))
        except Exception as e:
            db.session.rollback()
            flash(f'注册失败：{str(e)}', 'error')
            return render_template('auth/register.html')

    return render_template('auth/register.html')


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """用户登录"""
    if current_user.is_authenticated:
        return redirect(url_for('fund.dashboard'))

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()
        remember = request.form.get('remember', False)

        # 查找用户（支持用户名或邮箱登录）
        user = User.query.filter(
            (User.username == username) | (User.email == username)
        ).first()

        if user and user.check_password(password):
            login_user(user, remember=bool(remember))
            flash(f'欢迎回来，{user.username}！', 'success')
            next_page = request.args.get('next')
            return redirect(next_page or url_for('fund.dashboard'))
        else:
            flash('用户名或密码错误', 'error')
            return render_template('auth/login.html')

    return render_template('auth/login.html')


@auth_bp.route('/logout')
@login_required
def logout():
    """用户登出"""
    username = current_user.username
    logout_user()
    flash(f'{username}，您已成功退出登录', 'info')
    return redirect(url_for('auth.login'))