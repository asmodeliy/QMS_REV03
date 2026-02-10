# QMS Server - RAG (Retrieval Augmented Generation) System

## Overview

이 문서는 QMS Server에 통합된 RAG(Retrieval Augmented Generation) 시스템에 대한 설명입니다. 

RAG 시스템은 GPT4All 모델이 QMS 프로젝트의 전체 코드베이스와 문서를 학습하고, 사용자 쿼리에 대해 컨텍스트 기반의 더 정확한 답변을 제공할 수 있도록 합니다.

## Architecture

### Components

```
┌─────────────────────────────────────────────────────────────┐
│                    GPT4All Assistant                        │
│  (modules/mcp/gpt4all_client.py)                           │
└────────┬─────────────────────────────────────────────┬─────┘
         │                                             │
         ├─→ QMS Tools (Database Access)              │
         │                                             │
         └─→ RAG Retriever (Context Injection)        │
                                                       │
┌────────────────────────────────────────────────────────────┐
│              RAG System (modules/mcp/)                     │
├────────────────────────────────────────────────────────────┤
│  ┌──────────────────┐      ┌─────────────────────┐        │
│  │  RAG Indexer     │      │  RAG Retriever      │        │
│  │ (rag_indexer.py)│      │ (rag_retriever.py)  │        │
│  └────────────┬─────┘      └──────────┬──────────┘        │
│               │                       │                    │
│               └───────────┬───────────┘                    │
│                           │                                │
│                    ┌──────▼─────────┐                      │
│                    │   SQLite DB    │                      │
│                    │ (RAG Knowledge │                      │
│                    │     Base)      │                      │
│                    └────────────────┘                      │
└────────────────────────────────────────────────────────────┘
```

### Key Modules

1. **rag_indexer.py** - 문서 인덱싱
   - 프로젝트의 모든 개발 파일 색인
   - 문서를 청크 단위로 분할
   - SQLite 데이터베이스에 저장

2. **rag_retriever.py** - 문서 검색 및 컨텍스트 생성
   - 관련 문서 검색
   - LLM 프롬프트용 컨텍스트 생성
   - 시스템 아키텍처 이해 지원

3. **gpt4all_client.py** - GPT4All 통합
   - RAG와 GPT4All 모델 통합
   - 도구 기반 작업 실행
   - 대화 관리

4. **gpt4all_routes.py** - FastAPI 엔드포인트
   - RAG 검색 API
   - 인덱싱 트리거 API
   - 채팅 인터페이스 API

## Quick Start

### 1. 프로젝트 초기화

```bash
# RAG 시스템 테스트
python scripts/test_rag_integration.py

# RAG 데이터베이스 빌드
python scripts/index_rag_documents.py
```

### 2. GPT4All 모델 설치 (필수)

```bash
pip install gpt4all

# 또는 requirements.txt에 추가
echo "gpt4all>=3.4.0" >> requirements-optional.txt
```

### 3. 서버 시작

```bash
python app.py
```

### 4. RAG 채팅 인터페이스 접근

브라우저에서: `http://localhost:8000/ai-chat` (관리자만 접근 가능)

## Usage Guide

### Command Line Tools

#### 1. 프로젝트 인덱싱

```bash
# 기본 인덱싱
python scripts/index_rag_documents.py

# 상세 로깅
python scripts/index_rag_documents.py --verbose

# 데이터베이스 경로 지정
python scripts/index_rag_documents.py --db-path /path/to/rag.db

# 현재 통계 확인
python scripts/index_rag_documents.py --stats

# 지식 베이스 검색
python scripts/index_rag_documents.py --search "project management"
```

#### 2. 테스트 및 검증

```bash
# 전체 통합 테스트
python scripts/test_rag_integration.py

# 상세 테스트 로그
python scripts/test_rag_integration.py -v
```

### API Endpoints

#### Chat with RAG Context

```bash
curl -X POST http://localhost:8000/gpt4all/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Tell me about project management", "reset": false}'
```

#### RAG Search

```bash
curl -X POST http://localhost:8000/gpt4all/rag/search \
  -H "Content-Type: application/json" \
  -d '{"query": "database models", "limit": 5}'
```

#### Index Project

```bash
curl -X POST http://localhost:8000/gpt4all/rag/index
```

#### System Stats

```bash
curl http://localhost:8000/gpt4all/rag/stats
curl http://localhost:8000/gpt4all/status-extended
```

### Python API

```python
from modules.mcp.gpt4all_client import QMSAssistant
from modules.mcp.rag_retriever import RAGRetriever
from modules.mcp.rag_indexer import RAGIndexer

# RAG 시스템 초기화
indexer = RAGIndexer()
retriever = RAGRetriever(indexer=indexer)

# 프로젝트 인덱싱
counts = indexer.index_project()
print(f"Indexed {counts}")

# 문서 검색
results = retriever.retrieve("FastAPI authentication")
for result in results:
    print(f"Found: {result['file_path']}")

# 컨텍스트 생성
context = retriever.build_context("user authentication")
print(context)

# GPT4All 통합
assistant = QMSAssistant(enable_rag=True)
assistant.load_model()
response = assistant.chat("How does authentication work?")
print(response)
```

## Configuration

### Environment Variables

`.env` 파일에서 설정:

```bash
# GPT4All 설정
GPT4ALL_MODEL_PATH=/path/to/models
GPT4ALL_MODEL_NAME=Meta-Llama-3-8B-Instruct.Q4_0.gguf
LLM_N_CTX=2048

# RAG 설정
RAG_DB_PATH=rag_knowledge_base.db
RAG_ENABLED=true
```

### 인덱싱 설정

`modules/mcp/rag_indexer.py`에서 설정 가능:

- 인덱싱할 파일 유형 (Python, HTML, JS, CSS, MD)
- 스킵할 디렉토리 (`__pycache__`, `.git`, `node_modules`, 등)
- 청크 크기
- 문서 요약 길이

## Database Schema

### documents 테이블

```sql
CREATE TABLE documents (
    id INTEGER PRIMARY KEY,
    file_path TEXT UNIQUE,
    file_name TEXT,
    file_type TEXT,
    content_hash TEXT,
    content TEXT,
    summary TEXT,
    keywords TEXT (JSON),
    module_name TEXT,
    indexed_at TIMESTAMP,
    updated_at TIMESTAMP
)
```

### chunks 테이블

```sql
CREATE TABLE chunks (
    id INTEGER PRIMARY KEY,
    document_id INTEGER,
    chunk_index INTEGER,
    chunk_text TEXT,
    chunk_keywords TEXT (JSON),
    FOREIGN KEY (document_id) REFERENCES documents(id)
)
```

## Performance Considerations

### 인덱싱 성능

- 첫 인덱싱: 프로젝트 크기에 따라 수 초 ~ 수 분
- 증분 인덱싱: 변경된 파일만 업데이트 (파일 해시 기반)
- 권장 주기: 개발 후 주기적으로 (데일리 또는 위클리)

### 검색 성능

- 간단한 키워드 매칭 알고리즘 사용 (빠른 성능)
- 대부분의 쿼리: < 100ms
- 인덱스 지원: file_path, module_name

### 컨텍스트 크기

- 기본 컨텍스트 길이: 2000-4000 문자
- GPT4All 토큰 제한에 맞게 자동 조정
- 검색 결과 제한: 기본 5개 문서

## Troubleshooting

### 문제: GPT4All 모델을 찾을 수 없음

**해결책:**
```bash
# GPT4All 모델 설치
pip install gpt4all --upgrade

# 환경 변수 설정
export GPT4ALL_MODEL_PATH=/path/to/models
export GPT4ALL_MODEL_NAME=Meta-Llama-3-8B-Instruct.Q4_0.gguf
```

### 문제: RAG 데이터베이스가 너무 큼

**해결책:**
```bash
# 데이터베이스 재구성
rm rag_knowledge_base.db
python scripts/index_rag_documents.py

# 또는 특정 디렉토리만 인덱싱
python -c "
from modules.mcp.rag_indexer import RAGIndexer
indexer = RAGIndexer()
indexer.index_directory('core', '*.py')
"
```

### 문제: 검색 결과가 관련성이 낮음

**해결책:**
1. 인덱싱 재실행: `python scripts/index_rag_documents.py --stats`
2. 다양한 키워드로 검색 시도
3. 쿼리 정제 및 최적화

### 문제: 메모리 사용량이 높음

**해결책:**
1. 컨텍스트 크기 제한 감소
2. 청크 크기 조정
3. 모델 양자화 버전 사용

## Best Practices

### 문서 품질

1. **명확한 주석 추가**
   - 모든 함수에 docstring 작성
   - 복잡한 로직에 주석 추가

2. **일관된 코드 구조**
   - 모듈 간 소수 명확히 정의
   - 관련 함수들을 그룹화

3. **업데이트 주기**
   - 코드 변경 후 매번 재인덱싱
   - 또는 자동화된 CI/CD 파이프라인 구성

### 쿼리 최적화

1. **구체적인 질문**
   ```
   좋음: "How is user authentication implemented in the auth module?"
   나쁨: "authentication"
   ```

2. **컨텍스트 제공**
   - 관련 모듈명 포함
   - 문제 유형 명확히

3. **여러 쿼리 시도**
   - 다양한 표현 사용
   - 동의어 활용

## Advanced Features

### 커스텀 RAG Context

```python
from modules.mcp.rag_retriever import RAGContextBuilder

builder = RAGContextBuilder(retriever)

# 코드 분석 컨텍스트
context = builder.build_code_analysis_context(code_snippet)

# 에러 디버깅 컨텍스트
context = builder.build_troubleshooting_context(error_msg)

# 기능 요청 컨텍스트
context = builder.build_feature_request_context(feature_desc)
```

### Batch Processing

```python
from modules.mcp.rag_indexer import RAGIndexer

indexer = RAGIndexer()

# 특정 모듈만 인덱싱
indexer.index_directory('modules/rpmt', '*.py', recursive=True)
indexer.index_directory('modules/svit', '*.py', recursive=True)
```

## Integration with Existing Systems

### MCP (Model Context Protocol)

RAG 시스템은 MCP 서버와 통합되어 있습니다:
- 도구 호출: `list_projects`, `get_task_details` 등
- 자동 데이터 검색 및 응답 제공

### FastAPI 라우터

모든 RAG 엔드포인트는 Admin 인증 요구:
- `/gpt4all/chat` - 기본 채팅 (RAG 자동 활성화)
- `/gpt4all/chat/with-context` - 명시적 RAG 사용
- `/gpt4all/chat/no-context` - RAG 비활성화
- `/gpt4all/rag/*` - RAG 관리 엔드포인트

## Future Enhancements

1. **벡터 임베딩**
   - OpenAI 또는 Hugging Face 임베딩 모델 사용
   - 의미 기반 검색으로 정확도 개선

2. **자동 인덱싱**
   - 파일 시스템 감시 도구
   - 변경 시 자동 재인덱싱

3. **다중 언어 지원**
   - 영문/한글 쿼리 지원
   - 모듈명 자동 번역

4. **시맨틱 캐싱**
   - 자주 사용되는 쿼리 캐싱
   - 응답 시간 개선

5. **웹 UI 개선**
   - RAG 통계 대시보드
   - 인덱싱 진행 상황 표시
   - 검색 결과 시각화

## References

- RAG Indexer: [modules/mcp/rag_indexer.py](../modules/mcp/rag_indexer.py)
- RAG Retriever: [modules/mcp/rag_retriever.py](../modules/mcp/rag_retriever.py)
- GPT4All Client: [modules/mcp/gpt4all_client.py](../modules/mcp/gpt4all_client.py)
- API Routes: [modules/mcp/gpt4all_routes.py](../modules/mcp/gpt4all_routes.py)

## Support

- Issue 발생 시: `scripts/test_rag_integration.py` 실행으로 진단
- 로그 확인: `logs/` 디렉토리
- 관리 페이지: `http://localhost:8000/admin_dashboard`

---

**Version**: 1.0  
**Last Updated**: 2026-02-09  
**Status**: ✓ Production Ready
