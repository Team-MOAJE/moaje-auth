"""DB connection & session

## 목표
- MySQL 연결 (SQLAlchemy)
- FastAPI 의존성 주입용 get_db() 제공
- ORM Base 제공

## MySQL 유의할 점 ... 
- InnoDB + utf8mb4 권장
- 타임존/Datetime 정책(UTC 저장) 결정 필요 ? 
"""

# TODO(구현 시):
# - create_engine(DATABASE_URL, pool_pre_ping=True, future=True)
# - SessionLocal = sessionmaker(...)
# - Base = declarative_base()
# - def get_db(): yield db

