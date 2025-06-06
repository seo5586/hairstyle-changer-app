파일 구조도

hairstyle-changer-app/
│
├── .gitignore                		# Git이 무시할 파일 및 폴더 목록
│
├── backend/                 		# 백엔드 (Flask) 관련 파일 및 폴더
│   ├── migrations/          	 	# Flask-Migrate를 사용한 데이터베이스 스키마 변경 이력
│   │   ├── versions/        		#   ㄴ 실제 마이그레이션 스크립트 파일들
│   │   ├── alembic.ini     	#   ㄴ Alembic 설정 파일
│   │   ├── env.py           		#   ㄴ Alembic 환경 설정 스크립트
│   │   ├── README       		#   ㄴ Alembic README
│   │   └── script.py.mako 	#   ㄴ 마이그레이션 스크립트 템플릿
│   │
│   ├── static/               		# Flask 정적 파일 폴더 (이미지 등)
│   │   └── images/           	#   ㄴ 이미지 저장 폴더
│   │       ├── placeholder.jpg 	#      ㄴ 기본 대체 이미지
│   │       ├── google_logo.png 	#      ㄴ Google 로그인 버튼용 로고
│   │       └── ... (각 헤어스타일 이미지 파일들 - 사용자가 추가하는 경우)
│   │
│   ├── venv/                 		# Python 가상 환경 폴더 (보통 .gitignore에 추가)
│   ├── __pycache__/         	# Python 컴파일 캐시 폴더 (보통 .gitignore에 추가)
│   │
│   ├── app.py                		# 메인 Flask 애플리케이션 로직 (모든 API 라우트 포함)
│   ├── models.py             	# SQLAlchemy 데이터베이스 모델 정의 (Hairstyle, User)
│   ├── extensions.py        	# Flask 확장(SQLAlchemy, Migrate) 초기화
│   ├── requirements.txt      	# Python 프로젝트 의존성 패키지 목록
│   ├── seed_hairstyles.py    	# 데이터베이스 초기 데이터(Hairstyle) 삽입 스크립트
│   └── .env                  		# 환경 변수 설정 파일 (API 키, DB 접속 정보 등)
│
└── frontend/                 		# 프론트엔드 (HTML, CSS, JavaScript) 관련 파일
    │
    ├── index.html            		# 기능 1: 헤어스타일 변환 페이지
    ├── analyzer.html         		# 기능 2: 얼굴형 분석 & 추천 페이지
    ├── search.html           		# 기능 4: 헤어스타일 검색 페이지 (기능 3 전에 만듦)
    ├── map.html              		# 기능 3: 주변 미용실 검색 지도 페이지
    │
    ├── style.css             		# 모든 페이지에 공통으로 적용되는 주요 CSS 파일
    ├── common.js             		# 여러 페이지에서 공통으로 사용하는 JavaScript 로직
    │                         		# (예: 팝업, 네비게이션 링크 활성화, 인증 UI, 이미지 리사이징 함수)
    │
    ├── script.js            		# index.html (헤어스타일 변환) 페이지 전용 JavaScript
    ├── analyzer_script.js    		# analyzer.html (얼굴형 분석) 페이지 전용 JavaScript
    ├── search_script.js      		# search.html (헤어스타일 검색) 페이지 전용 JavaScript
    └── map_script.js         		# map.html (주변 미용실 검색) 페이지 전용 JavaScript


----------
현재 Render를 사용하여 웹서비스를 호스팅 중입니다. 접속하셔서 서비스를 확인하실 수 있습니다.
https://hairstyle-changer-app.onrender.com

참고로 DB 서버는 6월 10일까지 운영합니다. (무료 버전)
그 이후에는 잘 동작하지 않을 수 있습니다.

----------
HAIRITHM (헤어리즘) 서비스 로컬 실행 및 설치 안내서

안녕하세요. HAIRITHM 프로젝트를 평가해주셔서 감사합니다.
본 안내서는 로컬 컴퓨터에서 프로젝트를 성공적으로 실행하기 위한 절차를 담고 있습니다.

1. 사전 준비 사항 (Prerequisites)
본 프로젝트를 실행하기 위해서는 아래의 소프트웨어들이 설치되어 있어야 합니다.

Python: 3.10 이상 버전 권장
PostgreSQL: 14 이상 버전 권장 (데이터베이스 서버)
pgAdmin 또는 DBeaver: PostgreSQL 데이터베이스 관리를 위한 GUI 도구 (선택 사항이지만 권장)
Git: 버전 관리 시스템 (코드 확인용)
VS Code (또는 다른 코드 에디터): 코드 확인 및 실행용
VS Code 사용 시 Live Server 확장 프로그램을 설치하면 프론트엔드 실행이 편리합니다.


2. 로컬 환경 설정

1단계: 프로젝트 파일 준비
제출된 압축 파일을 해제합니다.
터미널 또는 명령 프롬프트를 열고, 압축 해제된 프로젝트 폴더 내의 backend 폴더로 이동합니다.
(Bash)
cd path/to/your/project/hairstyle-changer-app/backend

2단계: PostgreSQL 데이터베이스 생성
pgAdmin 또는 사용하시는 DB 도구를 통해 PostgreSQL 서버에 접속합니다.
새로운 데이터베이스를 생성합니다. (예: mydb)
중요: 생성한 데이터베이스에 pg_trgm 확장을 설치해야 합니다. 해당 데이터베이스에 대한 쿼리 도구를 열고 다음 SQL을 실행합니다. (슈퍼유저 권한이 필요할 수 있습니다.)

(SQL)
CREATE EXTENSION IF NOT EXISTS pg_trgm;


3단계: 백엔드 Python 가상 환경 설정 및 패키지 설치
  1. backend 폴더 경로의 터미널에서 아래 명령어를 실행하여 Python 가상 환경을 생성합니다.
(Bash)
python -m venv venv

  2. 생성된 가상 환경을 활성화합니다.
Windows:  .\venv\Scripts\activate
macOS / Linux: source venv/bin/activate

  3. requirements.txt 파일을 사용하여 필요한 모든 Python 패키지를 설치합니다.
(Bash)
pip install -r requirements.txt


3. 실행 방법

1단계: 백엔드 서버 실행
backend 폴더 경로의 터미널에서 (가상 환경 활성화 상태) 아래 명령어를 실행합니다.
ex) C:\Users\Admin\Desktop\hairstyle-changer-app\backend> python app.py
http://127.0.0.1:5001 에서 서버가 실행됩니다.

(Bash)
python app.py		

2단계: 프론트엔드 서버 실행
VS Code에서 프로젝트 폴더를 엽니다.
frontend 폴더의 index.html 파일을 마우스 오른쪽 버튼으로 클릭합니다.
**'Open with Live Server'**를 선택하여 실행합니다.
웹 브라우저에 http://127.0.0.1:5500/frontend/index.html (또는 유사한 주소) 페이지가 열립니다.