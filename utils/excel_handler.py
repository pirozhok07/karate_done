import pandas as pd
from datetime import datetime
from models import Participant

def import_participants_from_excel(file_path, id):
    """Импорт спортсменов из Excel файла"""
    try:
        df = pd.read_excel(file_path)
        
        participants = []
        for _, row in df.iterrows():
            participant = Participant(
                last_name=str(row.get('Фамилия', '')),
                first_name=str(row.get('Имя', '')),
                second_name=str(row.get('Отчество', '')),
                birth_date = parse_date(row.get('Дата рождения')),
                gender=str(row.get('Пол', '')),
                # weight=float(row.get('Вес', 0)) if pd.notna(row.get('Вес')) else None,
                # height=float(row.get('Рост', 0)) if pd.notna(row.get('Рост')) else None,
                club=str(row.get('Клуб', '')),
                registration_number=str(row.get('Номер', '')),
                competition_id = id
            )
            participant.set_age()
            participants.append(participant)
        
        return participants
    except Exception as e:
        raise Exception(f"Ошибка при чтении Excel файла: {str(e)}")

def parse_date(date_str):
    """Парсинг даты из различных форматов"""
    if pd.isna(date_str):
        return None
    try:
        if isinstance(date_str, datetime):
            return date_str.date()
        elif isinstance(date_str, str):
            return datetime.strptime(date_str, '%Y-%m-%d').date()
        return None
    except:
        return None

def export_results_to_excel(results, output_path):
    """Экспорт результатов в Excel"""
    data = []
    for result in results:
        data.append({
            'Место': result['place'],
            'Фамилия': result['last_name'],
            'Имя': result['first_name'],
            'Клуб': result['club'],
            'Категория': result['category'],
            'Раунд 1': result['round1'],
            'Раунд 2': result['round2'],
            'Раунд 3': result['round3'],
            'Общий балл': result['total'],
            'Средний балл': result['average']
        })
    
    df = pd.DataFrame(data)
    with pd.ExcelWriter(output_path, engine='xlsxwriter') as writer:
        df.to_excel(writer, sheet_name='Результаты', index=False)
        
        workbook = writer.book
        worksheet = writer.sheets['Результаты']
        
        # Форматирование
        header_format = workbook.add_format({
            'bold': True,
            'text_wrap': True,
            'valign': 'top',
            'bg_color': '#D7E4BC',
            'border': 1
        })
        
        for col_num, value in enumerate(df.columns.values):
            worksheet.write(0, col_num, value, header_format)
            worksheet.set_column(col_num, col_num, 15)
    
    return output_path