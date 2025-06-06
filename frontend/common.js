//  frontend/common.js

//const BACKEND_BASE_URL = 'https://hairstyle-changer.onrender.com';
//const BACKEND_BASE_URL = 'http://127.0.0.1:5001'; // 로컬 개발용
//window.BACKEND_BASE_URL = 'http://127.0.0.1:5001'; 
window.BACKEND_BASE_URL = 'https://hairstyle-changer.onrender.com';
window.FRONTEND_URL = "https://hairstyle-changer-app.onrender.com";

/* ================== Intro Popup Logic ================== */
// (참고: 이 함수들은 index.html 에만 있는 #introPopup 요소를 찾아서 동작하므로,
//  다른 페이지에서 이 스크립트가 로드되어도 오류 없이 실행됩니다.)
function closeIntroPopup() {
    const popup = document.getElementById("introPopup");
    if (!popup) return; // 해당 ID의 요소가 없으면 함수 종료
  
    if (document.getElementById("dontShowToday")?.checked) {
      const now = new Date();
      const tomorrow = new Date(now.getFullYear(), now.getMonth(), now.getDate() + 1);
      document.cookie = `hideIntroPopup=true; path=/; expires=${tomorrow.toUTCString()}`;
    }
    popup.classList.add("hidden");
    document.body.classList.remove("popup-open");
  }
  
  function checkPopupCookie() {
    const popup = document.getElementById("introPopup");
    if (!popup) return; // 해당 ID의 요소가 없으면 함수 종료
  
    const cookies = document.cookie.split(";").map((c) => c.trim());
    const hidePopup = cookies.some((c) => c.startsWith("hideIntroPopup=true"));
  
    if (!hidePopup) {
      popup.classList.remove("hidden");
      document.body.classList.add("popup-open");
    } else {
      popup.classList.add("hidden");
      document.body.classList.remove("popup-open");
    }
  }
  // 페이지 로드 시 팝업 쿠키 확인
  // index.html 외 페이지에서는 #introPopup이 없으므로 checkPopupCookie 함수 내부에서 return됨.
  document.addEventListener("DOMContentLoaded", checkPopupCookie);
  

//이미지 리사이징 헬퍼 함수
async function resizeImageIfNeeded(file, maxWidth, maxHeight, statusCallback) { // statusCallback 인자 추가
    return new Promise((resolve, reject) => {
        if (!file.type.startsWith('image/')) {
            console.log('이미지 파일이 아니므로 리사이징하지 않습니다.');
            resolve({ resized: false, file: file }); // 객체로 결과 반환
            return;
        }

        const reader = new FileReader();
        reader.onload = (event) => {
            const img = new Image();
            img.onload = () => {
                let currentWidth = img.width;
                let currentHeight = img.height;
                let originalWidth = img.width; // 원본 크기 저장
                let originalHeight = img.height; // 원본 크기 저장
                let shouldResize = false;

                if (currentWidth > maxWidth || currentHeight > maxHeight) {
                    shouldResize = true;
                    const aspectRatio = currentWidth / currentHeight;
                    if (currentWidth > currentHeight) {
                        if (currentWidth > maxWidth) {
                            currentWidth = maxWidth;
                            currentHeight = currentWidth / aspectRatio;
                        }
                    } else {
                        if (currentHeight > maxHeight) {
                            currentHeight = maxHeight;
                            currentWidth = currentHeight * aspectRatio;
                        }
                    }
                    if (currentHeight > maxHeight) { // 두 번째 조정
                        currentHeight = maxHeight;
                        currentWidth = currentHeight * aspectRatio;
                    }
                    if (currentWidth > maxWidth) { // 두 번째 조정
                        currentWidth = maxWidth;
                        currentHeight = currentWidth / aspectRatio;
                    }
                }

                if (shouldResize) {
                    currentWidth = Math.round(currentWidth);
                    currentHeight = Math.round(currentHeight);
                    console.log(`이미지 리사이징: <span class="math-inline">\{originalWidth\}x</span>{originalHeight} -> <span class="math-inline">\{currentWidth\}x</span>{currentHeight}`);
                    if (statusCallback) { // 콜백 함수가 있으면 호출
                        statusCallback(`이미지가 너무 커서 <span class="math-inline">\{currentWidth\}x</span>{currentHeight}로 자동 조절되었습니다.`, 'info');
                    }

                    const canvas = document.createElement('canvas');
                    canvas.width = currentWidth;
                    canvas.height = currentHeight;
                    const ctx = canvas.getContext('2d');
                    ctx.drawImage(img, 0, 0, currentWidth, currentHeight);
                    let outputType = file.type;
                    let quality = 0.9;
                    if (outputType !== 'image/png' && outputType !== 'image/jpeg') {
                        outputType = 'image/jpeg';
                    }
                    if (outputType === 'image/png') quality = undefined;

                    canvas.toBlob((blob) => {
                        if (blob) {
                            const resizedFile = new File([blob], file.name, {
                                type: outputType,
                                lastModified: Date.now(),
                            });
                            console.log(`리사이징된 파일 크기: ${(resizedFile.size / 1024 / 1024).toFixed(2)} MB`);
                            resolve({ resized: true, file: resizedFile, originalWidth, originalHeight, newWidth: currentWidth, newHeight: currentHeight });
                        } else {
                            reject(new Error('Canvas to Blob 변환 실패'));
                        }
                    }, outputType, quality);
                } else {
                    console.log('이미지 크기가 적절하여 리사이징하지 않습니다.');
                    resolve({ resized: false, file: file, originalWidth, originalHeight });
                }
            };
            img.onerror = () => reject(new Error('이미지 로드 실패 (리사이징 중)'));
            img.src = event.target.result;
        };
        reader.onerror = () => reject(new Error('파일 읽기 실패'));
        reader.readAsDataURL(file);
    });
}

//URL에서 토큰 처리
function handleTokenFromUrlAndRedirect() {

    console.log('[handleTokenFromUrlAndRedirect] 함수 시작. 현재 해시:', window.location.hash);

    if (window.location.hash.startsWith('#token=')) {
        const token = window.location.hash.substring('#token='.length);
        if (token) {
            console.log('URL에서 토큰 발견, localStorage에 저장합니다.');
            localStorage.setItem('jwtToken', token); // 토큰을 localStorage에 저장
            // URL에서 토큰 정보 제거 (주소창 깔끔하게, 히스토리 추가 없이)
            /*토큰 디버깅 때문에 잠시 주석 처리
            //history.replaceState(null, null, window.location.pathname + window.location.search);
            console.log('[handleTokenFromUrlAndRedirect] URL 해시 정리 시도함.'); */
            return true; // 토큰 처리 완료
        } else {
            console.log('[handleTokenFromUrlAndRedirect] #token= 접두사는 있지만 토큰 값이 비어있음.');
        }
    }
    console.log('[handleTokenFromUrlAndRedirect] URL에서 #token= 접두사를 찾지 못했거나 해시가 없음.');
    return false; // 처리할 토큰 없음
}

//단일 DOMContentLoaded 리스너로 통합
document.addEventListener("DOMContentLoaded", () => {
    console.log("Common.js DOMContentLoaded event fired."); // 실행 확인용 로그

    //페이지 로드 시 가장 먼저 URL에서 토큰 처리 시도
    const justLoggedIn = handleTokenFromUrlAndRedirect();
    console.log('[DOMContentLoaded] handleTokenFromUrlAndRedirect 실행 결과 (justLoggedIn):', justLoggedIn);

    // 1. Intro Popup 관련 초기화
    checkPopupCookie();

    // 2. Active Nav Link Logic
    let currentPage = location.pathname.substring(location.pathname.lastIndexOf('/') + 1);
    if (currentPage === '' || currentPage === '/') {
        currentPage = 'index.html';
    }
    const navLinks = document.querySelectorAll(".navbar a");
    navLinks.forEach((link) => {
        const linkPage = link.getAttribute("href");
        if (linkPage === currentPage) {
            link.classList.add("active");
        } else {
            link.classList.remove("active");
        }
    });

    // 3. Google 로그인 로고 이미지 경로 설정 (loginModalOverlay 내부)
    const googleLoginLogoImg = document.getElementById('googleLoginLogo');
    if (googleLoginLogoImg) {
        // BACKEND_BASE_URL은 이 파일 상단에 정의되어 있어야 합니다.
        if (typeof BACKEND_BASE_URL !== 'undefined') {
            googleLoginLogoImg.src = `${BACKEND_BASE_URL}/static/images/google_logo.png`;
        } else {
            console.error("BACKEND_BASE_URL is not defined in common.js for Google logo.");
        }
    } else {
        // googleLoginLogoImg 요소가 없는 페이지에서는 이 로그가 나올 수 있습니다 (정상)
        // console.warn("Google 로그인 로고 이미지 요소를 찾을 수 없습니다. (ID: googleLoginLogo) - 현재 페이지에 로그인 모달이 없을 수 있습니다.");
    }

    // 4. Authentication UI Logic 초기화 및 이벤트 리스너 설정
    const authButton = document.getElementById('authButton');
    const authButtonContainer = document.getElementById('authButtonContainer'); // 이 변수는 fetchAuthStatusAndUpdateButton에서 사용됨
    const loginModalOverlay = document.getElementById('loginModalOverlay');
    const googleLoginButton = document.getElementById('googleLoginButton');
    const closeLoginModalButton = document.getElementById('closeLoginModalButton');

    function updateAuthButton(isLoggedIn, userData) {
      console.log('updateAuthButton 호출됨. isLoggedIn:', isLoggedIn, 'userData:', userData);
        if (!authButton) {
            // console.log('authButton 요소를 찾을 수 없음 (updateAuthButton 내부)'); // 모든 페이지에 버튼이 있으므로 이 로그는 거의 안 나옴
            return;
        }
        if (isLoggedIn && userData) {
            authButton.textContent = '로그아웃';
            authButton.dataset.isLoggedIn = 'true';
        } else {
            authButton.textContent = '로그인';
            authButton.dataset.isLoggedIn = 'false';
        }
    }

    async function fetchAuthStatusAndUpdateButton() {
        if (!authButtonContainer) {
            console.log("Auth button container not found for fetchAuthStatus.");
            return;
        }
        try {
            const token = localStorage.getItem('jwtToken'); // localStorage에서 토큰 가져오기
            const headers = {
                'Content-Type': 'application/json' // 일반적으로 API 요청 시 명시
            };
            if (token) {
                headers['Authorization'] = `Bearer ${token}`; // 토큰이 있으면 Authorization 헤더 추가
                console.log('Authorization 헤더에 토큰 포함하여 /api/auth/status 호출');
            } else {
                console.log('localStorage에 토큰 없음, /api/auth/status 호출 (토큰 없이)');
            }

            const response = await fetch(`${BACKEND_BASE_URL}/api/auth/status`, {
                method: 'GET',
                headers: headers, // 수정된 헤더 사용
                credentials: 'omit' // JWT 사용 시 쿠키는 필요 없으므로 'omit' 또는 생략 가능. 
                                     // 'include'는 CORS 설정과 함께 쿠키 전송 시 사용.
                                     // 지금은 토큰 기반이므로 'omit'으로 명확히 하거나,
                                     // 서버 CORS 설정(supports_credentials=True)과 충돌하지 않도록
                                     // 이전처럼 'include'를 유지해도 괜찮습니다. 여기서는 'omit' 시도.
                                     // 만약 다른 쿠키 기반 기능이 있다면 'include' 유지.
                                     // 안전하게 가려면 'include'로 두고 서버 설정에 의존.
                                     // 여기서는 'include'로 다시 변경 (Authlib이 OAuth state에 세션 쿠키를 사용할 수 있으므로)
                // credentials: 'include' // 이전 설정 유지 또는 필요에 따라 'omit'
            });

            if (!response.ok) {
                console.error("Auth status check failed:", response.status, await response.text());
                updateAuthButton(false, null);
                if (response.status === 401) { // 토큰 만료 또는 무효로 인한 401 Unauthorized
                    localStorage.removeItem('jwtToken'); // 잘못된 토큰 제거
                    console.log("잘못된 토큰(401) 감지, localStorage에서 토큰 제거됨.");
                }
                return;
            }
            const data = await response.json();
            console.log('/api/auth/status 응답 데이터 (common.js):', data);
            updateAuthButton(data.logged_in, data.user);
        } catch (error) {
            console.error("Error fetching auth status (common.js):", error);
            updateAuthButton(false, null);
        }
    }

    // 페이지 로드 시 또는 토큰 처리 직후에 로그인 상태 확인
    fetchAuthStatusAndUpdateButton();
    // 페이지 로드 시 즉시 로그인 상태 확인 및 버튼 업데이트
    // if (authButton) { // authButton이 있을 때만 실행 (모든 페이지에 있을 것으로 예상)
    //     fetchAuthStatusAndUpdateButton();
    // }


    // 헤더의 로그인/로그아웃 버튼 클릭 이벤트
    if (authButton) {
        authButton.addEventListener('click', async () => {
            const isLoggedIn = authButton.dataset.isLoggedIn === 'true';
            if (isLoggedIn) { // 로그아웃 버튼 클릭 시
                if (confirm("로그아웃 하시겠습니까?")) {
                    localStorage.removeItem('jwtToken'); // localStorage에서 토큰 제거
                    console.log('JWT 토큰이 localStorage에서 제거되었습니다.');
                    updateAuthButton(false, null); // UI 즉시 업데이트
                    // 백엔드 /logout은 세션 정리(이제 불필요) 및 리다이렉션만 하므로,
                    // 클라이언트 측에서 토큰 제거 후 UI 업데이트하고, 필요시 메인으로 보내거나 새로고침.
                    // 여기서는 간단히 새로고침하여 /api/auth/status 재호출 유도
                    window.location.reload();
                    // 또는 window.location.href = `${BACKEND_BASE_URL}/logout`; // 백엔드에 알리고 리다이렉트 따르기
                }
            } else { // 로그인 버튼 클릭 시
                if (loginModalOverlay) {
                    loginModalOverlay.classList.remove('hidden');
                    document.body.classList.add('popup-open');
                } else {
                    console.log("Login modal not found on this page, redirecting to Google login directly.");
                    window.location.href = `${BACKEND_BASE_URL}/login/google`;
                }
            }
        });
    }

    // Google 로그인 버튼 클릭 이벤트 (모달 내)
    if (googleLoginButton) { // 모달 내 버튼이 있을 때만 리스너 추가
        googleLoginButton.addEventListener('click', () => {
            window.location.href = `${BACKEND_BASE_URL}/login/google`;
        });
    }

    // 로그인 모달 닫기 버튼 클릭 이벤트 (모달 내)
    if (closeLoginModalButton) { // 모달 내 버튼이 있을 때만 리스너 추가
        closeLoginModalButton.addEventListener('click', () => {
            if (loginModalOverlay) {
                loginModalOverlay.classList.add('hidden');
                document.body.classList.remove('popup-open');
            }
        });
    }
});