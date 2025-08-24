import sqlite3
import os
from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash, check_password_hash
import logging

# Configure logging
logging.basicConfig(level=logging.DEBUG)

class Database:
    def __init__(self, db_path='financial_system.db'):
        self.db_path = db_path
        self.init_db()
    
    def get_connection(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    def init_db(self):
        """Initialize database with all required tables"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Users table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                full_name TEXT NOT NULL,
                phone TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                active INTEGER DEFAULT 1,
                trial_start_date TEXT DEFAULT CURRENT_TIMESTAMP,
                trial_end_date TEXT,
                subscription_plan TEXT DEFAULT 'trial',
                subscription_status TEXT DEFAULT 'trial',
                subscription_end_date TEXT
            )
        ''')
        
        # Transactions table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                description TEXT NOT NULL,
                amount REAL NOT NULL,
                transaction_type TEXT NOT NULL,
                category TEXT,
                date TEXT DEFAULT CURRENT_TIMESTAMP,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                is_recurring INTEGER DEFAULT 0,
                recurrence_type TEXT,
                account_id INTEGER,
                FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE,
                FOREIGN KEY (account_id) REFERENCES accounts (id)
            )
        ''')
        
        # Accounts table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS accounts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                account_type TEXT NOT NULL,
                amount REAL DEFAULT 0,
                due_date TEXT,
                status TEXT DEFAULT 'pending',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
            )
        ''')
        
        # Financial goals table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS financial_goals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                title TEXT NOT NULL,
                target_amount REAL NOT NULL,
                current_amount REAL DEFAULT 0,
                target_date TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                is_completed INTEGER DEFAULT 0,
                FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
            )
        ''')
        
        conn.commit()
        conn.close()
        logging.info("Database initialized successfully")

# Global database instance
db_manager = Database()

class User:
    def __init__(self, id=None, username=None, email=None, password_hash=None, 
                 full_name=None, phone=None, created_at=None, active=None,
                 trial_start_date=None, trial_end_date=None, subscription_plan=None,
                 subscription_status=None, subscription_end_date=None):
        self.id = id
        self.username = username
        self.email = email
        self.password_hash = password_hash
        self.full_name = full_name
        self.phone = phone
        self.created_at = created_at
        self.active = bool(active) if active is not None else True
        self.trial_start_date = trial_start_date
        self.trial_end_date = trial_end_date
        self.subscription_plan = subscription_plan or 'trial'
        self.subscription_status = subscription_status or 'trial'
        self.subscription_end_date = subscription_end_date
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def is_authenticated(self):
        return True
    
    def is_active(self):
        return self.active
    
    def is_anonymous(self):
        return False
    
    def get_id(self):
        return str(self.id)
    
    def is_trial_expired(self):
        if not self.trial_end_date:
            return False
        trial_end = datetime.fromisoformat(self.trial_end_date.replace('Z', '+00:00'))
        return datetime.utcnow() > trial_end
    
    def is_subscription_active(self):
        if self.subscription_status == 'trial':
            return not self.is_trial_expired()
        return (self.subscription_status == 'active' and 
                self.subscription_end_date and 
                datetime.utcnow() <= datetime.fromisoformat(self.subscription_end_date.replace('Z', '+00:00')))
    
    def get_plan_features(self):
        features = {
            'trial': {
                'name': 'Teste Grátis',
                'transactions_limit': 10,
                'reports': False,
                'automation': False,
                'multi_user': False
            },
            'mei': {
                'name': 'Plano MEI',
                'transactions_limit': 100,
                'reports': True,
                'automation': False,
                'multi_user': False
            },
            'professional': {
                'name': 'Plano Profissional',
                'transactions_limit': 500,
                'reports': True,
                'automation': True,
                'multi_user': False
            },
            'enterprise': {
                'name': 'Plano Empresarial',
                'transactions_limit': -1,  # unlimited
                'reports': True,
                'automation': True,
                'multi_user': True
            }
        }
        return features.get(self.subscription_plan, features['trial'])
    
    @staticmethod
    def create(username, email, password, full_name, phone=None):
        """Create a new user"""
        conn = db_manager.get_connection()
        cursor = conn.cursor()
        
        # Set trial end date (7 days from now)
        trial_end = (datetime.utcnow() + timedelta(days=7)).isoformat()
        
        password_hash = generate_password_hash(password)
        
        cursor.execute('''
            INSERT INTO users (username, email, password_hash, full_name, phone, trial_end_date)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (username, email, password_hash, full_name, phone, trial_end))
        
        user_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        return User.get_by_id(user_id)
    
    @staticmethod
    def get_by_id(user_id):
        """Get user by ID"""
        conn = db_manager.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM users WHERE id = ?', (user_id,))
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return User(**dict(row))
        return None
    
    @staticmethod
    def get_by_email(email):
        """Get user by email"""
        conn = db_manager.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM users WHERE email = ?', (email,))
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return User(**dict(row))
        return None
    
    @staticmethod
    def get_by_username(username):
        """Get user by username"""
        conn = db_manager.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM users WHERE username = ?', (username,))
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return User(**dict(row))
        return None

class Transaction:
    def __init__(self, id=None, user_id=None, description=None, amount=None,
                 transaction_type=None, category=None, date=None, created_at=None,
                 is_recurring=None, recurrence_type=None, account_id=None):
        self.id = id
        self.user_id = user_id
        self.description = description
        self.amount = float(amount) if amount else 0.0
        self.transaction_type = transaction_type
        self.category = category
        self.date = date
        self.created_at = created_at
        self.is_recurring = bool(is_recurring) if is_recurring else False
        self.recurrence_type = recurrence_type
        self.account_id = account_id
    
    def save(self):
        """Save transaction to database"""
        conn = db_manager.get_connection()
        cursor = conn.cursor()
        
        if self.id:
            # Update existing
            cursor.execute('''
                UPDATE transactions 
                SET description=?, amount=?, transaction_type=?, category=?, 
                    date=?, is_recurring=?, recurrence_type=?, account_id=?
                WHERE id=?
            ''', (self.description, self.amount, self.transaction_type, self.category,
                  self.date, self.is_recurring, self.recurrence_type, self.account_id, self.id))
        else:
            # Create new
            cursor.execute('''
                INSERT INTO transactions (user_id, description, amount, transaction_type, 
                                        category, date, is_recurring, recurrence_type, account_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (self.user_id, self.description, self.amount, self.transaction_type,
                  self.category, self.date, self.is_recurring, self.recurrence_type, self.account_id))
            self.id = cursor.lastrowid
        
        conn.commit()
        conn.close()
        return self
    
    @staticmethod
    def get_by_user_id(user_id, limit=None, order_by='date DESC'):
        """Get transactions by user ID"""
        conn = db_manager.get_connection()
        cursor = conn.cursor()
        
        query = f'SELECT * FROM transactions WHERE user_id = ? ORDER BY {order_by}'
        if limit:
            query += f' LIMIT {limit}'
        
        cursor.execute(query, (user_id,))
        rows = cursor.fetchall()
        conn.close()
        
        return [Transaction(**dict(row)) for row in rows]
    
    @staticmethod
    def count_by_user_id(user_id):
        """Count transactions by user ID"""
        conn = db_manager.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('SELECT COUNT(*) FROM transactions WHERE user_id = ?', (user_id,))
        count = cursor.fetchone()[0]
        conn.close()
        
        return count
    
    @staticmethod
    def get_monthly_summary(user_id, month, year):
        """Get monthly income and expenses summary"""
        conn = db_manager.get_connection()
        cursor = conn.cursor()
        
        # Get monthly income
        cursor.execute('''
            SELECT COALESCE(SUM(amount), 0) FROM transactions 
            WHERE user_id = ? AND transaction_type = 'income' 
            AND strftime('%m', date) = ? AND strftime('%Y', date) = ?
        ''', (user_id, f'{month:02d}', str(year)))
        
        income = cursor.fetchone()[0]
        
        # Get monthly expenses
        cursor.execute('''
            SELECT COALESCE(SUM(amount), 0) FROM transactions 
            WHERE user_id = ? AND transaction_type = 'expense' 
            AND strftime('%m', date) = ? AND strftime('%Y', date) = ?
        ''', (user_id, f'{month:02d}', str(year)))
        
        expenses = cursor.fetchone()[0]
        conn.close()
        
        return float(income), float(expenses)

class Account:
    def __init__(self, id=None, user_id=None, name=None, account_type=None,
                 amount=None, due_date=None, status=None, created_at=None):
        self.id = id
        self.user_id = user_id
        self.name = name
        self.account_type = account_type
        self.amount = float(amount) if amount else 0.0
        self.due_date = due_date
        self.status = status or 'pending'
        self.created_at = created_at
    
    def save(self):
        """Save account to database"""
        conn = db_manager.get_connection()
        cursor = conn.cursor()
        
        if self.id:
            # Update existing
            cursor.execute('''
                UPDATE accounts 
                SET name=?, account_type=?, amount=?, due_date=?, status=?
                WHERE id=?
            ''', (self.name, self.account_type, self.amount, self.due_date, self.status, self.id))
        else:
            # Create new
            cursor.execute('''
                INSERT INTO accounts (user_id, name, account_type, amount, due_date, status)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (self.user_id, self.name, self.account_type, self.amount, self.due_date, self.status))
            self.id = cursor.lastrowid
        
        conn.commit()
        conn.close()
        return self
    
    @staticmethod
    def get_by_user_id(user_id, account_type=None):
        """Get accounts by user ID and optionally by type"""
        conn = db_manager.get_connection()
        cursor = conn.cursor()
        
        if account_type:
            cursor.execute('SELECT * FROM accounts WHERE user_id = ? AND account_type = ?', 
                          (user_id, account_type))
        else:
            cursor.execute('SELECT * FROM accounts WHERE user_id = ?', (user_id,))
        
        rows = cursor.fetchall()
        conn.close()
        
        return [Account(**dict(row)) for row in rows]
    
    @staticmethod
    def get_by_id(account_id, user_id=None):
        """Get account by ID, optionally filtered by user"""
        conn = db_manager.get_connection()
        cursor = conn.cursor()
        
        if user_id:
            cursor.execute('SELECT * FROM accounts WHERE id = ? AND user_id = ?', (account_id, user_id))
        else:
            cursor.execute('SELECT * FROM accounts WHERE id = ?', (account_id,))
        
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return Account(**dict(row))
        return None
    
    @staticmethod
    def get_pending_total(user_id, account_type):
        """Get total amount for pending accounts of a specific type"""
        conn = db_manager.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT COALESCE(SUM(amount), 0) FROM accounts 
            WHERE user_id = ? AND account_type = ? AND status = 'pending'
        ''', (user_id, account_type))
        
        total = cursor.fetchone()[0]
        conn.close()
        
        return float(total)

class FinancialGoal:
    def __init__(self, id=None, user_id=None, title=None, target_amount=None,
                 current_amount=None, target_date=None, created_at=None, is_completed=None):
        self.id = id
        self.user_id = user_id
        self.title = title
        self.target_amount = float(target_amount) if target_amount else 0.0
        self.current_amount = float(current_amount) if current_amount else 0.0
        self.target_date = target_date
        self.created_at = created_at
        self.is_completed = bool(is_completed) if is_completed else False
    
    def get_progress_percentage(self):
        if self.target_amount == 0:
            return 0
        return min(100, (self.current_amount / self.target_amount) * 100)
    
    def save(self):
        """Save goal to database"""
        conn = db_manager.get_connection()
        cursor = conn.cursor()
        
        if self.id:
            # Update existing
            cursor.execute('''
                UPDATE financial_goals 
                SET title=?, target_amount=?, current_amount=?, target_date=?, is_completed=?
                WHERE id=?
            ''', (self.title, self.target_amount, self.current_amount, 
                  self.target_date, self.is_completed, self.id))
        else:
            # Create new
            cursor.execute('''
                INSERT INTO financial_goals (user_id, title, target_amount, current_amount, target_date, is_completed)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (self.user_id, self.title, self.target_amount, self.current_amount, 
                  self.target_date, self.is_completed))
            self.id = cursor.lastrowid
        
        conn.commit()
        conn.close()
        return self
    
    @staticmethod
    def get_by_user_id(user_id, is_completed=None):
        """Get financial goals by user ID"""
        conn = db_manager.get_connection()
        cursor = conn.cursor()
        
        if is_completed is not None:
            cursor.execute('SELECT * FROM financial_goals WHERE user_id = ? AND is_completed = ?', 
                          (user_id, is_completed))
        else:
            cursor.execute('SELECT * FROM financial_goals WHERE user_id = ?', (user_id,))
        
        rows = cursor.fetchall()
        conn.close()
        
        return [FinancialGoal(**dict(row)) for row in rows]