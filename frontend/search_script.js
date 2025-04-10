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
        console.error('검색 오류:', error);
        // 오류 메시지를 좀 더 구체적으로 표시
        setStatus(`검색 중 오류 발생: ${error.message}`, 'error');
        resultsContainer.innerHTML = '<p>검색 중 오류가 발생했습니다.</p>';
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
        img.src = style.image_url || 'placeholder.jpg'; // 실제 대체 이미지 경로 지정
        img.alt = style.name;
        img.onerror = () => { img.src = 'placeholder.jpg'; img.style.backgroundColor='#eee'; }; // 예: 로드 실패 시 대체 이미지

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
            ${similarStylesDescHTML}
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