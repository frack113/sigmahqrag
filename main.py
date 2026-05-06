if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "src.main:create_app", host="0.0.0.0", port=7860, reload=True, factory=True
    )
