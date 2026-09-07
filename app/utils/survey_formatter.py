"""
Утилиты для форматирования результатов опросов.
"""
from app.schemas.analysis import AnalysisResult


def format_morning_survey_analysis(analysis: AnalysisResult, survey_data: dict) -> str:
    """
    Форматирует результат утреннего опроса с двумя подходами.
    """
    text = f"🌅 <b>Ваше утро</b>\n\n"
    
    # Краткая сводка
    text += f"📊 <b>Краткая сводка</b>\n"
    text += f"• Как проснулся: {survey_data.get('q1', 'Не указано')}\n"
    text += f"• Настроение: {survey_data.get('q3', 'Не указано')}\n"
    text += f"• Тело: {survey_data.get('q2', 'Не указано')}\n"
    text += f"• Мысли: {survey_data.get('q4', 'Не указано')}\n"
    text += f"• Сон: {survey_data.get('q5', 'Не указано')}\n\n"
    
    # Основной анализ
    text += f"{analysis.summary}\n\n"
    
    # Факторы
    if analysis.possible_factors:
        text += "📌 <b>Возможные факторы:</b>\n"
        for factor in analysis.possible_factors:
            text += f"• {factor}\n"
        text += "\n"
    
    # Паттерны
    if analysis.possible_patterns:
        text += "🔄 <b>Возможные паттерны:</b>\n"
        for pattern in analysis.possible_patterns:
            text += f"• {pattern}\n"
        text += "\n"
    
    # Раздел "Тело говорит подсознанию" (по Синельникову)
    text += "🧠 <b>Тело говорит подсознанию</b> (по Синельникову)\n"
    text += "Тело может отражать внутренние конфликты, невыраженные эмоции и бессознательные установки.\n"
    
    # Генерируем интерпретацию на основе ответов
    body_feeling = survey_data.get('q2', '')
    if 'напряжение' in body_feeling.lower() or 'боль' in body_feeling.lower():
        text += "• Напряжение в теле может быть связано с желанием контролировать ситуацию или нести «тяжкий груз».\n"
    if 'тревога' in survey_data.get('q3', '').lower():
        text += "• Тревога может указывать на внутренний конфликт или страх перед будущим.\n"
    text += "Важно: это возможная интерпретация для самонаблюдения, а не диагноз.\n\n"
    
    # Раздел "Современный подход"
    text += "🔬 <b>Современный подход</b>\n"
    text += "Современные исследования показывают, что утреннее состояние связано с качеством сна, "
    text += "уровнем кортизола и предыдущим днём. Регулярное наблюдение помогает снижать тревогу "
    text += "и повышать осознанность.\n"
    
    # Вопрос для самопроверки
    if analysis.check_question:
        text += f"\n❓ <b>Вопрос для самопроверки:</b>\n{analysis.check_question}\n"
    
    # Медицинское предупреждение
    if analysis.medical_warning:
        text += f"\n⚠️ {analysis.medical_warning}\n"
    
    return text