let map; // 지도 객체 변수
let service; // PlacesService 객체 변수
let infowindow; // 정보창 객체 변수
const statusMessage = document.getElementById('statusMessage');
const salonListContainer = document.getElementById('salonList');
let markers = {}; // 마커들을 place_id 기준으로 저장할 객체
let nearbySearchResults = []; // nearbySearch 결과 저장
const BACKEND_BASE_URL = 'http://127.0.0.1:5001'; // Flask 서버 주소

// Google Maps API 로드 완료 후 호출될 초기화 함수
function initMap() {
    setStatus('현재 위치를 찾는 중...', 'processing');
    //초기화
    markers = {};
    nearbySearchResults = [];
    if (salonListContainer) {
        salonListContainer.innerHTML = '<p>현재 위치를 찾는 중...</p>'; // 목록 초기화
    }

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
    if (!service) service = new google.maps.places.PlacesService(map);

    //목록 초기화
    if (salonListContainer) {
        salonListContainer.innerHTML = '<p>주변 미용실을 검색 중입니다...</p>';
   }
   clearMarkers(); // 기존 마커/목록 관련 변수 초기화 함수 호출 (아래 정의)

    // nearbySearch 콜백 함수
    service.nearbySearch(request, (results, status) => {
        if (status === google.maps.places.PlacesServiceStatus.OK && results && results.length > 0) {
            // 검색 성공 및 결과 있음
            setStatus(`주변 ${results.length}개의 미용실을 찾았습니다.`, 'success');
            nearbySearchResults = results;      // 검색 결과 저장
            displaySalonList(results);        // 목록 UI 생성 함수 호출
            fetchDetailsForAllSalons(results); // 모든 결과에 대한 상세 정보 요청 함수 호출
        } else if (status === google.maps.places.PlacesServiceStatus.ZERO_RESULTS) {
            // 검색 성공했으나 결과 없음
            setStatus('주변에 검색된 미용실이 없습니다.', 'info');
            if (salonListContainer) salonListContainer.innerHTML = '<p>주변에 검색된 미용실이 없습니다.</p>';
        } else {
            // 검색 중 오류 발생
            setStatus('주변 장소 검색 중 오류가 발생했습니다.', 'error');
            console.error("PlacesService nearbySearch failed: " + status);
            if (salonListContainer) salonListContainer.innerHTML = '<p>검색 중 오류가 발생했습니다.</p>';
        }
    });
}

//목록 표시 함수
function displaySalonList(results) {
    if (!salonListContainer) return;
    salonListContainer.innerHTML = ''; // 이전 목록 지우기

    results.forEach(place => {
        const listItem = document.createElement('div');
        listItem.classList.add('salon-list-item'); // CSS 클래스 적용 (flex container 역할)
        listItem.dataset.placeId = place.place_id;
        listItem.style.cursor = 'pointer';

        // 1. 텍스트 정보를 담을 div (왼쪽)
        const textInfoDiv = document.createElement('div');
        textInfoDiv.classList.add('salon-item-text-content'); // 텍스트 정보 영역 클래스
        textInfoDiv.innerHTML = `
            <h3>${place.name || '이름 정보 없음'}</h3>
            <div class="salon-details-specifics" data-place-id-details="${place.place_id}">
                <p class="loading-details">상세 정보 로딩 중...</p>
            </div>
        `;

        // 2. 이미지를 담을 img 태그 (오른쪽)
        const photoImg = document.createElement('img');
        photoImg.classList.add('salon-photo'); // CSS 클래스 적용
        // 초기에는 placeholder 이미지, 상세 정보 로드 시 실제 이미지로 변경됨
        photoImg.src = `${BACKEND_BASE_URL}/static/images/placeholder.jpg`;
        photoImg.alt = `${place.name || '미용실'} 사진`;
        photoImg.onerror = () => { // placeholder도 실패할 경우 대비
            if (photoImg.src !== `${BACKEND_BASE_URL}/static/images/placeholder.jpg`) {
                 photoImg.src = `${BACKEND_BASE_URL}/static/images/placeholder.jpg`;
            }
            photoImg.style.backgroundColor='#e0e0e0'; // onerror 시 배경색
        };


        listItem.appendChild(textInfoDiv); // 텍스트 정보 먼저 추가
        listItem.appendChild(photoImg);    // 그 다음 이미지 추가

        // 목록 아이템 클릭 시 지도 마커의 정보창 열기 (기존 로직 유지)
        listItem.addEventListener('click', () => {
            const marker = markers[place.place_id];
            if (marker) {
                if (marker.detailedInfoLoaded) {
                     infowindow.setContent(marker.infoWindowContent || '상세 정보 로딩 중...');
                     infowindow.open(map, marker);
                     map.panTo(marker.getPosition());
                } else {
                    infowindow.setContent('상세 정보 로딩 중...');
                    infowindow.open(map, marker);
                    map.panTo(marker.getPosition());
                    getPlaceDetails(place.place_id); // 상세 정보 요청
                }
            }
        });

        salonListContainer.appendChild(listItem);
        createMarker(place);
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

    //마커 객체 저장 및 상태 추가
    marker.placeId = place.place_id; // place_id 마커에 저장
    marker.detailedInfoLoaded = false; // 상세 정보 로드 상태
    marker.infoWindowContent = '상세 정보 로딩 중...'; // 정보창 초기 내용
    markers[place.place_id] = marker; // 전역 markers 객체에 저장

    google.maps.event.addListener(marker, "click", () => {
        if (marker.detailedInfoLoaded) {
            infowindow.setContent(marker.infoWindowContent);
            infowindow.open(map, marker);
        } else {
            // 아직 로드되지 않았다면 로딩 메시지 표시 후 상세 정보 요청
            infowindow.setContent('상세 정보 로딩 중...');
            infowindow.open(map, marker);
            getPlaceDetails(marker.placeId); // 상세 정보 요청 함수 호출
        }
        map.panTo(marker.getPosition()); // 클릭한 마커로 지도 이동
    });
}

//상세 정보 조회 함수
function getPlaceDetails(placeId) {
    if (!service) service = new google.maps.places.PlacesService(map);
    const fields = [
        'place_id', 'name', 'formatted_address', 'formatted_phone_number',
        'rating', 'opening_hours', 'geometry',
        'photos'
    ];
    service.getDetails({ placeId: placeId, fields: fields }, (placeDetails, status) => {
        if (status === google.maps.places.PlacesServiceStatus.OK && placeDetails) {
            // 상세 정보 로드 성공 시
            updateListItem(placeDetails); // 목록 아이템 업데이트 함수 호출
            updateMarkerInfoWindow(placeDetails); // 마커 정보창 내용 업데이트 함수 호출
        } else {
            console.error(`Place Details request failed for ${placeId}: ${status}`);
            // 상세 정보 로드 실패 처리 (목록 아이템에 실패 메시지 표시 등)
            const listItem = salonListContainer.querySelector(`[data-place-id="${placeId}"]`);
            if (listItem) {
                const loadingIndicator = listItem.querySelector('.loading-details');
                if(loadingIndicator) loadingIndicator.textContent = '상세 정보 로드 실패';
            }
            // 마커 정보창도 실패 처리
             const marker = markers[placeId];
             if (marker) {
                 marker.infoWindowContent = '상세 정보를 불러올 수 없습니다.';
                 // 만약 현재 이 마커의 정보창이 열려있다면 내용 업데이트
                 if (infowindow.getAnchor() === marker) {
                     infowindow.setContent(marker.infoWindowContent);
                 }
             }
        }
    });
}

//목록 아이템 업데이트 함수
function updateListItem(details) {
    const listItem = salonListContainer.querySelector(`[data-place-id="${details.place_id}"]`);
    if (!listItem) return;

    // 1. 사진 업데이트
    const photoImg = listItem.querySelector('.salon-photo'); // displaySalonList에서 생성한 img 태그
    if (photoImg) {
        if (details.photos && details.photos.length > 0) {
            photoImg.src = details.photos[0].getUrl({'maxWidth': 200, 'maxHeight': 200}); // 고화질 요청
            photoImg.alt = `${details.name || '미용실'} 사진`;
        } else {
            photoImg.src = `${BACKEND_BASE_URL}/static/images/placeholder.jpg`; // 사진 없으면 placeholder
            photoImg.alt = '미용실 사진 없음';
        }
        // onerror는 displaySalonList에서 이미 설정됨
    }

    // 2. 텍스트 상세 정보 업데이트
    //    (주의: detailsDiv -> detailsSpecificsDiv 로 변경, 위 displaySalonList 함수와 맞춰야 함)
    const detailsSpecificsDiv = listItem.querySelector(`.salon-details-specifics[data-place-id-details="${details.place_id}"]`);
    const loadingIndicator = listItem.querySelector('.loading-details'); // loadingIndicator는 detailsSpecificsDiv 안에 있음

    if (detailsSpecificsDiv) {
        let detailsHtml = `<p>${details.formatted_address || '주소 정보 없음'}</p>`;
        detailsHtml += `<p>${details.formatted_phone_number ? `<a href="tel:${details.formatted_phone_number}">${details.formatted_phone_number}</a>` : '전화번호 정보 없음'}</p>`;

        if (details.rating) {
            detailsHtml += `<p><strong>★ ${details.rating.toFixed(1)}</strong></p>`;
        } else {
            detailsHtml += `<p>별점 정보 없음</p>`;
        }

        let hoursHtml = '';
        let statusHtml = '<p><span class="salon-status">영업 상태 정보 없음</span></p>';
        if (details.opening_hours) {
            if (details.opening_hours.weekday_text) {
                hoursHtml = `<div class="salon-hours"><strong>영업 시간:</strong><br>${details.opening_hours.weekday_text.join('<br>')}</div>`;
            }
            if (details.opening_hours.open_now !== undefined) {
                const isOpen = details.opening_hours.open_now;
                statusHtml = `<p><span class="salon-status ${isOpen ? 'open' : 'closed'}">${isOpen ? '영업 중' : '영업 종료'}</span></p>`;
            }
        }
        detailsHtml += statusHtml;
        detailsHtml += hoursHtml;

        detailsSpecificsDiv.innerHTML = detailsHtml; // 상세 정보 텍스트 영역에 내용 채우기
        if (loadingIndicator) {
            loadingIndicator.style.display = 'none'; // 로딩 메시지 숨기기
        }
    }
}

//마커 정보창 업데이트 함수
function updateMarkerInfoWindow(details) {
    const marker = markers[details.place_id];
    if (!marker) return;

    let content = `<strong>${details.name}</strong>`;
    if (details.formatted_address) content += `<br>${details.formatted_address}`;
    if (details.formatted_phone_number) content += `<br>📞 <a href="tel:${details.formatted_phone_number}">${details.formatted_phone_number}</a>`;
    if (details.rating) content += `<br>★ ${details.rating.toFixed(1)}`;
    if (details.opening_hours && details.opening_hours.open_now !== undefined) {
         content += `<br><span class="salon-status ${details.opening_hours.open_now ? 'open' : 'closed'}">${details.opening_hours.open_now ? '영업 중' : '영업 종료'}</span>`;
    }

    marker.infoWindowContent = content; // 마커에 정보 저장
    marker.detailedInfoLoaded = true; // 로드 완료 상태로 변경

    // 만약 현재 이 마커의 정보창이 열려있다면 내용 업데이트
    if (infowindow.getAnchor() === marker) {
        infowindow.setContent(content);
    }
}

//상세 정보 일괄 요청 함수
function fetchDetailsForAllSalons(results) {
    results.forEach(place => {
        // 각 장소에 대해 상세 정보 요청 (API 호출 부하 주의)
        // 약간의 지연(setTimeout)을 두어 한꺼번에 너무 많은 요청 방지 (선택 사항)
        setTimeout(() => {
           getPlaceDetails(place.place_id);
        }, Math.random() * 500); // 0~0.5초 사이 랜덤 지연
    });
}

//마커 및 목록 초기화 함수
function clearMarkers() {
    for (const placeId in markers) {
        if (markers.hasOwnProperty(placeId)) {
            markers[placeId].setMap(null); // 지도에서 마커 제거
        }
    }
    markers = {}; // 마커 객체 초기화
    nearbySearchResults = []; // 검색 결과 초기화
    if (salonListContainer) salonListContainer.innerHTML = ''; // 목록 초기화
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
    //목록 초기화
    if (salonListContainer) {
        salonListContainer.innerHTML = '<p>기본 위치(서울 시청) 기준으로 표시합니다. 위치 권한을 확인해주세요.</p>';
    }
    clearMarkers();
}

// 상태 메시지 업데이트 함수
function setStatus(message, type) {
    statusMessage.textContent = message;
    statusMessage.className = `status ${type}`;
}

// initMap 함수를 전역 스코프에 노출 (Google API 콜백용)
window.initMap = initMap;