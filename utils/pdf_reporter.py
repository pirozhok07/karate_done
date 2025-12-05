from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch, cm
from reportlab.pdfgen import canvas
from reportlab.lib.enums import TA_CENTER

def generate_results_pdf(results, competition_info, output_path):
    """Генерация PDF отчета с результатами"""
    doc = SimpleDocTemplate(
        output_path,
        pagesize=A4,
        rightMargin=72,
        leftMargin=72,
        topMargin=72,
        bottomMargin=18
    )
    
    story = []
    styles = getSampleStyleSheet()
    
    # Заголовок
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        spaceAfter=30,
        alignment=TA_CENTER
    )
    
    story.append(Paragraph(f"Протокол соревнований: {competition_info['name']}", title_style))
    story.append(Paragraph(f"Дата: {competition_info['date']}", styles['Normal']))
    story.append(Paragraph(f"Место проведения: {competition_info['location']}", styles['Normal']))
    story.append(Spacer(1, 20))
    
    # Группировка по категориям
    categories = {}
    for result in results:
        category = result['category']
        if category not in categories:
            categories[category] = []
        categories[category].append(result)
    
    # Таблица для каждой категории
    for category, cat_results in categories.items():
        story.append(Paragraph(f"Категория: {category}", styles['Heading2']))
        story.append(Spacer(1, 10))
        
        # Сортировка по месту
        cat_results.sort(key=lambda x: x['place'])
        
        # Подготовка данных для таблицы
        data = [['Место', 'Спортсмен', 'Клуб', 'Раунд 1', 'Раунд 2', 'Раунд 3', 'Общий', 'Средний']]
        
        for result in cat_results:
            data.append([
                str(result['place']),
                f"{result['last_name']} {result['first_name']}",
                result['club'],
                f"{result['round1']:.2f}" if result['round1'] else '-',
                f"{result['round2']:.2f}" if result['round2'] else '-',
                f"{result['round3']:.2f}" if result['round3'] else '-',
                f"{result['total']:.2f}" if result['total'] else '-',
                f"{result['average']:.2f}" if result['average'] else '-'
            ])
        
        # Создание таблицы
        table = Table(data, colWidths=[1*cm, 4*cm, 3*cm, 2*cm, 2*cm, 2*cm, 2*cm, 2*cm])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('ALIGN', (1, 1), (1, -1), 'LEFT'),
        ]))
        
        story.append(table)
        story.append(Spacer(1, 30))
    
    # Подписи
    story.append(Spacer(1, 50))
    story.append(Paragraph("Главный судья: _________________________", styles['Normal']))
    story.append(Spacer(1, 20))
    story.append(Paragraph("Главный секретарь: _________________________", styles['Normal']))
    
    doc.build(story)
    return output_path