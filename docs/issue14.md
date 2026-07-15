### app/services/

비즈니스 로직을 작성하는 영역이다. API 계층은 요청을 받고 응답을 반환하는 역할에 집중하고, 실제 처리 규칙은 service 계층에 둔다.

예를 들어 회원 가입 시 이메일 중복 확인, 비밀번호 해싱, 권한 기본값 설정 같은 로직은 service에서 처리할 수 있다.

### app/apis/

FastAPI 라우터와 엔드포인트를 작성하는 영역이다. 클라이언트가 호출하는 URL, HTTP method, request body, response model을 정의한다.

예를 들어 `GET /practice_api/users` 같은 엔드포인트를 `APIRouter`로 작성하고, `app/main.py`에서 등록한다.
