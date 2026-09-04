#!/usr/bin/env bash
# moaje-grpc-contracts(third_party/moaje-grpc-contracts submodule)의 auth_service.proto로부터
# app/rpc/proto 아래 Python gRPC stub을 재생성한다.
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CONTRACTS_DIR="$ROOT_DIR/third_party/moaje-grpc-contracts/proto"
OUT_DIR="$ROOT_DIR/app/rpc/proto"

if [ ! -f "$CONTRACTS_DIR/grpc/auth_service.proto" ]; then
  echo "moaje-grpc-contracts submodule이 초기화되지 않았습니다. 'git submodule update --init' 를 먼저 실행하세요." >&2
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
