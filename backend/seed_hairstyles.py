# backend/seed_hairstyles.py

import os
import sys
import random
from contextlib import contextmanager
from sqlalchemy.sql import text

# Flask 앱과 SQLAlchemy db 객체를 가져오기 위해 경로 설정
# 현재 스크립트의 위치를 기준으로 backend 폴더의 부모 폴더를 경로에 추가
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, project_root)
sys.path.insert(0, os.path.dirname(__file__)) # backend 폴더도 추가

# --- Flask 앱 및 확장 초기화 ---
# app.py 에서 Flask 앱 객체를 가져옵니다.
# 순환 참조를 피하기 위해 앱 컨텍스트 내에서 모델을 import 할 수 있도록 구조화합니다.
# 주의: app.py 구조에 따라 import 방식이 달라질 수 있습니다.
# 여기서는 app.py에 app 객체가 있다고 가정합니다.
try:
    from app import app
    # extensions.py 에서 db 객체 가져오기
    from extensions import db
except ImportError as e:
    print(f"Error importing Flask app or extensions: {e}")
    print("Please ensure seed_hairstyles.py is in the backend folder and app.py/extensions.py are correctly structured.")
    sys.exit(1)

# --- 앱 컨텍스트 관리 ---
@contextmanager
def app_context():
    """Flask 앱 컨텍스트를 제공하는 컨텍스트 관리자"""
    context = app.app_context()
    context.push()
    try:
        yield
    finally:
        context.pop()

# --- 데이터 처리 함수 ---
def seed_data():
    """데이터베이스의 Hairstyle 테이블 데이터를 삭제하고 새로 추가합니다."""

    # 앱 컨텍스트 내에서 모델 import 및 DB 작업 수행
    with app_context():
        # 모델 import는 컨텍스트 내부에서 수행하는 것이 더 안전할 수 있음
        from models import Hairstyle

        print("Seeding database...")

        # 1. 기존 데이터 모두 삭제
        try:
            print("Deleting old Hairstyle data...")
            num_deleted = db.session.query(Hairstyle).delete()
            # PostgreSQL의 경우 TRUNCATE가 더 빠를 수 있으나, ORM 방식 사용
            # db.session.execute(text('TRUNCATE TABLE hairstyle RESTART IDENTITY CASCADE;')) # 필요시 Raw SQL 사용
            db.session.commit()
            print(f"Deleted {num_deleted} old records.")

            print("Resetting ID sequence for Hairstyle table...")
            # PostgreSQL에서 Hairstyle 테이블의 id 컬럼에 대한 시퀀스 이름은
            # 보통 'hairstyle_id_seq' 입니다. (테이블명_컬럼명_seq)
            # 만약 실제 시퀀스 이름이 다르다면 이 부분을 수정해야 합니다.
            sequence_name = 'hairstyle_id_seq'
            try:
                # text() 함수를 사용하여 SQL 인젝션 위험 없이 안전하게 실행
                db.session.execute(text(f'ALTER SEQUENCE {sequence_name} RESTART WITH 1;'))
                db.session.commit() # <<< 시퀀스 리셋 커밋
                print(f"Sequence '{sequence_name}' successfully reset to 1.")
            except Exception as seq_e:
                db.session.rollback() # 시퀀스 리셋 실패 시 롤백
                print(f"Warning: Could not reset sequence '{sequence_name}'. Error: {seq_e}")
                print("Proceeding without sequence reset. IDs might not start from 1.")
        except Exception as e:
            db.session.rollback()
            print(f"Error deleting data: {e}")
            return # 오류 발생 시 중단

        # 2. 추가할 새로운 헤어스타일 데이터 정의 (app.py의 hairstyle_name_map과 동일하게 유지)
        hairstyle_name_map = {
            # 남자 헤어스타일
            "BuzzCut": "버즈컷 (반삭)", "UnderCut": "언더컷", "Pompadour": "퐁파두르",
            "SlickBack": "슬릭백", # 남성 슬릭백 (이름 유지)
            "CurlyShag": "컬리 샤기컷", "WavyShag": "웨이비 샤기컷",
            "FauxHawk": "포호크", "Spiky": "스파이키", "CombOver": "콤오버 (가르마)",
            "HighTightFade": "하이 타이트 페이드", "ManBun": "맨번 (남자 묶음머리)",
            "Afro": "아프로", "LowFade": "로우 페이드", "UndercutLongHair": "언더컷 롱헤어",
            "TwoBlockHaircut": "투블럭컷", "TexturedFringe": "텍스처드 프린지 (질감 앞머리)",
            "BluntBowlCut": "블런트 보울컷 (바가지머리)", "LongWavyCurtainBangs": "롱 웨이비 커튼뱅",
            "MessyTousled": "메시 터슬드 (헝클어진 스타일)",
            "CornrowBraids": "콘로우", # 남성 콘로우 (이름 유지)
            "LongHairTiedUp": "긴 머리 묶음", "Middle-parted": "가운데 가르마",
            # 여자 헤어스타일
            "ShortPixieWithShavedSides": "숏 픽시 (사이드 쉐이브)", "ShortNeatBob": "짧은 단발",
            "DoubleBun": "더블 번 (양갈래 만두머리)", "Updo": "업두 (올림머리)", "Spiked": "스파이크 스타일",
            "bowlCut": "보울컷 (바가지머리)", # 여성 보울컷 (API 값이 달라 이름 중복 아님)
            "Chignon": "시뇽 (쪽머리)", "PixieCut": "픽시컷",
            "SlickedBack": "슬릭백 (여성)", # 여성 슬릭백 이름 수정
            "LongCurly": "긴 곱슬머리", "CurlyBob": "곱슬 단발",
            "StackedCurlsInShortBob": "스택 컬 숏 밥",
            "SidePartCombOverHairstyleWithHighFade": "사이드 파트 콤오버 (하이 페이드)",
            "WavyFrenchBobVibesfrom1920": "웨이비 프렌치 밥 (1920년대)", "BobCut": "단발컷",
            "ShortTwintails": "짧은 양갈래", "ShortCurlyPixie": "짧은 곱슬 픽시컷",
            "LongStraight": "긴 생머리", "LongWavy": "긴 웨이브", "FishtailBraid": "피쉬테일 브레이드",
            "TwinBraids": "양갈래 땋기", "Ponytail": "포니테일", "Dreadlocks": "드레드락",
            "Cornrows": "콘로우 (여성)", # 여성 콘로우 이름 수정
            "ShoulderLengthHair": "어깨 길이 머리",
            "LooseCurlyAfro": "루즈 컬리 아프로", "LongTwintails": "긴 양갈래",
            "LongHimeCut": "긴 히메컷", "BoxBraids": "박스 브레이드"
        }

        # 3. 새로운 데이터 추가
        print(f"Adding {len(hairstyle_name_map)} new Hairstyle records...")
        hairstyles_to_add = []
        for api_value, korean_name in hairstyle_name_map.items():
            # 임의의 데이터 생성
            description = f"세련되고 멋진 스타일, {korean_name}입니다. 당신의 개성을 표현해보세요."
            image_url = f"/static/images/{api_value.lower()}.jpg" # 예시 URL (실제 이미지 필요) 또는 "placeholder.jpg"
            # similar_styles_description 컬럼이 있다고 가정하고 추가
            similar_styles_desc = f"{korean_name} 스타일과 비슷한 느낌의 다른 헤어스타일도 많이 있습니다."
            brand_price = random.randint(5, 15) * 10000 # 50,000 ~ 150,000원
            normal_price = random.randint(3, 10) * 10000 # 30,000 ~ 100,000원

            # Hairstyle 객체 생성
            new_style = Hairstyle(
                name=korean_name, # 이름은 한국어로
                description=description,
                image_url=image_url,
                similar_styles_description=similar_styles_desc, # 추가된 컬럼
                brand_price=brand_price,
                normal_price=normal_price
            )
            hairstyles_to_add.append(new_style)

        try:
            db.session.add_all(hairstyles_to_add) # 여러 객체를 한 번에 추가 (더 효율적)
            db.session.commit()
            print("Successfully added new Hairstyle data.")
        except Exception as e:
            db.session.rollback()
            print(f"Error adding new data: {e}")

        print("Database seeding finished.")

# --- 스크립트 실행 부분 ---
if __name__ == "__main__":
    seed_data()