=== QMS Server 성능 최적화 가이드 ===

📋 배포 파일:
1. modules/mcp/gpt4all_routes.py (성능 타이밍 로그 추가)
2. modules/mcp/gpt4all_client.py (성능 타이밍 로그 추가)
3. optimize_server.sh (서버 최적화 스크립트)

📌 배포 단계:

## 1️⃣ Windows에서 Linux 서버로 파일 전송

# 파일 3개 전송
scp modules/mcp/gpt4all_routes.py ronnie@RSCH5:/home/ronnie/ADD_LLM/modules/mcp/
scp modules/mcp/gpt4all_client.py ronnie@RSCH5:/home/ronnie/ADD_LLM/modules/mcp/
scp optimize_server.sh ronnie@RSCH5:/home/ronnie/

---

## 2️⃣ Linux 서버에서 최적화 실행

ssh ronnie@RSCH5

# 스크립트 실행 권한 설정
chmod +x ~/optimize_server.sh

# 최적화 실행
bash ~/optimize_server.sh

---

## 3️⃣ 성능 테스트 (로그 보면서)

# 터미널 1: 로그 모니터링
ssh ronnie@RSCH5
tail -f ~/ADD_LLM/server.log | grep -E "PERF|Test|Chat"

# 터미널 2: 테스트 실행
for i in {1..3}; do
  echo "=== Test $i ==="
  time curl -X POST http://localhost:8000/gpt4all/chat/test \
    -H "Content-Type: application/json" \
    -d '{"message": "hi"}' -s | head -c 100
  sleep 2
done

---

## 📊 예상 성능 개선:

Before (reload mode + 중복 uvicorn)
  - 응답 시간: 5-10초 이상
  - CPU: 398% x 2 processes
  - 메모리: 6GB+

After (최적화됨)
  - 응답 시간: 1-3초 예상
  - CPU: 단일 프로세스
  - 메모리: 4-5GB

---

## 🔍 로그 해석:

[PERF] Chat init: XXXms
  → 채팅 초기화 시간

[PERF] LLM generation: XXXms
  → 모델 응답 생성 시간

[PERF] RAG context build: XXXms
  → RAG 검색 시간 (이게 크면 RAG가 병목)

[Test] Total time: XXXs
  → 전체 응답 시간

---

## ⚠️ 만약 여전히 느리면:

1. RAG 비활성화 테스트:
   curl ... -d '{"message": "hi", "use_rag": false}'

2. 모델 크기 확인:
   ls -lh /home/ronnie/LLM/models/*.gguf

3. 더 작은 Q4 모델 고려:
   - 현재: Meta-Llama-3-8B (5.4GB)
   - 대체: TinyLlama-1.1B 또는 Mistral-7B-Q4
