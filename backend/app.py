import os
import requests
import time
import uuid
import jwt # PyJWT 라이브러리
from flask import Flask, request, jsonify, send_from_directory, session, url_for, redirect
from authlib.integrations.flask_client import OAuth
from datetime import datetime, timedelta, timezone
from flask_cors import CORS
from dotenv import load_dotenv
from pathlib import Path
from PIL import Image # Pillow 라이브러리 import
import io # 이미지 데이터를 메모리에서 다루기 위해 import
# === extensions.py 에서 db, migrate 가져오기 ===
from extensions import db, migrate
from models import Hairstyle, User
from sqlalchemy import func


env_path = Path(__file__).resolve().parent.parent / '.env'
load_dotenv(dotenv_path=env_path, override=True)
print("[DEBUG] FRONTEND_URL resolved to:", os.getenv('FRONTEND_URL'))

app = Flask(__name__)

#세션 쿠키 설정을 추가합니다
app.config['SESSION_COOKIE_SAMESITE'] = 'None'  # 크로스 사이트 요청에서도 쿠키 전송 허용
app.config['SESSION_COOKIE_SECURE'] = True     # SameSite='None'일 경우 HTTPS를 통해서만 쿠키 전송 (필수)

# 기존 로컬 개발용 주소와 함께, 배포된 프론트엔드의 정확한 URL을 추가합니다.
frontend_deployed_url = "https://hairstyle-changer-app.onrender.com" # 사용자님의 프론트엔드 Render URL
allowed_origins = [
    'http://127.0.0.1:5500',    # 로컬 Live Server (http)
    'http://localhost:5500',     # 로컬 Live Server (http)
    frontend_deployed_url        # Render에 배포된 프론트엔드 (https)
]

#CORS(app) # 개발 환경에서 CORS 허용
# 명시적으로 프론트엔드 출처를 지정하고, 자격 증명(쿠키) 허용
CORS(app, supports_credentials=True, origins=allowed_origins)
#CORS(app, supports_credentials=True, origins=['http://127.0.0.1:5500', 'http://localhost:5500'])

# === DB 설정 ===
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'postgresql://postgres:password@localhost:5432/defaultdb')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False # SQLAlchemy 이벤트 처리 안 함 (권장)

# === 앱과 확장 연결 ===
db.init_app(app)   # extensions에서 가져온 db 객체에 앱 연결
migrate.init_app(app, db) # extensions에서 가져온 migrate 객체에 앱과 db 연결

# === OAuth 설정 ===
# FLASK_SECRET_KEY 로드 (세션 관리를 위해 필수)
app.secret_key = os.getenv('FLASK_SECRET_KEY', 'default_flask_secret_key_for_dev_only') # .env 파일에서 로드, 없으면 기본값
if app.secret_key == 'default_flask_secret_key_for_dev_only':
    print("경고: FLASK_SECRET_KEY가 기본값입니다. 프로덕션 환경에서는 반드시 변경하세요.")

# JWT 시크릿 키 로드
JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY')
if not JWT_SECRET_KEY:
    print("치명적 오류: JWT_SECRET_KEY 환경 변수가 설정되지 않았습니다. 앱을 시작할 수 없습니다.")
    # 실제 프로덕션에서는 여기서 앱 실행을 중단해야 합니다.
    # 개발 중에는 기본값을 사용할 수 있지만, 보안상 매우 취약합니다.
    JWT_SECRET_KEY = 'temp_jwt_secret_for_dev_use_only_!!!_CHANGE_ME_!!!' # << 개발용 임시값, 실제로는 .env에 설정
    if JWT_SECRET_KEY == 'temp_jwt_secret_for_dev_use_only_!!!_CHANGE_ME_!!!':
        print("경고: JWT_SECRET_KEY가 임시 기본값입니다. .env 파일에 강력한 키를 설정하세요.")


oauth = OAuth(app) # OAuth 객체 초기화

# Google OAuth 클라이언트 등록
# GOOGLE_CLIENT_ID와 GOOGLE_CLIENT_SECRET은 .env 파일에서 가져옵니다.
# 이 값들은 Google Cloud Console에서 발급받아야 합니다. (다음 단계에서 안내)
google = oauth.register(
    name='google',
    client_id=os.getenv('GOOGLE_CLIENT_ID'),
    client_secret=os.getenv('GOOGLE_CLIENT_SECRET'),
    access_token_url='https://accounts.google.com/o/oauth2/token',
    access_token_params=None,
    authorize_url='https://accounts.google.com/o/oauth2/auth',
    authorize_params=None,
    api_base_url='https://www.googleapis.com/oauth2/v1/',
    userinfo_endpoint='https://openidconnect.googleapis.com/v1/userinfo', # OIDC Userinfo endpoint
    client_kwargs={'scope': 'openid email profile'}, # 요청할 사용자 정보 범위
    jwks_uri="https://www.googleapis.com/oauth2/v3/certs", # JWKS URI 추가
)

# === 모델 Import ===
# 애플리케이션 컨텍스트 내부 또는 초기화 후에 모델을 임포트합니다.
# Flask-Migrate가 모델을 인식하려면 이 import가 필요합니다.
with app.app_context():
    from models import Hairstyle

# --- 환경 변수 또는 직접 설정 ---
# 중요: 실제 서비스에서는 환경 변수를 사용하세요!
API_KEY = os.getenv("AILAB_API_KEY", "IM3WWbmzxXNqKDIoMaw5VLRc2lDwhvlcRPdJ4yATk10jG67KuHtBsNXvSEz3xJSY")
if not API_KEY:
    print("오류: AILAB_API_KEY 환경 변수가 설정되지 않았습니다.")
    # 실제 환경에서는 여기서 종료하거나 기본 키 사용 X

# --- API 엔드포인트 ---
HAIRSTYLE_EDITOR_URL = "https://www.ailabapi.com/api/portrait/effects/hairstyle-editor-pro"
# 작업 결과 확인 URL (공식 문서 기반으로 수정됨)
TASK_RESULT_URL = "https://www.ailabapi.com/api/common/query-async-task-result"
# === 새로운 API 엔드포인트 정의 ===
FACE_ANALYZER_URL = "https://www.ailabapi.com/api/portrait/analysis/face-analyzer"

# === 얼굴형/성별 기반 추천 정보 (실제 헤어스타일 목록 연동) ===
# styles 리스트에는 hairstyle_name_map의 key (API value)를 사용
recommendations_db = {
    0: { # 각진형
        0: { # 남성
            "styles": ["TwoBlockHaircut", "Pompadour", "CombOver", "MessyTousled"],
            "reason": "옆머리는 깔끔하게 정리하고 윗머리에 볼륨을 주거나, 자연스럽게 헝클어진 스타일로 시선을 분산시켜 각진 턱선을 부드럽게 보완할 수 있습니다."
        },
        1: { # 여성
            "styles": ["LongWavy", "ShoulderLengthHair", "BobCut", "LongHimeCut"], # 히메컷은 옆선을 가려줌
            "reason": "얼굴 옆선을 부드럽게 감싸는 웨이브나 레이어드 스타일, 또는 턱선 주변에 볼륨감을 주는 단발/중단발 기장이 각진 부분을 커버하고 여성스러운 느낌을 줍니다."
        }
    },
    1: { # 삼각형
        0: { # 남성
            "styles": ["Spiky", "TexturedFringe", "LowFade", "FauxHawk"], # 윗머리 볼륨 강조
            "reason": "이마가 좁고 턱이 발달한 얼굴형에는 윗머리에 볼륨과 질감을 살린 스타일이 잘 어울립니다. 시선을 위로 끌어올려 얼굴 전체의 균형을 맞춰줍니다."
        },
        1: { # 여성
            "styles": ["PixieCut", "ShortNeatBob", "CurlyBob", "Updo"], # 윗부분/옆부분 볼륨
            "reason": "윗머리와 옆머리 윗부분에 볼륨을 주어 좁은 이마를 보완하고, 턱선으로 갈수록 가벼워지는 스타일이 좋습니다. 얼굴 위쪽에 시선을 집중시켜 균형을 맞춥니다."
        }
    },
    2: { # 타원형 (계란형)
        0: { # 남성
            "styles": ["SlickBack", "UnderCut", "Middle-parted", "ManBun"], # 다양한 스타일 가능
            "reason": "축복받은 얼굴형! 대부분의 헤어스타일이 잘 어울립니다. 원하는 분위기나 개성에 맞춰 자유롭게 시도해보세요. 깔끔하거나 개성있는 스타일 모두 좋습니다."
        },
        1: { # 여성
            "styles": ["LongStraight", "Ponytail", "BobCut", "ShortTwintails"], # 다양한 스타일 가능
            "reason": "이상적인 얼굴형으로, 어떤 헤어스타일을 해도 예쁘게 소화할 수 있습니다. 긴 생머리부터 짧은 머리, 묶음 머리까지 다양하게 연출해보세요."
        }
    },
    3: { # 하트형 (역삼각형)
        0: { # 남성
            "styles": ["UndercutLongHair", "MessyTousled", "ManBun", "TexturedFringe"], # 아래쪽 볼륨, 부드러움
            "reason": "넓은 이마와 좁은 턱선을 보완하기 위해 옆머리나 목덜미 부분에 볼륨감을 주거나, 부드러운 질감의 스타일이 좋습니다. 구레나룻을 살리는 것도 도움이 됩니다."
        },
        1: { # 여성
            "styles": ["BobCut", "ShoulderLengthHair", "LongWavy", "Chignon"], # 턱선 부근 볼륨
            "reason": "턱선 부근에 볼륨감이나 C컬, S컬을 넣어 좁은 하관을 보완하는 것이 중요합니다. 앞머리(사이드뱅, 시스루뱅 등)로 넓은 이마를 자연스럽게 커버할 수 있습니다."
        }
    },
    4: { # 둥근형
        0: { # 남성
            "styles": ["FauxHawk", "HighTightFade", "Spiky", "Pompadour"], # 세로 길이 강조
            "reason": "얼굴의 세로 길이를 강조하는 것이 중요합니다. 윗머리에 높이와 볼륨을 주고 옆머리는 짧게 눌러주어 얼굴이 갸름해 보이도록 연출하는 것이 좋습니다."
        },
        1: { # 여성
            "styles": ["LongStraight", "Updo", "Ponytail", "PixieCut"], # 세로선 강조, 옆 볼륨 자제
            "reason": "정수리 볼륨을 살려 얼굴의 세로 길이를 늘려주고, 얼굴 옆선을 따라 자연스럽게 떨어지거나 옆으로 넘기는 스타일이 둥근 느낌을 완화해줍니다. 옆 볼륨은 최소화하는 것이 좋습니다."
        }
    },
    "unknown": { # 알 수 없음
        0: { # 남성
            "styles": ["TwoBlockHaircut", "UnderCut", "SlickBack"], # 기본/무난 스타일
            "reason": "얼굴형 분석에 실패했습니다. 기본적으로 많은 사람들에게 잘 어울리는 스타일을 참고해보세요."
        },
        1: { # 여성
            "styles": ["LongStraight", "BobCut", "Ponytail"], # 기본/무난 스타일
            "reason": "얼굴형 분석에 실패했습니다. 기본적으로 많은 사람들에게 잘 어울리는 스타일을 참고해보세요."
        }
    }
}

# --- 임시 파일 저장 경로 (선택 사항) ---
UPLOAD_FOLDER = 'uploads'
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER


# 헤어스타일 변환 옵션 정보 (index.html 기반)
# API 'value'를 key로, '한국어 이름'을 value로 하는 딕셔너리
hairstyle_name_map = {
    # 남자 헤어스타일
    "BuzzCut": "버즈컷 (반삭)", "UnderCut": "언더컷", "Pompadour": "퐁파두르",
    "SlickBack": "슬릭백", "CurlyShag": "컬리 샤기컷", "WavyShag": "웨이비 샤기컷",
    "FauxHawk": "포호크", "Spiky": "스파이키", "CombOver": "콤오버 (가르마)",
    "HighTightFade": "하이 타이트 페이드", "ManBun": "맨번 (남자 묶음머리)",
    "Afro": "아프로", "LowFade": "로우 페이드", "UndercutLongHair": "언더컷 롱헤어",
    "TwoBlockHaircut": "투블럭컷", "TexturedFringe": "텍스처드 프린지 (질감 앞머리)",
    "BluntBowlCut": "블런트 보울컷 (바가지머리)", "LongWavyCurtainBangs": "롱 웨이비 커튼뱅",
    "MessyTousled": "메시 터슬드 (헝클어진 스타일)", "CornrowBraids": "콘로우 브레이드",
    "LongHairTiedUp": "긴 머리 묶음", "Middle-parted": "가운데 가르마",
    # 여자 헤어스타일
    "ShortPixieWithShavedSides": "숏 픽시 (사이드 쉐이브)", "ShortNeatBob": "짧은 단발",
    "DoubleBun": "더블 번 (양갈래 만두머리)", "Updo": "업두 (올림머리)", "Spiked": "스파이크 스타일",
    "bowlCut": "보울컷 (바가지머리)", "Chignon": "시뇽 (쪽머리)", "PixieCut": "픽시컷",
    "SlickedBack": "슬릭백", "LongCurly": "긴 곱슬머리", "CurlyBob": "곱슬 단발",
    "StackedCurlsInShortBob": "스택 컬 숏 밥",
    "SidePartCombOverHairstyleWithHighFade": "사이드 파트 콤오버 (하이 페이드)",
    "WavyFrenchBobVibesfrom1920": "웨이비 프렌치 밥 (1920년대)", "BobCut": "단발컷",
    "ShortTwintails": "짧은 양갈래", "ShortCurlyPixie": "짧은 곱슬 픽시컷",
    "LongStraight": "긴 생머리", "LongWavy": "긴 웨이브", "FishtailBraid": "피쉬테일 브레이드",
    "TwinBraids": "양갈래 땋기", "Ponytail": "포니테일", "Dreadlocks": "드레드락",
    "Cornrows": "콘로우", "ShoulderLengthHair": "어깨 길이 머리",
    "LooseCurlyAfro": "루즈 컬리 아프로", "LongTwintails": "긴 양갈래",
    "LongHimeCut": "긴 히메컷", "BoxBraids": "박스 브레이드"
}

# 얼굴형 코드와 한국어 이름 매핑 (기존 recommendations_db 에서 분리 또는 활용)
face_shape_kr_map = {
    0: "각진형", 1: "삼각형", 2: "타원형 (계란형)",
    3: "하트형 (역삼각형)", 4: "둥근형", "unknown": "알 수 없음"
}

# 성별 코드와 한국어 이름 매핑
gender_kr_map = {
    0: "남성", 1: "여성", "unknown": "알 수 없음" # 예비
}



# --- 정적 파일 서빙 (결과 이미지 표시용) ---
# 실제 프로덕션에서는 Nginx 같은 웹 서버를 통해 서빙하는 것이 더 효율적입니다.
# 여기서는 개발 편의성을 위해 Flask에서 직접 서빙합니다.
# 결과 이미지는 API에서 URL 형태로 제공되므로, 이 부분은 백엔드에 저장할 필요 없이
# 프론트엔드에서 직접 URL을 사용하면 됩니다. 따라서 이 라우트는 실제 사용되지 않을 수 있습니다.
@app.route('/results/<filename>')
def send_result_image(filename):
    # 이 함수는 API 결과가 URL이 아닌 파일 데이터일 경우 필요합니다.
    # ailabapi는 보통 결과 URL을 주므로, 사용되지 않을 가능성이 높습니다.
    # return send_from_directory(app.config['UPLOAD_FOLDER'], filename)
    pass # 여기서는 사용 안 함

# === 이미지 해상도 체크 함수 ===
def check_image_resolution(image_stream):
    """ Pillow를 사용해 이미지 해상도를 체크하고 2000x2000 이하인지 확인 """
    try:
        image_stream.seek(0) # 스트림 포인터를 처음으로 되돌림
        img = Image.open(image_stream)
        width, height = img.size
        print(f"이미지 해상도: {width}x{height}")
        if width > 2000 or height > 2000:
            return False
        return True
    except Exception as e:
        print(f"이미지 해상도 분석 오류: {e}")
        return False # 오류 발생 시 일단 유효하지 않음으로 처리
    finally:
        image_stream.seek(0) # 다른 곳에서 파일을 다시 읽을 수 있도록 포인터 되돌림

# === 얼굴 분석 API 라우트 수정 ===
@app.route('/api/analyze-face', methods=['POST'])
def analyze_face():

    # ... (파일 수신 및 기본 유효성 검사는 이전과 동일) ...
    if 'image' not in request.files: return jsonify({"error": "이미지 파일이 없습니다."}), 400
    image_file = request.files['image']
    if image_file.filename == '': return jsonify({"error": "파일이 선택되지 않았습니다."}), 400
    allowed_extensions = {'png', 'jpg', 'jpeg', 'bmp'}; file_ext = image_file.filename.rsplit('.', 1)[1].lower() if '.' in image_file.filename else '';
    if not file_ext or file_ext not in allowed_extensions: return jsonify({"error": "허용되지 않는 파일 형식입니다 (PNG, JPG, JPEG, BMP)."}), 400
    if image_file.content_length > 5 * 1024 * 1024: return jsonify({"error": "이미지 파일 크기는 5MB를 초과할 수 없습니다."}), 400
    image_stream_copy = io.BytesIO(image_file.read()); image_file.seek(0);
    if not check_image_resolution(image_stream_copy): return jsonify({"error": "이미지 해상도는 2000x2000 픽셀을 초과할 수 없습니다."}), 400

    # AILab Face Analyzer API 호출 준비
    payload = {
        # 얼굴형(Shape)과 성별(Gender) 정보 요청 (쉼표로 구분)
        'face_attributes_type': 'Shape,Gender' # <<--- 'Gender' 추가
    }
    files = {'image': (image_file.filename, image_stream_copy, image_file.mimetype)}
    headers = {'ailabapi-api-key': API_KEY }

    try:
        print(f"AILab Face Analyzer API 요청 시작: {FACE_ANALYZER_URL}, Payload: {payload}")
        response = requests.post(FACE_ANALYZER_URL, headers=headers, data=payload, files=files, timeout=30)
        response.raise_for_status()
        api_data = response.json()
        print(f"AILab Face Analyzer API 응답: {api_data}")

        if api_data.get("error_code") != 0:
            return jsonify({"error": f"얼굴 분석 API 오류: {api_data.get('error_msg', '알 수 없는 오류')}"}), 500

        face_infos = api_data.get("face_detail_infos")
        if not face_infos or len(face_infos) == 0:
            return jsonify({"error": "이미지에서 얼굴을 감지하지 못했습니다."}), 400

        attributes_info = face_infos[0].get("face_detail_attributes_info")
        if not attributes_info:
             return jsonify({"error": "얼굴 속성 정보를 가져올 수 없습니다."}), 400

        # 얼굴형(shape) 정보 추출
        shape_info = attributes_info.get("shape")
        if not shape_info or 'type' not in shape_info:
             # 얼굴형 분석 실패 시 기본값 처리 또는 오류 반환
             face_shape_type = "unknown"
             # return jsonify({"error": "얼굴형(shape) 정보를 찾을 수 없습니다."}), 400
        else:
            face_shape_type = shape_info.get("type")

        # 성별(gender) 정보 추출
        gender_info = attributes_info.get("gender")
        if not gender_info or 'type' not in gender_info:
            # 성별 분석 실패 시 기본값 처리 또는 오류 반환
            gender_type = 0 # 기본값 남성 또는 다른 값으로 설정 가능
            # return jsonify({"error": "성별(gender) 정보를 찾을 수 없습니다."}), 400
        else:
            gender_type = gender_info.get("type") # 성별 타입 (0: Male, 1: Female)

        # DB(딕셔너리)에서 추천 정보 조회 (얼굴형과 성별 모두 사용)
        face_shape_data = recommendations_db.get(face_shape_type, recommendations_db["unknown"])
        recommendation_data = face_shape_data.get(gender_type, face_shape_data.get(0)) # 해당 성별 정보가 없으면 남성(0) 정보 사용 (예외처리)


        # 추천 스타일 value 리스트 가져오기
        recommended_style_values = recommendation_data.get("styles", [])
        recommendation_reason = recommendation_data.get("reason", "추천 이유를 찾을 수 없습니다.")

        #DB에서 추천 스타일 상세 정보(이름, 이미지 URL) 조회
        recommendations_details = [] # 최종 추천 목록 (이름, 이미지 URL 포함)
        if recommended_style_values:
            # value에 해당하는 한국어 이름 리스트 생성 (DB 쿼리용)
            korean_names_to_query = [hairstyle_name_map.get(val, val) for val in recommended_style_values]

            # DB에서 해당 이름들의 Hairstyle 정보 조회
            # Hairstyle.name 필드를 기준으로 조회합니다. (이름이 unique하다고 가정)
            try:
                found_styles = Hairstyle.query.filter(Hairstyle.name.in_(korean_names_to_query)).all()
                # 결과를 {name: image_url} 딕셔너리로 만들어 빠른 조회 가능하게 함
                style_details_map = {style.name: style.image_url for style in found_styles}

                # 추천 목록 순서대로 이름과 이미지 URL 매칭하여 리스트 생성
                for api_value in recommended_style_values:
                    korean_name = hairstyle_name_map.get(api_value, api_value) # Map에서 한국어 이름 찾기
                    image_url = style_details_map.get(korean_name, 'placeholder.jpg') # DB 결과에서 이미지 URL 찾기

                    recommendations_details.append({
                        "name": korean_name,
                        "image_url": image_url,
                        "value": api_value  # <<< API value 추가!
                    })
            except Exception as db_e:
                print(f"Error querying Hairstyle DB: {db_e}")
                # DB 조회 실패 시, 이름만이라도 보내주기 (선택적 처리)
                recommendations_details = [
                     {"name": hairstyle_name_map.get(val, val), "image_url": "placeholder.jpg", "value": val}
                     for val in recommended_style_values
                ]
   
        # 성별 코드(0, 1)를 한국어 문자열로 변환
        gender_kr = "남성" if gender_type == 0 else "여성" if gender_type == 1 else "알 수 없음"

        # 얼굴형, 성별 한국어 이름 가져오기
        face_shape_kr = face_shape_kr_map.get(face_shape_type, "알 수 없음")
        gender_kr = gender_kr_map.get(gender_type, "알 수 없음")

        # 프론트엔드로 보낼 최종 결과 구성 (성별 정보 추가)
        result = {
            "face_shape_kr": face_shape_kr,
            "gender_kr": gender_kr,
            "recommendations": recommendations_details,
            "reason": recommendation_reason
        }
        return jsonify(result)

    except requests.exceptions.RequestException as e:
        print(f"얼굴 분석 API 요청 오류: {e}")
        return jsonify({"error": f"얼굴 분석 API 요청 중 오류 발생: {e}"}), 500
    except Exception as e:
        import traceback
        print(f"서버 내부 오류: {e}")
        traceback.print_exc()
        return jsonify({"error": f"서버 내부 오류 발생: {e}"}), 500

#헤어스타일 번환
@app.route('/api/transform-hairstyle', methods=['POST'])
def transform_hairstyle():
    if 'image' not in request.files:
        return jsonify({"error": "이미지 파일이 없습니다."}), 400
    if 'hair_style' not in request.form:
        return jsonify({"error": "헤어스타일 정보가 없습니다."}), 400

    image_file = request.files['image']
    hair_style = request.form['hair_style']
    # .get()을 사용하여 color 값이 없어도 오류가 발생하지 않도록 함
    hair_color = request.form.get('color')
    api_key_from_header = request.headers.get('X-Api-Key', API_KEY) # 헤더 우선, 없으면 .env 값 사용

    # --- 파일 유효성 검사 (예시) ---
    if image_file.filename == '':
        return jsonify({"error": "파일이 선택되지 않았습니다."}), 400

    allowed_extensions = {'png', 'jpg', 'jpeg'}
    if '.' not in image_file.filename or \
       image_file.filename.rsplit('.', 1)[1].lower() not in allowed_extensions:
        return jsonify({"error": "허용되지 않는 파일 형식입니다 (PNG, JPG, JPEG)."}), 400

    # --- 파일 크기 제한 (예시: 3MB) ---
    if image_file.content_length > 3 * 1024 * 1024:
         return jsonify({"error": "이미지 파일 크기는 3MB를 초과할 수 없습니다."}), 400

    # --- AILab API 호출 (비동기 요청) ---
    payload = {
        'task_type': 'async',
        'hair_style': hair_style
        # 'hair_color': '...' # API가 색상 변경도 지원한다면 추가
    }
    # hair_color 값이 존재하고 빈 문자열이 아닐 경우에만 payload에 추가
    if hair_color: # 빈 문자열('')이 아닌 경우 True
        payload['color'] = hair_color # <<--- payload에 color 추가

    files = {
        'image': (image_file.filename, image_file.stream, image_file.mimetype)
    }
    headers = {
        'ailabapi-api-key': api_key_from_header
    }

    try:
        print(f"AILab API 요청 시작: {HAIRSTYLE_EDITOR_URL}")
        response = requests.post(HAIRSTYLE_EDITOR_URL, headers=headers, data=payload, files=files, timeout=30) # 타임아웃 설정
        response.raise_for_status() # 200 OK가 아니면 예외 발생
        initial_data = response.json()
        print(f"AILab API 초기 응답: {initial_data}")

        if initial_data.get("error_code") != 0:
            return jsonify({"error": f"API 오류: {initial_data.get('error_msg', '알 수 없는 오류')}"}), 500

        task_id = initial_data.get("task_id")
        if not task_id:
            return jsonify({"error": "API 응답에서 task_id를 찾을 수 없습니다."}), 500

        # --- 결과 폴링 (Polling) ---
        polling_result = poll_for_result(task_id, api_key_from_header) # api_key_from_header 또는 API_KEY

        if polling_result.get("error"):
            # 폴링 중 오류 발생 시, AILab에서 받은 상세 메시지 사용
            error_message = polling_result.get("message", "작업 결과를 가져오는 중 알 수 없는 오류가 발생했습니다.")
            # AILab에서 HTTP 상태 코드를 주면 그것을 사용, 아니면 기본값 400 또는 500
            status_code = polling_result.get("status_code")
            # AILab의 내부 error_code (422 등)와 HTTP 상태 코드를 구분해야 할 수 있음
            # 여기서는 AILab이 422 오류를 HTTP 422로 반환한다고 가정하고,
            # 그 외 AILab 내부 error_code는 HTTP 400으로 매핑
            http_status_code = 400 # 기본 클라이언트 오류
            if isinstance(status_code, int):
                if 400 <= status_code < 600 : # HTTP 상태 코드 범위라면 그대로 사용
                    http_status_code = status_code
                # 그 외 AILab 내부 오류 코드는 400으로 처리하거나 필요시 더 세분화
            
            return jsonify({"error": error_message}), http_status_code
        
        elif polling_result.get("url"):
            return jsonify({"result_image_url": polling_result.get("url")})
        else:
            # 이 경우는 poll_for_result가 {"error": False, "url": None} 등을 반환하는 예외적 상황
            return jsonify({"error": "알 수 없는 이유로 작업 결과를 가져오지 못했습니다."}), 500
    
    except requests.exceptions.RequestException as e:
        print(f"API 요청 오류: {e}")
        return jsonify({"error": f"API 요청 중 오류 발생: {e}"}), 500
    except Exception as e:
        print(f"서버 내부 오류: {e}")
        return jsonify({"error": f"서버 내부 오류 발생: {e}"}), 500

# 헤어스타일 미리보기
@app.route('/api/hairstyle-info')
def hairstyle_info():
    style_value = request.args.get('value')
    if not style_value:
        return jsonify({'error': '헤어스타일 값이 전달되지 않았습니다.'}), 400

    # API value → 한글 이름으로 매핑
    korean_name = hairstyle_name_map.get(style_value)
    if not korean_name:
        return jsonify({'error': f'알 수 없는 스타일: {style_value}'}), 404

    # DB에서 name으로 검색
    style = Hairstyle.query.filter_by(name=korean_name).first()
    if not style:
        return jsonify({'error': f'{korean_name} 스타일을 찾을 수 없습니다.'}), 404

    return jsonify({
        'name': style.name,
        'description': style.description,
        'image_url': style.image_url
    })

# === 새로운 헤어스타일 검색 API 라우트 ===
@app.route('/api/search-hairstyles', methods=['GET'])
def search_hairstyles_api():
    query = request.args.get('q', '')
    results_list = []

    if query:
        # --- 1. 유사도(Similarity) 검색 먼저 시도 ---
        print(f"Attempting similarity search for: {query}")
        threshold = 0.2 # 임계값 설정 (0.15 ~ 0.25 사이에서 조절)
                       # ilike가 fallback이므로, 약간 높여서 더 유사한 것 위주로 찾아도 됨
        try:
            hairstyles = Hairstyle.query.filter(
                func.similarity(Hairstyle.name, query) >= threshold
            ).order_by(
                func.similarity(Hairstyle.name, query).desc() # 유사도 높은 순 정렬
            ).limit(20).all()
            print(f"Similarity search found {len(hairstyles)} results.")
        except Exception as sim_e:
            # 데이터베이스 오류 등 예외 처리
            print(f"Error during similarity search: {sim_e}. Falling back to ILIKE.")
            hairstyles = [] # 오류 발생 시 빈 리스트로 초기화

        # --- 2. 유사도 검색 결과가 없으면, ILIKE 검색으로 재시도 ---
        if not hairstyles: # 유사도 검색 결과가 비어있는 경우
            print(f"Similarity search yielded no results. Falling back to ILIKE search for: {query}")
            search_term = f"%{query}%" # ILIKE용 검색어 (%와일드카드% 사용)
            try:
                # ILIKE 검색 실행 (대소문자 무시)
                hairstyles = Hairstyle.query.filter(
                    Hairstyle.name.ilike(search_term)
                ).order_by(Hairstyle.name).limit(20).all() # 이름순 정렬 또는 다른 기준
                print(f"ILIKE search found {len(hairstyles)} results.")
            except Exception as ilike_e:
                # ILIKE 검색 중 오류 발생 시
                print(f"Error during ILIKE search: {ilike_e}")
                hairstyles = [] # 오류 시 빈 리스트 보장

    else:
        # 검색어가 없을 때
        print("No query, fetching initial list (limit 20)...")
        hairstyles = Hairstyle.query.order_by(Hairstyle.name).limit(20).all()

        # 결과 직렬화
    for style in hairstyles:
        results_list.append({
            'id': style.id,
            'name': style.name,
            'description': style.description,
            'image_url': style.image_url,
            'brand_price': style.brand_price,
            'normal_price': style.normal_price,
            'similar_styles_description': style.similar_styles_description
        })

    return jsonify({'results': results_list})

#Google 로그인 시작 라우트
@app.route('/login/google')
def login_google():
    # Google 로그인 페이지로 리다이렉트할 URL 생성
    # redirect_uri는 Google Cloud Console에 등록된 리다이렉트 URI와 일치해야 함
    redirect_uri = url_for('authorized_google', _external=True)
    return google.authorize_redirect(redirect_uri)

#Google 로그인 후 콜백 처리 라우트
@app.route('/login/google/authorized')
def authorized_google():
    print("--- Google Authorized Callback Received ---")
    print(f"Request URL: {request.url}")
    print(f"Request args: {request.args}")
    try:
        print("Attempting to authorize access token with Authlib...")
        token = google.authorize_access_token() # Google로부터 토큰 받아오기
        print(f"Received token from Google: {token}") # 받아온 토큰 전체 로그

        if token is None:
            print("Failed to receive token from Google (token is None).")
            return jsonify({"error": "Google 로그인 실패: 접근 토큰을 받을 수 없습니다."}), 400

        # 토큰 응답에 userinfo가 포함되어 있는지 확인하고 사용 (OIDC 표준)
        # 로그에서 token 안에 userinfo가 있고, 그 안에 'sub'가 있는 것을 확인했습니다.
        user_info_from_token = token.get('userinfo')

        if not user_info_from_token:
            # 만약 토큰에 userinfo가 없다면 (드문 경우), 별도로 userinfo 엔드포인트 호출
            print("Userinfo not directly in token, attempting to fetch via userinfo_endpoint...")
            try:
                user_info_from_token = google.get('userinfo').json() # 또는 oauth.google.userinfo(token=token)
            except Exception as e_userinfo_fetch:
                print(f"Failed to fetch userinfo separately: {e_userinfo_fetch}")
                return jsonify({"error": "Google 사용자 정보를 가져오는 데 실패했습니다 (별도 요청 실패)."}), 500
        
        print(f"User Info to process: {user_info_from_token}")

        # Google 사용자의 고유 ID는 'sub' (subject) 필드입니다.
        if not user_info_from_token or not user_info_from_token.get('sub'):
            print(f"Google user ID ('sub') not found in user_info: {user_info_from_token}")
            return jsonify({"error": "Google 사용자 ID를 가져올 수 없습니다."}), 400

        google_id = user_info_from_token['sub']
        email = user_info_from_token.get('email')
        name = user_info_from_token.get('name')
        profile_pic_url = user_info_from_token.get('picture')
        print(f"Extracted Google ID: {google_id}, Email: {email}, Name: {name}")

        # 데이터베이스에서 사용자 조회 또는 생성
        user = User.query.filter_by(google_id=google_id).first()

        if user:
            # 기존 사용자: 마지막 로그인 시간, 필요한 경우 이메일/이름/프로필 사진 업데이트
            user.last_login_at = datetime.now(timezone.utc)
            if email and user.email != email: user.email = email
            if name and user.name != name: user.name = name
            if profile_pic_url and user.profile_pic_url != profile_pic_url: user.profile_pic_url = profile_pic_url
            print(f"기존 사용자 업데이트: ID={user.id}, Email={user.email}")
        else:
            # 신규 사용자: DB에 새로 추가
            user = User(
                google_id=google_id,
                email=email,
                name=name,
                profile_pic_url=profile_pic_url,
                last_login_at=datetime.now(timezone.utc),
                credits=0 # 기본 크레딧
            )
            db.session.add(user)
            print(f"새로운 사용자 생성: Email={user.email}")
        
        db.session.commit()
        print(f"사용자 정보 DB에 커밋 완료 (User ID: {user.id})")

        payload = {
            'user_id': user.id, # 우리 DB의 사용자 ID
            'email': user.email,
            'name': user.name,
            'exp': datetime.now(timezone.utc) + timedelta(hours=1) # 토큰 만료 시간 (예: 1시간)
            # 필요하다면 다른 정보(google_id, profile_pic_url 등)도 포함 가능
        }
        jwt_token = jwt.encode(payload, JWT_SECRET_KEY, algorithm="HS256")
        print(f"JWT 발급됨 (User ID: {user.id}): {jwt_token[:20]}...") # 토큰 일부만 로깅

        # 세션에 사용자 정보 저장
        # session['user'] = {
        #     'id': user.id, # 우리 DB의 사용자 ID
        #     'google_id': user.google_id,
        #     'email': user.email,
        #     'name': user.name,
        #     'profile_pic_url': user.profile_pic_url
        # }
        # print(f"세션에 저장된 사용자 정보: {session.get('user')}")

        # 로그인 성공 후 프론트엔드의 메인 페이지(또는 이전에 있던 페이지)로 리다이렉트
        frontend_url = os.getenv('FRONTEND_URL', 'https://hairstyle-changer-app.onrender.com') # Live Server 포트
        redirect_target_url = f"{frontend_url}/index.html#token={jwt_token}"
        print(f"프론트엔드로 리다이렉션 시도: {redirect_target_url}")

        return redirect(redirect_target_url) # 예시: index.html로 리다이렉트

    except Exception as e:
        import traceback
        print(f"!!!!!!!!!! Google 로그인 콜백 처리 중 예외 발생 !!!!!!!!!!")
        print(f"오류 상세: {e}")
        traceback.print_exc()
        # Authlib에서 발생하는 특정 OAuth 오류는 다른 상태 코드를 가질 수 있지만,
        # 일반적인 예외는 500으로 처리합니다.
        return jsonify({"error": f"Google 로그인 처리 중 서버 내부 오류 발생: {str(e)}"}), 500

#로그아웃 라우트
@app.route('/logout')
def logout():
    #session.pop('user', None) # 세션에서 사용자 정보 제거
    frontend_url = os.getenv('FRONTEND_URL', 'http://127.0.0.1:5500')
    print(f"[DEBUG] FRONTEND_URL resolved to: {frontend_url}")
    return redirect(f"{frontend_url}/index.html") # 로그아웃 후 메인 페이지로

#현재 로그인 상태 확인 API (프론트엔드용
@app.route('/api/auth/status')
def auth_status():
    # session 대신 Authorization 헤더의 Bearer 토큰 확인
    auth_header = request.headers.get('Authorization')
    if not auth_header or not auth_header.startswith('Bearer '):
        return jsonify({"logged_in": False, "message": "인증 토큰이 없거나 형식이 잘못되었습니다."})

    token = auth_header.split(" ")[1] # "Bearer " 다음의 토큰 부분 추출

    try:
        # 토큰 디코딩 및 검증
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=["HS256"])
        user_id = payload.get('user_id')

        if not user_id:
            return jsonify({"logged_in": False, "message": "토큰에 사용자 ID가 없습니다."})

        # DB에서 사용자 정보 조회 (선택 사항: 매번 조회할지, 토큰 내용만 믿을지)
        # 여기서는 DB 조회를 통해 최신 정보를 가져오고, 사용자 존재 여부도 확인
        current_user = User.query.get(user_id)
        if current_user:
            # 프론트엔드에 전달할 사용자 정보 구성
            user_data_for_frontend = {
                'id': current_user.id,
                'email': current_user.email,
                'name': current_user.name,
                'profile_pic_url': current_user.profile_pic_url
                # 필요하다면 'credits': current_user.credits 등 추가
            }
            return jsonify({"logged_in": True, "user": user_data_for_frontend})
        else:
            return jsonify({"logged_in": False, "message": "사용자를 찾을 수 없습니다."})

    except jwt.ExpiredSignatureError:
        return jsonify({"logged_in": False, "message": "토큰이 만료되었습니다."})
    except jwt.InvalidTokenError:
        return jsonify({"logged_in": False, "message": "유효하지 않은 토큰입니다."})
    except Exception as e:
        print(f"Auth status error: {e}")
        return jsonify({"logged_in": False, "message": "인증 상태 확인 중 오류 발생"}), 500

def poll_for_result(task_id, api_key):
    """주어진 task_id로 공통 비동기 작업 결과 API를 주기적으로 확인합니다."""
    headers = {'ailabapi-api-key': api_key}
    params = {'task_id': task_id}
    max_attempts = 20
    wait_interval = 5

    for attempt in range(max_attempts):
        try:
            print(f"결과 확인 시도 {attempt + 1}/{max_attempts} (Task ID: {task_id})")
            response = requests.get(TASK_RESULT_URL, headers=headers, params=params, timeout=15)
            
            # HTTP 오류가 발생하면 여기서 바로 예외 처리로 넘어감 (예: 422)
            response.raise_for_status() 
            
            result_data = response.json()
            print(f"결과 확인 응답: {result_data}")

            # API 응답 내 error_code 확인 (AILab 자체 오류 코드)
            if result_data.get("error_code") != 0:
                error_msg = result_data.get('error_msg', 'AILab 작업 처리 중 오류가 발생했습니다.')
                error_detail = result_data.get('error_detail', {})
                # error_detail 안에 더 구체적인 메시지가 있을 수 있음
                specific_message = error_detail.get('message') or error_detail.get('code_message') or error_msg
                print(f"결과 확인 API 내부 오류: {specific_message}")
                return {"error": True, "message": specific_message, "status_code": result_data.get("error_code")}

            task_status = result_data.get("task_status")
            print(f"작업 상태 코드: {task_status}")

            if task_status == 2: # 성공
                print("작업 성공! 결과 URL 추출 시도.")
                data_field = result_data.get("data")
                if data_field:
                    images_list = data_field.get("images")
                    if images_list and isinstance(images_list, list) and len(images_list) > 0:
                        return {"error": False, "url": images_list[0]} # 성공 시 URL 반환
                    else:
                        return {"error": True, "message": "작업은 성공했으나 결과 이미지 목록을 찾을 수 없습니다."}
                else:
                    return {"error": True, "message": "작업은 성공했으나 결과 데이터 필드를 찾을 수 없습니다."}
            elif task_status == 0 or task_status == 1: # 대기 또는 처리 중
                print("작업 대기 또는 처리 중...")
                time.sleep(wait_interval)
            else: # 실패 또는 알 수 없는 상태
                error_msg = result_data.get('error_msg', f'알 수 없는 작업 상태 코드: {task_status}')
                error_detail = result_data.get('error_detail', {})
                specific_message = error_detail.get('message') or error_detail.get('code_message') or error_msg
                print(f"작업 실패 또는 알 수 없는 상태: {specific_message}")
                return {"error": True, "message": specific_message, "status_code": task_status}

        except requests.exceptions.Timeout:
            print("결과 확인 API 타임아웃.")
            # 마지막 시도에서 타임아웃되면 아래의 max_attempts 초과로 넘어감
            if attempt == max_attempts - 1:
                 return {"error": True, "message": "결과 확인 시간 초과. 잠시 후 다시 시도해주세요."}
            time.sleep(wait_interval) # 타임아웃 시 잠시 후 재시도

        except requests.exceptions.RequestException as e: # HTTP 오류 (예: 422) 포함
            error_response_text = "알 수 없는 API 요청 오류"
            status_code_to_return = 500 # 기본 서버 오류 코드
            if e.response is not None:
                status_code_to_return = e.response.status_code
                try:
                    error_json = e.response.json()
                    print(f"AILab API 오류 응답 (JSON): {error_json}") # 전체 JSON 응답 로깅
                    error_msg = error_json.get('error_msg', 'AILab API에서 오류가 반환되었습니다.')
                    error_detail = error_json.get('error_detail', {})
                    specific_message = error_detail.get('message') or error_detail.get('code_message') or error_msg
                    error_response_text = specific_message
                except ValueError: # JSON 파싱 실패 시
                    error_response_text = e.response.text
            print(f"결과 확인 API 요청 오류: {e} 응답 내용: {error_response_text}")
            return {"error": True, "message": error_response_text, "status_code": status_code_to_return}
        
        except Exception as e:
            import traceback
            print(f"결과 확인 중 예상치 못한 내부 오류: {e}")
            traceback.print_exc()
            return {"error": True, "message": "결과 확인 중 서버 내부 오류 발생"}

    print("최대 시도 횟수 초과. 결과 확인 실패.")
    return {"error": True, "message": "최대 시도 횟수 초과. 결과 확인에 실패했습니다."}

if __name__ == '__main__':
    # 개발 서버 실행 (디버그 모드 활성화)
    # 실제 배포 시에는 Gunicorn, uWSGI 등과 함께 사용
    app.run(debug=True, host='0.0.0.0', port=5001) # 포트 번호는 원하는 대로 변경 가능