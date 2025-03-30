from flask import Blueprint, render_template, request, redirect, url_for, session, make_response
from db_utils import read_all_records, read_record_by_id, connect_db
from io import BytesIO
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from datetime import datetime, timedelta

summary_bp = Blueprint('summary', __name__)

def is_user_gvcn():
    if 'user_id' in session:
        user = read_record_by_id('Users', session['user_id'])
        role = read_record_by_id('Roles', user[6]) # role_id is at index 6
        return (role and role[1] == 'GVCN') # role name is at index 1
    return False

@summary_bp.route('/group_summary', methods=['GET', 'POST'])
def group_summary():
    if 'user_id' in session:
        # Lấy tham số sắp xếp từ query string
        sort_by = request.args.get('sort_by', 'group_name')
        sort_order = request.args.get('sort_order', 'asc')

        # Danh sách cột hợp lệ để sắp xếp
        valid_columns = {
            'group_name': 'group_name',
            'total_points': 'total_points'
        }
        sort_column = valid_columns.get(sort_by, 'group_name')
        sort_direction = 'DESC' if sort_order == 'desc' else 'ASC'

        # Lấy role_id của GVCN và group_id của "Giáo viên" để lọc
        conn = connect_db()
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM Roles WHERE name = 'GVCN'")
        role_result = cursor.fetchone()
        gvcn_role_id = role_result[0] if role_result else None
        cursor.execute("SELECT id FROM Groups WHERE name = 'Giáo viên'")
        group_result = cursor.fetchone()
        teacher_group_id = group_result[0] if group_result else None
        conn.close()

        # Lấy danh sách groups (loại bỏ "Giáo viên")
        conn = connect_db()
        cursor = conn.cursor()
        if teacher_group_id is not None:
            cursor.execute("SELECT id, name FROM Groups WHERE is_deleted = 0 AND id != ?", (teacher_group_id,))
        else:
            cursor.execute("SELECT id, name FROM Groups WHERE is_deleted = 0")
        groups = cursor.fetchall()
        conn.close()

        # Tính toán ngày mặc định: Thứ 2~6 gần ngày hệ thống nhất
        today = datetime.today()
        if today.weekday() >= 5:  # Nếu là thứ Bảy (5) hoặc Chủ Nhật (6)
            nearest_monday = today - timedelta(days=today.weekday())  # Thứ Hai tuần hiện tại
        else:  # Nếu là thứ Hai (0) đến thứ Sáu (4)
            nearest_monday = today - timedelta(days=today.weekday() + 7)  # Thứ Hai tuần trước
        default_date_from = nearest_monday.strftime('%Y-%m-%d')
        default_date_to = (nearest_monday + timedelta(days=4)).strftime('%Y-%m-%d')  # Thứ Sáu gần nhất

        # Khởi tạo các biến lọc
        selected_groups = []
        date_from = default_date_from
        date_to = default_date_to
        data_source = 'user_conduct'
        select_all_groups = False

        # Xử lý yêu cầu POST hoặc GET
        if request.method == 'POST':
            select_all_groups = request.form.get('select_all_groups') == 'on'
            selected_groups = request.form.getlist('groups')
            date_from = request.form.get('date_from') or default_date_from
            date_to = request.form.get('date_to') or default_date_to
            data_source = request.form.get('data_source', 'user_conduct')
        else:
            select_all_groups = request.args.get('select_all_groups') == 'on'
            selected_groups = request.args.getlist('groups')
            date_from = request.args.get('date_from') or default_date_from
            date_to = request.args.get('date_to') or default_date_to
            data_source = request.args.get('data_source', 'user_conduct')

        # Kết nối database
        conn = connect_db()
        cursor = conn.cursor()

        # Xây dựng truy vấn SQL (loại bỏ user có role GVCN)
        queries = []
        params = []

        # Truy vấn cho User_Conduct
        if data_source in ['user_conduct', 'all']:
            if gvcn_role_id is not None:
                query_uc = """
                        SELECT g.name AS group_name, SUM(uc.total_points) AS total_points
                        FROM User_Conduct uc
                        JOIN Users u ON uc.user_id = u.id
                        JOIN Groups g ON u.group_id = g.id
                        WHERE uc.is_deleted = 0 AND u.role_id != ?
                    """
                params_uc = [gvcn_role_id]
            else:
                query_uc = """
                        SELECT g.name AS group_name, SUM(uc.total_points) AS total_points
                        FROM User_Conduct uc
                        JOIN Users u ON uc.user_id = u.id
                        JOIN Groups g ON u.group_id = g.id
                        WHERE uc.is_deleted = 0
                    """
                params_uc = []
            if select_all_groups:
                all_group_ids = [group[0] for group in groups]
                if all_group_ids:
                    query_uc += " AND u.group_id IN ({})".format(','.join('?' * len(all_group_ids)))
                    params_uc.extend(all_group_ids)
            elif selected_groups:
                query_uc += " AND u.group_id IN ({})".format(','.join('?' * len(selected_groups)))
                params_uc.extend(selected_groups)
            if date_from:
                query_uc += " AND uc.registered_date >= ?"
                params_uc.append(date_from)
            if date_to:
                query_uc += " AND uc.registered_date <= ?"
                params_uc.append(date_to)
            query_uc += " GROUP BY g.id, g.name"
            queries.append((query_uc, params_uc))

        # Truy vấn cho User_Subjects
        if data_source in ['user_subjects', 'all']:
            if gvcn_role_id is not None:
                query_us = """
                        SELECT g.name AS group_name, SUM(us.total_points) AS total_points
                        FROM User_Subjects us
                        JOIN Users u ON us.user_id = u.id
                        JOIN Groups g ON u.group_id = g.id
                        WHERE us.is_deleted = 0 AND u.role_id != ?
                    """
                params_us = [gvcn_role_id]
            else:
                query_us = """
                        SELECT g.name AS group_name, SUM(us.total_points) AS total_points
                        FROM User_Subjects us
                        JOIN Users u ON us.user_id = u.id
                        JOIN Groups g ON u.group_id = g.id
                        WHERE us.is_deleted = 0
                    """
                params_us = []
            if select_all_groups:
                all_group_ids = [group[0] for group in groups]
                if all_group_ids:
                    query_us += " AND u.group_id IN ({})".format(','.join('?' * len(all_group_ids)))
                    params_us.extend(all_group_ids)
            elif selected_groups:
                query_us += " AND u.group_id IN ({})".format(','.join('?' * len(selected_groups)))
                params_us.extend(selected_groups)
            if date_from:
                query_us += " AND us.registered_date >= ?"
                params_us.append(date_from)
            if date_to:
                query_us += " AND us.registered_date <= ?"
                params_us.append(date_to)
            query_us += " GROUP BY g.id, g.name"
            queries.append((query_us, params_us))

        # Thực thi truy vấn và tổng hợp kết quả
        records = {}
        for query, params in queries:
            cursor.execute(query, params)
            results = cursor.fetchall()
            for group_name, total_points in results:
                if group_name in records:
                    records[group_name] += total_points if total_points else 0
                else:
                    records[group_name] = total_points if total_points else 0

        # Chuyển dict thành list để hiển thị và sắp xếp
        records_list = [(group_name, total_points) for group_name, total_points in records.items()]
        records_list.sort(key=lambda x: x[0 if sort_column == 'group_name' else 1], reverse=(sort_direction == 'DESC'))

        conn.close()

        return render_template('group_summary.html',
                               records=records_list,
                               groups=groups,
                               date_from=date_from,
                               date_to=date_to,
                               selected_groups=selected_groups,
                               select_all_groups=select_all_groups,
                               data_source=data_source,
                               sort_by=sort_by,
                               sort_order=sort_order,
                               is_gvcn=is_user_gvcn())
    else:
        return redirect(url_for('auth.login'))

@summary_bp.route('/user_summary', methods=['GET', 'POST'])
def user_summary():
    if 'user_id' in session:
        sort_by = request.args.get('sort_by', 'user_name')
        sort_order = request.args.get('sort_order', 'asc')

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
        all_users = cursor.fetchall()
        if teacher_group_id is not None:
            cursor.execute("SELECT id, name FROM Groups WHERE is_deleted = 0 AND id != ?", (teacher_group_id,))
        else:
            cursor.execute("SELECT id, name FROM Groups WHERE is_deleted = 0")
        groups = cursor.fetchall()
        conn.close()

        # Tính toán ngày mặc định: Thứ 2~6 gần ngày hệ thống nhất
        today = datetime.today()
        if today.weekday() >= 5:  # Nếu là thứ Bảy (5) hoặc Chủ Nhật (6)
            nearest_monday = today - timedelta(days=today.weekday())  # Thứ Hai tuần hiện tại
        else:  # Nếu là thứ Hai (0) đến thứ Sáu (4)
            nearest_monday = today - timedelta(days=today.weekday() + 7)  # Thứ Hai tuần trước
        default_date_from = nearest_monday.strftime('%Y-%m-%d')
        default_date_to = (nearest_monday + timedelta(days=4)).strftime('%Y-%m-%d')  # Thứ Sáu gần nhất

        selected_users = []
        selected_groups = []
        date_from = default_date_from
        date_to = default_date_to
        select_all_users = False
        select_all_groups = False

        if request.method == 'POST':
            select_all_users = request.form.get('select_all_users') == 'on'
            selected_users = request.form.getlist('users')
            select_all_groups = request.form.get('select_all_groups') == 'on'
            selected_groups = request.form.getlist('groups')
            date_from = request.form.get('date_from') or default_date_from
            date_to = request.form.get('date_to') or default_date_to
        else:
            select_all_users = request.args.get('select_all_users') == 'on'
            selected_users = request.args.getlist('users')
            select_all_groups = request.args.get('select_all_groups') == 'on'
            selected_groups = request.args.getlist('groups')
            date_from = request.args.get('date_from') or default_date_from
            date_to = request.args.get('date_to') or default_date_to

        conn = connect_db()
        cursor = conn.cursor()

        if gvcn_role_id is not None:
            user_query = """
                    SELECT id, name
                    FROM Users
                    WHERE is_deleted = 0 AND role_id != ?
                """
            user_params = [gvcn_role_id]
        else:
            user_query = """
                    SELECT id, name
                    FROM Users
                    WHERE is_deleted = 0
                """
            user_params = []

        if select_all_users:
            all_user_ids = [user[0] for user in all_users]
            if all_user_ids:
                user_query += " AND id IN ({})".format(','.join('?' * len(all_user_ids)))
                user_params.extend(all_user_ids)
        elif selected_users:
            user_query += " AND id IN ({})".format(','.join('?' * len(selected_users)))
            user_params.extend(selected_users)
        if select_all_groups:
            all_group_ids = [group[0] for group in groups]
            if all_group_ids:
                user_query += " AND group_id IN ({})".format(','.join('?' * len(all_group_ids)))
                user_params.extend(all_group_ids)
        elif selected_groups:
            user_query += " AND group_id IN ({})".format(','.join('?' * len(selected_groups)))
            user_params.extend(selected_groups)

        cursor.execute(user_query, user_params)
        filtered_users = cursor.fetchall()

        records = []
        for user_id, user_name in filtered_users:
            total_points = 0
            has_data = False

            uc_query = """
                    SELECT SUM(total_points)
                    FROM User_Conduct
                    WHERE user_id = ? AND is_deleted = 0
                """
            uc_params = [user_id]
            if date_from:
                uc_query += " AND registered_date >= ?"
                uc_params.append(date_from)
            if date_to:
                uc_query += " AND registered_date <= ?"
                uc_params.append(date_to)
            cursor.execute(uc_query, uc_params)
            uc_points = cursor.fetchone()[0]
            if uc_points:
                total_points += uc_points
                has_data = True

            us_query = """
                    SELECT SUM(total_points)
                    FROM User_Subjects
                    WHERE user_id = ? AND is_deleted = 0
                """
            us_params = [user_id]
            if date_from:
                us_query += " AND registered_date >= ?"
                us_params.append(date_from)
            if date_to:
                us_query += " AND registered_date <= ?"
                us_params.append(date_to)
            cursor.execute(us_query, us_params)
            us_points = cursor.fetchone()[0]
            if us_points:
                total_points += us_points
                has_data = True

            records.append((user_name, total_points if total_points else 0, has_data, user_id))

        if sort_by == 'user_name':
            records.sort(key=lambda x: x[0], reverse=(sort_order == 'desc'))
        elif sort_by == 'total_points':
            records.sort(key=lambda x: x[1], reverse=(sort_order == 'desc'))
        elif sort_by == 'in':
            records.sort(key=lambda x: x[2], reverse=(sort_order == 'desc'))

        conn.close()

        return render_template('user_summary.html',
                               records=records,
                               all_users=all_users,
                               groups=groups,
                               date_from=date_from,
                               date_to=date_to,
                               selected_users=selected_users,
                               selected_groups=selected_groups,
                               select_all_users=select_all_users,
                               select_all_groups=select_all_groups,
                               sort_by=sort_by,
                               sort_order=sort_order,
                               is_gvcn=is_user_gvcn())
    else:
        return redirect(url_for('auth.login'))


def generate_pdf_for_user(user_data, date_from, date_to, y_start, canvas_obj, page_height):
    """Helper function to generate content for a single user on half an A4 page."""
    pdfmetrics.registerFont(TTFont('Arial', 'ARIAL.TTF'))  # Đăng ký font hỗ trợ tiếng Việt

    # Kích thước trang A4: 595 điểm chiều rộng, mỗi nửa A5 cao 421 điểm
    page_width = 595  # Chiều rộng A4

    # Tiêu đề "Báo Cáo Rèn Luyện Học Sinh" căn giữa, font lớn hơn
    canvas_obj.setFont("Arial", 16)  # Font lớn hơn (16)
    canvas_obj.drawCentredString(page_width / 2, y_start + 360, "Báo Cáo Rèn Luyện Học Sinh")

    # Khoảng thời gian căn giữa, font nhỏ hơn
    canvas_obj.setFont("Arial", 10)  # Font nhỏ hơn (10)
    canvas_obj.drawCentredString(page_width / 2, y_start + 345, f"{date_from or ' - '} đến {date_to or ' - '}")

    # Tên học sinh căn trái
    canvas_obj.setFont("Arial", 12)  # Font tiêu đề phụ
    canvas_obj.drawString(50, y_start + 330, f"{user_data['name']}")

    # Dòng tiêu đề bảng
    y = y_start + 300  # Giảm y xuống để nhường chỗ cho tiêu đề
    canvas_obj.setFont("Arial", 11)
    canvas_obj.drawString(50, y, "Ngày")
    canvas_obj.drawString(120, y, "Môn Học")
    canvas_obj.drawString(220, y, "Học Tập")
    canvas_obj.drawString(390, y, "Hạnh Kiểm")
    canvas_obj.drawRightString(550, y, "Điểm Ngày")  # Căn phải tiêu đề "Điểm Ngày" sát mép phải
    canvas_obj.setLineWidth(0.5)  # Giảm độ dày của đường kẻ xuống 0.5 (mảnh hơn)
    canvas_obj.line(50, y - 5, 550, y - 5)  # Đường kẻ ngang dưới tiêu đề

    # Dữ liệu
    y -= 10  # Khoảng cách từ tiêu đề bảng đến dòng dữ liệu đầu tiên
    canvas_obj.setFont("Arial", 10)
    total_points_sum = 0

    # Gom nhóm theo registered_date
    for date, entries in sorted(user_data['details'].items()):  # Sắp xếp theo ngày
        y -= 10
        canvas_obj.drawString(50, y, str(date) if date else "")
        first_line = True
        for entry in entries:
            if not first_line:
                y -= 10  # Khoảng cách giữa các row
                canvas_obj.drawString(50, y, "")  # Để trống cột date cho các dòng tiếp theo
            canvas_obj.drawString(120, y, entry.get('subject_name', ''))
            canvas_obj.drawString(220, y, entry.get('criteria_name', ''))
            canvas_obj.drawString(390, y, entry.get('conduct_name', ''))
            points = entry.get('total_points', 0)
            canvas_obj.drawRightString(550, y, str(points))  # Căn phải sát mép phải của cột "Điểm Ngày"
            canvas_obj.setLineWidth(0.05)  # Giảm độ dày của đường kẻ xuống 0.5 (mảnh hơn)
            canvas_obj.line(50, y - 5, 550, y - 5)  # Đường kẻ ngang ngăn cách các row
            total_points_sum += points
            first_line = False
            y -= 10  # Giảm khoảng cách giữa các row
            if y < y_start + 50:  # Nếu hết chỗ trong nửa trang A5, dừng lại
                break

    # Tổng điểm
    y -= 12
    canvas_obj.setFont("Arial", 12)
    canvas_obj.drawString(50, y, f"Tổng Điểm: {total_points_sum}")

def generate_combined_pdf(users_data_list, date_from, date_to):
    """Generates a PDF with two users per A4 page."""
    buffer = BytesIO()
    p = canvas.Canvas(buffer, pagesize=A4)  # Kích thước A4: 595 x 842 điểm
    a4_height = 842
    a5_height = a4_height / 2  # Một nửa chiều cao A4 = A5 dọc

    for i in range(0, len(users_data_list), 2):
        # Học sinh đầu tiên (nửa trên của A4)
        user1_data = users_data_list[i]
        generate_pdf_for_user(user1_data, date_from, date_to, a5_height, p, a5_height)

        # Học sinh thứ hai (nửa dưới của A4), nếu có
        if i + 1 < len(users_data_list):
            user2_data = users_data_list[i + 1]
            generate_pdf_for_user(user2_data, date_from, date_to, 0, p, a5_height)

        p.showPage()  # Kết thúc trang A4 hiện tại

    p.save()
    buffer.seek(0)
    return buffer


@summary_bp.route('/print_users', methods=['POST'])
def print_users():
    """Generates and downloads PDFs for selected users with detailed data, 2 per A4 page."""
    selected_users = request.form.get('selected_users', '').split(',')
    date_from = request.form.get('date_from')
    date_to = request.form.get('date_to')

    if not selected_users or selected_users == ['']:
        return "No users selected for printing.", 400

    conn = connect_db()
    cursor = conn.cursor()

    users_data_list = []
    for user_id in selected_users:
        # Lấy thông tin user
        cursor.execute("SELECT name FROM Users WHERE id = ? AND is_deleted = 0", (user_id,))
        user_info = cursor.fetchone()
        if not user_info:
            continue

        user_data = {'name': user_info[0], 'details': {}}

        # Truy vấn User_Subjects
        us_query = """
            SELECT us.registered_date, s.name AS subject_name, c.name AS criteria_name, us.total_points
            FROM User_Subjects us
            LEFT JOIN Subjects s ON us.subject_id = s.id
            LEFT JOIN Criteria c ON us.criteria_id = c.id
            WHERE us.user_id = ? AND us.is_deleted = 0
        """
        us_params = [user_id]
        if date_from:
            us_query += " AND us.registered_date >= ?"
            us_params.append(date_from)
        if date_to:
            us_query += " AND us.registered_date <= ?"
            us_params.append(date_to)
        cursor.execute(us_query, us_params)
        us_results = cursor.fetchall()

        # Truy vấn User_Conduct
        uc_query = """
            SELECT uc.registered_date, con.name AS conduct_name, uc.total_points
            FROM User_Conduct uc
            LEFT JOIN Conduct con ON uc.conduct_id = con.id
            WHERE uc.user_id = ? AND uc.is_deleted = 0
        """
        uc_params = [user_id]
        if date_from:
            uc_query += " AND uc.registered_date >= ?"
            uc_params.append(date_from)
        if date_to:
            uc_query += " AND uc.registered_date <= ?"
            uc_params.append(date_to)  # Sửa từ us_params thành uc_params
        cursor.execute(uc_query, uc_params)
        uc_results = cursor.fetchall()

        # Gom nhóm dữ liệu theo registered_date
        for row in us_results:
            reg_date = row[0]
            subject_name = row[1] if row[1] else ''
            criteria_name = row[2] if row[2] else ''
            total_points = row[3] if row[3] is not None else 0

            if reg_date not in user_data['details']:
                user_data['details'][reg_date] = []
            user_data['details'][reg_date].append({
                'subject_name': subject_name,
                'criteria_name': criteria_name,
                'conduct_name': '',
                'total_points': total_points
            })

        for row in uc_results:
            reg_date = row[0]
            conduct_name = row[1] if row[1] else ''
            total_points = row[2] if row[2] is not None else 0

            if reg_date not in user_data['details']:
                user_data['details'][reg_date] = []
            user_data['details'][reg_date].append({
                'subject_name': '',
                'criteria_name': '',
                'conduct_name': conduct_name,
                'total_points': total_points
            })

        users_data_list.append(user_data)

    conn.close()

    # Tạo PDF kết hợp
    pdf_buffer = generate_combined_pdf(users_data_list, date_from, date_to)

    # Trả về file PDF
    response = make_response(pdf_buffer.getvalue())
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = 'attachment; filename=user_reports.pdf'
    return response