let map; // 지도 객체 변수
let service; // PlacesService 객체 변수
let infowindow; // 정보창 객체 변수
const statusMessage = document.getElementById('statusMessage');

// Google Maps API 로드 완료 후 호출될 초기화 함수
function initMap() {
    setStatus('현재 위치를 찾는 중...', 'processing');

    // HTML5 Geolocation API를 사용하여 현재 위치 얻기
    if (navigator.geolocation) {
        navigator.geolocation.getCurrentPosition(
            (position) => {
                // 위치 얻기 성공
                const userLocation = {
                    lat: position.coords.latitude,
                    lng: position.coords.longitude
                };
                setStatus('지도 표시 및 주변 미용실 검색 중...', 'processing');

                // 사용자의 현재 위치를 중심으로 지도 생성
                map = new google.maps.Map(document.getElementById("map"), {
                    center: userLocation,
                    zoom: 15, // 확대 수준 (숫자가 클수록 확대)
                });

                // 사용자 위치에 마커 추가
                new google.maps.Marker({
                    position: userLocation,
                    map: map,
                    title: "내 위치",
                    icon: { // 파란색 원 모양 아이콘 (선택사항)
                        path: google.maps.SymbolPath.CIRCLE,
                        scale: 8,
                        fillColor: "#4285F4",
                        fillOpacity: 1,
                        strokeWeight: 0
                      }
                });

                // 정보창 객체 초기화
                infowindow = new google.maps.InfoWindow();

                // 주변 미용실 검색 함수 호출
                searchNearbySalons(userLocation);
            },
            () => {
                // 위치 얻기 실패 또는 권한 거부
                handleLocationError(true);
            }
        );
    } else {
        // 브라우저가 Geolocation을 지원하지 않음
        handleLocationError(false);
    }
}

// 주변 미용실 검색 함수
function searchNearbySalons(location) {
    const request = {
        location: location,
        radius: 1500, // 숫자 타입 유지 (또는 작동했던 '1500' 문자열)
        // type: ['hair_care'], // 주석 처리 유지
        keyword: '미용실'
    };

    service = new google.maps.places.PlacesService(map);
    // nearbySearch 콜백 함수
    service.nearbySearch(request, (results, status) => {
        if (status === google.maps.places.PlacesServiceStatus.OK && results) {
            setStatus(`주변 ${results.length}개의 미용실을 찾았습니다. 지도에서 마커를 클릭하세요.`, 'success'); // 상태 메시지 업데이트

            // 검색된 각 장소에 대해 마커 생성만 수행
            for (let i = 0; i < results.length; i++) {
                createMarker(results[i]);
            }

        } else if (status === google.maps.places.PlacesServiceStatus.ZERO_RESULTS) {
            setStatus('주변에 검색된 미용실이 없습니다.', 'info');
        } else {
            setStatus('주변 장소 검색 중 오류가 발생했습니다.', 'error');
            console.error("PlacesService failed: " + status);
        }
    });
}


// === 지도에 마커 생성 및 클릭 시 상세 정보 요청 함수 ===
function createMarker(place) {
    if (!place.geometry || !place.geometry.location || !place.place_id) {
        // place_id가 없으면 상세 정보를 가져올 수 없으므로 마커 생성 중단 또는 기본 정보만 표시
        console.warn("장소 정보가 불완전하여 마커를 생성할 수 없습니다:", place.name);
        return;
    }

    const marker = new google.maps.Marker({
        map: map,
        position: place.geometry.location,
        title: place.name
        // placeId: place.place_id // 마커와 장소를 연결하기 위한 ID 저장 (선택사항)
    });

    google.maps.event.addListener(marker, "click", () => {
        // 정보창에 로딩 메시지 우선 표시
        infowindow.setContent(`<strong>${place.name}</strong><br>상세 정보 로딩 중...`);
        infowindow.open(map, marker);

        // Place Details 요청 객체 생성
        const detailsRequest = {
            placeId: place.place_id, // 해당 장소의 고유 ID
            // 필요한 필드 명시 (필수! 비용 및 할당량 관리, 원하는 정보만 요청)
            fields: ['name', 'formatted_phone_number', 'vicinity', 'geometry'] // 이름, 전화번호, 주변 주소, 위치
            // 필요에 따라 'website', 'opening_hours', 'rating' 등 추가 가능
        };

        // getDetails 요청 보내기
        service.getDetails(detailsRequest, (placeDetails, status) => {
            if (status === google.maps.places.PlacesServiceStatus.OK && placeDetails) {
                // 성공 시 정보창 내용 업데이트
                let content = `<strong>${placeDetails.name}</strong>`;
                if (placeDetails.vicinity) {
                    content += `<br>${placeDetails.vicinity}`;
                }
                // 전화번호가 있으면 추가
                if (placeDetails.formatted_phone_number) {
                    content += `<br>📞 <a href="tel:${placeDetails.formatted_phone_number}">${placeDetails.formatted_phone_number}</a>`; // 전화 걸기 링크 추가
                } else {
                    content += `<br>전화번호 정보 없음`;
                }
                // 다른 정보(website 등) 필요 시 여기에 추가

                infowindow.setContent(content); // 업데이트된 내용으로 정보창 설정
                // 이미 열려있는 정보창의 내용을 갱신 (다시 open() 호출)
                infowindow.open(map, marker);

            } else {
                // getDetails 실패 시 오류 메시지 표시
                console.error("Place Details request failed: " + status);
                infowindow.setContent(`<strong>${place.name}</strong><br>상세 정보를 불러오는 데 실패했습니다.`);
                infowindow.open(map, marker);
            }
        });
    });
}

// 위치 정보 오류 처리 함수
function handleLocationError(browserHasGeolocation) {
    const errorMessage = browserHasGeolocation
        ? "위치 정보 접근 권한이 없거나 현재 위치를 찾을 수 없습니다. 기본 위치로 지도를 표시합니다."
        : "오류: 사용 중인 브라우저가 위치 정보 기능을 지원하지 않습니다.";

    setStatus(errorMessage, 'error');
    console.error(errorMessage);

    // 기본 위치 설정 (예: 서울 시청) 및 지도 표시
    const defaultLocation = { lat: 37.5665, lng: 126.9780 };
    map = new google.maps.Map(document.getElementById("map"), {
        center: defaultLocation,
        zoom: 14,
    });
    // 기본 위치 주변 검색 (선택사항)
    // searchNearbySalons(defaultLocation);
}

// 상태 메시지 업데이트 함수
function setStatus(message, type) {
    statusMessage.textContent = message;
    statusMessage.className = `status ${type}`;
}

// initMap 함수를 전역 스코프에 노출 (Google API 콜백용)
window.initMap = initMap;