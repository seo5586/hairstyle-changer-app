# backend/extensions.py
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate

# 앱 객체 없이 확장 초기화
db = SQLAlchemy()
migrate = Migrate()