"""
Gateway API for Trading-Copilot
Layer 2 in the architecture
"""
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union
import logging

from fastapi import FastAPI, Depends, HTTPException, status, WebSocket, WebSocketDisconnect
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.middleware.cors import CORSMiddleware
from jose import JWTError, jwt
from pydantic import BaseModel

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Constants
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "REPLACE_WITH_SECURE_SECRET_KEY")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60

# Models
class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: Optional[str] = None

class User(BaseModel):
    username: str
    disabled: Optional[bool] = None

class UserInDB(User):
    hashed_password: str

class QueryRequest(BaseModel):
    query: str
    context: Optional[Dict[str, Any]] = None

class QueryResponse(BaseModel):
    response: str
    created_at: datetime
    execution_time_ms: float
    context: Optional[Dict[str, Any]] = None
    chart_uri: Optional[str] = None

# Authentication functions
def get_user(username: str) -> Optional[UserInDB]:
    # In a real system, this would query a database
    # For demo purposes, we use a hardcoded user
    if username == "demo":
        return UserInDB(
            username="demo", 
            hashed_password="$2b$12$CqxrHXmDtrDm5viDXTGQpORIBKVoFg/PgQaQx9eI6P3NVKucxYi2y",  # "password"
            disabled=False
        )
    return None

def authenticate_user(username: str, password: str) -> Optional[User]:
    # In production, use proper password hashing
    user = get_user(username)
    if not user:
        return None
    # Mock verification - in production use proper password verification
    if password != "password":  # This is just for demo
        return None
    return user

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

# Dependency
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

async def get_current_user(token: str = Depends(oauth2_scheme)) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
        token_data = TokenData(username=username)
    except JWTError:
        raise credentials_exception
    user = get_user(username=token_data.username)
    if user is None:
        raise credentials_exception
    return user

# WebSocket Connection Manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def send_text(self, message: str, websocket: WebSocket):
        await websocket.send_text(message)

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            await connection.send_text(message)

# Initialize FastAPI app
app = FastAPI(title="Trading-Copilot Gateway API")
manager = ConnectionManager()

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, restrict this to your frontend domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Endpoints
@app.post("/token", response_model=Token)
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    user = authenticate_user(form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

@app.post("/ask", response_model=QueryResponse)
async def ask_question(
    request: QueryRequest,
    current_user: User = Depends(get_current_user)
):
    """
    Endpoint to ask natural language questions about trading performance
    """
    # Import with proper path now that parent directory is in sys.path
    from user_data.trading_copilot.orchestrator.main import process_query
    
    start_time = datetime.now()
    
    # Scrub any sensitive information from the request
    clean_request = scrub_sensitive_info(request)
    
    # Forward the request to the orchestrator
    try:
        result = await process_query(clean_request.query, clean_request.context)
        execution_time = (datetime.now() - start_time).total_seconds() * 1000  # ms
        
        response = QueryResponse(
            response=result["response"],
            created_at=datetime.now(),
            execution_time_ms=execution_time,
            context=result.get("context"),
            chart_uri=result.get("chart_uri")
        )
        return response
    except Exception as e:
        logger.error(f"Error processing query: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing query: {str(e)}"
        )

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            # Process the received message
            from user_data.trading_copilot.orchestrator.main import process_streaming_query
            
            # Start processing in a stream
            async for chunk in process_streaming_query(data):
                await manager.send_text(chunk, websocket)
    except WebSocketDisconnect:
        manager.disconnect(websocket)

def scrub_sensitive_info(request: QueryRequest) -> QueryRequest:
    """
    Remove any sensitive information like API keys or account IDs from the request
    """
    # Implement scrubbing logic here
    # For example, using regex to detect and mask API keys
    return request

# Main entry point
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("gateway:app", host="0.0.0.0", port=8000, reload=True)
