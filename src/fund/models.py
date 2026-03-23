"""
基金业务模型
"""
from datetime import datetime, date
from decimal import Decimal
from src.database import db

class FundPosition(db.Model):
    """基金持仓表"""
    __tablename__ = 'fund_positions'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    fund_code = db.Column(db.String(20), nullable=False)
    fund_name = db.Column(db.String(100))
    cost_price = db.Column(db.Numeric(10, 4), nullable=False)  # DECIMAL(10,4)
    shares = db.Column(db.Numeric(12, 4), nullable=False)      # DECIMAL(12,4)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 关系
    transactions = db.relationship('FundTransaction', backref='position', lazy=True, cascade='all, delete-orphan')
    nav_history = db.relationship('FundNavHistory', backref='position', lazy=True)

    # 复合唯一约束：一个用户只能有一个相同的基金持仓
    __table_args__ = (db.UniqueConstraint('user_id', 'fund_code', name='unique_user_fund'),)

    def __repr__(self):
        return f'<FundPosition {self.fund_code} - {self.fund_name}>'

    @property
    def cost_value(self):
        """持仓成本价值"""
        return self.cost_price * self.shares

    def to_dict(self):
        """转换为字典"""
        return {
            'id': self.id,
            'fund_code': self.fund_code,
            'fund_name': self.fund_name,
            'cost_price': float(self.cost_price),
            'shares': float(self.shares),
            'cost_value': float(self.cost_value),
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }


class FundTransaction(db.Model):
    """交易记录表"""
    __tablename__ = 'fund_transactions'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    fund_code = db.Column(db.String(20), db.ForeignKey('fund_positions.fund_code'), nullable=False)
    trans_type = db.Column(db.String(10), nullable=False)  # BUY/SELL
    trans_price = db.Column(db.Numeric(10, 4), nullable=False)  # DECIMAL(10,4)
    trans_shares = db.Column(db.Numeric(12, 4), nullable=False)  # DECIMAL(12,4)
    trans_amount = db.Column(db.Numeric(12, 2), nullable=False)  # DECIMAL(12,2)
    trans_date = db.Column(db.DateTime, nullable=False)
    note = db.Column(db.String(200))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<FundTransaction {self.fund_code} {self.trans_type} {self.trans_date}>'

    @classmethod
    def create_buy_transaction(cls, user_id, fund_code, price, shares, amount, trans_date, note=None):
        """创建买入交易记录"""
        return cls(
            user_id=user_id,
            fund_code=fund_code,
            trans_type='BUY',
            trans_price=price,
            trans_shares=shares,
            trans_amount=amount,
            trans_date=trans_date,
            note=note
        )

    @classmethod
    def create_sell_transaction(cls, user_id, fund_code, price, shares, amount, trans_date, note=None):
        """创建卖出交易记录"""
        return cls(
            user_id=user_id,
            fund_code=fund_code,
            trans_type='SELL',
            trans_price=price,
            trans_shares=shares,
            trans_amount=amount,
            trans_date=trans_date,
            note=note
        )

    def to_dict(self):
        """转换为字典"""
        return {
            'id': self.id,
            'fund_code': self.fund_code,
            'trans_type': self.trans_type,
            'trans_price': float(self.trans_price),
            'trans_shares': float(self.trans_shares),
            'trans_amount': float(self.trans_amount),
            'trans_date': self.trans_date.isoformat() if self.trans_date else None,
            'note': self.note,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class FundNavHistory(db.Model):
    """净值历史表"""
    __tablename__ = 'fund_nav_history'

    id = db.Column(db.Integer, primary_key=True)
    fund_code = db.Column(db.String(20), db.ForeignKey('fund_positions.fund_code'), nullable=False)
    nav_date = db.Column(db.Date, nullable=False)
    nav = db.Column(db.Numeric(10, 4))  # 单位净值 DECIMAL(10,4)
    acc_nav = db.Column(db.Numeric(10, 4))  # 累计净值 DECIMAL(10,4)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # 复合唯一约束：同一个基金在同一天只能有一条净值记录
    __table_args__ = (db.UniqueConstraint('fund_code', 'nav_date', name='unique_fund_nav_date'),)

    def __repr__(self):
        return f'<FundNavHistory {self.fund_code} {self.nav_date} {self.nav}>'

    def to_dict(self):
        """转换为字典"""
        return {
            'id': self.id,
            'fund_code': self.fund_code,
            'nav_date': self.nav_date.isoformat() if self.nav_date else None,
            'nav': float(self.nav) if self.nav else None,
            'acc_nav': float(self.acc_nav) if self.acc_nav else None,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }