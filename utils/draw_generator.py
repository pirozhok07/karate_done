import random
from datetime import datetime
from models import Participant, Category

def categorize_athletes(athletes, categories):
    """Распределение спортсменов по категориям"""
    categorized = {}
    
    for athlete in athletes:
        assigned = False
        for category in categories:
            if matches_category(athlete, category):
                if category.name not in categorized:
                    categorized[category.name] = []
                categorized[category.name].append(athlete)
                athlete.category_id = category.id
                assigned = True
                break
        
        if not assigned:
            if 'Без категории' not in categorized:
                categorized['Без категории'] = []
            categorized['Без категории'].append(athlete)
    
    return categorized

def matches_category(athlete, category):
    """Проверка соответствия спортсмена категории"""
    # Проверка пола
    if category.gender and category.gender != athlete.gender:
        return False
    
    # Проверка возраста
    if athlete.birth_date:
        age = calculate_age(athlete.birth_date)
        if category.min_age and age < category.min_age:
            return False
        if category.max_age and age > category.max_age:
            return False
    
    # # Проверка веса
    # if athlete.weight:
    #     if category.min_weight and athlete.weight < category.min_weight:
    #         return False
    #     if category.max_weight and athlete.weight > category.max_weight:
    #         return False
    
    return True

def calculate_age(birth_date):
    """Расчет возраста"""
    today = datetime.today()
    return today.year - birth_date.year - (
        (today.month, today.day) < (birth_date.month, birth_date.day)
    )

def generate_draw(category_athletes):
    """Генерация сетки соревнований"""
    draw = {}
    
    for category_name, athletes in category_athletes.items():
        # Случайный порядок выступления
        random.shuffle(athletes)
        
        # Создание пар для первого раунда
        orders = []
        for i in range(0, len(athletes)):
            orders.append([athletes[i]])
   
        draw = {
            'category_name': category_name,
            'orders': orders
        }
    
    return draw