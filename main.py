from fastapi import FastAPI

app = FastAPI(title="AITinkerers API")

from api_handlers import log_analyzer_router

@app.get("/")
async def root():
    return {"message": "Welcome to the AITinkerers API!"}

# Include the log analyzer router
app.include_router(log_analyzer_router.router, prefix="/log_analyzer", tags=["Log Analyzer"])

# More endpoints will be added here
