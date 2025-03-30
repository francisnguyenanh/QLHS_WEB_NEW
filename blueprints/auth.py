from flask import Blueprint, render_template, request, redirect, url_for, session
from db_utils import read_all_records, read_record_by_id

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/', methods=['GET', 'POST'])
@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = read_all_records('Users', condition=f"username = '{username}' AND password = '{password}'")
        if user:
            session['user_id'] = user[0][0]
            return redirect(url_for('admin.index'))  # Chuyển hướng đến base.html
        else:
            error = 'Invalid username or password'
    return render_template('login.html', error=error)

@auth_bp.route('/logout')
def logout():
    session.pop('user_id', None)
    return redirect(url_for('auth.login'))