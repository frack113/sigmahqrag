import os
from pathlib import Path
from huggingface_hub import hf_hub_download
import shutil

def perform_download():
    repo_id = "sentence-transformers/all-MiniLM-L6-v2"
    filename = "config.json"  # We'll download config.json as a proxy for the model
    target_dir = Path("./models/embeddings/sentence-transformers/all-MiniLM-L6-v2")
    
    print(f"Starting download of {repo_id} ({filename})")
    print(f"Target directory: {target_dir.absolute()}")

    try:
        # Ensure target directory exists
        target_dir.mkdir(parents=True, exist_ok=True)

        # Download the file using hf_hub_download
        # This returns the path to the downloaded file in the HF cache
        downloaded_path = hf_hub_download(repo_id=repo_id, filename=filename)
        print(f"Downloaded file from cache: {download_path}")

        # Define destination path
        dest_path = target_dir / filename
        
        # Copy/Move the file to the final destination
        shutil.copy2(downloaded_path, dest_path)
        print(f"Successfully moved file to: {dest_path}")

        if dest_path.exists():
            print("Verification: File exists at target location.")
        else:
            print("Error: File NOT found at target location.")

    except Exception as e:
        print(f"An error occurred during the download process: {e}")

if __name__ == "__main__":
    perform_download()
