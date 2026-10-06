#!/usr/bin/env bash
# 공통 계약 레포(기본 ../grpcs/proto)의 auth_service.proto로부터
# app/rpc/proto 아래 Python gRPC stub을 재생성한다.
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CONTRACTS_DIR="${CONTRACTS_DIR:-$ROOT_DIR/../grpcs/proto}"
OUT_DIR="$ROOT_DIR/app/rpc/proto"

if [ ! -f "$CONTRACTS_DIR/grpc/auth_service.proto" ]; then
  echo "CONTRACTS_DIR에 공통 계약 레포의 proto 디렉터리를 지정하세요: $CONTRACTS_DIR" >&2
  exit 1
fi

mkdir -p "$OUT_DIR"

python -m grpc_tools.protoc \
  -I "$CONTRACTS_DIR/grpc" \
  --python_out="$OUT_DIR" \
  --grpc_python_out="$OUT_DIR" \
  --pyi_out="$OUT_DIR" \
  "$CONTRACTS_DIR/grpc/auth_service.proto"

# grpc_tools가 생성하는 최상위 절대 import를 패키지 상대 import로 교체한다.
sed -i.bak \
  "s/^import auth_service_pb2 as auth__service__pb2$/from . import auth_service_pb2 as auth__service__pb2/" \
  "$OUT_DIR/auth_service_pb2_grpc.py"
rm -f "$OUT_DIR/auth_service_pb2_grpc.py.bak"

touch "$OUT_DIR/__init__.py"

echo "Generated stubs in $OUT_DIR"
