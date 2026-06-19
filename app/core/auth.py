import jwt
from fastapi import HTTPException, Depends, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from ..schemas.config import settings

security_schema = HTTPBearer()

async def verify_auth0_token(credentials: HTTPAuthorizationCredentials = Depends(security_schema)) -> dict:
    token = credentials.credentials

    try:
        jwks_url = f'http://{settings.AUTH0_DOMAIN}/.well-known/jwks.json'
        jwks_client = jwt.PyJWKClient(jwks_url)
        signing_key = jwks_client.get_signing_key_from_jwt(token)

        payload = jwt.decode(
            token,
            signing_key.key,
            algorithms=[settings.ALGORITHM],
            audience=settings.AUTH0_AUDIENCE,
            issuer=f'http://{settings.AUTH0_DOMAIN}/'
        )
        return payload
    except jwt.PyJWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f'Invalid token Auth0: {str(e)}'
        )