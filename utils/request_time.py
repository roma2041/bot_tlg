from datetime import datetime, time

# Настройки времени (можно менять для удобства)
REQUEST_TIME_START = time(8, 0)   # 08:00
REQUEST_TIME_END = time(22, 00)    # 22:00

def is_allowed_request_time() -> bool:
    now = datetime.now().time()
    return REQUEST_TIME_START <= now <= REQUEST_TIME_END

def get_time_limits_str() -> str:
    return f"с {REQUEST_TIME_START.strftime('%H:%M')} до {REQUEST_TIME_END.strftime('%H:%M')}"