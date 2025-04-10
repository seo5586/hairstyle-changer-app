const imageUpload = document.getElementById('imageUpload');
const imagePreview = document.getElementById('imagePreview');
const hairStyleSelect = document.getElementById('hairStyleSelect');
const transformButton = document.getElementById('transformButton');
const statusMessage = document.getElementById('statusMessage');
const resultImage = document.getElementById('resultImage');
const hairColorSelect = document.getElementById('hairColorSelect');

// 백엔드 API 엔드포인트 URL (백엔드 서버 주소 및 포트에 맞게 수정)
const BACKEND_API_URL = 'http://127.0.0.1:5001/api/transform-hairstyle'; // 백엔드 주소 확인!

// (선택사항) 보안을 위해 API 키를 프론트엔드에서 직접 관리하지 않고,
// 백엔드에서 환경 변수로 관리하는 것이 좋습니다.
// 하지만 만약 API 정책 상 프론트엔드에서 키를 보내야 한다면 (권장되지 않음):
// const AILAB_API_KEY = '여기에_API_키_입력'; // !!! 매우 비권장 !!!

// 이미지 미리보기 기능
imageUpload.addEventListener('change', function(event) {
    const file = event.target.files[0];
    if (file) {
        const reader = new FileReader();
        reader.onload = function(e) {
            imagePreview.src = e.target.result;
            imagePreview.style.display = 'block';
        }
        reader.readAsDataURL(file);
        resultImage.style.display = 'none'; // 새 이미지 업로드 시 결과 숨김
        statusMessage.textContent = '';
        statusMessage.className = 'status';
    } else {
        imagePreview.style.display = 'none';
    }
});

// 변환 버튼 클릭 이벤트
transformButton.addEventListener('click', async () => {
    const file = imageUpload.files[0];
    const selectedStyle = hairStyleSelect.value;
    const selectedColor = hairColorSelect.value;

    // 입력값 검증
    if (!file) {
        setStatus('이미지 파일을 업로드해주세요.', 'error');
        return;
    }
    if (!selectedStyle) {
        setStatus('헤어스타일을 선택해주세요.', 'error');
        return;
    }

    // 파일 크기 검증 (3MB) - 클라이언트 측에서도 확인하면 사용자 경험 향상
    if (file.size > 3 * 1024 * 1024) {
        setStatus('이미지 파일 크기는 3MB를 초과할 수 없습니다.', 'error');
        return;
    }

    // FormData 객체 생성
    const formData = new FormData();
    formData.append('image', file);
    formData.append('hair_style', selectedStyle);
    formData.append('color', selectedColor);

    // 상태 업데이트 및 버튼 비활성화
    setStatus('이미지 변환 중... 시간이 걸릴 수 있습니다.', 'processing');
    transformButton.disabled = true;
    resultImage.style.display = 'none'; // 이전 결과 숨김

    try {
        // 백엔드 API 호출 (fetch 사용)
        const response = await fetch(BACKEND_API_URL, {
            method: 'POST',
            body: formData,
            // headers: { // API 키를 헤더로 보내야 하는 경우 (백엔드에서 처리하는 것이 더 안전)
            //     'X-Api-Key': AILAB_API_KEY
            // }
        });

        // 응답 처리
        if (!response.ok) {
            // HTTP 상태 코드가 2xx가 아닌 경우 오류 처리
            const errorData = await response.json().catch(() => ({ error: `HTTP 오류: ${response.status}` }));
            throw new Error(errorData.error || `서버 응답 오류: ${response.status}`);
        }

        const data = await response.json();

        if (data.error) {
            // 백엔드에서 보낸 명시적 오류 처리
             throw new Error(data.error);
        }

        if (data.result_image_url) {
            // 성공 시 결과 이미지 표시
            resultImage.src = data.result_image_url;
            resultImage.style.display = 'block';
            setStatus('헤어스타일 변환 완료!', 'success');
        } else {
            // 결과 URL이 없는 경우 (예상치 못한 응답)
            throw new Error('변환 결과를 받지 못했습니다.');
        }

    } catch (error) {
        // 오류 발생 시 메시지 표시
        console.error('오류 발생:', error);
        setStatus(`오류: ${error.message}`, 'error');
    } finally {
        // 버튼 다시 활성화
        transformButton.disabled = false;
    }
});

// 상태 메시지 업데이트 함수
function setStatus(message, type) {
    statusMessage.textContent = message;
    statusMessage.className = `status ${type}`; // CSS 클래스 적용 (processing, error, success)
}