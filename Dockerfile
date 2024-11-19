# Python 베이스 이미지 사용
FROM python:3.9-slim

# 작업 디렉터리 설정
WORKDIR /app

# 현재 디렉터리의 파일들을 컨테이너의 /app 으로 복사
COPY . /app

# 필요한 패키지 설치
RUN pip install --no-cache-dir -r requirements.txt

# 컨테이너 외부에 노출할 포트 설정
EXPOSE 5000

# 환경변수 설정
ENV FLASK_APP=app.py
ENV FLASK_ENV=development

# 컨테이너 실행 시 실행할 명령어
CMD ["flask", "run", "--host=0.0.0.0"]