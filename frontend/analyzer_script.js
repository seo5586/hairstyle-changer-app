const imageUpload = document.getElementById('imageUpload');
const imagePreview = document.getElementById('imagePreview');
const analyzeButton = document.getElementById('analyzeButton');
const statusMessage = document.getElementById('statusMessage');
const resultArea = document.getElementById('resultArea');
const faceShapeResult = document.getElementById('faceShapeResult');
const recommendationsContainer = document.getElementById('recommendationsContainer');
const recommendationReason = document.getElementById('recommendationReason');
const genderResult = document.getElementById('genderResult');
const ANALYZER_MAX_IMAGE_WIDTH = 2000;  // 얼굴 분석 API의 권장 최대 가로 크기
const ANALYZER_MAX_IMAGE_HEIGHT = 2000; // 얼굴 분석 API의 권장 최대 세로 크기

const BACKEND_BASE_URL = 'http://127.0.0.1:5001'; // Flask 서버 주소 및 포트

// 백엔드의 새 API 엔드포인트 URL
const BACKEND_API_URL = `${BACKEND_BASE_URL}/api/analyze-face`; // 백엔드 주소 확인!

// 이미지 미리보기 기능 (이전과 동일)
imageUpload.addEventListener('change', function(event) {
    const file = event.target.files[0];
    if (file) {
        const reader = new FileReader();
        reader.onload = function(e) {
            imagePreview.src = e.target.result;
            imagePreview.style.display = 'block';
        }
        reader.readAsDataURL(file);
        resultArea.style.display = 'none'; // 새 이미지 업로드 시 결과 숨김
        setStatus('', ''); // 상태 메시지 초기화
    } else {
        imagePreview.style.display = 'none';
    }
});

// 측정하기 버튼 클릭 이벤트
analyzeButton.addEventListener('click', async () => {
    let originalFile = imageUpload.files[0];

    // 입력값 검증
    if (!originalFile) { // 'originalFile' 변수 사용
        setStatus('이미지 파일을 업로드해주세요.', 'error');
        return;
    }


    // 상태 업데이트 및 버튼 비활성화
    setStatus('이미지 처리 중...', 'processing');
    analyzeButton.disabled = true;
    resultArea.style.display = 'none'; // 이전 결과 숨김

    let fileToUpload;

    try {
        // 이미지 리사이징 로직 호출 (common.js의 함수 사용)
        console.log(`Analyzer - 원본 파일: ${originalFile.name}, 크기: ${(originalFile.size / 1024 / 1024).toFixed(2)} MB`);
        // setStatus 함수를 콜백으로 전달
        const resizeResult = await resizeImageIfNeeded(originalFile, ANALYZER_MAX_IMAGE_WIDTH, ANALYZER_MAX_IMAGE_HEIGHT, setStatus);
        fileToUpload = resizeResult.file; // 리사이징된 (또는 원본) 파일
        console.log(`Analyzer - 업로드할 파일: ${fileToUpload.name}, 크기: ${(fileToUpload.size / 1024 / 1024).toFixed(2)} MB`);
        // resizeResult.resized 가 true이면 이미 setStatus가 호출되었음

        // 리사이징된 파일에 대한 크기/타입 제한 재확인 (API 요구사항에 맞게)
        if (fileToUpload.size > 5 * 1024 * 1024) { // 5MB 제한
            setStatus('이미지 파일 크기는 5MB를 초과할 수 없습니다 (자동 조절 후).', 'error');
            throw new Error('Resized file still too large for analyzer');
        }
        const allowedTypes = ['image/jpeg', 'image/png', 'image/bmp', 'image/jpg'];
        // 리사이징 과정에서 파일 타입이 변경될 수 있으므로, 변경된 타입을 기준으로 검사
        const fileTypeToCheck = fileToUpload.type || originalFile.type;
        if (!allowedTypes.includes(fileTypeToCheck)) {
            setStatus('지원하지 않는 파일 형식입니다 (JPG, PNG, BMP).', 'error');
            throw new Error('Invalid file type after resize attempt');
        }
        // 해상도 제한은 리사이징 함수에서 이미 처리되었으므로, 여기서는 파일 크기 위주로 검증

        // FormData 객체 생성 (fileToUpload 사용)
        const formData = new FormData();
        formData.append('image', fileToUpload);

        setStatus('얼굴형 분석 중...', 'processing'); // 실제 분석 시작 알림

        // 백엔드 API 호출 (fetch 사용)
        const response = await fetch(BACKEND_API_URL, {
            method: 'POST',
            body: formData,
            // headers: { 'X-Api-Key': 'YOUR_API_KEY' } // 키를 헤더로 보내야 한다면
        });

        // 응답 처리
        if (!response.ok) {
            const errorData = await response.json().catch(() => ({ error: `HTTP 오류: ${response.status}` }));
            throw new Error(errorData.error || `서버 응답 오류: ${response.status}`);
        }

        const data = await response.json();

        //로그 추가
        console.log('Backend로부터 받은 전체 데이터:', data);
        console.log('받은 recommendations 데이터:', data.recommendations);

        if (data.error) {
             throw new Error(data.error);
        }

        // 성공 시 결과 표시 (이미지 + 이름 형태)
        if (data.face_shape_kr && data.gender_kr && data.recommendations && data.reason) {
            genderResult.textContent = data.gender_kr;
            faceShapeResult.textContent = data.face_shape_kr;

            // 추천 목록을 표시할 컨테이너 (새 변수 이름 사용)
            recommendationsContainer.innerHTML = ''; // 컨테이너 내용 비우기

            // recommendations 데이터가 배열이고 내용이 있는지 확인
            if (Array.isArray(data.recommendations) && data.recommendations.length > 0) {
                data.recommendations.forEach(style => {
                    // console.log('현재 처리 중인 style 객체:', style); // 로그는 유지해도 좋습니다.

                    // 각 추천 항목을 위한 div 생성
                    const itemDiv = document.createElement('div');
                    itemDiv.classList.add('recommendation-item'); // CSS 클래스 적용
                    itemDiv.style.cursor = 'pointer';
                    itemDiv.dataset.value = style.value;

                    // 이미지 요소 생성
                    const img = document.createElement('img'); // 'img' 변수 여기서 선언!
                    img.alt = style.name;

                    const imageUrlFromAPI = style.image_url; // 예: "/static/images/some.jpg"
                    const placeholderFullUrl = `${BACKEND_BASE_URL}/static/images/placeholder.jpg`;

                    if (imageUrlFromAPI && typeof imageUrlFromAPI === 'string' && imageUrlFromAPI.startsWith('/static/')) {
                        img.src = `${BACKEND_BASE_URL}${imageUrlFromAPI}`;
                    } else {
                        console.warn(`잘못된 이미지 URL ("${imageUrlFromAPI}") 또는 URL 없음. Placeholder를 사용합니다.`);
                        img.src = placeholderFullUrl;
                    }

                    // 'img' 변수는 이 onerror 함수 스코프에서 접근 가능해야 합니다.
                    img.onerror = () => {
                        console.warn(`이미지 로드 실패: ${img.src}. Placeholder 이미지로 대체합니다.`);
                        // onerror 발생 시 placeholder 절대 URL로 설정 (무한 루프 방지)
                        // 여기서 img.src는 실패한 원래 URL일 수 있으므로, placeholderFullUrl과 비교
                        if (img.src !== placeholderFullUrl) {
                           img.src = placeholderFullUrl;
                        }
                        img.style.backgroundColor='#e9ecef';
                    };

                    // 이름 표시용 span 요소 생성
                    const nameSpan = document.createElement('span');
                    nameSpan.textContent = style.name; // 객체의 name 속성 사용 (핵심 수정!)

                    // div에 이미지와 이름 추가
                    itemDiv.appendChild(img);
                    itemDiv.appendChild(nameSpan);

                    //클릭 이벤트 리스너
                    itemDiv.addEventListener('click', () => {
                        const selectedHairstyleValue = itemDiv.dataset.value; // 저장된 value 가져오기
                        if (selectedHairstyleValue) {
                            // index.html로 리다이렉트하면서 URL 파라미터 추가
                            const redirectUrl = `index.html?hairstyle=${encodeURIComponent(selectedHairstyleValue)}`;
                            console.log(`Redirecting to: ${redirectUrl}`); // 확인용 로그
                            window.location.href = redirectUrl; // 페이지 이동
                        } else {
                            console.error("Hairstyle value not found on clicked item.");
                        }
                    });

                    // 컨테이너에 완성된 항목 추가
                    recommendationsContainer.appendChild(itemDiv); // 올바른 컨테이너에 추가

                    // console.log('이미지 URL:', style.image_url, '이름:', style.name); // 로그는 유지해도 좋습니다.
                });
            } else {
                // 추천 항목이 없을 경우 메시지 표시
                recommendationsContainer.innerHTML = '<p>이 얼굴형/성별에 대한 추천 헤어스타일을 찾지 못했습니다.</p>';
            }

            // 추천 이유 표시
            recommendationReason.textContent = data.reason;
            // 결과 영역 전체 보이기
            resultArea.style.display = 'block';
            setStatus('분석 완료!', 'success');

        } else {
            // 필요한 데이터가 응답에 없는 경우
            throw new Error('분석 결과를 처리하는데 필요한 정보가 부족합니다.');
        }

    } catch (error) {
        console.error('상세 오류 (얼굴 분석):', error); // 디버깅용 상세 오류 출력

        let userMessage = "얼굴 분석 중 예상치 못한 오류가 발생했습니다. 잠시 후 다시 시도해주세요."; // 기본 메시지

        if (error.message) {
            const msg = error.message.toLowerCase();

            if (msg.includes("파일 크기") || msg.includes("초과할 수 없습니다")) {
                userMessage = "이미지 파일 크기가 너무 큽니다 (5MB 이하). 다른 파일을 선택해주세요.";
            } else if (msg.includes("파일 형식") || msg.includes("허용되지 않는")) {
                userMessage = "지원하지 않는 파일 형식입니다 (JPG, PNG, BMP). 다른 파일을 선택해주세요.";
            } else if (msg.includes("해상도") || msg.includes("픽셀을 초과")) {
                userMessage = "이미지 해상도가 너무 높습니다 (2000x2000px 이하). 다른 파일을 선택해주세요.";
            } else if (msg.includes("얼굴을 감지하지 못했습니다")) {
                userMessage = "사진에서 얼굴을 찾을 수 없습니다. 얼굴이 더 선명하게 나온 정면 사진을 사용해보세요.";
            } else if (msg.includes("얼굴 속성 정보") || msg.includes("분석 결과") || msg.includes("필요한 정보가 누락")) {
                 userMessage = "얼굴 분석 결과를 처리하는 중 오류가 발생했습니다. 다른 사진으로 시도해보세요.";
            } else if (msg.includes("얼굴 분석 api 오류")) {
                userMessage = "얼굴 분석 서비스에 문제가 발생했습니다. 잠시 후 다시 시도해주세요.";
            } else if (msg.includes("http 오류") || msg.includes("서버 응답 오류") || msg.includes("서버 내부 오류")) {
                 userMessage = "서버와 통신 중 오류가 발생했습니다. 잠시 후 다시 시도해주세요.";
            } else if (msg.includes("failed to fetch")) { // 네트워크 연결 실패
                 userMessage = "서버에 연결할 수 없습니다. 네트워크 상태를 확인해주세요.";
            }
            // 필요에 따라 다른 특정 오류 메시지에 대한 처리 추가 가능
        }

        setStatus(userMessage, 'error');
    } finally {
        analyzeButton.disabled = false;
    }
});

// 상태 메시지 업데이트 함수 (이전과 동일)
function setStatus(message, type) {
    statusMessage.textContent = message;
    statusMessage.className = `status ${type}`;
}