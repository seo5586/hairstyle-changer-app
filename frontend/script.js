const imageUpload = document.getElementById('imageUpload');
const imagePreview = document.getElementById('imagePreview');
const hairStyleSelect = document.getElementById('hairStyleSelect');
const transformButton = document.getElementById('transformButton');
const statusMessage = document.getElementById('statusMessage');
const resultImage = document.getElementById('resultImage');
const hairColorSelect = document.getElementById('hairColorSelect');
const resultButtonsContainer = document.getElementById('resultButtonsContainer');
const hairstylePreviewArea = document.getElementById('hairstylePreviewArea');
const MAX_IMAGE_WIDTH = 1500;
const MAX_IMAGE_HEIGHT = 1500;

// 백엔드 API 엔드포인트 URL 
const BACKEND_BASE_URL = 'https://hairstyle-changer.onrender.com'; // Flask 서버 주소 (백엔드 서버 주소 및 포트에 맞게 수정)
const TRANSFORM_API_URL = `${BACKEND_BASE_URL}/api/transform-hairstyle`; // 기존 변환 API URL 수정
const HAIRSTYLE_INFO_API_URL = `${BACKEND_BASE_URL}/api/hairstyle-info`; // 새 미리보기 정보 API URL

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
    let originalFile = imageUpload.files[0];
    const selectedStyle = hairStyleSelect.value;
    const selectedColor = hairColorSelect.value;

    // 입력값 검증
    if (!originalFile) {
        setStatus('이미지 파일을 업로드해주세요.', 'error');
        return;
    }
    if (!selectedStyle) {
        setStatus('헤어스타일을 선택해주세요.', 'error');
        return;
    }

    //초기 상태 업데이트 및 UI 비활성화
    setStatus('이미지 처리 중...', 'processing'); // '처리 중'으로 메시지 변경
    transformButton.disabled = true;
    resultImage.style.display = 'none';
    if(resultButtonsContainer) resultButtonsContainer.style.display = 'none'; // 새 결과 버튼도 숨김

    let fileToUpload; // 최종적으로 업로드할 파일 변수

    try {
        //이미지 리사이징 로직 호출
        console.log(`Transform - 원본 파일: ${originalFile.name}, 크기: ${(originalFile.size / 1024 / 1024).toFixed(2)} MB`);
        // common.js의 함수를 호출하면서, setStatus 함수를 콜백으로 전달
        const resizeResult = await resizeImageIfNeeded(originalFile, MAX_IMAGE_WIDTH, MAX_IMAGE_HEIGHT, setStatus);
        fileToUpload = resizeResult.file; // 반환된 객체에서 파일 가져오기
        console.log(`Transform - 업로드할 파일: ${fileToUpload.name}, 크기: ${(fileToUpload.size / 1024 / 1024).toFixed(2)} MB`);
        // resizeResult.resized 가 true이면 이미 setStatus가 common.js 내에서 호출되었을 것입니다.       

        //리사이징된 파일에 대한 크기 재검증
        if (fileToUpload.size > 3 * 1024 * 1024) { // 3MB 제한
            setStatus('이미지 파일 크기가 3MB를 초과합니다 (자동 조절 후). 다른 이미지를 사용해주세요.', 'error');
            throw new Error('Resized file still too large'); // catch 블록으로 이동하여 finally에서 버튼 활성화
        }        

        // FormData 객체 생성
        const formData = new FormData();
        formData.append('image', fileToUpload);
        formData.append('hair_style', selectedStyle);
        formData.append('color', selectedColor);

        //이미지 변환 시작 알림
        setStatus('이미지 변환 중... 시간이 걸릴 수 있습니다.', 'processing');

        // 백엔드 API 호출 (fetch 사용)
        const response = await fetch(TRANSFORM_API_URL, {
            method: 'POST',
            body: formData,
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

            if(resultButtonsContainer) resultButtonsContainer.style.display = 'flex';

            setStatus('헤어스타일 변환 완료!', 'success');
        } else {
            // 결과 URL이 없는 경우 (예상치 못한 응답)
            throw new Error('변환 결과를 받지 못했습니다.');
        }

    } catch (error) {
        console.error('상세 오류 (헤어스타일 변환):', error); // 디버깅용 상세 오류 출력

        let userMessage = "헤어스타일 변환 중 예상치 못한 오류가 발생했습니다. 잠시 후 다시 시도해주세요."; // 기본 메시지

        if (error.message) {
            const msg = error.message.toLowerCase();
            

            if (msg.includes("파일 크기") || msg.includes("초과할 수 없습니다")) {
                userMessage = "이미지 파일 크기가 너무 큽니다 (3MB 이하). 다른 파일을 선택해주세요.";
            } else if (msg.includes("파일 형식") || msg.includes("허용되지 않는")) {
                userMessage = "지원하지 않는 파일 형식입니다 (JPG, PNG). 다른 파일을 선택해주세요.";
            } else if (msg.includes("api 오류") || msg.includes("task_id")) {
                userMessage = "헤어스타일 변환 서비스에 문제가 발생했습니다. 잠시 후 다시 시도해주세요.";
            } else if (msg.includes("http 오류") || msg.includes("서버 응답 오류") || msg.includes("서버 내부 오류")) {
                 userMessage = "서버와 통신 중 오류가 발생했습니다. 잠시 후 다시 시도해주세요.";
            } else if (msg.includes("failed to fetch")) { // 네트워크 연결 실패
                 userMessage = "서버에 연결할 수 없습니다. 네트워크 상태를 확인해주세요.";
            } else if (msg.includes("결과를 받지 못했습니다") || msg.includes("시간이 초과")) {
                 userMessage = "변환 결과를 가져오는 데 실패했습니다. 잠시 후 다시 시도하거나 다른 스타일/이미지를 사용해보세요.";
            }
            // 필요에 따라 다른 특정 오류 메시지에 대한 처리 추가 가능
        }

        setStatus(userMessage, 'error');

        if(resultButtonsContainer) resultButtonsContainer.style.display = 'none';

    } finally {
        transformButton.disabled = false; // 버튼 다시 활성화
    }
});

//헤어스타일 선택 시 미리보기 로드 로직
hairStyleSelect.addEventListener('change', async function() {
    const selectedValue = this.value; // 선택된 헤어스타일의 API value (예: "BuzzCut")

    if (!selectedValue) { // "-- 스타일 선택 --" 이거나 값이 없는 경우
        hairstylePreviewArea.innerHTML = '<p>스타일을 선택하면 여기에 미리보기가 표시됩니다.</p>';
        hairstylePreviewArea.style.display = 'none'; // 또는 'block'으로 두고 내부 메시지만 변경
        return;
    }

    // 로딩 메시지 표시
    hairstylePreviewArea.innerHTML = '<p>미리보기 로딩 중...</p>';
    hairstylePreviewArea.style.display = 'block'; // 미리보기 영역 보이기

    try {
        const response = await fetch(`${HAIRSTYLE_INFO_API_URL}?value=${encodeURIComponent(selectedValue)}`);
        if (!response.ok) {
            const errorData = await response.json().catch(() => null);
            const errorMessage = errorData?.error || `HTTP 오류: ${response.status}`;
            throw new Error(errorMessage);
        }

        const data = await response.json();

        if (data.error) {
            throw new Error(data.error);
        }

        // 미리보기 HTML 생성 (이미지 왼쪽, 이름/설명 오른쪽)
        // 이미지 URL은 백엔드에서 /static/... 형태로 오므로, BACKEND_BASE_URL을 붙여야 함
        const imageUrl = data.image_url && data.image_url.startsWith('/static/')
                            ? `${BACKEND_BASE_URL}${data.image_url}`
                            : `${BACKEND_BASE_URL}/static/images/placeholder.jpg`; // 기본 placeholder

        hairstylePreviewArea.innerHTML = `
            <div class="preview-content">
                <img src="${imageUrl}" alt="${data.name || '헤어스타일'}" class="preview-image" onerror="this.onerror=null; this.src='${BACKEND_BASE_URL}/static/images/placeholder.jpg';">
                <div class="preview-info">
                    <h4 class="preview-name">${data.name || '이름 없음'}</h4>
                    <p class="preview-description">${data.description || '설명 없음'}</p>
                </div>
            </div>
        `;
        hairstylePreviewArea.style.display = 'block'; // 확실히 보이도록

    } catch (error) {
        console.error("미리보기 로드 오류:", error);
        hairstylePreviewArea.innerHTML = `<p style="color: red;">미리보기를 불러오는 데 실패했습니다: ${error.message}</p>`;
        hairstylePreviewArea.style.display = 'block';
    }
});

// 상태 메시지 업데이트 함수
function setStatus(message, type) {
    statusMessage.textContent = message;
    statusMessage.className = `status ${type}`; // CSS 클래스 적용 (processing, error, success)
}


// 이미지 다운로드
function saveImage() {
    const image = document.getElementById("resultImage");
    // 이미지 소스가 유효한지 (실제 URL인지, 초기 '#'이 아닌지) 확인
    if (image && image.src && !image.src.endsWith('#') && image.style.display !== 'none') {
      const a = document.createElement("a");
      a.href = image.src;
      // 파일 이름에 타임스탬프를 넣어 중복 방지 및 최신 파일임을 알 수 있도록
      a.download = `hairithm_result_${Date.now()}.jpg`;
      document.body.appendChild(a); // 링크를 DOM에 추가해야 클릭 이벤트가 일부 브라우저에서 제대로 동작
      a.click(); // 프로그래밍 방식으로 클릭하여 다운로드 트리거
      document.body.removeChild(a); // 임시로 추가했던 링크 제거
    } else {
      alert("저장할 이미지가 없습니다. 먼저 변환을 실행해주세요.");
    }
}

document.addEventListener('DOMContentLoaded', () => {
    // 페이지 로드 시 URL 파라미터 확인
    const urlParams = new URLSearchParams(window.location.search);
    const hairstyleFromUrl = urlParams.get('hairstyle'); // 'hairstyle' 파라미터 값 가져오기

    if (hairstyleFromUrl) {
        console.log(`URL 파라미터에서 hairstyle 발견: ${hairstyleFromUrl}`); // 확인용 로그
        // 헤어스타일 선택 select 요소를 찾음 (파일 상단에 이미 변수 선언되어 있을 수 있음)
        const hairStyleSelect = document.getElementById('hairStyleSelect');
        if (hairStyleSelect) {
            // 해당 value를 가진 option이 실제로 존재하는지 확인
            const optionExists = Array.from(hairStyleSelect.options).some(option => option.value === hairstyleFromUrl);

            if (optionExists) {
                // select 요소의 값을 URL 파라미터 값으로 설정
                hairStyleSelect.value = hairstyleFromUrl;
                console.log(`드롭다운 값이 ${hairstyleFromUrl} (으)로 설정되었습니다.`);
                // 선택된 값으로 change 이벤트를 수동으로 발생시켜 미리보기를 로드
                hairStyleSelect.dispatchEvent(new Event('change'));                
            } else {
                console.warn(`URL 파라미터 값 "${hairstyleFromUrl}"에 해당하는 옵션이 드롭다운에 없습니다.`);
            }
        } else {
            console.error("헤어스타일 선택(hairStyleSelect) 요소를 찾을 수 없습니다.");
        }
    }

});