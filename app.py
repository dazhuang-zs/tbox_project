# -*- coding: utf-8 -*-
"""
tbox_project - 登录系统主应用
"""
from flask import Flask, render_template, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash
import os

app = Flask(__name__)
app.secret_key = os.urandom(24)  # 用于会话加密

# 模拟用户数据库（实际项目中应使用真实数据库）
users_db = {
    "admin": {
        "username": "admin",
        "password": generate_password_hash("admin123"),
        "email": "admin@example.com"
    }
}


def get_user(username):
    """获取用户信息"""
    return users_db.get(username)


def add_user(username, password, email):
    """添加新用户"""
    if username in users_db:
        return False
    users_db[username] = {
        "username": username,
        "password": generate_password_hash(password),
        "email": email
    }
    return True


@app.route('/')
def index():
    """首页"""
    if 'username' in session:
        return render_template('index.html', username=session['username'])
    return redirect(url_for('login'))


@app.route('/register', methods=['GET', 'POST'])
def register():
    """用户注册"""
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()
        email = request.form.get('email', '').strip()
        
        # 验证输入
        if not username or not password or not email:
            flash('所有字段都是必填的', 'error')
            return render_template('register.html')
        
        if len(password) < 6:
            flash('密码长度至少6位', 'error')
            return render_template('register.html')
        
        # 添加用户
        if add_user(username, password, email):
            flash('注册成功！请登录', 'success')
            return redirect(url_for('login'))
        else:
            flash('用户名已存在', 'error')
            return render_template('register.html')
    
    return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    """用户登录"""
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()
        
        user = get_user(username)
        
        if user and check_password_hash(user['password'], password):
            # 登录成功
            session['username'] = username
            session['email'] = user['email']
            flash(f'欢迎回来，{username}！', 'success')
            return redirect(url_for('index'))
        else:
            flash('用户名或密码错误', 'error')
            return render_template('login.html')
    
    return render_template('login.html')


@app.route('/logout')
def logout():
    """用户登出"""
    username = session.get('username', '用户')
    session.clear()
    flash(f'{username}，您已成功退出登录', 'info')
    return redirect(url_for('login'))


if __name__ == '__main__':
    # 创建templates目录（如果不存在）
    os.makedirs('templates', exist_ok=True)
    os.makedirs('static', exist_ok=True)
    
    print("🚀 登录系统已启动...")
    print("📍 访问地址: http://127.0.0.1:5000")
    print("默认账号: admin / admin123")
    
    app.run(debug=True, host='0.0.0.0', port=8080)
