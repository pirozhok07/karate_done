from datetime import datetime
from database import db


class Competition(db.Model):
    __tablename__ = 'competitions'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)  # Добавлено поле описания
    start_date = db.Column(db.DateTime)
    end_date = db.Column(db.DateTime)
    location = db.Column(db.String(200))
    status = db.Column(db.String(20), default='pending')  # pending, active, completed

    categories = db.relationship('Category', backref='competition', lazy=True, cascade='all, delete-orphan')

class Category(db.Model):
    __tablename__ = 'categories'

    id = db.Column(db.Integer, primary_key=True)
    competition_id = db.Column(db.Integer, db.ForeignKey('competitions.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    min_age = db.Column(db.Integer)
    max_age = db.Column(db.Integer)
    gender = db.Column(db.String(10))
    
    participants  = db.relationship('Participant', backref='category', lazy=True)

class Participant(db.Model):
    __tablename__ = 'participants'

    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(50), nullable=False)
    second_name = db.Column(db.String(50), nullable=True)
    last_name = db.Column(db.String(50), nullable=False)
    birth_date = db.Column(db.Date)
    age = db.Column(db.Integer)
    gender = db.Column(db.String(10))
    club = db.Column(db.String(100))
    registration_number = db.Column(db.String(50), unique=True)
    competition_id = db.Column(db.Integer, db.ForeignKey('competitions.id'))
    category_id = db.Column(db.Integer, db.ForeignKey('categories.id'))
    is_active = db.Column(db.Boolean, default=True)
    
    scores = db.relationship('Score', backref='participant', lazy=True)

    def set_age(self):
        today = datetime.now()
        age = today.year - self.birth_date.year
        if today.month < self.birth_date.month:
            age -= 1
        elif today.month == self.birth_date.month and today.day < self.birth_date.day:
            age -= 1
        self.age = age

    def set_category(self, id):
        self.category_id=id

class Score(db.Model):
    __tablename__ = 'scores'

    id = db.Column(db.Integer, primary_key=True)
    participant_id  = db.Column(db.Integer, db.ForeignKey('participants.id'), nullable=False)
    round_number = db.Column(db.Integer, nullable=False)
    judge1 = db.Column(db.Float)
    judge2 = db.Column(db.Float)
    judge3 = db.Column(db.Float)
    judge4 = db.Column(db.Float)
    referee = db.Column(db.Float)
    total = db.Column(db.Float)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def calculate_scores(self):
        scores = [self.judge1, self.judge2, self.judge3, self.judge4, self.referee]
        valid_scores = [s for s in scores if s is not None]
        if valid_scores:
            valid_scores.sort()
            valid_scores = valid_scores[1:-1]  # Убираем мин и макс
            self.total = sum(valid_scores)