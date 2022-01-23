from flask import Flask, render_template, request, url_for, make_response, session, redirect, flash
from flask_login import login_required, current_user
from mysql_db import MySQL
import mysql.connector as connector
import math

app = Flask(__name__)
application = app

app.config.from_pyfile('config.py')

mysql = MySQL(app)

from auth import bp as auth_bp, init_login_manager, check_rights

init_login_manager(app)
app.register_blueprint(auth_bp)
PER_PAGE = 5


@app.route('/')
def index():
    return render_template('index.html')

@app.route('/reviews')
@check_rights('users_review')
@login_required
def users_review():
    user_id = getattr(current_user, 'id', None)
    cursor = mysql.connection.cursor(named_tuple=True)
    cursor.execute('SELECT t1.name, t2.rating, t2.review_text, t2.date_added, t3.status FROM exam_course t1 JOIN exam_reviews t2 ON t1.id=t2.course_id JOIN exam_reviews_status t3 ON t3.id=t2.status_id WHERE user_id=%s and t1.id=t2.course_id;', (user_id,))
    reviews = cursor.fetchall()
    cursor.close()
    return render_template('reviews/review_user.html', reviews=reviews)

@app.route('/reviews/moderator')
@check_rights('moder_review')
@login_required
def moder_review():
    page = request.args.get('page', 1, type=int)
    with mysql.connection.cursor(named_tuple=True) as cursor:
        cursor.execute('SELECT count(t1.id) AS count FROM exam_reviews t1 JOIN exam_reviews_status t2 ON t1.status_id=t2.id WHERE t2.status="на рассмотрении";')
        total_count = cursor.fetchone().count
    total_pages = math.ceil(total_count/PER_PAGE)
    pagination_info = {
        'current_page': page,
        'total_pages': total_pages,
        'per_page': PER_PAGE
    }
    query = ''' 
        SELECT t2.id, t1.name, t2.date_added, t4.last_name, t4.first_name 
        FROM exam_course t1 JOIN exam_reviews t2 ON t1.id=t2.course_id JOIN exam_reviews_status t3 ON t3.id=t2.status_id JOIN exam_users t4 ON t4.id=t2.user_id 
        WHERE t1.id=t2.course_id and (t2.status_id IN (SELECT t3.id WHERE t3.status="на рассмотрении")) ORDER BY t2.date_added DESC LIMIT %s OFFSET %s;
    '''
    cursor = mysql.connection.cursor(named_tuple=True)
    cursor.execute(query, (PER_PAGE, PER_PAGE*(page-1)))
    reviews = cursor.fetchall()
    cursor.close()
    return render_template('reviews/moderator/review_moder.html', reviews=reviews, pagination_info=pagination_info)

@app.route('/courses')
def courses():
    page = request.args.get('page', 1, type=int)
    with mysql.connection.cursor(named_tuple=True) as cursor:
        cursor.execute('SELECT count(*) AS count FROM exam_course;')
        total_count = cursor.fetchone().count
    total_pages = math.ceil(total_count/PER_PAGE)
    pagination_info = {
        'current_page': page,
        'total_pages': total_pages,
        'per_page': PER_PAGE
    }
    query = '''
        SELECT id, name, teacher, number FROM exam_course ORDER BY number DESC LIMIT %s OFFSET %s;
        '''
    cursor = mysql.connection.cursor(named_tuple=True)
    cursor.execute(query, (PER_PAGE, PER_PAGE*(page-1)))
    courses = cursor.fetchall()
    
    cursor.execute('SELECT COUNT(t1.id) AS ct, t2.id FROM exam_reviews t1 JOIN exam_course t2 ON t1.course_id=t2.id WHERE t1.status_id IN (SELECT id FROM exam_reviews_status WHERE status="Одобренно") GROUP BY t2.id;')
    reviews = cursor.fetchall()
    cursor.close()
    return render_template('courses/index.html', courses=courses, reviews=reviews, pagination_info=pagination_info)

@app.route('/courses/<int:course_id>')
@check_rights('show')
@login_required
def show(course_id):
    cursor = mysql.connection.cursor(named_tuple=True)
    cursor.execute('SELECT * FROM exam_course WHERE id = %s;', (course_id,))
    course = cursor.fetchone()
    cursor.execute('SELECT t1.review_text, t1.rating, t1.date_added, t2.last_name, t2.first_name FROM exam_reviews t1 JOIN exam_users t2 ON t1.user_id=t2.id WHERE ((course_id=%s) and t1.status_id IN (SELECT id FROM exam_reviews_status WHERE status="Одобренно"));', (course_id,))
    reviews = cursor.fetchall()
    cursor.close()
    return render_template('courses/show.html', course=course, reviews=reviews)


@app.route('/courses/comment/<int:course_id>', methods=['POST', 'GET'])
@check_rights('show')
@login_required
def comment(course_id):
    cursor = mysql.connection.cursor(named_tuple=True)
    user_id = getattr(current_user, 'id', None)
    if request.method == "GET":
        return render_template('courses/comments.html')
    if request.method == "POST":
        review_text = request.form.get('review_text')
        rating = (request.form.get('rating'))
        query = '''
                INSERT INTO exam_reviews (course_id, user_id, rating, review_text)
                VALUES (%s,%s,%s,%s);
                    '''    
        cursor.execute(query, (course_id, user_id, rating, review_text))        
        mysql.connection.commit()
        cursor.close()
        flash(f'Ваш отзыв был успешно добавлен.', 'success')
    return redirect(url_for('courses'))


@app.route('/courses/<int:course_id>/delete', methods=['POST'])
@check_rights('delete')
@login_required
def delete(course_id):
    with mysql.connection.cursor(named_tuple=True) as cursor:
        try:
            cursor.execute('DELETE FROM exam_course WHERE id = %s;', (course_id,))
        except connector.errors.DatabaseError:
            flash('Не удалось удалить запись.', 'danger')
            return redirect(url_for('courses'))
        mysql.connection.commit()
        flash('Курс был успешно удален.', 'success')
    return redirect(url_for('courses'))

@app.route('/courses/<int:course_id>/edit')
@check_rights('edit')
@login_required
def edit(course_id):
    cursor = mysql.connection.cursor(named_tuple=True)
    cursor.execute('SELECT * FROM exam_course WHERE id = %s;', (course_id,))
    course = cursor.fetchone()
    cursor.close()
    return render_template('courses/edit.html', course=course)

@app.route('/courses/<int:course_id>/update', methods=['POST'])
@check_rights('edit')
@login_required
def update(course_id):
    name = request.form.get('name') or None
    description = request.form.get('description') or None
    number = request.form.get('number') or None
    duration = request.form.get('duration') or None
    teacher = request.form.get('teacher') or None
    link = request.form.get('link') or None
    query = '''
        UPDATE exam_course SET name=%s, description=%s, number=%s, duration=%s, teacher=%s, link=%s
        WHERE id=%s;
    '''
    cursor = mysql.connection.cursor(named_tuple=True)
    try:
        cursor.execute(query, (name, description, number, duration, teacher, link, course_id))
    except connector.errors.DatabaseError:
        flash('Введены некорректные данные, ошибка сохранения', 'danger')
        course = {
            'id': course_id,
            'name': name,
            'description': description, 
            'number': number,
            'duration': duration,
            'teacher': teacher,
            'link': link,
        }
        flash('Введены некорректные данные, ошибка сохранения', 'danger')
        return render_template('course/edit.html', course=course)
    mysql.connection.commit()
    cursor.close()
    flash(f'Курс {name} был успешно обновлён.', 'success')
    return redirect(url_for('courses'))


@app.route('/courses/new')
@check_rights('new')
@login_required
def new():
    return render_template('courses/new.html', course={})

@app.route('/courses/create', methods=['POST'])
@check_rights('new')
@login_required
def create():
    name = request.form.get('name') or None
    description = request.form.get('description') or None
    number = request.form.get('number') or None
    duration = request.form.get('duration') or None
    teacher = request.form.get('teacher') or None
    link = request.form.get('link') or None
    # link = request.form.get('link') or None
    # actors = None
    # duration = request.form.get('duration') or None
    # genre_id = int(request.form.get('genre_id')) or None
    query = '''
        INSERT INTO exam_course (name, description, number, duration, teacher, link)
        VALUES (%s, %s, %s, %s, %s, %s);
    '''
    cursor = mysql.connection.cursor(named_tuple=True)
    try:
        cursor.execute(query, (name, description, number, duration, teacher, link))
    except connector.errors.DatabaseError:
        flash('Введены некорректные данные, ошибка сохранения', 'danger')
        course = {
            'name': name,
            'description': description,
            'duration': duration,
            'teacher': teacher,
            'link': link,
            # 'actors': actors,
            # 'duration': duration
        }
        return render_template('courses/new.html', course=course)
    cursor = mysql.connection.cursor(named_tuple=True)
    mysql.connection.commit()
    cursor.close()
    flash(f'Курс {name} был успешно добавлен.', 'success')
    return redirect(url_for('courses'))



@app.route('/reviews/moderator/<int:review_id>')
@check_rights('moder_review')
@login_required
def show_review(review_id):
    query = ''' 
        SELECT t2.id, t1.name, t2.date_added, t2.rating, t2.review_text, t4.last_name, t4.first_name 
        FROM exam_course t1 JOIN exam_reviews t2 ON t1.id=t2.course_id JOIN exam_reviews_status t3 ON t3.id=t2.status_id JOIN exam_users t4 ON t4.id=t2.user_id 
        WHERE t2.id=%s;
    '''
    cursor = mysql.connection.cursor(named_tuple=True)
    cursor.execute(query, (review_id,)) 
    reviews = cursor.fetchall()
    cursor.close()
    return render_template('reviews/moderator/show_review.html', reviews=reviews)

@app.route('/reviews/moderator/<int:review_id>/approve', methods=['POST', 'GET'])
@check_rights('moder_review')
@login_required
def approve(review_id):
    cursor = mysql.connection.cursor(named_tuple=True)
    if request.method == "POST":
        status = (request.form.get('status'))
        query = '''
            UPDATE exam_reviews SET status_id=%s
            WHERE id=%s;
        '''
        try:
            cursor.execute(query, (status, review_id ))
            mysql.connection.commit()
            cursor.close()
            flash(f'Статус рецензии был успешо изменен', 'success')
            return redirect(url_for('moder_review'))
        except connector.errors.DatabaseError:
            flash('Введены некорректные данные, ошибка сохранения', 'danger')
    return redirect(url_for('moder_review'))                