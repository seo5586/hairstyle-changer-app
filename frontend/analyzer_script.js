const imageUpload = document.getElementById('imageUpload');
const imagePreview = document.getElementById('imagePreview');
const analyzeButton = document.getElementById('analyzeButton');
const statusMessage = document.getElementById('statusMessage');
const resultArea = document.getElementById('resultArea');
const faceShapeResult = document.getElementById('faceShapeResult');
const recommendationsList = document.getElementById('recommendationsList');
const recommendationReason = document.getElementById('recommendationReason');
const genderResult = document.getElementById('genderResult');

// 백엔드의 새 API 엔드포인트 URL
const BACKEND_API_URL = 'http://localhost:5001/api/analyze-face'; // 백엔드 주소 확인!

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
    const file = imageUpload.files[0];

    // 입력값 검증
    if (!file) {
        setStatus('이미지 파일을 업로드해주세요.', 'error');
        return;
    }

    // 파일 크기/타입 제한 (API 요구사항에 맞게)
    if (file.size > 5 * 1024 * 1024) { // 5MB 제한
        setStatus('이미지 파일 크기는 5MB를 초과할 수 없습니다.', 'error');
        return;
    }
    const allowedTypes = ['image/jpeg', 'image/png', 'image/bmp', 'image/jpg'];
    if (!allowedTypes.includes(file.type)) {
        setStatus('지원하지 않는 파일 형식입니다 (JPG, PNG, BMP).', 'error');
        return;
    }
    // 해상도 제한은 클라이언트 측에서 정확히 확인하기 어려우므로 백엔드에서 처리

    // FormData 객체 생성
    const formData = new FormData();
    formData.append('image', file);
    // face_attributes_type은 백엔드에서 고정값으로 추가할 예정

    // 상태 업데이트 및 버튼 비활성화
    setStatus('얼굴형 분석 중...', 'processing');
    analyzeButton.disabled = true;
    resultArea.style.display = 'none'; // 이전 결과 숨김

    try {
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

        if (data.error) {
             throw new Error(data.error);
        }

         // 성공 시 결과 표시 (성별 정보 추가)
         if (data.face_shape_kr && data.gender_kr && data.recommendations && data.reason) { // gender_kr 확인 추가
            genderResult.textContent = data.gender_kr; // <<--- 성별 정보 표시
            faceShapeResult.textContent = data.face_shape_kr;
            recommendationsList.innerHTML = '';
            data.recommendations.forEach(style => {
                const li = document.createElement('li');
                li.textContent = style;
                recommendationsList.appendChild(li);
            });
            recommendationReason.textContent = data.reason;
            resultArea.style.display = 'block';
            setStatus('분석 완료!', 'success');
        } else {
            throw new Error('분석 결과를 받지 못했거나 필요한 정보가 누락되었습니다.'); // 오류 메시지 수정
        }

    } catch (error) {
        console.error('오류 발생:', error);
        setStatus(`오류: ${error.message}`, 'error');
    } finally {
        // 버튼 다시 활성화
        analyzeButton.disabled = false;
    }
});

// 상태 메시지 업데이트 함수 (이전과 동일)
function setStatus(message, type) {
    statusMessage.textContent = message;
    statusMessage.className = `status ${type}`;
}