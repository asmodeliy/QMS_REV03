#!/bin/bash

echo "=== llama.cpp CPU 최적화 빌드 (Rocky Linux) ==="
echo ""

# 1. 필수 패키지 설치
echo "1️⃣ 개발 도구 설치..."
sudo dnf groupinstall "Development Tools" -y
sudo dnf install cmake git -y

echo ""
echo "2️⃣ llama.cpp 저장소 클론..."
cd /tmp
rm -rf llama.cpp
git clone https://github.com/ggerganov/llama.cpp
cd llama.cpp

echo ""
echo "3️⃣ NATIVE 최적화 빌드 (핵심 - 30분 소요)..."
echo "   활성화될 최적화: AVX2, FMA, BMI2, Zen3"
make clean
make LLAMA_NATIVE=1 -j32

if [ -f ./main ]; then
    echo ""
    echo "✅ 빌드 성공!"
    echo ""
    echo "4️⃣ 성능 테스트..."
    ./main -m /home/ronnie/LLM/models/Meta-Llama-3-8B-Instruct.Q5_K_M.gguf \
      -t 32 \
      -ngl 0 \
      -n 64 \
      -p "안녕하세요. 이것은 성능 테스트입니다."
    
    echo ""
    echo "⏱️ 위의 [평균 토큰 속도] 확인:"
    echo "   - 정상: 10~20 tokens/sec"
    echo "   - 현재: 0.3~0.8 tokens/sec"
else
    echo ""
    echo "❌ 빌드 실패. 에러 확인하세요."
fi

echo ""
echo "5️⃣ 빌드 검증 (컴파일 플래그 확인):"
grep -o "\-mavx2\|\-mfma\|\-mbmi2" /tmp/llama.cpp/Makefile || echo "Makefile에서 확인 필요"

echo ""
echo "=== llama.cpp 빌드 완료 ==="
