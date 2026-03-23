"""
基金业务路由
"""
from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user

fund_bp = Blueprint('fund', __name__)

@fund_bp.route('/')
@fund_bp.route('/dashboard')
@login_required
def dashboard():
    """仪表盘页面"""
    return render_template('fund/dashboard.html')

@fund_bp.route('/positions')
@login_required
def positions():
    """持仓列表页面"""
    return render_template('fund/positions.html')

@fund_bp.route('/positions/<int:position_id>')
@login_required
def position_detail(position_id):
    """持仓详情页面"""
    return render_template('fund/position_detail.html', position_id=position_id)

@fund_bp.route('/positions/new', methods=['GET', 'POST'])
@login_required
def add_position():
    """新增持仓页面"""
    if request.method == 'POST':
        # TODO: 处理表单提交
        flash('持仓添加成功', 'success')
        return redirect(url_for('fund.positions'))
    return render_template('fund/add_position.html')

@fund_bp.route('/transactions')
@login_required
def transactions():
    """交易记录页面"""
    return render_template('fund/transactions.html')