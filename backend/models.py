# backend/models.py

# === extensions.py 에서 db 객체 가져오기 ===
from extensions import db
from datetime import datetime
from datetime import timezone
# ==========================================

class Hairstyle(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False, index=True)
    description = db.Column(db.Text, nullable=True)
    image_url = db.Column(db.String(500), nullable=True)
    similar_styles_description = db.Column(db.Text, nullable=True)
    brand_price = db.Column(db.Integer, nullable=True)
    normal_price = db.Column(db.Integer, nullable=True)

    def __repr__(self):
        return f'<Hairstyle {self.id}: {self.name}>'

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True) # 사용자 고유 ID (자동 증가)
    google_id = db.Column(db.String(200), unique=True, nullable=False) # Google 사용자의 고유 ID
    email = db.Column(db.String(120), unique=True, nullable=False) # 이메일 주소 (Google 제공)
    name = db.Column(db.String(100), nullable=True) # 사용자 이름 (Google 제공, 선택적)
    profile_pic_url = db.Column(db.String(500), nullable=True) # 프로필 사진 URL (Google 제공, 선택적)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    last_login_at = db.Column(db.DateTime, nullable=True) # 마지막 로그인 일시
    credits = db.Column(db.Integer, default=0, nullable=False) # 보유 크레딧 (기본값 0)

    def __repr__(self):
        return f'<User {self.id}: {self.email}>'