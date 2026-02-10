#!/bin/bash

# Rocky Linux 8.10 서버에서 uvicorn 재시작 및 성능 테스트
# 사용법: ./restart_and_test.sh [port]

PORT=${1:-8000}
APP_DIR="/home/ronnie/ADD_LLM"
LOG_FILE="$APP_DIR/server.log"

echo "=========================================="
echo "uvicorn 재시작 및 성능 테스트"
echo "=========================================="
echo "Port: $PORT"
echo "App Dir: $APP_DIR"
echo "Log: $LOG_FILE"
echo ""

# 기존 프로세스 확인
echo "[1/5] 기존 uvicorn 프로세스 확인..."
if pgrep -f "uvicorn.*app:app" > /dev/null; then
    echo "✓ 기존 프로세스 발견, 종료 중..."
    pkill -f "uvicorn.*app:app"
    sleep 2
    echo "✓ 프로세스 종료됨"
else
    echo "✓ 기존 프로세스 없음"
fi

echo ""
echo "[2/5] 디렉토리 확인..."
if [ ! -d "$APP_DIR" ]; then
    echo "[ERROR] 디렉토리 없음: $APP_DIR"
    exit 1
fi
echo "✓ $APP_DIR 존재"

echo ""
echo "[3/5] 새 서버 시작..."
cd "$APP_DIR"

# Uvicorn 시작 (백그라운드)
nohup python3 -m uvicorn app:app \
    --host 127.0.0.1 \
    --port $PORT \
    --workers 1 \
    > "$LOG_FILE" 2>&1 &

UVICORN_PID=$!
echo "✓ uvicorn 시작됨 (PID: $UVICORN_PID)"

# 서버 시작 대기
echo ""
echo "[4/5] 서버 초기화 대기 (5초)..."
sleep 5

# 포트 확인
if lsof -Pi :$PORT -sTCP:LISTEN -t >/dev/null 2>&1; then
    echo "✓ 포트 $PORT에서 서비스 중"
else
    echo "[WARNING] 포트 $PORT에서 서비스 감지 불가"
    echo "로그 확인:"
    tail -20 "$LOG_FILE"
    exit 1
fi

echo ""
echo "[5/5] 성능 테스트..."
echo ""
echo "테스트 1: 기본 Hello 메시지 (빠른 응답)"
echo "---"
time curl -s -X POST http://localhost:$PORT/gpt4all/chat/test \
    -H "Content-Type: application/json" \
    -d '{"message": "hi"}' | head -50
echo ""

echo "테스트 2: 일반 쿼리 (5-12초 예상)"
echo "---"
time curl -s -X POST http://localhost:$PORT/gpt4all/chat/test \
    -H "Content-Type: application/json" \
    -d '{"message": "What is 2+2?"}' | head -50

echo ""
echo ""
echo "=========================================="
echo "✓ 테스트 완료!"
echo "=========================================="
echo ""
echo "성능 지표 확인:"
echo "  CPU 사용률: top -p $UVICORN_PID"
echo "  메모리: ps aux | grep uvicorn"
echo "  응답 시간: 로그 또는 test endpoin 사용"
echo ""
echo "예상 성능:"
echo "  - 응답 시간: 5-12초 (개선 전: 60+ 초)"
echo "  - CPU: 40-80% (개선 전: 1-2%)"
echo "  - Tokens/sec: 10-20 (개선 전: 0.3-0.8)"
echo ""
echo "로그 실시간 모니터링:"
echo "  tail -f $LOG_FILE"
echo ""
echo "서버 중지:"
echo "  kill $UVICORN_PID"
echo ""
