#!/bin/bash

# QMS HTTPS 빠른 설정 스크립트
# 오프라인 환경용 Self-Signed 인증서 생성

set -e

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🔒 QMS HTTPS 설정 시작"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# 설정
CERT_DIR="/etc/ssl/certs"
KEY_DIR="/etc/ssl/private"
CERT_FILE="$CERT_DIR/qms-cert.pem"
KEY_FILE="$KEY_DIR/qms-key.pem"
DAYS_VALID=365

# 도메인/IP 입력
read -p "서버 도메인 또는 IP를 입력하세요 (예: qms.company.local 또는 192.168.1.100): " SERVER_NAME
if [ -z "$SERVER_NAME" ]; then
    SERVER_NAME="qms.local"
    echo "기본값 사용: $SERVER_NAME"
fi

# 1. 디렉토리 생성
echo ""
echo "📁 디렉토리 확인 중..."
mkdir -p $CERT_DIR
mkdir -p $KEY_DIR

# 2. 기존 인증서 백업
if [ -f "$CERT_FILE" ]; then
    echo "⚠️  기존 인증서 발견! 백업 중..."
    sudo mv $CERT_FILE ${CERT_FILE}.backup.$(date +%Y%m%d_%H%M%S)
    sudo mv $KEY_FILE ${KEY_FILE}.backup.$(date +%Y%m%d_%H%M%S)
fi

# 3. Self-Signed 인증서 생성
echo ""
echo "📝 Self-Signed 인증서 생성 중..."
echo "   유효 기간: $DAYS_VALID일"
echo "   서버 이름: $SERVER_NAME"

openssl req -x509 -newkey rsa:4096 -nodes \
  -keyout $KEY_FILE \
  -out $CERT_FILE \
  -days $DAYS_VALID \
  -subj "/C=KR/ST=Seoul/L=Seoul/O=Company/OU=IT Department/CN=$SERVER_NAME" \
  2>/dev/null

# 4. 권한 설정
echo ""
echo "🔐 파일 권한 설정 중..."
chmod 600 $KEY_FILE
chmod 644 $CERT_FILE
chown root:root $KEY_FILE
chown root:root $CERT_FILE

# 5. 인증서 정보 출력
echo ""
echo "✅ 인증서 생성 완료!"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📋 인증서 정보"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
openssl x509 -in $CERT_FILE -noout -subject -dates

# 6. 클라이언트 인증서 복사
echo ""
echo "📦 클라이언트용 인증서 복사 중..."
cp $CERT_FILE ./qms-cert.pem 2>/dev/null || cp $CERT_FILE ./qms-cert.pem
chmod 644 ./qms-cert.pem
echo "   위치: $(pwd)/qms-cert.pem"

# 7. 사용 방법 안내
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🚀 다음 단계"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "1. Uvicorn으로 HTTPS 실행:"
echo "   uvicorn app:app --host 0.0.0.0 --port 8443 \\"
echo "     --ssl-keyfile $KEY_FILE \\"
echo "     --ssl-certfile $CERT_FILE"
echo ""
echo "2. 또는 Nginx 설정 (추천):"
echo "   - qms-nginx.conf 파일 참조"
echo "   - sudo systemctl reload nginx"
echo ""
echo "3. 클라이언트 설정:"
echo "   - Windows: qms-cert.pem을 '신뢰할 수 있는 루트 인증 기관'에 설치"
echo "   - Linux: sudo cp qms-cert.pem /usr/local/share/ca-certificates/qms-cert.crt"
echo "            sudo update-ca-certificates"
echo "   - macOS: sudo security add-trusted-cert -d -r trustRoot -k /Library/Keychains/System.keychain qms-cert.pem"
echo ""
echo "4. 브라우저 접속:"
echo "   https://$SERVER_NAME:8443"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✨ HTTPS 설정 완료!"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
