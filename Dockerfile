FROM python:3.12-slim

WORKDIR /app

# 의존성 설치 (requirements.txt에 ccxt, python-dotenv만 있음)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 전체 코드 복사
COPY . .

# 로그와 .env를 호스트에서 마운트할 수 있게 준비
VOLUME ["/app/logs"]

# 실행 명령 (사용자가 .env를 마운트해야 함)
ENTRYPOINT ["python", "bot_manager.py"]
CMD ["start", "all"]
