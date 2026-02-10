@echo off
REM GitHub에 QMS_SERVER 푸시 및 빌드 트리거

echo === QMS_SERVER를 GitHub에 푸시 ===
echo.

REM 현재 디렉토리 확인
cd /d "%~dp0"
echo Current directory: %cd%

REM Git 확인
git --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Git이 설치되지 않았습니다.
    echo https://git-scm.com/download/win 에서 설치하세요.
    exit /b 1
)

echo.
echo [1/5] Git 저장소 초기화...
git init

echo [2/5] 모든 파일 추가...
git add .

echo [3/5] 커밋...
git commit -m "Add GitHub Actions workflow for llama.cpp NATIVE build - Rocky 8.10"

echo [4/5] main 브랜치로 설정...
git branch -M main

echo [5/5] GitHub 원격 저장소 설정...
REM YOUR_USERNAME을 본인의 GitHub 사용자명으로 변경하세요
set GITHUB_USERNAME=YOUR_USERNAME
set REPO_NAME=QMS_SERVER

git remote add origin https://github.com/%GITHUB_USERNAME%/%REPO_NAME%.git

echo.
echo === GitHub 푸시 ===
echo [경고] GitHub 계정 인증 필요:
echo - https://github.com/settings/tokens에서 Personal Access Token 생성
echo - Token scope: repo (Full control of private repositories)
echo.

git push -u origin main

echo.
echo === 빌드 트리거 (태그 생성) ===
echo 태그를 생성하면 자동으로 GitHub Actions 빌드가 시작됩니다.
echo.

set BUILD_TAG=v1.0.0-llama-native

echo 태그 생성: %BUILD_TAG%
git tag %BUILD_TAG%

echo 태그 푸시 (빌드 시작)...
git push origin %BUILD_TAG%

echo.
echo === 완료! ===
echo GitHub Actions에서 빌드 진행 중입니다:
echo https://github.com/%GITHUB_USERNAME%/%REPO_NAME%/actions
echo.
echo 20~30분 후에 다음 위치에서 빌드 결과 다운로드:
echo Artifacts (GitHub Actions 페이지):
echo  - llama-main-native-rocky8.10
echo  - llama_cpp_python-*.whl
echo.
echo 또는 Releases 탭에서 자동 생성된 릴리스별로 다운로드.
echo.
pause
