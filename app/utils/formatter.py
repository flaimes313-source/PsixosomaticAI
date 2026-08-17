"""
Форматтер для красивого вывода анализа в Telegram.
"""
from app.schemas.analysis import AnalysisResult


def format_analysis_for_telegram(result: AnalysisResult) -> str:
    """
    Форматирует результат анализа для отправки в Telegram.
    """
    lines = []
    
    # Заголовок
    lines.append("🧠 **Результат анализа**")
    lines.append("")
    
    # Резюме
    lines.append("📋 **Что я вижу**")
    lines.append(result.summary)
    lines.append("")
    
    # Факторы
    if result.possible_factors:
        lines.append("🔄 **Возможные факторы**")
        for factor in result.possible_factors:
            lines.append(f"• {factor}")
        lines.append("")
    
    # Паттерны
    if result.possible_patterns:
        lines.append("🔍 **Возможные паттерны**")
        for pattern in result.possible_patterns:
            lines.append(f"• {pattern}")
        lines.append("")
    
    # Вопрос для самопроверки
    if result.check_question:
        lines.append("❓ **Вопрос для самопроверки**")
        lines.append(result.check_question)
        lines.append("")
    
    # Практическое действие
    if result.micro_action:
        lines.append("💡 **Что попробовать**")
        lines.append(result.micro_action)
        lines.append("")
    
    # Наблюдения
    if result.things_to_observe:
        lines.append("👀 **За чем понаблюдать**")
        for item in result.things_to_observe:
            lines.append(f"• {item}")
        lines.append("")
    
    # Медицинское предупреждение
    if result.medical_warning:
        lines.append("⚠️ **Важно!**")
        lines.append(result.medical_warning)
        lines.append("")
    
    # Подвал
    lines.append("━━━━━━━━━━━━━━━━━━━")
    lines.append("💡 Вы можете задать до 3 уточняющих вопросов.")
    lines.append("⚠️ Важно: это не медицинский диагноз.")
    
    return "\n".join(lines)