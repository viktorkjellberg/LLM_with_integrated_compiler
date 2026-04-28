from pathlib import Path
import shutil


def copy_language_named_files(source_folder, destination_folder):
    source = Path(source_folder)
    destination = Path(destination_folder)

    if not source.exists():
        raise FileNotFoundError(f"Source folder does not exist: {source}")

    if not source.is_dir():
        raise NotADirectoryError(f"Source path is not a folder: {source}")

    prefixes = ("java_", "c_", "python_")

    for file_path in source.rglob("*"):
        if file_path.is_file():
            filename = file_path.name.lower()

            if filename.startswith(prefixes):
                relative_path = file_path.relative_to(source)
                target_path = destination / relative_path

                target_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(file_path, target_path)


if __name__ == "__main__":
    source_folder = "output_alvis_new_2026_04_21"
    destination_folder = "output_alvis_new"
    print(f"Copying files from '{source_folder}' to '{destination_folder}'...")
    input("Press Enter to continue...")
    copy_language_named_files(source_folder, destination_folder)