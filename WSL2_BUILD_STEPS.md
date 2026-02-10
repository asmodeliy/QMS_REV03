=== Windows WSL2에서 Rocky Linux용 llama.cpp 빌드 ===

📋 준비:
1. Windows Terminal 열기 (Win + X → Terminal)
2. "Ubuntu" 선택 (WSL2 Ubuntu 시작)
3. 아래 명령 복사-붙여넣기

---

🔨 빌드 명령 (WSL2 Ubuntu 터미널에서):

# Step 1: 필수 도구 설치
sudo apt-get update && sudo apt-get install -y cmake build-essential git python3-pip

# Step 2: llama.cpp 다운로드 + 빌드
cd /tmp
rm -rf llama.cpp
git clone https://github.com/ggerganov/llama.cpp
cd llama.cpp
make LLAMA_NATIVE=1 -j$(nproc)

# 빌드 완료 확인 (main 바이너리 있는지)
ls -lh ./main

# Step 3: llama-cpp-python 빌드
cd /tmp
git clone https://github.com/abetlen/llama-cpp-python
cd llama-cpp-python
CMAKE_ARGS="-DLLAMA_NATIVE=on" pip3 install . --no-cache-dir

# Step 4: Wheel 파일 생성
pip3 wheel . --wheel-dir=/tmp/wheels --no-cache-dir

# 생성된 wheel 확인
ls -lh /tmp/wheels/*.whl

---

📦 생성된 파일을 Windows로 복사:

# Windows 경로로 복사 (WSL에서)
cp /tmp/llama.cpp/main /mnt/c/Users/이상원/Downloads/QMS_SERVER/llama-main-native
cp /tmp/wheels/*.whl /mnt/c/Users/이상원/Downloads/QMS_SERVER/

---

📤 Linux 서버에 전송:

# PowerShell (Windows)에서:
scp llama-main-native ronnie@RSCH5:/home/ronnie/LLM/bin/
scp llama_cpp_python*.whl ronnie@RSCH5:/home/ronnie/

---

🔧 Linux 서버에서 설치:

ssh ronnie@RSCH5

# Wheel 설치
pip install ~/llama_cpp_python*.whl

# GPT4All 재설정 (gpt4all-routes.py 수정)
# enable_rag=True로 변경 (현재 False)

# 서버 재시작
pkill -f uvicorn
cd ~/ADD_LLM
nohup uvicorn app:app --host 127.0.0.1 --port 8000 --workers 1 > server.log 2>&1 &

---

⏱️ 성능 테스트:

time curl -X POST http://localhost:8000/gpt4all/chat/test \
  -H "Content-Type: application/json" \
  -d '{"message": "hi"}'

# 예상:
# Before: 60+ 초
# After: 5-12 초
