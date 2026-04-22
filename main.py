if __name__ == "__main__":
    import uvicorn
    from src.sigmahqrag.main import app
    uvicorn.run(app, host="0.0.0.0", port=7860)
