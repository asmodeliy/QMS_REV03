=== QMS LLM 성능 복구 계획 ===

📊 문제 진단:
✓ CPU: Ryzen 9 5950X (충분)
✓ RAM: 125GB (충분)  
✓ 모델: Llama-3-8B Q5_K_M (적절)
❌ 원인: llama.cpp가 CPU 최적화 없이 실행 중

증거:
- 2분 응답 시간 (비정상: 100배 느림)
- CPU 사용률 1~2% (정상: 45~80%)
- 토큰 속도 0.3 tokens/sec (정상: 10~20 tokens/sec)

---

🔧 해결 단계 (순서대로):

## Step 1: 현재 CPU 적용 상태 확인
```bash
ssh ronnie@RSCH5

# 응답 생성 중인 다른 터미널에서:
top -b -n 1 | grep -E 'Cpu|python'

# 확인 사항:
# - Cpu(s): 1~3% → 비정상 ❌
# - Cpu(s): 40~80% → 정상 ✅
```

## Step 2: llama.cpp 직접 빌드 (30분 소요)
```bash
ssh ronnie@RSCH5

# 개발 도구 설치
sudo dnf groupinstall "Development Tools" -y
sudo dnf install cmake git -y

# llama.cpp 빌드 (LLAMA_NATIVE=1 필수)
cd /tmp
rm -rf llama.cpp 2>/dev/null
git clone https://github.com/ggerganov/llama.cpp
cd llama.cpp

# 핵심: NATIVE 최적화 빌드
make LLAMA_NATIVE=1 -j32

# 활성화되는 최적화:
# - AVX2 (256-bit SIMD)
# - FMA (Fused Multiply-Add)
# - BMI2 (Bit Manipulation)
# - Zen3 아키텍처 최적화
```

## Step 3: 단독 성능 테스트
```bash
cd /tmp/llama.cpp

# 32스레드 전부 사용해서 테스트
./main -m /home/ronnie/LLM/models/Meta-Llama-3-8B-Instruct.Q5_K_M.gguf \
  -t 32 \
  -ngl 0 \
  -n 64 \
  -p "hi"

# 로그에서 확인할 부분:
# [평균 토큰 속도] XXX tokens/sec
# - 현재: 0.3~0.8 tokens/sec
# - 목표: 10~20 tokens/sec
```

## Step 4: llama-cpp-python 재설치 (GPT4All에 적용)
```bash
# 현재 llama-cpp-python 제거
pip uninstall llama-cpp-python -y

# NATIVE 최적화로 재설치
CMAKE_ARGS="-DLLAMA_NATIVE=on" pip install llama-cpp-python --no-cache-dir -v

# 또는 로컬 빌드:
cd /tmp
git clone https://github.com/abetlen/llama-cpp-python
cd llama-cpp-python
pip install -e . --no-cache-dir -v
```

## Step 5: 서버 재시작 + 테스트
```bash
# 서버 재시작
pkill -f uvicorn
sleep 2
cd ~/ADD_LLM
nohup uvicorn app:app --host 127.0.0.1 --port 8000 --workers 1 > server.log 2>&1 &
sleep 3

# 성능 테스트
time curl -X POST http://localhost:8000/gpt4all/chat/test \
  -H "Content-Type: application/json" \
  -d '{"message": "hi"}'

# 예상 결과:
# 현재: 60s 초과 ❌
# 목표: 5~12s ✅
```

---

⚠️ 주의사항:

1. Step 2 빌드는 30분~1시간 소요
2. 반드시 `LLAMA_NATIVE=1` 옵션 필요
3. Step 3 단독 테스트로 확인 필수 (GPT4All 앞에)
4. 빌드 중 에러나면 `make clean` 후 재시도

---

📋 예상 결과:

Before (현재):
- 응답 시간: 60+ 초
- CPU 사용: 1~2% (1-2 코어)
- Tokens/sec: 0.3~0.8

After (최적화 후):
- 응답 시간: 5~12 초
- CPU 사용: 40~80% (16-32 코어)  
- Tokens/sec: 10~20

→ 약 5~10배 빨라집니다!

---

🆘 만약 여전히 느리면:
1. 스레드 옵션 (`-t 32`) 재확인
2. `numactl` 사용 고려
3. TinyLlama로 모델 다운그레이드 (1~2초 응답)
