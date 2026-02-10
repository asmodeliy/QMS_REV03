# QMS Server - 배포 준비 체크리스트

## ✅ 완료된 작업

### 1. Chat 기능 보안 (Admin Only)
- [x] `/gpt4all/chat` 엔드포인트 - Admin only로 변경
- [x] `/gpt4all/reset` 엔드포인트 - Admin only로 변경
- [x] `/gpt4all/chat/with-context` - Admin only 유지
- [x] `/gpt4all/chat/no-context` - Admin only 유지
- [x] AI Chat 페이지 (`/ai-chat`) - Admin only로 이미 설정됨

**위치:** `modules/mcp/gpt4all_routes.py`

### 2. RAG 인덱싱 성능 최적화
- [x] Incremental Indexing 시스템 구현
- [x] 변경된 파일만 인덱싱하도록 변경
- [x] 파일 해시 기반 변경 감지
- [x] 상태 파일 추적 (`.rag_indexed_state.json`)
- [x] 배치 처리 유지 (20개 파일/배치)

**새로운 기능:**
- 첫 번째 실행: 모든 파일 인덱싱
- 이후 실행: 변경된 파일만 인덱싱 (매우 빠름)
- 자동 상태 추적으로 중단/재개 지원

**위치:** `modules/mcp/rag_indexer_incremental.py` (새로 생성)

### 3. 임시 파일 정리
- [x] 모든 `test_*.py` 파일 제거
- [x] 셋업 가이드 문서 제거
- [x] 임시 스크립트 파일 제거
- [x] 관리 도구 파일 제거

**제거된 파일:**
- test_verify_links.py, test_spec_links.py, test_chat_spec_links.py 등
- show_setup_summary.py, start_rag_background.py
- run_rag_background.ps1, run_rag_background.bat
- manage_rag_background.py
- START_RAG_BACKGROUND.md, RAG_BACKGROUND_GUIDE.md, SUCCESS_SETUP.txt

### 4. 서버 배포 준비
- [x] 불필요한 파일 모두 제거
- [x] 핵심 서비스만 유지
- [x] 에러 처리 개선
- [x] 로깅 시스템 유지

---

## 📦 배포용 핵심 파일

### 메인 애플리케이션
```
✅ app.py                      - FastAPI 메인 앱
✅ models.py                   - 데이터 모델
✅ services.py                 - 비즈니스 로직
```

### RAG 시스템 (최적화됨)
```
✅ modules/mcp/rag_indexer_incremental.py   - 새로운 Incremental 인덱서
✅ modules/mcp/rag_indexer.py               - 기본 RAG 인덱서
✅ modules/mcp/rag_retriever.py             - RAG 검색 엔진
✅ rag_background_service.py                - 백그라운드 서비스 (최적화됨)
```

### 인증 & 권한
```
✅ core/auth/                  - 사용자 인증 시스템
✅ modules/mcp/gpt4all_routes.py  - Admin only Chat 라우트
```

### 모듈
```
✅ modules/cits/               - CITS 모듈
✅ modules/rpmt/               - RPMT 모듈
✅ modules/svit/               - SVIT 모듈
✅ modules/spec_center/        - Spec-Center 모듈
```

### 데이터베이스
```
✅ core/db.py                  - DB 연결
✅ *.db                        - SQLite 데이터베이스 파일
✅ rag_knowledge_base.db       - RAG 지식 DB
```

---

## 🚀 배포 단계

### 1단계: 환경 설정 (서버)
```bash
# Python 3.8+ 필요
python --version

# 의존성 설치
pip install -r requirements.txt

# 환경 변수 설정
export DATABASE_URL=postgresql://user:pass@localhost/qms
export SECRET_KEY=your-secret-key-here
```

### 2단계: 데이터베이스 초기화
```bash
# 마이그레이션 실행 (필요시)
python -c "from core.db import init_db; init_db()"
```

### 3단계: RAG 초기 인덱싱 (선택적)
```bash
# 첫 번째 인덱싱은 시간이 걸릴 수 있음 (~10분)
python rag_background_service.py

# 또는 백그라운드로 실행
nohup python rag_background_service.py > rag.log 2>&1 &
```

### 4단계: 서버 시작
```bash
# 개발 모드
python app.py

# 프로덕션 (Uvicorn)
uvicorn app:app --host 0.0.0.0 --port 8000 --workers 4
```

---

## 🔐 권한 설정

### Chat 기능 접근 권한
- Admin 역할 사용자만 `/gpt4all/chat` 접근 가능
- `core/config.py`에서 `GARAGE_ADMIN_EMAILS` 확인 및 설정

### 파일 접근
- 모든 업로드 파일에 대한 읽기 권한 필요
- Linux: `chmod -R 755 uploads/`
- 권한 설정은 배포 스크립트에서 자동 처리

---

## 📊 성능 개선 (Incremental RAG)

### 개선 사항
- **첫 실행:** ~10분 (모든 파일 인덱싱)
- **이후 실행:** ~30초 (변경된 파일만 인덱싱)
- **메모리:** 효율적인 배치 처리
- **CPU:** 파일 해시로 빠른 변경 감지

### 설정
`rag_background_service.py`에서:
```python
# 5분마다 변경 확인 (권장)
service.run_continuous(check_interval=300)

# More frequent (1분마다)
service.run_continuous(check_interval=60)
```

---

## 📋 배포 전 확인 사항

- [ ] Python 3.8+ 설치됨
- [ ] 모든 의존성 설치됨 (`pip install -r requirements.txt`)
- [ ] 환경 변수 설정됨 (DATABASE_URL, SECRET_KEY, etc.)
- [ ] 데이터베이스 마이그레이션 완료
- [ ] 업로드 디렉토리 생성됨 (`uploads/`)
- [ ] RAG DB 초기화됨 (첫 실행시 자동)
- [ ] 로그 디렉토리 쓰기 권한 있음
- [ ] Spec-Center 파일 업로드됨 (선택사항)

---

## 🔍 모니터링

### 실시간 로그 확인
```bash
tail -f logs/app.log
```

### RAG 인덱싱 상태
```bash
cat .rag_indexed_state.json
```

### 백그라운드 서비스 상태
```bash
ps aux | grep rag_background_service.py
```

---

## ⚠️ 주의 사항

1. **RAG 인덱싱 시간**
   - 첫 실행: 10-20분 소요 (파일 크기에 따라 다름)
   - 변경이 없으면 2-3초 만에 완료

2. **Chat 기능**
   - Admin 사용자만 접근 가능
   - 다른 사용자는 403 Forbidden 응답

3. **메모리 사용**
   - RAG DB: ~100-500MB
   - 배치 처리로 메모리 효율화

4. **디스크 공간**
   - RAG DB: ~200-500MB
   - 로그 파일: 정기적 정리 필요

---

## 📞 지원

문제 발생 시:

1. `logs/app.log` 확인
2. `.rag_indexed_state.json` 상태 확인
3. 권한 설정 확인 (`ls -la uploads/`)
4. 데이터베이스 연결 확인

---

**마지막 업데이트:** 2026-02-10
**상태:** ✅ 배포 준비 완료
