import uvicorn
from app.core.config import settings    

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        port=settings.APP_PORT,
        reload=True if settings.environment == "dev" else False  
    )