#!/usr/bin/env python3
"""
LLM 모델 설정 확인 스크립트

사용자가 다운로드한 모델 파일을 자동으로 감지하고 설정합니다.
"""

import os
import sys
from pathlib import Path

print("=" * 80)
print("LLM 모델 설정 확인")
print("=" * 80)

# 모델 경로
model_dir = Path(r"C:\Users\이상원\Downloads\Models")
model_name = "Meta-Llama-3-8B-Instruct.Q5_K_M.gguf"
model_path = model_dir / model_name

print(f"\n예상 모델 경로: {model_path}")

# 1. 모델 파일 확인
print("\n1️⃣ 모델 파일 확인...")
if model_path.exists():
    size_gb = model_path.stat().st_size / (1024**3)
    print(f"   ✓ 모델 파일 발견: {model_name}")
    print(f"   크기: {size_gb:.2f} GB")
else:
    print(f"   ✗ 모델 파일 없음: {model_path}")
    print(f"   아직 다운로드하지 않으셨다면:")
    print(f"   - 수동 다운로드: https://huggingface.co/TheBloke/Llama-2-7b-Chat-GGML")
    print(f"   - 또는 Ollama 사용: ollama pull llama2")
    sys.exit(1)

# 2. 환경 변수 확인
print("\n2️⃣ 환경 변수 확인...")
from dotenv import load_dotenv
load_dotenv()

configs = {
    'LLM_MODEL_PATH': os.environ.get('LLM_MODEL_PATH', r'C:\Users\이상원\Downloads\Models'),
    'LLM_MODEL_NAME': os.environ.get('LLM_MODEL_NAME', 'Meta-Llama-3-8B-Instruct.Q5_K_M'),
    'LLM_N_CTX': os.environ.get('LLM_N_CTX', '4096'),
    'LLM_BACKEND': os.environ.get('LLM_BACKEND', 'gpt4all'),
}

print("   현재 설정:")
for key, val in configs.items():
    print(f"   - {key}: {val}")

# 3. GPT4All 테스트
print("\n3️⃣ GPT4All 로드 테스트...")
try:
    from gpt4all import GPT4All
    print("   ✓ GPT4All 설치 확인됨")
    
    print(f"   모델 로드 중... (첫 로드는 시간 소요)")
    model = GPT4All(
        model_name=configs['LLM_MODEL_NAME'],
        model_path=configs['LLM_MODEL_PATH'],
        allow_download=False
    )
    print("   ✓ 모델 로드 성공!")
    
    # 간단한 응답 생성 테스트
    print("\n4️⃣ 모델 응답 테스트...")
    print("   프롬프트: 'Hello'")
    response = model.generate("Hello", max_tokens=20, temp=0.7)
    print(f"   응답: {response[:100]}...")
    
except Exception as e:
    print(f"   ✗ 오류: {e}")
    sys.exit(1)

print("\n" + "=" * 80)
print("✅ 모든 설정이 완료되었습니다!")
print("=" * 80)

print("\n다음 단계:")
print("1. 서버 시작:")
print("   python app.py")
print("\n2. 웹브라우저에서 접속:")
print("   http://localhost:8000/ai-chat")
print("\n3. RAG 인덱싱 (옵션):")
print("   python scripts/index_rag_documents.py")

    sys.exit(1)
