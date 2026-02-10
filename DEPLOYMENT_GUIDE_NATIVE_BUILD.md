# llama.cpp 네이티브 빌드 배포 가이드

## 개요

이 가이드는 Rocky Linux 8.10 서버에 최적화된 llama.cpp 바이너리와 llama-cpp-python을 배포하는 방법을 설명합니다.

**목표 성능 개선:**
- 응답 시간: **60+ 초 → 5-12 초** (10배 향상)
- CPU 사용률: **1-2% → 40-80%** (모든 코어 활성화)
- Tokens/sec: **0.3-0.8 → 10-20** (10배 향상)

**근본 원인:**
llama.cpp가 CPU SIMD 최적화 없이 컴파일됨
- ❌ AVX2 (256-bit SIMD) 비활성화
- ❌ FMA (Fused Multiply-Add) 비활성화
- ❌ BMI2 (Bit Manipulation) 비활성화
- ❌ Zen3 아키텍처 최적화 비활성화

**해결책:**
GitHub Actions에서 `LLAMA_NATIVE=1` 플래그로 Rocky 8.10 대상으로 재컴파일

---

## 단계별 배포 절차

### 단계 1: Windows에서 GitHub 푸시 및 빌드 트리거

#### 1.1 GitHub 계정 및 저장소 설정

```powershell
# 1. GitHub 개인 액세스 토큰 생성 (필수)
# - https://github.com/settings/tokens 방문
# - New Personal Access Token 클릭
# - Token (classic) 선택
# - Scopes: repo (Full control of private repositories)
# - Generate token → 값 복사해서 안전하게 저장
```

#### 1.2 QMS_SERVER 푸시

**방법 A: 배치 스크립트 사용 (권장)**

```powershell
# 1. Windows PowerShell에서
cd c:\Users\이상원\Downloads\QMS_SERVER

# 2. push_to_github.bat 실행
.\push_to_github.bat
```

**또는 방법 B: 수동 명령**

```bash
cd c:\Users\이상원\Downloads\QMS_SERVER

# 1. Git 초기화 (처음만)
git init
git add .
git commit -m "Add GitHub Actions workflow for llama.cpp NATIVE build - Rocky 8.10"
git branch -M main

# 2. GitHub 원격 저장소 추가 (YOUR_USERNAME 변경)
git remote add origin https://github.com/YOUR_USERNAME/QMS_SERVER.git

# 3. Main 브랜치 푸시
git push -u origin main

# 4. 빌드 트리거 (태그 생성 및 푸시)
git tag v1.0.0-llama-native
git push origin v1.0.0-llama-native
```

#### 1.3 GitHub Actions 빌드 모니터링

1. https://github.com/YOUR_USERNAME/QMS_SERVER/actions 접속
2. "Build llama.cpp NATIVE" 워크플로우 선택
3. 최신 실행 클릭 → 진행 상황 모니터링

**빌드 시간:** 약 20-30분

**빌드 완료 후 결과물:**
- `llama-main-native-rocky8.10`: 최적화된 llama.cpp 바이너리
- `llama_cpp_python-*.whl`: 최적화된 Python 패키지

---

### 단계 2: Rocky 8.10 서버에서 다운로드 및 설치

#### 2.1 서버 접속

```bash
ssh ronnie@RSCH5
```

또는

```bash
ssh ronnie@[SERVER_IP_ADDRESS]
```

#### 2.2 빌드 결과 다운로드

**방법 A: 자동 다운로드 스크립트 사용 (권장)**

```bash
# 1. 스크립트 실행 가능하게 변경
chmod +x ~/download_and_install.sh

# 2. 다운로드 및 설치 (태그와 GitHub 사용자명 입력)
~/download_and_install.sh v1.0.0-llama-native YOUR_USERNAME
```

**또는 방법 B: 수동 다운로드**

```bash
# 1. 임시 디렉토리 생성
mkdir -p /tmp/llama_native_build
cd /tmp/llama_native_build

# 2. GitHub Releases에서 직접 다운로드
# https://github.com/YOUR_USERNAME/QMS_SERVER/releases/tag/v1.0.0-llama-native
# 또는 GitHub Actions의 Artifacts에서 다운로드

# 3. Windows에서 scp로 전송 (PowerShell에서)
scp -r "llama-main-native-rocky8.10" "ronnie@RSCH5:/tmp/llama_native_build/"
scp -r "llama_cpp_python-*.whl" "ronnie@RSCH5:/tmp/llama_native_build/"
```

#### 2.3 파일 설치

```bash
# 1. 바이너리 설치
mkdir -p /home/ronnie/LLM/bin
cp /tmp/llama_native_build/llama-main-native-rocky8.10 /home/ronnie/LLM/bin/
chmod +x /home/ronnie/LLM/bin/llama-main-native-rocky8.10

# 2. llama-cpp-python wheel 설치
python3 -m pip install --upgrade /tmp/llama_native_build/llama_cpp_python-*.whl

# 3. 설치 확인
python3 -c "import llama_cpp; print(f'✓ 설치 완료: {llama_cpp.__file__}')"
```

---

### 단계 3: 서버 재시작 및 성능 테스트

#### 3.1 기존 프로세스 중지

```bash
pkill -f "uvicorn.*app:app"
sleep 2
```

#### 3.2 새 서버 시작

```bash
cd /home/ronnie/ADD_LLM

# 백그라운드에서 시작
nohup python3 -m uvicorn app:app \
    --host 127.0.0.1 \
    --port 8000 \
    --workers 1 \
    > server.log 2>&1 &

# 또는 자동 스크립트 사용
chmod +x ~/restart_and_test.sh
~/restart_and_test.sh
```

#### 3.3 성능 테스트

```bash
# 테스트 1: 빠른 응답 확인
time curl -X POST http://localhost:8000/gpt4all/chat/test \
    -H "Content-Type: application/json" \
    -d '{"message": "hi"}'

# 테스트 2: 일반 쿼리 최적화 확인
time curl -X POST http://localhost:8000/gpt4all/chat/test \
    -H "Content-Type: application/json" \
    -d '{"message": "What is the capital of France?"}'

# 테스트 3: CPU 모니터링
top -p $(pgrep -f "uvicorn")
```

---

## 성능 기준

### 예상 결과 (Ryzen 9 5950X, Llama-3-8B Q5_K_M)

| 지표 | 개선 전 | 개선 후 | 향상도 |
|------|--------|--------|--------|
| 응답 시간 | 60+ 초 | 5-12 초 | **10배 향상** |
| Tokens/sec | 0.3-0.8 | 10-20 | **12-15배 향상** |
| CPU 사용률 | 1-2% | 40-80% | **모두 활성화** |
| 메모리 | 5.4GB | 5.4GB | 변화 없음 |

### 로그 확인

```bash
# 서버 로그 실시간 모니터링
tail -f /home/ronnie/ADD_LLM/server.log

# [PERF] 마커로 성능 지표 확인
grep "\[PERF\]" /home/ronnie/ADD_LLM/server.log | tail -20

# 예상 로그 (개선 후)
# [PERF] Model generation: 2.34s  (개선 전: 60s)
# [PERF] Chat total: 2.89s
# [PERF] Response tokens: 23, time: 2.34s (10.0 t/s)
```

---

## 문제 해결

### 빌드 실패

**증상:** GitHub Actions 빌드가 실패

**해결책:**
1. GitHub Actions 페이지에서 빌드 로그 확인
2. 오류 메시지 검토 (CMake, 컴파일러 등)
3. Dockerfile 업데이트 및 재시도

```bash
# 로컬에서 테스트 (Rocky Linux 8.10 필요)
docker run --rm -it rockylinux:8.10 bash
dnf groupinstall -y "Development Tools"
dnf install -y cmake git python3
# ... 컴파일 시도
```

### 설치 실패

**증상:** `pip install` 실패 또는 import 오류

**해결책:**

```bash
# 1. 기존 패키지 제거
pip3 uninstall -y llama-cpp-python

# 2. 캐시 삭제
pip3 cache purge

# 3. 재설치 (--force-reinstall 사용)
pip3 install --force-reinstall --no-cache-dir /path/to/wheel.whl

# 4. 설치 확인
python3 -c "import llama_cpp; print(llama_cpp.__version__)"
```

### 성능 개선 없음

**증상:** 응답 시간이 여전히 60+ 초

**확인 사항:**

```bash
# 1. 올바른 wheel이 설치되었는가?
python3 -c "import llama_cpp; print(llama_cpp.__file__)"

# 2. 새 프로세스가 실행 중인가?
ps aux | grep uvicorn

# 3. 서버가 올바르게 재시작되었는가?
curl http://localhost:8000/gpt4all/chat/test

# 4. CPU 최적화가 활성화되었는가? (로그 확인)
grep "AVX2\|FMA\|BMI2" /home/ronnie/ADD_LLM/server.log

# 5. 이전 wheel 캐시가 있는가?
pip3 show llama-cpp-python  # 경로 확인
ls -la /path/to/site-packages/llama_cpp/
```

### 디스크 공간 부족

```bash
# 임시 파일 정리
rm -rf /tmp/llama_native_build
pip3 cache purge

# 오래된 wheel 파일 정리
rm -f ~/llama_cpp_python-*.whl
```

---

## 역할 및 책임

| 단계 | 위치 | 담당 | 도구 |
|------|------|------|------|
| 빌드 | GitHub | GitHub Actions | rockylinux:8.10 컨테이너 |
| 다운로드 | Windows 또는 서버 | 사용자 | curl 또는 브라우저 |
| 설치 | Rocky Linux 서버 | 사용자 | pip3, bash |
| 테스트 | Rocky Linux 서버 | 사용자 | curl, top |

---

## 요약 체크리스트

**Windows에서:**
- [ ] GitHub 개인 액세스 토큰 생성
- [ ] `git remote add origin ...` 및 `git push` 실행
- [ ] `git tag v1.0.0-llama-native` 및 `git push origin --tags` 실행
- [ ] GitHub Actions 빌드 모니터링 (20-30분)

**Rocky Linux 서버에서:**
- [ ] 빌드 결과 다운로드 (Artifacts 또는 Releases)
- [ ] llama-main-native 바이너리 설치
- [ ] llama-cpp-python wheel 설치
- [ ] 기존 uvicorn 프로세스 중지
- [ ] 새 서버 시작 (자동으로 새 wheel 사용)
- [ ] 성능 테스트 (curl endpoint)
- [ ] 응답 시간 및 CPU 사용률 확인

**예상 완료 시간:**
- 배포 준비: 5분
- 빌드 (GitHub Actions): 20-30분
- 설치 및 테스트: 5-10분
- **총: 30-50분**

---

## 참고자료

- GitHub Actions Workflow: `.github/workflows/build-llama-cpp-native.yml`
- llama.cpp 최적화: https://github.com/ggerganov/llama.cpp
- llama-cpp-python: https://github.com/abetlen/llama-cpp-python
- Performance Tuning: `modules/mcp/gpt4all_routes.py`, `modules/mcp/gpt4all_client.py`

---

마지막 질문이나 추가 조정이 필요하면 언제든 문의하세요!
