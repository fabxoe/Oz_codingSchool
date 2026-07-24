# pneumonia_ensemble_v1 테스트 이미지

FastAPI 화면과 `pneumonia_ensemble_v1` 추론 동작을 확인하기 위한 흉부 X-ray 10장이다.

## 구성

- `normal_*.png`: 정답 NORMAL 5장
- `pneumonia_*.png`: 정답 PNEUMONIA 5장
- `samples_manifest.csv`: 원본 파일명, 정답, OOF 확률, 난이도 구분
- `service_predictions.csv`: 현재 서비스 추론 코드로 검증한 실제 출력

각 클래스는 다음 사례를 포함한다.

- `high`: 모델이 비교적 명확하게 구분한 사례
- `moderate`: 중간 수준의 확신을 보인 사례
- `boundary`: 상대적으로 경계에 가까운 사례

10장 모두 현재 서비스 추론에서 정답과 일치하는 것을 확인했다.

## 사용

웹 화면에서 진료 기록을 등록할 때 원하는 PNG 파일을 X-ray 이미지로 업로드한 후 AI 예측을 실행한다.

파일명의 `normal` 또는 `pneumonia` 부분은 테스트 정답 확인을 위한 표시일 뿐이며, 모델 추론 코드에서는 파일명을 사용하지 않는다.

이 샘플은 공개 해커톤 학습 데이터에서 가져온 기능 검증용 자료다. 실제 의료 진단이나 임상 성능 검증 용도로 사용하면 안 된다.
