if __name__ == "__main__":
    import uvicorn
    from src.main import create_app
    app = create_app()
    uvicorn.run(app, host="0.0.0.0", port=7860)
