#!/bin/bash

# Rocky Linux 8.10 서버에서 GitHub Actions 빌드 결과 다운로드 및 설치
# 사용법: ./download_and_install.sh v1.0.0-llama-native YOUR_USERNAME

if [ $# -lt 2 ]; then
    echo "사용법: $0 <tag> <github_username>"
    echo "예: $0 v1.0.0-llama-native myusername"
    exit 1
fi

GITHUB_TAG=$1
GITHUB_USERNAME=$2
REPO_NAME=QMS_SERVER
DOWNLOAD_DIR="/tmp/llama_native_build"
INSTALL_PREFIX="/home/ronnie/LLM"

echo "=========================================="
echo "GitHub Actions 빌드 결과 다운로드 및 설치"
echo "=========================================="
echo "Tag: $GITHUB_TAG"
echo "GitHub: $GITHUB_USERNAME/$REPO_NAME"
echo "기본 설치 경로: $INSTALL_PREFIX"
echo ""

# 다운로드 디렉토리 생성
mkdir -p "$DOWNLOAD_DIR"
cd "$DOWNLOAD_DIR"

echo "[1/4] GitHub Releases에서 바이너리 및 wheel 다운로드..."
echo ""

# GitHub API를 통해 Release 정보 가져오기
RELEASE_API="https://api.github.com/repos/$GITHUB_USERNAME/$REPO_NAME/releases/tags/$GITHUB_TAG"

echo "Release API 호출: $RELEASE_API"
RELEASE_JSON=$(curl -s "$RELEASE_API")

if echo "$RELEASE_JSON" | grep -q "Not Found"; then
    echo "[ERROR] Release를 찾을 수 없습니다."
    echo "다음을 확인하세요:"
    echo "  1. 태그가 존재하는가: git tag -l"
    echo "  2. GitHub Actions 빌드가 완료되었는가"
    echo "  3. GitHub 저장소 URL이 정확한가: https://github.com/$GITHUB_USERNAME/$REPO_NAME"
    exit 1
fi

# Release Assets 다운로드
echo "$RELEASE_JSON" | grep '"download_url"' | head -2 | cut -d '"' -f 4 | while read url; do
    echo "다운로드 중: $url"
    curl -L -O "$url"
done

echo ""
echo "[2/4] 다운로드 파일 확인..."
ls -lh "$DOWNLOAD_DIR"

if [ ! -f "$DOWNLOAD_DIR/llama-main-native-rocky8" ]; then
    echo "[WARNING] 바이너리 파일이 없습니다. GitHub Actions 빌드 페이지 확인:"
    echo "https://github.com/$GITHUB_USERNAME/$REPO_NAME/actions?query=tag%3A$GITHUB_TAG"
    echo ""
    echo "(업로드된 Artifacts 사용으로 변경된 경우) 수동으로 다운로드:"
    echo "  1. https://github.com/$GITHUB_USERNAME/$REPO_NAME/actions 방문"
    echo "  2. 최신 'Build llama.cpp NATIVE' 워크플로우 클릭"
    echo "  3. Artifacts 섹션에서 다운로드"
fi

# wheel 패키지 확인
if ls "$DOWNLOAD_DIR"/llama_cpp_python-*.whl 1>/dev/null 2>&1; then
    WHEEL_FILE=$(ls "$DOWNLOAD_DIR"/llama_cpp_python-*.whl | head -1)
    echo "✓ Wheel 파일 발견: $(basename $WHEEL_FILE)"
else
    echo "[WARNING] llama-cpp-python wheel을 찾을 수 없습니다."
fi

echo ""
echo "[3/4] 파일 설치..."

# 바이너리 설치
if [ -f "$DOWNLOAD_DIR/llama-main-native-rocky8" ]; then
    mkdir -p "$INSTALL_PREFIX/bin"
    cp "$DOWNLOAD_DIR/llama-main-native-rocky8" "$INSTALL_PREFIX/bin/"
    chmod +x "$INSTALL_PREFIX/bin/llama-main-native-rocky8"
    echo "✓ 바이너리 설치: $INSTALL_PREFIX/bin/llama-main-native-rocky8"
fi

# wheel 설치
if ls "$DOWNLOAD_DIR"/llama_cpp_python-*.whl 1>/dev/null 2>&1; then
    echo "pip를 사용하여 wheel 설치 중..."
    python3 -m pip install --upgrade "$DOWNLOAD_DIR"/llama_cpp_python-*.whl
    echo "✓ llama-cpp-python 설치 완료"
fi

echo ""
echo "[4/4] 설치 확인..."
python3 -c "import llama_cpp; print(f'✓ llama-cpp-python 설치됨: {llama_cpp.__version__}')" 2>/dev/null || \
    echo "[WARNING] llama-cpp-python 임포트 실패. pip install 로그 확인하세요."

echo ""
echo "=========================================="
echo "✓ 설치 완료!"
echo "=========================================="
echo ""
echo "다음 단계:"
echo "1. 기존 uvicorn 프로세스 종료:"
echo "   pkill -f uvicorn"
echo "   sleep 2"
echo ""
echo "2. 새 서버 시작 (llama-cpp-python 자동 사용):"
echo "   cd ~/ADD_LLM"
echo "   nohup uvicorn app:app --host 127.0.0.1 --port 8000 --workers 1 > server.log 2>&1 &"
echo ""
echo "3. 성능 테스트:"
echo "   time curl -X POST http://localhost:8000/gpt4all/chat/test \\"
echo "     -H 'Content-Type: application/json' \\"
echo "     -d '{\"message\": \"hi\"}'"
echo ""
echo "예상 성능:"
echo "  - 응답 시간: 60+ 초 → 5-12 초 (10배 향상)"
echo "  - CPU 사용률: 1-2% → 40-80%"
echo "  - Tokens/sec: 0.3-0.8 → 10-20"
echo ""
echo "로그 확인:"
echo "  tail -f ~/ADD_LLM/server.log"
echo ""
