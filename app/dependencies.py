from fastapi import HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError
from fastapi import Depends

import os
SECRET_KEY = os.getenv("SECRET_KEY", "influencia-chave-super-secreta-2024")
ALGORITHM = "HS256"

oauth2_scheme = HTTPBearer()

def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(oauth2_scheme)
):
    token = credentials.credentials
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username = payload.get("sub")
        if username is None:
            raise HTTPException(status_code=401, detail="Token invalido")
        return username
    except JWTError:
        raise HTTPException(status_code=401, detail="Token invalido")
