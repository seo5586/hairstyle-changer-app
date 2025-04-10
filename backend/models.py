# backend/models.py

# === extensions.py 에서 db 객체 가져오기 ===
from extensions import db
# ==========================================

class Hairstyle(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False, index=True)
    description = db.Column(db.Text, nullable=True)
    image_url = db.Column(db.String(500), nullable=True)
    similar_styles_description = db.Column(db.Text, nullable=True)

    def __repr__(self):
        return f'<Hairstyle {self.id}: {self.name}>'
    