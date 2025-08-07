#!/usr/bin/env python3
"""
Тестовый скрипт для проверки обработки callback'ов
"""

import re
import logging

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_callback_patterns():
    """Тестирует паттерны callback'ов"""
    
    # Тестовые callback'и
    test_callbacks = [
        "approve_123",
        "clarify_456", 
        "cancel_789",
        "duplicate_operator_7010480336_4",
        "edited_approve_999",
        "operator_123_456",
        "test_callback"
    ]
    
    # Паттерны из conv_admin
    patterns = [
        r"^(approve_|clarify_|cancel_|duplicate_operator_|duplicate_cancel_|duplicate_request_|edited_approve_|edited_cancel_|edited_operator_)",
        r"^(operator_|edited_operator_)"
    ]
    
    logger.info("=== ТЕСТ ПАТТЕРНОВ CALLBACK ===")
    
    for callback in test_callbacks:
        logger.info(f"Тестируем callback: {callback}")
        
        for i, pattern in enumerate(patterns):
            if re.match(pattern, callback):
                logger.info(f"  ✓ Совпадение с паттерном {i+1}: {pattern}")
            else:
                logger.info(f"  ✗ Нет совпадения с паттерном {i+1}: {pattern}")
        
        logger.info("")

if __name__ == "__main__":
    test_callback_patterns() 