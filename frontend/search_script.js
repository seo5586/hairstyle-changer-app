const BACKEND_BASE_URL = 'http://127.0.0.1:5001'; // Flask 서버 주소 및 포트
const searchInput = document.getElementById('searchInput');
const searchButton = document.getElementById('searchButton');
const resultsContainer = document.getElementById('results');
const statusMessage = document.getElementById('statusMessage');

// 검색 실행 함수
async function performSearch() {
    const query = searchInput.value.trim();
    // 검색어가 없어도 일단 API 호출 (백엔드에서 빈 결과 반환)
    // if (!query) { ... }

    setStatus('검색 중...', 'processing');
    resultsContainer.innerHTML = ''; // 이전 결과 지우기

    try {
        // fetch URL을 절대 경로로 수정
        const response = await fetch(`${BACKEND_BASE_URL}/api/search-hairstyles?q=${encodeURIComponent(query)}`); 

        if (!response.ok) {
            // 오류 처리를 위해 응답 내용을 확인하려 시도
            let errorMsg = `HTTP 오류: ${response.status}`;
            try {
                const errorData = await response.json();
                errorMsg = errorData.error || errorMsg; // 백엔드에서 보낸 에러 메시지 사용
            } catch (e) {
                // JSON 파싱 실패 시 무시
            }
            throw new Error(errorMsg);
        }

        const data = await response.json();

        if (data.results && data.results.length > 0) {
            setStatus(query ? `'${query}'에 대한 ${data.results.length}개의 검색 결과를 찾았습니다.` : '헤어스타일 목록', 'success');
            displayResults(data.results);
        } else {
            setStatus(query ? `'${query}'에 대한 검색 결과가 없습니다.` : '표시할 헤어스타일이 없습니다.', 'info');
            resultsContainer.innerHTML = '<p>검색 결과가 없습니다.</p>';
        }

    } catch (error) {
        console.error('상세 오류 (헤어스타일 검색):', error); // 디버깅용 상세 오류 출력

        let userMessage = "검색 중 예상치 못한 오류가 발생했습니다. 잠시 후 다시 시도해주세요."; // 기본 메시지

        if (error.message) {
            const msg = error.message.toLowerCase();

            // search_script.js에서는 사용자 입력 오류보다는 서버/네트워크 오류가 주를 이룰 것으로 예상됨
            if (msg.includes("http 오류") || msg.includes("서버 응답 오류") || msg.includes("서버 내부 오류")) {
                 userMessage = "검색 서버와 통신 중 오류가 발생했습니다. 잠시 후 다시 시도해주세요.";
            } else if (msg.includes("failed to fetch")) { // 네트워크 연결 실패
                 userMessage = "검색 서버에 연결할 수 없습니다. 네트워크 상태를 확인해주세요.";
            }
            // 필요에 따라 다른 특정 오류 메시지에 대한 처리 추가 가능
        }

        setStatus(userMessage, 'error');
        // 오류 발생 시 검색 결과 영역도 비워주는 것이 좋을 수 있습니다.
        resultsContainer.innerHTML = `<p>${userMessage}</p>`; // 결과 영역에도 메시지 표시 (선택 사항)
    }
}

// 가격을 원화 형식으로 포맷하고, null 또는 유효하지 않은 경우 처리하는 함수
function formatPrice(price) {
    // price가 null, undefined 또는 숫자가 아니면 "정보 없음" 반환
    if (price === null || price === undefined || isNaN(price)) {
        return '정보 없음';
    }
    // 숫자인 경우, 한국 원화 형식(쉼표 포함)으로 변환하고 '원' 붙이기
    try {
        // price를 숫자로 변환 시도 (문자열로 올 수도 있으므로)
        const numericPrice = Number(price);
        if (isNaN(numericPrice)) {
            return '정보 없음'; // 숫자로 변환 실패 시
        }
        return `${numericPrice.toLocaleString('ko-KR')}원`;
    } catch (e) {
        console.error("Error formatting price:", price, e);
        return '정보 없음'; // 포맷팅 중 오류 발생 시
    }
}

// 검색 결과를 화면에 표시하는 함수
function displayResults(results) {
    resultsContainer.innerHTML = ''; // 결과 영역 초기화
    results.forEach(style => {
        const item = document.createElement('div');
        item.classList.add('result-item');

        const img = document.createElement('img');
        // 이미지 URL이 없거나 로드 실패 시 대체 처리 필요
        //img.src = style.image_url || 'placeholder.jpg'; // 실제 대체 이미지 경로 지정
        img.alt = style.name;
        // DB에서 받은 image_url (상대 경로) 앞에 백엔드 주소를 붙여 절대 URL 생성
        // DB 값이 null이거나 없을 경우 placeholder 절대 URL 사용
        const imageUrlFromDB = style.image_url;
        const placeholderUrl = `${BACKEND_BASE_URL}/static/images/placeholder.jpg`;

        // DB URL이 유효한 경우 (null 아니고 /static/으로 시작 가정) 전체 URL 생성, 아니면 placeholder URL 사용
        img.src = (imageUrlFromDB && imageUrlFromDB.startsWith('/static/'))
                    ? `${BACKEND_BASE_URL}${imageUrlFromDB}`
                    : placeholderUrl;        

        img.onerror = () => {
            // 이미지 로드 실패 시, 올바른 절대 경로의 placeholder 이미지로 설정
            console.warn(`이미지 로드 실패: ${img.src}. Placeholder 이미지로 대체합니다.`); // 실패 로그 추가
            img.src = placeholderUrl; // <<< 상대 경로 대신 절대 경로 사용
            img.style.backgroundColor='#eee'; // 배경색 유지
        };

        const info = document.createElement('div');
        info.classList.add('info');

        let similarStylesDescHTML = ''; // 표시할 HTML 문자열 초기화
        // similar_styles_description 필드에 내용이 있을 경우에만 p 태그 생성
        if (style.similar_styles_description) {
            similarStylesDescHTML = `<p class="similar-desc"><b>유사 스타일 예시:</b> ${style.similar_styles_description}</p>`;
        }

        info.innerHTML = `
            <h3>${style.name}</h3>
            <p>${style.description || '설명 없음'}</p>
            <p class="price">일반가: ${formatPrice(style.normal_price)}</p>
            <p class="price">브랜드가: ${formatPrice(style.brand_price)}</p>
            ${style.similar_styles_description ? `<p class="similar-desc">유사 스타일: ${style.similar_styles_description}</p>` : ''}
        `;
        item.appendChild(img);
        item.appendChild(info);
        resultsContainer.appendChild(item);
    });
}

// 검색 버튼 클릭 시 검색 실행
searchButton.addEventListener('click', performSearch);

// 엔터 키 입력 시 검색 실행
searchInput.addEventListener('keypress', function(event) {
    if (event.key === 'Enter') {
        performSearch();
    }
});

// 상태 메시지 업데이트 함수 (필요시 정의)
function setStatus(message, type) {
    statusMessage.textContent = message;
    statusMessage.className = `status ${type}`;
}

// 초기 로드 시 빈 검색어로 검색 실행하여 전체 목록 표시 (선택사항)
// performSearch();