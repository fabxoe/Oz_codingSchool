import enum


class Gender(str, enum.Enum):
    M = "M"  # male
    F = "F"  # female


class Role(str, enum.Enum):
    PENDING = "PENDING"  # 권한 부여 대기
    STAFF = "STAFF"      # 폐렴 추적 관련 데이터 CRUD 허용
    ADMIN = "ADMIN"      # 전체 데이터 CRUD 허용


class Department(str, enum.Enum):
    MEDICAL = "MEDICAL"    # 의료진
    DEV = "DEV"            # 개발팀
    RESEARCH = "RESEARCH"  # 연구진
