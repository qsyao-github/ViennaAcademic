"""
多用户系统，用户认证和授权及其文件系统初始化
"""

import os
from datetime import datetime, timedelta, timezone
from typing import Annotated, Optional

import jwt
import psycopg
from dotenv import load_dotenv
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jwt.exceptions import InvalidTokenError
from passlib.context import CryptContext
from pydantic import BaseModel

# 初始化所有环境变量
load_dotenv()

# 连接用户数据库
conn = psycopg.connect(
    conninfo="postgresql://vienna_academic:vienna_academic@postgres:5432/vadb"
)
cursor = conn.cursor()

# 初始化表
cursor.execute(
    """
    CREATE TABLE IF NOT EXISTS users (
        id SERIAL PRIMARY KEY,
        username VARCHAR(16) UNIQUE NOT NULL,
        password_hash CHAR(60) NOT NULL
    );
"""
)
conn.commit()

# 设立用户文件系统
DIRECTORIES = ("code", "knowledgeBase", "paper", "convert", "retrievers")
cursor.execute("SELECT username FROM users;")
for user in cursor.fetchall():
    for directory in DIRECTORIES:
        os.makedirs(f"documents/{user[0]}/{directory}", exist_ok=True)


# 初始化密钥，数据类型，token有效期
SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 1080


class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    username: str | None = None


class User(BaseModel):
    username: str
    hashed_password: str


class NewUser(BaseModel):
    id: str
    username: str


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


def get_user(username: str) -> Optional[User]:
    """
    从数据库中获取用户名和哈希加密密码

    若不存在，返回None
    """
    cursor.execute(
        """SELECT username, password_hash FROM users WHERE username = %s;""",
        (username,),
    )
    if result := cursor.fetchone():
        return User(username=result[0], hashed_password=result[1])


def authenticate_user(username: str, password: str) -> Optional[User]:
    """
    通过用户名或密码认证用户，获取用户信息

    若认证未通过，返回None
    """
    user = get_user(username)
    if not user:
        return None
    if not pwd_context.verify(password, user.hashed_password):
        return None
    return user


def create_access_token(data: dict, expires_delta: timedelta | None = None):
    """
    获取jwt token
    """
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=60)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


async def get_current_user(token: Annotated[str, Depends(oauth2_scheme)]):
    """
    根据jwt token获取认证用户
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username = payload.get("sub")
        if username is None:
            raise credentials_exception
        token_data = TokenData(username=username)
    except InvalidTokenError:
        raise credentials_exception
    user = get_user(username=token_data.username)
    if user is None:
        raise credentials_exception
    return user
