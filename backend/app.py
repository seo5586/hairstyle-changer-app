import os
import requests
import time
import uuid
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from dotenv import load_dotenv
from PIL import Image # Pillow 라이브러리 import
import io # 이미지 데이터를 메모리에서 다루기 위해 import
# === extensions.py 에서 db, migrate 가져오기 ===
from extensions import db, migrate
from models import Hairstyle
from sqlalchemy import func


load_dotenv() # .env 파일 로드

app = Flask(__name__)
CORS(app) # 개발 환경에서 CORS 허용

# === DB 설정 ===
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'postgresql://postgres:password@localhost:5432/defaultdb')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False # SQLAlchemy 이벤트 처리 안 함 (권장)

# === 앱과 확장 연결 ===
db.init_app(app)   # extensions에서 가져온 db 객체에 앱 연결
migrate.init_app(app, db) # extensions에서 가져온 migrate 객체에 앱과 db 연결

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
        # task_id를 poll_for_result 함수로 전달 (함수 내부에서 job_id 파라미터로 사용)
        result_image_url = poll_for_result(task_id, api_key_from_header)

        if result_image_url:
            return jsonify({"result_image_url": result_image_url})
        else:
            return jsonify({"error": "작업 결과를 가져오는 데 실패했거나 시간이 초과되었습니다."}), 500

    except requests.exceptions.RequestException as e:
        print(f"API 요청 오류: {e}")
        return jsonify({"error": f"API 요청 중 오류 발생: {e}"}), 500
    except Exception as e:
        print(f"서버 내부 오류: {e}")
        return jsonify({"error": f"서버 내부 오류 발생: {e}"}), 500

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

def poll_for_result(task_id, api_key):
    """주어진 task_id로 공통 비동기 작업 결과 API를 주기적으로 확인합니다."""
    headers = {'ailabapi-api-key': api_key}
    params = {'task_id': task_id} # task_id를 파라미터로 사용

    max_attempts = 20
    wait_interval = 5 # 필요시 대기 시간 조절 가능

    for attempt in range(max_attempts):
        try:
            print(f"결과 확인 시도 {attempt + 1}/{max_attempts} (Task ID: {task_id})")
            response = requests.get(TASK_RESULT_URL, headers=headers, params=params, timeout=15) # 타임아웃 약간 늘림
            response.raise_for_status() # 4xx, 5xx 오류 발생 시 예외 발생
            result_data = response.json()
            print(f"결과 확인 응답: {result_data}")

            # API 자체 오류 코드 확인 (0이 아니면 실패)
            if result_data.get("error_code") != 0:
                print(f"결과 확인 API 오류: {result_data.get('error_msg')}")
                return None

            # 작업 상태 확인 (문서 기준: 0=대기, 1=처리중, 2=성공)
            task_status = result_data.get("task_status")
            print(f"작업 상태 코드: {task_status}")

            if task_status == 2: # 상태 코드 2: 성공
                print("작업 성공! 결과 URL 추출 시도.")
                # 결과 데이터 추출 (data 객체 -> images 배열 -> 첫번째 요소)
                data_field = result_data.get("data")
                if data_field:
                    images_list = data_field.get("images")
                    # images 리스트가 존재하고, 비어있지 않은지 확인
                    if images_list and isinstance(images_list, list) and len(images_list) > 0:
                        result_url = images_list[0]
                        print(f"결과 이미지 URL 발견: {result_url}")
                        return result_url # 성공적으로 URL 반환
                    else:
                        print("오류: 작업 상태는 성공(2)이나, 응답 내 data.images 목록이 비어있거나 형식이 다릅니다.")
                        return None
                else:
                    print("오류: 작업 상태는 성공(2)이나, 응답 내 data 필드를 찾을 수 없습니다.")
                    return None

            elif task_status == 0 or task_status == 1: # 상태 코드 0 또는 1: 대기 또는 처리 중
                print("작업 대기 또는 처리 중...")
                time.sleep(wait_interval) # 잠시 대기 후 다시 시도

            else: # 상태 코드가 0, 1, 2 가 아닌 경우 (실패 또는 알 수 없는 상태)
                print(f"작업 실패 또는 알 수 없는 상태 코드: {task_status}")
                return None # 실패로 간주하고 종료

        except requests.exceptions.Timeout:
            print("결과 확인 API 타임아웃.")
            # 타임아웃 시 계속 시도할 수도 있지만, 여기서는 일단 실패로 간주하거나 재시도 횟수를 늘릴 수 있음
            # time.sleep(wait_interval) # 타임아웃 시 재시도 원하면 주석 해제

        except requests.exceptions.RequestException as e:
            error_response_text = ""
            if e.response is not None:
                try: error_response_text = e.response.text
                except Exception: pass
            print(f"결과 확인 API 요청 오류: {e} 응답 내용: {error_response_text}")
            return None # HTTP 오류 발생 시 종료
        except Exception as e:
            import traceback # 디버깅을 위해 traceback 추가
            print(f"결과 확인 중 예상치 못한 내부 오류: {e}")
            traceback.print_exc() # 오류 상세 내용 출력
            return None # 예상 못한 오류 시 종료

    print("최대 시도 횟수 초과. 결과 확인 실패.")
    return None


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

if __name__ == '__main__':
    # 개발 서버 실행 (디버그 모드 활성화)
    # 실제 배포 시에는 Gunicorn, uWSGI 등과 함께 사용
    app.run(debug=True, host='0.0.0.0', port=5001) # 포트 번호는 원하는 대로 변경 가능