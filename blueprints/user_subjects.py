from flask import Blueprint, render_template, request, redirect, url_for, session, jsonify
from db_utils import (create_record, read_all_records, read_record_by_id,
                      update_record, delete_record, connect_db)
from datetime import datetime, timedelta

user_subjects_bp = Blueprint('user_subjects', __name__)

def is_user_gvcn():
    if 'user_id' in session:
        user = read_record_by_id('Users', session['user_id'])
        role = read_record_by_id('Roles', user[6])
        return role and role[1] == 'GVCN'
    return False

def get_users_excluding_gvcn():
    try:
        conn = connect_db()
        cursor = conn.cursor()

        # Lấy ID của vai trò GVCN
        cursor.execute("SELECT id FROM Roles WHERE name = 'GVCN'")
        role_result = cursor.fetchone()
        gvcn_role_id = role_result[0] if role_result else None

        # Lấy danh sách người dùng dựa trên vai trò GVCN
        if gvcn_role_id is not None:
            cursor.execute("SELECT id, name FROM Users WHERE is_deleted = 0 AND role_id != ?", (gvcn_role_id,))
        else:
            cursor.execute("SELECT id, name FROM Users WHERE is_deleted = 0")

        users = cursor.fetchall()
        return users

    except Exception as e:
        print(f"Lỗi khi lấy danh sách người học sinh: {e}")
        return None  # Trả về None nếu có lỗi

    finally:
        # Không đóng kết nối ở đây, để hàm gọi quyết định.
        pass


@user_subjects_bp.route('/user_subjects', methods=['GET', 'POST'])
def user_subjects_list():
    if 'user_id' in session:
        sort_by = request.args.get('sort_by', 'registered_date')
        sort_order = request.args.get('sort_order', 'asc')

        valid_columns = {
            'user_name': 'u.name',
            'subject_name': 's.name',
            'criteria_name': 'cr.name',
            'group_name': 'g.name',
            'registered_date': 'us.registered_date',
            'total_points': 'us.total_points',
            'entered_by': 'us.entered_by'
        }
        sort_column = valid_columns.get(sort_by, 'us.registered_date')
        sort_direction = 'DESC' if sort_order == 'desc' else 'ASC'

        conn = connect_db()
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM Roles WHERE name = 'GVCN'")
        role_result = cursor.fetchone()
        gvcn_role_id = role_result[0] if role_result else None
        cursor.execute("SELECT id FROM Groups WHERE name = 'Giáo viên'")
        group_result = cursor.fetchone()
        teacher_group_id = group_result[0] if group_result else None
        conn.close()

        users = get_users_excluding_gvcn()

        conn = connect_db()
        cursor = conn.cursor()
        cursor.execute("SELECT id, name FROM Subjects WHERE is_deleted = 0")
        subjects = cursor.fetchall()
        cursor.execute("SELECT id, name FROM Criteria WHERE is_deleted = 0")
        criteria = cursor.fetchall()
        if teacher_group_id is not None:
            cursor.execute("SELECT id, name FROM Groups WHERE is_deleted = 0 AND id != ?", (teacher_group_id,))
        else:
            cursor.execute("SELECT id, name FROM Groups WHERE is_deleted = 0")
        groups = cursor.fetchall()
        conn.close()

        today = datetime.today()
        if today.weekday() >= 5:
            nearest_monday = today - timedelta(days=today.weekday())
        else:
            nearest_monday = today - timedelta(days=today.weekday() + 7)
        default_date_from = nearest_monday.strftime('%Y-%m-%d')
        default_date_to = (nearest_monday + timedelta(days=4)).strftime('%Y-%m-%d')

        selected_users = []
        date_from = default_date_from
        date_to = default_date_to
        selected_subjects = []
        selected_groups = []
        select_all_users = False
        select_all_subjects = False
        select_all_groups = False

        if request.method == 'POST':
            select_all_users = request.form.get('select_all_users') == 'on'
            selected_users = request.form.getlist('users')
            date_from = request.form.get('date_from') or default_date_from
            date_to = request.form.get('date_to') or default_date_to
            select_all_subjects = request.form.get('select_all_subjects') == 'on'
            selected_subjects = request.form.getlist('subjects')
            select_all_groups = request.form.get('select_all_groups') == 'on'
            selected_groups = request.form.getlist('groups')
        else:
            select_all_users = request.args.get('select_all_users') == 'on'
            selected_users = request.args.getlist('users')
            date_from = request.args.get('date_from') or default_date_from
            date_to = request.args.get('date_to') or default_date_to
            select_all_subjects = request.args.get('select_all_subjects') == 'on'
            selected_subjects = request.args.getlist('subjects')
            select_all_groups = request.args.get('select_all_groups') == 'on'
            selected_groups = request.args.getlist('groups')

        conn = connect_db()
        cursor = conn.cursor()
        if gvcn_role_id is not None:
            query = """
                SELECT us.id, u.name AS user_name, s.name AS subject_name, cr.name AS criteria_name, 
                       us.registered_date, us.total_points, us.entered_by, g.name AS group_name
                FROM User_Subjects us
                JOIN Users u ON us.user_id = u.id
                JOIN Subjects s ON us.subject_id = s.id
                LEFT JOIN Criteria cr ON us.criteria_id = cr.id
                JOIN Groups g ON u.group_id = g.id
                WHERE us.is_deleted = 0 AND u.role_id != ?
            """
            params = [gvcn_role_id]
        else:
            query = """
                SELECT us.id, u.name AS user_name, s.name AS subject_name, cr.name AS criteria_name, 
                       us.registered_date, us.total_points, us.entered_by, g.name AS group_name
                FROM User_Subjects us
                JOIN Users u ON us.user_id = u.id
                JOIN Subjects s ON us.subject_id = s.id
                LEFT JOIN Criteria cr ON us.criteria_id = cr.id
                JOIN Groups g ON u.group_id = g.id
                WHERE us.is_deleted = 0
            """
            params = []

        if select_all_users:
            all_user_ids = [user[0] for user in users]
            if all_user_ids:
                query += " AND us.user_id IN ({})".format(','.join('?' * len(all_user_ids)))
                params.extend(all_user_ids)
        elif selected_users:
            query += " AND us.user_id IN ({})".format(','.join('?' * len(selected_users)))
            params.extend(selected_users)

        if date_from:
            query += " AND us.registered_date >= ?"
            params.append(date_from)
        if date_to:
            query += " AND us.registered_date <= ?"
            params.append(date_to)

        if select_all_subjects:
            all_subject_ids = [subject[0] for subject in subjects]
            if all_subject_ids:
                query += " AND us.subject_id IN ({})".format(','.join('?' * len(all_subject_ids)))
                params.extend(all_subject_ids)
        elif selected_subjects:
            query += " AND us.subject_id IN ({})".format(','.join('?' * len(selected_subjects)))
            params.extend(selected_subjects)

        if select_all_groups:
            all_group_ids = [group[0] for group in groups]
            if all_group_ids:
                query += " AND u.group_id IN ({})".format(','.join('?' * len(all_group_ids)))
                params.extend(all_group_ids)
        elif selected_groups:
            query += " AND u.group_id IN ({})".format(','.join('?' * len(selected_groups)))
            params.extend(selected_groups)

        query += f" ORDER BY {sort_column} {sort_direction}"
        cursor.execute(query, params)
        records = cursor.fetchall()
        conn.close()

        return render_template('user_subjects.html',
                               records=records,
                               users=users,
                               subjects=subjects,
                               criteria=criteria,
                               groups=groups,
                               sort_by=sort_by,
                               sort_order=sort_order,
                               date_from=date_from,
                               date_to=date_to,
                               selected_users=selected_users,
                               selected_subjects=selected_subjects,
                               selected_groups=selected_groups,
                               select_all_users=select_all_users,
                               select_all_subjects=select_all_subjects,
                               select_all_groups=select_all_groups,
                               is_gvcn=is_user_gvcn())
    return redirect(url_for('auth.login'))

@user_subjects_bp.route('/user_subjects/create', methods=['GET', 'POST'])
def user_subjects_create():
    if 'user_id' in session:
        sort_by = request.args.get('sort_by', 'registered_date')
        sort_order = request.args.get('sort_order', 'asc')
        date_from = request.args.get('date_from', '')
        date_to = request.args.get('date_to', '')
        selected_users = request.args.getlist('users')
        selected_subjects = request.args.getlist('subjects')
        selected_groups = request.args.getlist('groups')
        select_all_users = request.args.get('select_all_users') == 'on'
        select_all_subjects = request.args.get('select_all_subjects') == 'on'
        select_all_groups = request.args.get('select_all_groups') == 'on'

        # Lấy thông tin user đang đăng nhập
        current_user_id = session['user_id']
        current_user = read_record_by_id('Users', current_user_id, ['id', 'name'])
        current_user_name = current_user[1] if current_user else 'Unknown'  # Lấy tên user, mặc định là 'Unknown' nếu không tìm thấy

        if request.method == 'POST':
            user_id = request.form['user_id']
            subject_id = request.form['subject_id']
            criteria_id = request.form['criteria_id'] if request.form['criteria_id'] else None
            registered_date = request.form['registered_date']
            criteria_points = float(request.form['criteria_points'])

            data = {
                'user_id': user_id,
                'subject_id': subject_id,
                'criteria_id': criteria_id,
                'registered_date': registered_date,
                'total_points': criteria_points,
                'entered_by': request.form['entered_by'],
                'is_deleted': 0
            }
            create_record('User_Subjects', data)

            return redirect(url_for('user_subjects.user_subjects_list',
                                    sort_by=sort_by,
                                    sort_order=sort_order,
                                    date_from=date_from,
                                    date_to=date_to,
                                    users=selected_users,
                                    subjects=selected_subjects,
                                    groups=selected_groups,
                                    select_all_users=select_all_users,
                                    select_all_subjects=select_all_subjects,
                                    select_all_groups=select_all_groups))

        users = get_users_excluding_gvcn()

        conn = connect_db()
        cursor = conn.cursor()
        cursor.execute("SELECT id, name FROM Subjects WHERE is_deleted = 0")
        subjects = cursor.fetchall()
        cursor.execute("SELECT id, name FROM Criteria WHERE is_deleted = 0")
        criteria = cursor.fetchall()
        conn.close()

        return render_template('user_subjects_create.html',
                               users=users,
                               subjects=subjects,
                               criteria=criteria,
                               sort_by=sort_by,
                               sort_order=sort_order,
                               date_from=date_from,
                               date_to=date_to,
                               selected_users=selected_users,
                               selected_subjects=selected_subjects,
                               selected_groups=selected_groups,
                               select_all_users=select_all_users,
                               select_all_subjects=select_all_subjects,
                               select_all_groups=select_all_groups,
                               current_user_name=current_user_name,  # Truyền tên user đang đăng nhập vào template
                               is_gvcn=is_user_gvcn())
    return redirect(url_for('auth.login'))

@user_subjects_bp.route('/user_subjects/edit/<int:id>', methods=['GET', 'POST'])
def user_subjects_edit(id):
    if 'user_id' in session:
        sort_by = request.args.get('sort_by', 'registered_date')
        sort_order = request.args.get('sort_order', 'asc')
        date_from = request.args.get('date_from', '')
        date_to = request.args.get('date_to', '')
        selected_users = request.args.getlist('users')
        selected_subjects = request.args.getlist('subjects')
        selected_groups = request.args.getlist('groups')
        select_all_users = request.args.get('select_all_users') == 'on'
        select_all_subjects = request.args.get('select_all_subjects') == 'on'
        select_all_groups = request.args.get('select_all_groups') == 'on'

        if request.method == 'POST':
            user_id = request.form['user_id']
            subject_id = request.form['subject_id']
            criteria_id = request.form['criteria_id'] if request.form['criteria_id'] else None
            registered_date = request.form['registered_date']
            criteria_points = float(request.form['criteria_points'])

            data = {
                'user_id': user_id,
                'subject_id': subject_id,
                'criteria_id': criteria_id,
                'registered_date': registered_date,
                'total_points': criteria_points,
                'entered_by': request.form['entered_by']
            }
            update_record('User_Subjects', id, data)

            return redirect(url_for('user_subjects.user_subjects_list',
                                    sort_by=sort_by,
                                    sort_order=sort_order,
                                    date_from=date_from,
                                    date_to=date_to,
                                    users=selected_users,
                                    subjects=selected_subjects,
                                    groups=selected_groups,
                                    select_all_users=select_all_users,
                                    select_all_subjects=select_all_subjects,
                                    select_all_groups=select_all_groups))

        record = read_record_by_id('User_Subjects', id,
                                   ['id', 'user_id', 'subject_id', 'criteria_id', 'registered_date', 'total_points', 'entered_by'])

        users = get_users_excluding_gvcn()

        conn = connect_db()
        cursor = conn.cursor()
        cursor.execute("SELECT id, name FROM Subjects WHERE is_deleted = 0")
        subjects = cursor.fetchall()
        cursor.execute("SELECT id, name FROM Criteria WHERE is_deleted = 0")
        criteria = cursor.fetchall()
        conn.close()

        print(f"id: {id}")
        return render_template('user_subjects_edit.html',
                               id=id,  # Thêm dòng này để truyền id vào template
                               record=record,
                               users=users,
                               subjects=subjects,
                               criteria=criteria,
                               sort_by=sort_by,
                               sort_order=sort_order,
                               date_from=date_from,
                               date_to=date_to,
                               selected_users=selected_users,
                               selected_subjects=selected_subjects,
                               selected_groups=selected_groups,
                               select_all_users=select_all_users,
                               select_all_subjects=select_all_subjects,
                               select_all_groups=select_all_groups,
                               is_gvcn=is_user_gvcn())
    return redirect(url_for('auth.login'))

@user_subjects_bp.route('/user_subjects/delete/<int:id>')
def user_subjects_delete(id):
    sort_by = request.args.get('sort_by', 'registered_date')
    sort_order = request.args.get('sort_order', 'asc')
    date_from = request.args.get('date_from', '')
    date_to = request.args.get('date_to', '')
    selected_users = request.args.getlist('users')
    selected_subjects = request.args.getlist('subjects')
    selected_groups = request.args.getlist('groups')
    select_all_users = request.args.get('select_all_users') == 'on'
    select_all_subjects = request.args.get('select_all_subjects') == 'on'
    select_all_groups = request.args.get('select_all_groups') == 'on'

    delete_record('User_Subjects', id)

    return redirect(url_for('user_subjects.user_subjects_list',
                            sort_by=sort_by,
                            sort_order=sort_order,
                            date_from=date_from,
                            date_to=date_to,
                            users=selected_users,
                            subjects=selected_subjects,
                            groups=selected_groups,
                            select_all_users=select_all_users,
                            select_all_subjects=select_all_subjects,
                            select_all_groups=select_all_groups))

@user_subjects_bp.route('/get_criteria_points/<int:criteria_id>')
def get_criteria_points(criteria_id):
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("SELECT criterion_points FROM Criteria WHERE id = ? AND is_deleted = 0", (criteria_id,))
    result = cursor.fetchone()
    conn.close()
    return jsonify({'criterion_points': result[0] if result else 0})

@user_subjects_bp.route('/user_subjects_total_points')
def user_subjects_total_points():
    user_id = request.args.get('user_id')
    registered_date = request.args.get('registered_date')
    exclude_id = request.args.get('exclude_id')

    conn = connect_db()  # Giả sử connect_db() là hàm kết nối database của bạn
    cursor = conn.cursor()
    query = """
        SELECT SUM(total_points) 
        FROM User_Subjects
        WHERE user_id = ? AND registered_date = ? AND is_deleted = 0
    """
    params = [user_id, registered_date]

    print(exclude_id)
    if exclude_id:
        query += " AND id != ?"
        params.append(exclude_id)

    print(query)
    print(params)
    cursor.execute(query, params)
    total_points = cursor.fetchone()[0] or 0
    conn.close()
    return jsonify({'total_points': total_points})