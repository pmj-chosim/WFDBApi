# 공식 Python 3.11 이미지 사용
FROM python:3.11

# 작업 디렉토리 설정
WORKDIR /app

# 종속성 설치
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Flask 코드 복사
COPY . .

# 컨테이너 실행 시 Flask 서버 시작
CMD ["python", "server.py"]
