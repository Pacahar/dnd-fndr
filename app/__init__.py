from flask import Flask
from flask import session
import os


def create_app():
    """
    Создаёт и конфигурирует экземпляр приложения Flask.
    """
    app = Flask(__name__)

    # Загрузка конфигурации
    from config import Config
    app.config.from_object(Config)

    # Установка ключа для сессии
    app.secret_key = "mysecretkey"

    # Регистрация блюпринтов (маршрутов)
    from .routes.main import main_bp
    app.register_blueprint(main_bp)

    return app
