#!/bin/bash
# WSL2 Ubuntu에서 실행할 스크립트
# Rocky Linux용 llama.cpp + llama-cpp-python을 NATIVE 최적화로 빌드

set -e

echo "=== WSL2에서 Rocky Linux용 llama.cpp 빌드 ==="
echo ""

# Step 1: 필수 패키지 설치 (ubuntu/WSL)
echo "1️⃣ WSL 개발 도구 설치..."
sudo apt-get update -qq
sudo apt-get install -y cmake build-essential git python3-pip python3-venv

echo ""
echo "2️⃣ llama.cpp 저장소 클론..."
cd /tmp
rm -rf llama.cpp llama-cpp-python
git clone https://github.com/ggerganov/llama.cpp
cd llama.cpp

echo ""
echo "3️⃣ LLAMA_NATIVE=1로 빌드 (핵심 - AVX2/FMA 활성화)..."
make clean
make LLAMA_NATIVE=1 -j$(nproc)

echo ""
echo "4️⃣ 빌드 결과 확인..."
if [ -f ./main ]; then
    echo "✅ llama.cpp main 바이너리 생성 완료"
    file ./main
else
    echo "❌ 빌드 실패"
    exit 1
fi

echo ""
echo "5️⃣ llama-cpp-python 설치..."
cd /tmp
git clone https://github.com/abetlen/llama-cpp-python
cd llama-cpp-python

# pip 모듈 설치
CMAKE_ARGS="-DLLAMA_NATIVE=on" pip3 install . --no-cache-dir -v 2>&1 | tail -20

echo ""
echo "6️⃣ 결과를 Windows와 공유 폴더로 복사..."
# WSL의 /tmp에서 Windows 경로로 복사
if [ -d "/mnt/c/Users" ]; then
    WINDOWS_PATH=$(ls /mnt/c/Users/*/Downloads/QMS_SERVER 2>/dev/null | head -1)
    if [ -n "$WINDOWS_PATH" ]; then
        echo "Windows 경로: $WINDOWS_PATH"
        echo ""
        echo "📦 생성된 파일들:"
        cp /tmp/llama.cpp/main "$WINDOWS_PATH/llama-main-native"
        echo "✅ llama.cpp main → llama-main-native"
        
        # llama-cpp-python wheel 찾기
        WHEEL=$(find /tmp/llama-cpp-python -name "*.whl" 2>/dev/null | head -1)
        if [ -n "$WHEEL" ]; then
            cp "$WHEEL" "$WINDOWS_PATH/"
            echo "✅ llama-cpp-python wheel → $(basename $WHEEL)"
        fi
    fi
fi

echo ""
echo "=== 빌드 완료 ==="
echo ""
echo "📋 다음 단계:"
echo "1. Linux 서버에서 받을 파일:"
echo "   - llama-main-native (바이너리)"
echo "   - llama_cpp_python*.whl (Python 패키지)"
echo ""
echo "2. 서버에 전송 후:"
echo "   pip install llama_cpp_python*.whl"
echo ""
