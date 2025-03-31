from flask import Blueprint, render_template, request, redirect, url_for, session
from db_utils import (create_record, read_all_records, read_record_by_id,
                      update_record, delete_record, connect_db)

admin_bp = Blueprint('admin', __name__)

def is_user_gvcn():
    if 'user_id' in session:
        user = read_record_by_id('Users', session['user_id'])
        role = read_record_by_id('Roles', user[6])  # Giả sử cột role_id là cột thứ 7 (index 6)
        return role and role[1] == 'GVCN'
    return False


@admin_bp.route('/')
def index():
    if 'user_id' in session:
        user = read_record_by_id('Users', session['user_id'])  # Lấy thông tin user từ DB
        username = user[1] if user else "Người dùng"  # Giả sử cột tên là cột thứ 2 (index 1)
        return render_template('base.html', is_gvcn=is_user_gvcn(), username=username)
    return redirect(url_for('auth.login'))

# --- Classes ---
@admin_bp.route('/classes')
def classes_list():
    if 'user_id' in session:
        classes = read_all_records('Classes', ['id', 'name'])
        return render_template('classes.html', classes=classes, is_gvcn=is_user_gvcn())
    return redirect(url_for('auth.login'))

@admin_bp.route('/classes/create', methods=['GET', 'POST'])
def class_create():
    if 'user_id' in session:
        if request.method == 'POST':
            data = {'name': request.form['name'], 'is_deleted': 0}
            create_record('Classes', data)
            return redirect(url_for('admin.classes_list'))
        return render_template('class_create.html', is_gvcn=is_user_gvcn())
    return redirect(url_for('auth.login'))

@admin_bp.route('/classes/edit/<int:id>', methods=['GET', 'POST'])
def class_edit(id):
    if 'user_id' in session:
        if request.method == 'POST':
            data = {'name': request.form['name']}
            update_record('Classes', id, data)
            return redirect(url_for('admin.classes_list'))
        class_data = read_record_by_id('Classes', id, ['id', 'name'])
        return render_template('class_edit.html', class_data=class_data, is_gvcn=is_user_gvcn())
    return redirect(url_for('auth.login'))

@admin_bp.route('/classes/delete/<int:id>')
def class_delete(id):
    delete_record('Classes', id)
    return redirect(url_for('admin.classes_list'))

# --- Groups ---
@admin_bp.route('/groups')
def groups_list():
    if 'user_id' in session:
        groups = read_all_records('Groups', ['id', 'name'])
        return render_template('groups.html', groups=groups, is_gvcn=is_user_gvcn())
    return redirect(url_for('auth.login'))

@admin_bp.route('/groups/create', methods=['GET', 'POST'])
def group_create():
    if 'user_id' in session:
        if request.method == 'POST':
            data = {'name': request.form['name'], 'is_deleted': 0}
            create_record('Groups', data)
            return redirect(url_for('admin.groups_list'))
        return render_template('group_create.html', is_gvcn=is_user_gvcn())
    return redirect(url_for('auth.login'))

@admin_bp.route('/groups/edit/<int:id>', methods=['GET', 'POST'])
def group_edit(id):
    if 'user_id' in session:
        if request.method == 'POST':
            data = {'name': request.form['name']}
            update_record('Groups', id, data)
            return redirect(url_for('admin.groups_list'))
        group_data = read_record_by_id('Groups', id, ['id', 'name'])
        return render_template('group_edit.html', group_data=group_data, is_gvcn=is_user_gvcn())
    return redirect(url_for('auth.login'))

@admin_bp.route('/groups/delete/<int:id>')
def group_delete(id):
    delete_record('Groups', id)
    return redirect(url_for('admin.groups_list'))

# --- Roles ---
@admin_bp.route('/roles')
def roles_list():
    if 'user_id' in session:
        roles = read_all_records('Roles', ['id', 'name'])
        return render_template('roles.html', roles=roles, is_gvcn=is_user_gvcn())
    return redirect(url_for('auth.login'))

@admin_bp.route('/roles/create', methods=['GET', 'POST'])
def role_create():
    if 'user_id' in session:
        if request.method == 'POST':
            data = {'name': request.form['name'], 'is_deleted': 0}
            create_record('Roles', data)
            return redirect(url_for('admin.roles_list'))
        return render_template('role_create.html', is_gvcn=is_user_gvcn())
    return redirect(url_for('auth.login'))

@admin_bp.route('/roles/edit/<int:id>', methods=['GET', 'POST'])
def role_edit(id):
    if 'user_id' in session:
        if request.method == 'POST':
            data = {'name': request.form['name']}
            update_record('Roles', id, data)
            return redirect(url_for('admin.roles_list'))
        role_data = read_record_by_id('Roles', id, ['id', 'name'])
        return render_template('role_edit.html', role_data=role_data, is_gvcn=is_user_gvcn())
    return redirect(url_for('auth.login'))

@admin_bp.route('/roles/delete/<int:id>')
def role_delete(id):
    delete_record('Roles', id)
    return redirect(url_for('admin.roles_list'))

# --- Conduct ---
@admin_bp.route('/conducts')
def conducts_list():
    if 'user_id' in session:
        conducts = read_all_records('Conduct', ['id', 'name', 'conduct_type', 'conduct_points'])
        return render_template('conducts.html', conducts=conducts, is_gvcn=is_user_gvcn())
    return redirect(url_for('auth.login'))

@admin_bp.route('/conducts/create', methods=['GET', 'POST'])
def conduct_create():
    if 'user_id' in session:
        if request.method == 'POST':
            data = {
                'name': request.form['name'],
                'conduct_type': request.form['conduct_type'],
                'conduct_points': request.form['conduct_points'],
                'is_deleted': 0
            }
            create_record('Conduct', data)
            return redirect(url_for('admin.conducts_list'))
        return render_template('conduct_create.html', is_gvcn=is_user_gvcn())
    return redirect(url_for('auth.login'))

@admin_bp.route('/conducts/edit/<int:id>', methods=['GET', 'POST'])
def conduct_edit(id):
    if 'user_id' in session:
        if request.method == 'POST':
            data = {
                'name': request.form['name'],
                'conduct_type': request.form['conduct_type'],
                'conduct_points': request.form['conduct_points']
            }
            update_record('Conduct', id, data)
            return redirect(url_for('admin.conducts_list'))
        conduct_data = read_record_by_id('Conduct', id, ['id', 'name', 'conduct_type', 'conduct_points'])
        return render_template('conduct_edit.html', conduct_data=conduct_data, is_gvcn=is_user_gvcn())
    return redirect(url_for('auth.login'))

@admin_bp.route('/conducts/delete/<int:id>')
def conduct_delete(id):
    delete_record('Conduct', id)
    return redirect(url_for('admin.conducts_list'))

# --- Subjects ---
@admin_bp.route('/subjects')
def subjects_list():
    if 'user_id' in session:
        subjects = read_all_records('Subjects', ['id', 'name'])
        return render_template('subjects.html', subjects=subjects, is_gvcn=is_user_gvcn())
    return redirect(url_for('auth.login'))

@admin_bp.route('/subjects/create', methods=['GET', 'POST'])
def subject_create():
    if 'user_id' in session:
        if request.method == 'POST':
            data = {'name': request.form['name'], 'is_deleted': 0}
            create_record('Subjects', data)
            return redirect(url_for('admin.subjects_list'))
        return render_template('subject_create.html', is_gvcn=is_user_gvcn())
    return redirect(url_for('auth.login'))

@admin_bp.route('/subjects/edit/<int:id>', methods=['GET', 'POST'])
def subject_edit(id):
    if 'user_id' in session:
        if request.method == 'POST':
            data = {'name': request.form['name']}
            update_record('Subjects', id, data)
            return redirect(url_for('admin.subjects_list'))
        subject_data = read_record_by_id('Subjects', id, ['id', 'name'])
        return render_template('subject_edit.html', subject_data=subject_data, is_gvcn=is_user_gvcn())
    return redirect(url_for('auth.login'))

@admin_bp.route('/subjects/delete/<int:id>')
def subject_delete(id):
    delete_record('Subjects', id)
    return redirect(url_for('admin.subjects_list'))

# --- Criteria ---
@admin_bp.route('/criteria')
def criteria_list():
    if 'user_id' in session:
        criteria = read_all_records('Criteria', ['id', 'name', 'criterion_type', 'criterion_points'])
        return render_template('criteria.html', criteria=criteria, is_gvcn=is_user_gvcn())
    return redirect(url_for('auth.login'))

@admin_bp.route('/criteria/create', methods=['GET', 'POST'])
def criteria_create():
    if 'user_id' in session:
        if request.method == 'POST':
            data = {
                'name': request.form['name'],
                'criterion_type': 1 if request.form.get('criterion_type') == 'on' else 0,
                'criterion_points': request.form['criterion_points'],
                'is_deleted': 0
            }
            create_record('Criteria', data)
            return redirect(url_for('admin.criteria_list'))
        return render_template('criteria_create.html', is_gvcn=is_user_gvcn())
    return redirect(url_for('auth.login'))

@admin_bp.route('/criteria/edit/<int:id>', methods=['GET', 'POST'])
def criteria_edit(id):
    if 'user_id' in session:
        if request.method == 'POST':
            data = {
                'name': request.form['name'],
                'criterion_type': 1 if request.form.get('criterion_type') == 'on' else 0,
                'criterion_points': request.form['criterion_points']
            }
            update_record('Criteria', id, data)
            return redirect(url_for('admin.criteria_list'))
        criteria_data = read_record_by_id('Criteria', id, ['id', 'name', 'criterion_type', 'criterion_points'])
        return render_template('criteria_edit.html', criteria_data=criteria_data, is_gvcn=is_user_gvcn())
    return redirect(url_for('auth.login'))

@admin_bp.route('/criteria/delete/<int:id>')
def criteria_delete(id):
    delete_record('Criteria', id)
    return redirect(url_for('admin.criteria_list'))

# --- Users ---
@admin_bp.route('/users')
def users_list():
    if 'user_id' in session:
        conn = connect_db()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT u.id, u.name, u.username, c.name AS class_name, r.name AS role_name
            FROM Users u
            LEFT JOIN Classes c ON u.class_id = c.id
            LEFT JOIN Roles r ON u.role_id = r.id
            WHERE u.is_deleted = 0
        """)
        users = cursor.fetchall()
        conn.close()
        return render_template('users.html', users=users, is_gvcn=is_user_gvcn())
    return redirect(url_for('auth.login'))

@admin_bp.route('/users/create', methods=['GET', 'POST'])
def user_create():
    if 'user_id' in session:
        error_message = None
        if request.method == 'POST':
            name = request.form['name']
            username = request.form['username']
            password = request.form['password']
            class_id = request.form['class_id']
            role_id = request.form['role_id']

            if not all([name, username, password, class_id, role_id]):
                error_message = 'Vui lòng điền đầy đủ tất cả các trường.'
                classes = read_all_records('Classes', ['id', 'name'])
                roles = read_all_records('Roles', ['id', 'name'])
                return render_template('user_create.html', classes=classes, roles=roles, error_message=error_message, is_gvcn=is_user_gvcn())

            conn = connect_db()
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM Users WHERE username = ? AND is_deleted = 0", (username,))
            existing_user = cursor.fetchone()

            if existing_user:
                conn.close()
                error_message = 'Tên đăng nhập đã tồn tại. Vui lòng chọn tên khác.'
                classes = read_all_records('Classes', ['id', 'name'])
                roles = read_all_records('Roles', ['id', 'name'])
                return render_template('user_create.html', classes=classes, roles=roles, error_message=error_message, is_gvcn=is_user_gvcn())

            data = {
                'name': name,
                'username': username,
                'password': password,
                'class_id': class_id,
                'role_id': role_id,
                'is_deleted': 0
            }
            create_record('Users', data)
            conn.close()
            return redirect(url_for('admin.users_list'))

        classes = read_all_records('Classes', ['id', 'name'])
        roles = read_all_records('Roles', ['id', 'name'])
        return render_template('user_create.html', classes=classes, roles=roles, error_message=error_message, is_gvcn=is_user_gvcn())
    return redirect(url_for('auth.login'))

@admin_bp.route('/users/edit/<int:id>', methods=['GET', 'POST'])
def user_edit(id):
    if 'user_id' in session:
        error_message = None
        if request.method == 'POST':
            name = request.form['name']
            username = request.form['username']
            password = request.form['password']
            class_id = request.form['class_id']
            role_id = request.form['role_id']

            if not all([name, username, password, class_id, role_id]):
                error_message = 'Vui lòng điền đầy đủ tất cả các trường.'
                user = read_record_by_id('Users', id, ['id', 'name', 'username', 'password', 'class_id', 'group_id', 'role_id'])
                classes = read_all_records('Classes', ['id', 'name'])
                roles = read_all_records('Roles', ['id', 'name'])
                return render_template('user_edit.html', user=user, classes=classes, roles=roles, error_message=error_message, is_gvcn=is_user_gvcn())

            conn = connect_db()
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM Users WHERE username = ? AND id != ? AND is_deleted = 0", (username, id))
            existing_user = cursor.fetchone()

            if existing_user:
                conn.close()
                error_message = 'Tên đăng nhập đã tồn tại. Vui lòng chọn tên khác.'
                user = read_record_by_id('Users', id, ['id', 'name', 'username', 'password', 'class_id', 'group_id', 'role_id'])
                classes = read_all_records('Classes', ['id', 'name'])
                roles = read_all_records('Roles', ['id', 'name'])
                return render_template('user_edit.html', user=user, classes=classes, roles=roles, error_message=error_message, is_gvcn=is_user_gvcn())

            data = {
                'name': name,
                'username': username,
                'password': password,
                'class_id': class_id,
                'role_id': role_id
            }
            update_record('Users', id, data)
            conn.close()
            return redirect(url_for('admin.users_list'))

        user = read_record_by_id('Users', id, ['id', 'name', 'username', 'password', 'class_id', 'group_id', 'role_id'])
        classes = read_all_records('Classes', ['id', 'name'])
        roles = read_all_records('Roles', ['id', 'name'])
        return render_template('user_edit.html', user=user, classes=classes, roles=roles, error_message=error_message, is_gvcn=is_user_gvcn())
    return redirect(url_for('auth.login'))

@admin_bp.route('/users/delete/<int:id>')
def user_delete(id):
    delete_record('Users', id)
    return redirect(url_for('admin.users_list'))