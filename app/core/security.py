from pwdlib import PasswordHash

# Argon2 기반 해시 도구 생성
password_hash = PasswordHash.recommended()

# 1. 해시 생성 (회원가입 시 사용)
def hash_password(password: str) -> str:
    return password_hash.hash(password)

# 2. 해시 검증 (로그인 시 사용)
def verify_password(plain_password: str, hashed_password: str) -> bool:
    return password_hash.verify(plain_password, hashed_password)
