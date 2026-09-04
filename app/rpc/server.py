"""gRPC 서버 기동/종료."""

from __future__ import annotations

import logging

import grpc

from app.core.config import get_settings
from app.rpc.proto import auth_service_pb2_grpc
from app.rpc.service import AuthServiceServicer

logger = logging.getLogger(__name__)


def create_server() -> grpc.aio.Server:
    settings = get_settings()
    server = grpc.aio.server()
    auth_service_pb2_grpc.add_AuthServiceServicer_to_server(AuthServiceServicer(), server)

    address = f"0.0.0.0:{settings.grpc_port}"
    if settings.grpc_tls_cert and settings.grpc_tls_key:
        credentials = grpc.ssl_server_credentials(
            [(settings.grpc_tls_key.encode("utf-8"), settings.grpc_tls_cert.encode("utf-8"))]
        )
        server.add_secure_port(address, credentials)
    else:
        logger.warning(
            "GRPC_TLS_CERT/GRPC_TLS_KEY가 설정되지 않아 gRPC 서버를 TLS 없이 기동합니다. "
            "운영 환경에서는 반드시 TLS 인증서를 설정하세요."
        )
        server.add_insecure_port(address)

    return server
