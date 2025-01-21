import os
import zipfile
from django.core.files.storage import default_storage
from django.conf import settings

def handle_uploaded_folder(upload_folder):
    # Get list of files in the folder
    files = os.listdir(upload_folder)
    valid_extensions = ('.jpg', '.jpeg', '.png', '.gif', '.txt', '.xml')
    invalid_files = []

    # Check each file for valid extensions
    for file in files:
        _, ext = os.path.splitext(file)
        if ext.lower() not in valid_extensions:
            invalid_files.append(file)

    if invalid_files:
        print("Invalid files found in the folder:", invalid_files)
        return False
    else:
        # Move valid files to the media/test directory
        destination = os.path.join(settings.MEDIA_ROOT, 'test')
        os.makedirs(destination, exist_ok=True)
        for file in files:
            source_path = os.path.join(upload_folder, file)
            destination_path = os.path.join(destination, file)
            default_storage.move(source_path, destination_path)
        return True

def handle_uploaded_zip(zip_file):
    # Extract the zip file
    with zipfile.ZipFile(zip_file, 'r') as zip_ref:
        zip_ref.extractall(settings.MEDIA_ROOT)

    # Get the extracted folder path
    extracted_folder = os.path.join(settings.MEDIA_ROOT, zip_file.name.split('.')[0])

    # Handle the extracted folder as normal
    return handle_uploaded_folder(extracted_folder)
