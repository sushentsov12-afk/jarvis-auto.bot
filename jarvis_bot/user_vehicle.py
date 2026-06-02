import json
import os


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
USER_VEHICLE_FILE = os.path.join(BASE_DIR, "user_vehicle.json")


class UserVehicle:
    def __init__(self, file_path: str = USER_VEHICLE_FILE):
        self.file_path = file_path
        self.data = self._load()

    def _load(self):
        """Загружает сохранённый автомобиль пользователя."""
        if not os.path.exists(self.file_path):
            return {}
        try:
            with open(self.file_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except json.JSONDecodeError:
            return {}

    def _save(self):
        """Сохраняет данные в JSON."""
        with open(self.file_path, "w", encoding="utf-8") as f:
            json.dump(self.data, f, ensure_ascii=False, indent=2)

    def set_vehicle(self, user_id: int, brand: str, model: str, year: str = None):
        """Сохраняет выбранный автомобиль пользователя."""
        self.data[str(user_id)] = {
            "brand": brand,
            "model": model,
            "year": year
        }
        self._save()

    def get_vehicle(self, user_id: int):
        """Возвращает сохранённый автомобиль пользователя."""
        return self.data.get(str(user_id))

    def clear_vehicle(self, user_id: int):
        """Удаляет выбранный автомобиль."""
        if str(user_id) in self.data:
            del self.data[str(user_id)]
            self._save()

    def has_vehicle(self, user_id: int) -> bool:
        """Проверяет, есть ли сохранённый автомобиль."""
        return str(user_id) in self.data


# Глобальный экземпляр
user_vehicle = UserVehicle()
