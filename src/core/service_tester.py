import asyncio

from src.core.service_manager import create_service_manager


async def main():
    # Create an instance of ServiceManager
    service_manager = create_service_manager()

    # Download or update binaries
    print("Downloading/updating binaries...")
    result = await service_manager.download_or_update_binaries()
    print("Download/update result:", result)

    if not result["success"]:
        print("Failed to download or update binaries.")
        return

    # Debug: Verify binary paths and existence
    print(f"llama.cpp path: {service_manager.llama_bin}")
    print(f"Qdrant path: {service_manager.qdrant_bin}")

    if not service_manager.llama_bin.exists():
        print("Error: llama.cpp binary does not exist.")
        return
    else:
        print(f"llama.cpp exists and is a file: {service_manager.llama_bin.is_file()}")

    if not service_manager.qdrant_bin.exists():
        print("Error: Qdrant binary does not exist.")
        return
    else:
        print(f"Qdrant exists and is a file: {service_manager.qdrant_bin.is_file()}")

    # Start services (binaries are expected to exist now)
    print("Starting services...")
    llama_start_result = await service_manager.start_llama(
        model_path="path/to/model.bin", port=8080
    )
    qdrant_start_result = await service_manager.start_qdrant()

    print("Llama start result:", llama_start_result)
    print("Qdrant start result:", qdrant_start_result)

    if not llama_start_result["success"] or not qdrant_start_result["success"]:
        print("Failed to start one or both services.")
        return

    # Check status after starting
    print("Checking service status...")
    llama_status = (
        await service_manager.llama_service_status()
    )  # Placeholder for status method (not implemented)
    qdrant_status = (
        await service_manager.qdrant_service_status()
    )  # Placeholder for status method (not implemented)

    print("Llama status:", llama_status)
    print("Qdrant status:", qdrant_status)


if __name__ == "__main__":
    asyncio.run(main())
