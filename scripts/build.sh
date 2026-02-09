#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." >/dev/null && pwd)"
cd "$REPO_ROOT"

if command -v python3.11 >/dev/null 2>&1; then PY=python3.11; else PY=python3; fi

BUILD_VENV_DIR="../venv_rsch_qms"
if [ "${USE_EXISTING_VENV:-0}" = "1" ]; then
    if [ ! -d ".venv" ]; then
        echo "Creating project .venv with $PY"
        $PY -m venv .venv
    fi
    echo "Using project .venv for build (USE_EXISTING_VENV=1)"
    source ../venv_rsch_qms/bin/activate
else
    if [ ! -d "$BUILD_VENV_DIR" ]; then
        echo "Creating isolated build venv at $BUILD_VENV_DIR with $PY"
        $PY -m venv "$BUILD_VENV_DIR"
    fi
    source "$BUILD_VENV_DIR/bin/activate"
fi

if pip show pathlib >/dev/null 2>&1; then
    if [ "${USE_EXISTING_VENV:-0}" = "1" ]; then
        echo "\nERROR: The active venv contains the incompatible 'pathlib' backport which PyInstaller refuses to run with." >&2
        echo "Either uninstall it from the venv (pip uninstall pathlib) or run the build without USE_EXISTING_VENV so an isolated build venv will be used." >&2
        exit 1
    else
        echo "Found 'pathlib' in build venv; uninstalling to avoid PyInstaller error..."
        pip uninstall -y pathlib || true
    fi
fi

if [ -f ./scripts/make_icon.py ]; then
    echo "Generating icon (if possible)"
    set +e
    python ./scripts/make_icon.py
    set -e
fi


ICON_PATH="${REPO_ROOT}/static/icons/qms-q.ico"
if [ -f "$ICON_PATH" ]; then
    ICON_ARG="--icon=$ICON_PATH"
    echo "Using icon: $ICON_PATH"
else
    ICON_ARG=""
    echo "Icon not found; building without icon"
fi

if [ -x "${REPO_ROOT}/scripts/upx/upx" ]; then
    UPX_DIR="$(dirname "${REPO_ROOT}/scripts/upx/upx")"
    UPX_ARG="--upx-dir=$UPX_DIR"
    echo "Using local UPX from $UPX_DIR"
elif command -v upx >/dev/null 2>&1; then
    UPX_DIR="$(dirname "$(readlink -f "$(command -v upx)")")"
    UPX_ARG="--upx-dir=$UPX_DIR"
    echo "Using system UPX from $UPX_DIR"
else
    UPX_ARG=""
    echo "UPX not found; skipping UPX compression"
fi

EXCLUDE_ARGS=(
    "--exclude-module=pandas"
    "--exclude-module=sqlalchemy"
    "--exclude-module=fastapi"
    "--exclude-module=uvicorn"
    "--exclude-module=numpy"
    "--exclude-module=openpyxl"
    "--exclude-module=scipy"
    "--exclude-module=pathlib"
)

EXCLUDE_STR="${EXCLUDE_ARGS[*]}"

run_pyinstaller() {
    echo "Running PyInstaller (UPX: ${UPX_ARG:+yes})"
    pyinstaller --noconfirm --onefile --clean --windowed --name qms-desktop $ICON_ARG $UPX_ARG $EXCLUDE_STR app_desktop_qt.py
}

set +e
run_pyinstaller
rc=$?
set -e
if [ $rc -ne 0 ]; then
    echo "PyInstaller failed on first attempt (rc=$rc); retrying without UPX..."
    set +e
    pyinstaller --noconfirm --onefile --clean --windowed --name qms-desktop $ICON_ARG $EXCLUDE_STR app_desktop_qt.py
    rc2=$?
    set -e
    if [ $rc2 -ne 0 ]; then
        echo "PyInstaller failed on retry without UPX (rc=$rc2). Check the build logs above." >&2
        exit $rc2
    fi
fi

mkdir -p ./static/downloads
if [ -f ./dist/qms-desktop ]; then
    cp -f ./dist/qms-desktop ./static/downloads/qms-desktop
    size=$(stat -c%s "./static/downloads/qms-desktop")
    sha256=$(sha256sum "./static/downloads/qms-desktop" | awk '{print $1}')
    builtAt=$(date -Iseconds)
    gitHash=""
    if command -v git >/dev/null 2>&1; then
        gitHash=$(git rev-parse --short HEAD 2>/dev/null || true)
    fi
    cat > ./static/downloads/qms-desktop.json <<EOF
{
  "file": "qms-desktop.exe",
  "sizeBytes": $size,
  "sha256": "$sha256",
  "builtAt": "$builtAt",
  "git": "$gitHash"
}
EOF
    echo "Built and copied to static/downloads/qms-desktop (Size: $size bytes)"
else
    echo "Build failed: dist/qms-desktop not found" >&2
    exit 1
fi

exit 0
