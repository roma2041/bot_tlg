from telegram import InlineKeyboardButton, InlineKeyboardMarkup

class TimePicker:
    @staticmethod
    def generate(hour=None, minute=None, time_type="start"):
        buttons = []
        for h in [0, 6, 12, 18]:
            row = []
            for i in range(6):
                if h + i < 24:
                    selected = (hour is not None) and (h + i == hour)
                    row.append(InlineKeyboardButton(
                        f"{'🟢' if selected else '⚪'}{h+i:02d}",
                        callback_data=f"time_{time_type}_hour_{h+i}"
                    ))
            buttons.append(row)
        
        # Добавляем текстовую строку между часами и минутами
        buttons.append([
            InlineKeyboardButton("выберите минуты", callback_data="ignore")
        ])
        
        buttons.append([
            InlineKeyboardButton(
                f"{'🟢' if (minute is not None) and (m == minute) else '⚪'}{m:02d}",
                callback_data=f"time_{time_type}_min_{m}"
            ) for m in [1, 10, 20, 30, 40, 59]
        ])
        buttons.append([
            InlineKeyboardButton("✅ Подтвердить", callback_data=f"time_{time_type}_confirm"),
            InlineKeyboardButton("🔄 Сбросить", callback_data=f"time_{time_type}_reset")
        ])
        return InlineKeyboardMarkup(buttons)