# 폐렴 예측 Worker 이미지
#
# torch/torchvision 이 크므로 requirements.txt 를 먼저 복사해
# 코드가 바뀌어도 설치 단계를 캐시에서 재사용하게 한다.

FROM python:3.13-slim

WORKDIR /app

# torch 는 CPU 전용 휠을 쓴다. 기본 인덱스의 CUDA 포함 버전은 수 GB에 달한다.
COPY worker/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir \
    --extra-index-url https://download.pytorch.org/whl/cpu \
    -r requirements.txt

# 코드만 복사한다. 모델 파일(worker/models)은 용량이 커서
# .dockerignore 로 제외하고 볼륨으로 연결한다.
COPY worker ./worker

# -u: 출력 버퍼링을 꺼서 print 로그가 컨테이너 로그에 즉시 보이게 한다.
CMD ["python", "-u", "-m", "worker.main"]
