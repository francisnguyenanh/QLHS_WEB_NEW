from flask import Blueprint, render_template, request, redirect, url_for, session, jsonify
from db_utils import (create_record, read_all_records, read_record_by_id,
                      update_record, delete_record, connect_db)
from datetime import datetime, timedelta

user_conduct_bp = Blueprint('user_conduct', __name__)

def is_user_gvcn():
    if 'user_id' in session:
        user = read_record_by_id('Users', session['user_id'])
        role = read_record_by_id('Roles', user[6])
        return role and role[1] == 'GVCN'
    return False

@user_conduct_bp.route('/user_conduct', methods=['GET', 'POST'])
def user_conduct_list():
    if 'user_id' in session:
        sort_by = request.args.get('sort_by', 'registered_date')
        sort_order = request.args.get('sort_order', 'asc')

        valid_columns = {
            'user_name': 'u.name',
            'conduct_name': 'c.name',
            'group_name': 'g.name',
            'registered_date': 'uc.registered_date',
            'total_points': 'uc.total_points',
            'entered_by': 'uc.entered_by'
        }
        sort_column = valid_columns.get(sort_by, 'uc.registered_date')
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

        conn = connect_db()
        cursor = conn.cursor()
        if gvcn_role_id is not None:
            cursor.execute("SELECT id, name FROM Users WHERE is_deleted = 0 AND role_id != ?", (gvcn_role_id,))
        else:
            cursor.execute("SELECT id, name FROM Users WHERE is_deleted = 0")
        users = cursor.fetchall()
        cursor.execute("SELECT id, name FROM Conduct WHERE is_deleted = 0")
        conducts = cursor.fetchall()
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
        selected_conducts = []
        selected_groups = []
        select_all_users = False
        select_all_conducts = False
        select_all_groups = False

        if request.method == 'POST':
            select_all_users = request.form.get('select_all_users') == 'on'
            selected_users = request.form.getlist('users')
            date_from = request.form.get('date_from') or default_date_from
            date_to = request.form.get('date_to') or default_date_to
            select_all_conducts = request.form.get('select_all_conducts') == 'on'
            selected_conducts = request.form.getlist('conducts')
            select_all_groups = request.form.get('select_all_groups') == 'on'
            selected_groups = request.form.getlist('groups')
        else:
            select_all_users = request.args.get('select_all_users') == 'on'
            selected_users = request.args.getlist('users')
            date_from = request.args.get('date_from') or default_date_from
            date_to = request.args.get('date_to') or default_date_to
            select_all_conducts = request.args.get('select_all_conducts') == 'on'
            selected_conducts = request.args.getlist('conducts')
            select_all_groups = request.args.get('select_all_groups') == 'on'
            selected_groups = request.args.getlist('groups')

        conn = connect_db()
        cursor = conn.cursor()
        if gvcn_role_id is not None:
            query = """
                SELECT uc.id, u.name AS user_name, c.name AS conduct_name, uc.registered_date, uc.total_points, uc.entered_by, g.name AS group_name
                FROM User_Conduct uc
                JOIN Users u ON uc.user_id = u.id
                JOIN Conduct c ON uc.conduct_id = c.id
                JOIN Groups g ON u.group_id = g.id
                WHERE uc.is_deleted = 0 AND u.role_id != ?
            """
            params = [gvcn_role_id]
        else:
            query = """
                SELECT uc.id, u.name AS user_name, c.name AS conduct_name, uc.registered_date, uc.total_points, uc.entered_by, g.name AS group_name
                FROM User_Conduct uc
                JOIN Users u ON uc.user_id = u.id
                JOIN Conduct c ON uc.conduct_id = c.id
                JOIN Groups g ON u.group_id = g.id
                WHERE uc.is_deleted = 0
            """
            params = []

        if select_all_users:
            all_user_ids = [user[0] for user in users]
            if all_user_ids:
                query += " AND uc.user_id IN ({})".format(','.join('?' * len(all_user_ids)))
                params.extend(all_user_ids)
        elif selected_users:
            query += " AND uc.user_id IN ({})".format(','.join('?' * len(selected_users)))
            params.extend(selected_users)

        if date_from:
            query += " AND uc.registered_date >= ?"
            params.append(date_from)
        if date_to:
            query += " AND uc.registered_date <= ?"
            params.append(date_to)

        if select_all_conducts:
            all_conduct_ids = [conduct[0] for conduct in conducts]
            if all_conduct_ids:
                query += " AND uc.conduct_id IN ({})".format(','.join('?' * len(all_conduct_ids)))
                params.extend(all_conduct_ids)
        elif selected_conducts:
            query += " AND uc.conduct_id IN ({})".format(','.join('?' * len(selected_conducts)))
            params.extend(selected_conducts)

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

        return render_template('user_conduct.html',
                               records=records,
                               users=users,
                               conducts=conducts,
                               groups=groups,
                               sort_by=sort_by,
                               sort_order=sort_order,
                               date_from=date_from,
                               date_to=date_to,
                               selected_users=selected_users,
                               selected_conducts=selected_conducts,
                               selected_groups=selected_groups,
                               select_all_users=select_all_users,
                               select_all_conducts=select_all_conducts,
                               select_all_groups=select_all_groups,
                               is_gvcn=is_user_gvcn())
    return redirect(url_for('auth.login'))

@user_conduct_bp.route('/user_conduct/create', methods=['GET', 'POST'])
def user_conduct_create():
    if 'user_id' in session:
        sort_by = request.args.get('sort_by', 'registered_date')
        sort_order = request.args.get('sort_order', 'asc')
        date_from = request.args.get('date_from', '')
        date_to = request.args.get('date_to', '')
        selected_users = request.args.getlist('users')
        selected_conducts = request.args.getlist('conducts')
        selected_groups = request.args.getlist('groups')
        select_all_users = request.args.get('select_all_users') == 'on'
        select_all_conducts = request.args.get('select_all_conducts') == 'on'
        select_all_groups = request.args.get('select_all_groups') == 'on'

        # Lấy thông tin user đang đăng nhập
        current_user_id = session['user_id']
        current_user = read_record_by_id('Users', current_user_id, ['id', 'name'])
        current_user_name = current_user[1] if current_user else 'Unknown'  # Lấy tên user, mặc định là 'Unknown' nếu không tìm thấy

        if request.method == 'POST':
            user_id = request.form['user_id']
            conduct_id = request.form['conduct_id']
            registered_date = request.form['registered_date']
            conduct_points = float(request.form['conduct_points'])

            data = {
                'user_id': user_id,
                'conduct_id': conduct_id,
                'registered_date': registered_date,
                'total_points': conduct_points,
                'entered_by': request.form['entered_by'],
                'is_deleted': 0
            }
            create_record('User_Conduct', data)

            return redirect(url_for('user_conduct.user_conduct_list',
                                    sort_by=sort_by,
                                    sort_order=sort_order,
                                    date_from=date_from,
                                    date_to=date_to,
                                    users=selected_users,
                                    conducts=selected_conducts,
                                    groups=selected_groups,
                                    select_all_users=select_all_users,
                                    select_all_conducts=select_all_conducts,
                                    select_all_groups=select_all_groups))

        users = read_all_records('Users', ['id', 'name'])
        conducts = read_all_records('Conduct', ['id', 'name'])
        return render_template('user_conduct_create.html',
                               users=users,
                               conducts=conducts,
                               sort_by=sort_by,
                               sort_order=sort_order,
                               date_from=date_from,
                               date_to=date_to,
                               selected_users=selected_users,
                               selected_conducts=selected_conducts,
                               selected_groups=selected_groups,
                               select_all_users=select_all_users,
                               select_all_conducts=select_all_conducts,
                               select_all_groups=select_all_groups,
                               current_user_name=current_user_name,  # Truyền tên user đang đăng nhập vào template
                               is_gvcn=is_user_gvcn())
    return redirect(url_for('auth.login'))

@user_conduct_bp.route('/user_conduct/edit/<int:id>', methods=['GET', 'POST'])
def user_conduct_edit(id):
    if 'user_id' in session:
        sort_by = request.args.get('sort_by', 'registered_date')
        sort_order = request.args.get('sort_order', 'asc')
        date_from = request.args.get('date_from', '')
        date_to = request.args.get('date_to', '')
        selected_users = request.args.getlist('users')
        selected_conducts = request.args.getlist('conducts')
        selected_groups = request.args.getlist('groups')
        select_all_users = request.args.get('select_all_users') == 'on'
        select_all_conducts = request.args.get('select_all_conducts') == 'on'
        select_all_groups = request.args.get('select_all_groups') == 'on'

        if request.method == 'POST':
            user_id = request.form['user_id']
            conduct_id = request.form['conduct_id']
            registered_date = request.form['registered_date']
            conduct_points = float(request.form['conduct_points'])  # Lấy giá trị từ ô Điểm hạnh kiểm

            data = {
                'user_id': user_id,
                'conduct_id': conduct_id,
                'registered_date': registered_date,
                'total_points': conduct_points,  # Lưu conduct_points vào total_points của bản ghi
                'entered_by': request.form['entered_by']
            }
            update_record('User_Conduct', id, data)

            return redirect(url_for('user_conduct.user_conduct_list',
                                    sort_by=sort_by,
                                    sort_order=sort_order,
                                    date_from=date_from,
                                    date_to=date_to,
                                    users=selected_users,
                                    conducts=selected_conducts,
                                    groups=selected_groups,
                                    select_all_users=select_all_users,
                                    select_all_conducts=select_all_conducts,
                                    select_all_groups=select_all_groups))

        record = read_record_by_id('User_Conduct', id,
                                   ['id', 'user_id', 'conduct_id', 'registered_date', 'total_points', 'entered_by'])
        users = read_all_records('Users', ['id', 'name'])
        conducts = read_all_records('Conduct', ['id', 'name'])
        return render_template('user_conduct_edit.html',
                               id=id,  # Truyền id vào template
                               record=record,
                               users=users,
                               conducts=conducts,
                               sort_by=sort_by,
                               sort_order=sort_order,
                               date_from=date_from,
                               date_to=date_to,
                               selected_users=selected_users,
                               selected_conducts=selected_conducts,
                               selected_groups=selected_groups,
                               select_all_users=select_all_users,
                               select_all_conducts=select_all_conducts,
                               select_all_groups=select_all_groups,
                               is_gvcn=is_user_gvcn())
    return redirect(url_for('auth.login'))

@user_conduct_bp.route('/user_conduct/delete/<int:id>')
def user_conduct_delete(id):
    sort_by = request.args.get('sort_by', 'registered_date')
    sort_order = request.args.get('sort_order', 'asc')
    date_from = request.args.get('date_from', '')
    date_to = request.args.get('date_to', '')
    selected_users = request.args.getlist('users')
    selected_conducts = request.args.getlist('conducts')
    selected_groups = request.args.getlist('groups')
    select_all_users = request.args.get('select_all_users') == 'on'
    select_all_conducts = request.args.get('select_all_conducts') == 'on'
    select_all_groups = request.args.get('select_all_groups') == 'on'

    delete_record('User_Conduct', id)

    return redirect(url_for('user_conduct.user_conduct_list',
                            sort_by=sort_by,
                            sort_order=sort_order,
                            date_from=date_from,
                            date_to=date_to,
                            users=selected_users,
                            conducts=selected_conducts,
                            groups=selected_groups,
                            select_all_users=select_all_users,
                            select_all_conducts=select_all_conducts,
                            select_all_groups=select_all_groups))

@user_conduct_bp.route('/get_conduct_points/<int:conduct_id>')
def get_conduct_points(conduct_id):
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("SELECT conduct_points FROM Conduct WHERE id = ? AND is_deleted = 0", (conduct_id,))
    result = cursor.fetchone()
    conn.close()
    return jsonify({'conduct_points': result[0] if result else 0})

@user_conduct_bp.route('/user_conduct_total_points')
def user_conduct_total_points():
    user_id = request.args.get('user_id')
    registered_date = request.args.get('registered_date')
    exclude_id = request.args.get('exclude_id')

    conn = connect_db()
    cursor = conn.cursor()
    query = """
        SELECT SUM(total_points) 
        FROM User_Conduct
        WHERE user_id = ? AND registered_date = ? AND is_deleted = 0
    """
    params = [user_id, registered_date]

    if exclude_id:
        query += " AND id != ?"
        params.append(exclude_id)

    cursor.execute(query, params)
    total_points = cursor.fetchone()[0] or 0
    conn.close()
    return jsonify({'total_points': total_points})