#!/bin/bash

echo "=== CPU 사용률 모니터링 (응답 생성 중에 확인) ==="
echo ""
echo "현재 스레드 정보:"
nproc --all
echo ""

echo "다른 터미널에서 응답 생성 시작 후,"
echo "이 명령 실행하세요:"
echo ""
echo "  top -b -n 1 | grep -E 'Cpu|python'"
echo ""

echo "[정상 상태]"
echo "Cpu(s): ~45.0%us, 2.0%sy, 0.0%ni, 53.0%id"
echo "→ CPU 약 1400%+ (16~32개 코어 활용)"
echo ""

echo "[비정상 상태 (현재)]"  
echo "Cpu(s): ~3.0%us, 0.5%sy, 0.0%ni, 96.5%id"
echo "→ CPU 약 100~200% (1~2개 코어만 활용)"
echo ""

echo "=== 자동 모니터링 (60초) ==="
top -b -n 60 -d 1 | grep -E '^top|Cpu|python' | head -30
