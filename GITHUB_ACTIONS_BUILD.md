=== GitHub Actions를 통한 llama.cpp NATIVE 빌드 ===

📋 준비 단계:

1️⃣ GitHub에 리포지토리 푸시
```powershell
cd c:\Users\이상원\Downloads\QMS_SERVER

git init
git add .
git commit -m "Add GitHub Actions workflow for llama.cpp native build"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/QMS_SERVER.git
git push -u origin main
```

2️⃣ 태그 생성으로 빌드 실행
```powershell
git tag v1.0.0-llama-native
git push origin v1.0.0-llama-native
```

---

🚀 빌드 자동 실행:

GitHub Actions → Actions 탭에서:
- "Build llama.cpp NATIVE" 워크플로우 자동 시작
- Rocky 8.10 컨테이너에서 컴파일
- 20~30분 소요

---

📦 결과 다운로드:

빌드 완료 후:

1. Artifacts 탭:
   - llama-cpp-native-rocky8.10 다운로드
   - 포함 파일:
     • llama-main-native-rocky8.10 (바이너리)
     • llama_cpp_python-*.whl (Python 패키지)

2. 또는 Releases 탭:
   - 자동 생성된 release에서 다운로드
   - .zip으로 묶여있음

---

📤 Linux 서버에 전송:

빌드 완료 후:

```bash
# Windows에서 (PowerShell)
# GitHub Releases에서 다운로드한 파일들:

# 1. 바이너리 및 wheel 파일 준비
# llama-main-native-rocky8.10
# llama_cpp_python-*.whl

# 2. 서버에 전송
scp llama-main-native-rocky8.10 ronnie@RSCH5:/home/ronnie/LLM/bin/llama-main-native
scp llama_cpp_python-*.whl ronnie@RSCH5:/home/ronnie/
```

---

🔧 Linux 서버에서 설치:

```bash
ssh ronnie@RSCH5

# 1. Python wheel 설치
pip install ~/llama_cpp_python-*.whl

# 2. 바이너리 권한 설정
chmod +x ~/LLM/bin/llama-main-native

# 3. GPT4All 설정 확인 (gpt4all_routes.py)
# enable_rag=True 상태 확인

# 4. 서버 재시작
pkill -f uvicorn
sleep 2
cd ~/ADD_LLM
nohup uvicorn app:app --host 127.0.0.1 --port 8000 --workers 1 > server.log 2>&1 &

# 5. 성능 테스트
sleep 3
time curl -X POST http://localhost:8000/gpt4all/chat/test \
  -H "Content-Type: application/json" \
  -d '{"message": "hi"}'
```

---

⏱️ 예상 결과:

| 항목 | 이전 | 이후 |
|------|------|------|
| 응답 시간 | 60+ 초 | 5-12 초 |
| CPU 사용률 | 1-2% | 40-80% |
| Tokens/sec | 0.3-0.8 | 10-20 |

---

⚠️ 주의:

1. GitHub 리포지토리가 공개(Public)여야 함
   - 비공개면 GitHub Premium 필요

2. 태그 형식: `v*` (v1.0.0, v1.0.1 등)
   - 다른 형식의 태그는 빌드 실행 안 됨

3. 빌드 로그 확인:
   - GitHub Actions → 워크플로우 선택 → 상세 로그 보기

4. 재빌드 필요시:
   ```bash
   git tag -d v1.0.0  # 기존 태그 삭제
   git push origin :refs/tags/v1.0.0
   git tag v1.0.1
   git push origin v1.0.1
   ```

---

💡 대안 (Artifacts만 필요):

빌드 완료 후 GitHub Actions → Artifacts에서 직접 다운로드:
- 릴리스 버전 없이도 아티팩트 사용 가능
- 최신 빌드 결과 즉시 다운로드 가능
