from collections import defaultdict
from flask import Flask, render_template, request, redirect, url_for, flash, send_file, jsonify
from flask_wtf import FlaskForm
from sqlalchemy import and_
from wtforms import FileField, SelectField, SubmitField, StringField, DateField, FloatField, IntegerField, TextAreaField
from wtforms.validators import DataRequired
from werkzeug.utils import secure_filename
import os
import json
from datetime import datetime

from config import Config
from database import db
from models import Participant, Category, Competition, Score
from utils.excel_handler import import_participants_from_excel, export_results_to_excel
from utils.draw_generator import categorize_athletes, generate_draw
from utils.pdf_reporter import generate_results_pdf

from loguru import logger

app = Flask(__name__)
app.config.from_object(Config)
db.init_app(app)

# Флаг инициализации

app_initialized = False
FORMAT_LOG: str = "{time:YYYY-MM-DD at HH:mm:ss} | {level} | {message}"
LOG_ROTATION: str = "10 MB"
log_file_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "log.txt")
logger.add(log_file_path, format=FORMAT_LOG, level="INFO", rotation=LOG_ROTATION)

@app.before_request
def initialize_on_first_request():
    """Инициализация при первом запросе"""
    global app_initialized
    
    if not app_initialized:
        # Создание таблиц в базе данных
        with app.app_context():
            db.create_all()
            
            # Создание папки для загрузок
            uploads_dir = app.config['UPLOAD_FOLDER']
            os.makedirs(uploads_dir, exist_ok=True)
            print(f"✅ Приложение инициализировано: создана папка {uploads_dir}")
        
        app_initialized = True

# Формы
class CompetitionForm(FlaskForm):
    name = StringField('Название соревнования', validators=[DataRequired()])
    location = StringField('Место проведения')
    description = TextAreaField('Описание')
    start_date  = DateField('Дата начала', validators=[DataRequired()])
    end_date   = DateField('Дата окончания', validators=[DataRequired()])
    submit = SubmitField('Создать')

class UploadForm(FlaskForm):
    excel_file = FileField('Excel файл', validators=[DataRequired()])
    submit = SubmitField('Загрузить')

class CategoryForm(FlaskForm):
    name = StringField('Название категории', validators=[DataRequired()])
    min_age = IntegerField('Минимальный возраст')
    max_age = IntegerField('Максимальный возраст')
    gender = SelectField('Пол', choices=[('mixed', 'Смешанный'), ('male', 'Мужской'), ('female', 'Женский')])
    submit = SubmitField('Создать категорию')


# Вспомогательные функции
def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

# Маршруты
@app.route('/')
def index():
    competitions = Competition.query.all()
    athletes_count = Participant.query.count()
    active_competitions = Competition.query.filter_by(status='active').count()
    
    return render_template('index.html', 
                         competitions=competitions,
                         athletes_count=athletes_count,
                         active_competitions=active_competitions)



@app.route('/create_competition', methods=['GET', 'POST'])
def create_competition():
    form = CompetitionForm()
    if form.validate_on_submit():
        competition = Competition(
            name=form.name.data,
            start_date=form.start_date.data,
            end_date=form.end_date.data,
            location=form.location.data,
                description=form.description.data,
            status='pending'
        )
        db.session.add(competition)
        db.session.commit()
        
        flash('Соревнование создано')
        return redirect(url_for('view_competition', id=competition.id))
    
    return render_template('create_competition.html', form=form)

@app.route('/competition/<int:id>')
def view_competition(id):
    competition = Competition.query.get_or_404(id)
    # draw = json.loads(competition.draw_data) if competition.draw_data else {}
    
    # Получение результатов
    # scores = Score.query.filter_by(competition_id=id).all()
    # scores = Score.query.all()
    participants_count = Participant.query.filter_by(competition_id=id).count()
    categories_count = Category.query.filter_by(competition_id=id).count()
    return render_template('competition.html', 
                         competition=competition, 
                         participants_count=participants_count,
                         categories_count=categories_count,
                        #  draw=draw,
                        #  scores=scores
                        )

@app.route('/competition/<int:id>/upload/', methods=['GET', 'POST'])
def upload_participants(id):
    form = UploadForm()
    if form.validate_on_submit():
        if 'excel_file' not in request.files:
            flash('Файл не выбран')
            return redirect(request.url)
        
        file = request.files['excel_file']
        if file.filename == '':
            flash('Файл не выбран')
            return redirect(request.url)
        
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)
            
            try:
                participants = import_participants_from_excel(filepath, id)
                for participant in participants:
                    db.session.add(participant)
                db.session.commit()
                flash(f'Успешно загружено {len(participants)} спортсменов')
                return redirect(url_for('manage_categories', id =id))
            except Exception as e:
                flash(f'Ошибка: {str(e)}')
    
    return render_template('upload.html', form=form)

@app.route('/competition/<int:id>/categories/', methods=['GET', 'POST'])
def manage_categories(id):
    competition = Competition.query.get_or_404(id)
    form = CategoryForm()
    if form.validate_on_submit():
        logger.error(form.gender.data)
        category = Category(
            name=form.name.data,
            competition_id = id,
            min_age=form.min_age.data,
            max_age=form.max_age.data,
            gender="м" if form.gender.data == "male" else "ж"
        )
        db.session.add(category)
        participants = Participant.query.filter(and_(Participant.age>=category.min_age,
                                                     Participant.age<=category.max_age,
                                                     Participant.gender==category.gender)).all()
        for participant in participants:
            participant.set_category(category.id)
        db.session.commit()
        flash('Категория создана')
        return redirect(url_for('manage_categories', id=id))
    
    categories = Category.query.all()
    participants = Participant.query.all()
    
    # Автоматическое распределение
    categorized = categorize_athletes(participants, categories)
    
    return render_template('categories.html', 
                         form=form, 
                         competition=competition,
                         categories=categories, 
                         participants=participants,
                         categorized=categorized)

@app.route('/competition/<int:id>/categories_view/')
def view_competition_categories(id):
    """Просмотр категорий соревнования с участниками и результатами"""
    # db = get_db()
    # cursor = db.cursor()
    
    # Получаем соревнование
    competition = Competition.query.get_or_404(id)
    
    # Получаем распределение по категориям
    participants = db.session.query(Participant, Category).join(Category, Category.id == Participant.category_id
                                                                      ).filter(and_(Participant.competition_id==id,Participant.category_id!=None)).all()
    
    participants_categories={}
    for participant, category in participants:
        if participants_categories.get(category.id) ==0:
            participants_categories["category.id"] = {'participant':participant,
                                                      ''}
    # for row in participants:
    #     athletes_by_category[row['category_name']].append(dict(row))
    
    # # Получаем сетку (draw_data) если есть
    # draw_data = None
    # if competition['draw_data']:
    #     try:
    #         draw_data = json.loads(competition['draw_data'])
    #     except json.JSONDecodeError:
    #         draw_data = {}
    
    # Получаем оценки для каждого участника    
    scores_data = Score.query.all()
    
    # # Группируем оценки по участникам
    # athlete_scores = defaultdict(lambda: {1: None, 2: None, 3: None, 'total': 0, 'average': 0})
    # for score in scores_data:
    #     athlete_id = score['athlete_id']
    #     round_num = score['round_number']
    #     athlete_scores[athlete_id][round_num] = score['average']
    
    # # Рассчитываем итоговые баллы (2 лучших раунда из 3)
    # for athlete_id, scores in athlete_scores.items():
    #     round_scores = [scores[1], scores[2], scores[3]]
    #     valid_scores = [s for s in round_scores if s is not None]
        
    #     if len(valid_scores) >= 2:
    #         valid_scores.sort(reverse=True)
    #         total = sum(valid_scores[:2])
    #         average = total / 2
    #     elif valid_scores:
    #         total = valid_scores[0]
    #         average = valid_scores[0]
    #     else:
    #         total = 0
    #         average = 0
        
    #     scores['total'] = total
    #     scores['average'] = average
    
    return render_template('competition_categories.html',
                         competition=competition,
                         participants=participants
                        #  athletes_by_category=athletes_by_category,
                        #  draw_data=draw_data,
                        #  athlete_scores=athlete_scores
                         )

@app.route('/enter_scores', methods=['POST'])
def enter_scores():
    data = request.json
    athlete_id = data['athlete_id']
    competition_id = data['competition_id']
    round_number = data['round_number']
    scores = data['scores']
    
    # Поиск существующей записи
    score = Score.query.filter_by(
        athlete_id=athlete_id,
        competition_id=competition_id,
        round_number=round_number
    ).first()
    
    if not score:
        score = Score(
            athlete_id=athlete_id,
            competition_id=competition_id,
            round_number=round_number
        )
    
    # Установка оценок
    score.judge1 = scores[0]
    score.judge2 = scores[1]
    score.judge3 = scores[2]
    score.judge4 = scores[3]
    score.judge5 = scores[4]
    score.calculate_scores()
    
    db.session.add(score)
    db.session.commit()
    
    return jsonify({'success': True, 'average': score.average})

@app.route('/results/<int:competition_id>')
def show_results(competition_id):
    competition = Competition.query.get_or_404(competition_id)
    
    # Расчет результатов
    results = calculate_final_results(competition_id)
    
    return render_template('results.html', 
                         competition=competition,
                         results=results)

def calculate_final_results(competition_id):
    """Расчет финальных результатов"""
    athletes = Participant.query.all()
    results = []
    
    for athlete in athletes:
        scores = Score.query.filter_by(
            competition_id=competition_id,
            athlete_id=athlete.id
        ).order_by(Score.round_number).all()
        
        if scores:
            round1 = scores[0].average if len(scores) > 0 else None
            round2 = scores[1].average if len(scores) > 1 else None
            round3 = scores[2].average if len(scores) > 2 else None
            
            # Сумма лучших двух раундов
            valid_scores = [s for s in [round1, round2, round3] if s is not None]
            if len(valid_scores) >= 2:
                valid_scores.sort(reverse=True)
                total = sum(valid_scores[:2])
                average = total / 2
            else:
                total = sum(valid_scores) if valid_scores else 0
                average = total / len(valid_scores) if valid_scores else 0
            
            results.append({
                'athlete_id': athlete.id,
                'first_name': athlete.first_name,
                'last_name': athlete.last_name,
                'club': athlete.club,
                'category': athlete.category.name if athlete.category else 'Без категории',
                'round1': round1,
                'round2': round2,
                'round3': round3,
                'total': total,
                'average': average
            })
    
    # Сортировка по среднему баллу
    results.sort(key=lambda x: x['average'], reverse=True)
    
    # Присвоение мест
    for i, result in enumerate(results):
        result['place'] = i + 1
    
    return results

@app.route('/export/excel/<int:competition_id>')
def export_excel(competition_id):
    results = calculate_final_results(competition_id)
    competition = Competition.query.get(competition_id)
    
    filename = f"results_{competition.name.replace(' ', '_')}.xlsx"
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    
    export_results_to_excel(results, filepath)
    
    return send_file(filepath, as_attachment=True)

@app.route('/export/pdf/<int:competition_id>')
def export_pdf(competition_id):
    results = calculate_final_results(competition_id)
    competition = Competition.query.get(competition_id)
    
    filename = f"protocol_{competition.name.replace(' ', '_')}.pdf"
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    
    competition_info = {
        'name': competition.name,
        'date': competition.date.strftime('%d.%m.%Y'),
        'location': competition.location
    }
    
    generate_results_pdf(results, competition_info, filepath)
    
    return send_file(filepath, as_attachment=True)

if __name__ == '__main__':
    app.run(debug=True)