# from icrawler.builtin import GoogleImageCrawler
# import os
# import uuid
# from django.conf import settings
# from .models import InsectsImage

# def crawl_images(ename, quantity):
#     # Generate a unique identifier for the session
#     unique_id = str(uuid.uuid4())
#     tmp_crawler_dir = os.path.join(settings.MEDIA_ROOT, f'tmp_crawler/{unique_id}')
#     os.makedirs(tmp_crawler_dir, exist_ok=True)

#     # Initialize the GoogleImageCrawler with the unique directory
#     google_crawler = GoogleImageCrawler(storage={'root_dir': tmp_crawler_dir})
#     google_crawler.crawl(keyword=ename, max_num=quantity, file_idx_offset='auto')

#     # Return the unique_id to reference in further actions
#     return unique_id

# def get_image_urls(unique_id):
#     tmp_crawler_dir = os.path.join(settings.MEDIA_ROOT, f'tmp_crawler/{unique_id}')
#     image_filenames = os.listdir(tmp_crawler_dir)
#     image_urls = [os.path.join(settings.MEDIA_URL, f'tmp_crawler/{unique_id}', filename) for filename in image_filenames]
#     return image_urls


# def upload_images_from_tmp(insect_id, unique_id):
#     tmp_crawler_dir = os.path.join(settings.MEDIA_ROOT, f'tmp_crawler/{unique_id}')
#     final_images_dir = os.path.join(settings.MEDIA_ROOT, 'images')

#     for filename in os.listdir(tmp_crawler_dir):
#         old_path = os.path.join(tmp_crawler_dir, filename)
#         new_path = os.path.join(final_images_dir, filename)

#         # Move the file
#         os.rename(old_path, new_path)

#         # Create database entry
#         img_id = os.path.splitext(filename)[0]  # Removing file extension for ID
#         url = os.path.join('images', filename)
#         InsectsImage.objects.create(img_id=img_id, url=url, insects_id=insect_id)

#     # Clear the unique tmp_crawler directory after upload
#     os.rmdir(tmp_crawler_dir)  # Remove the unique directory

# def cancel_crawl(unique_id):
#     tmp_crawler_dir = os.path.join(settings.MEDIA_ROOT, f'tmp_crawler/{unique_id}')
#     for filename in os.listdir(tmp_crawler_dir):
#         os.remove(os.path.join(tmp_crawler_dir, filename))
#     os.rmdir(tmp_crawler_dir)  # Remove the unique directory
#     print("Crawling cancelled, temporary images deleted.")

import os
import shutil
from google_images_download import google_images_download
from .models import Species, InsectsImage

def download_images(keyword, quantity):
    response = google_images_download.googleimagesdownload()

    # Create a directory for temporary storage if it doesn't exist
    tmp_crawler_dir = os.path.join('media', 'tmp_crawler')
    os.makedirs(tmp_crawler_dir, exist_ok=True)

    # Download images
    arguments = {
        "keywords": keyword,
        "limit": quantity,
        "output_directory": tmp_crawler_dir,
        "no_directory": True,
    }
    rs_data = response.download(arguments)
    print('rs_data',rs_data)
    # Move downloaded images to the final directory
    images = []
    if len(rs_data) ==0:
        return images
    for keyword, paths in rs_data[0].items():
        for path in paths:
            image_name = os.path.basename(path)
            new_path = os.path.join('media', 'images', image_name)
            shutil.move(path, new_path)
            images.append(new_path)

    return images


def delete_tmp_images():
    tmp_crawler_dir = os.path.join('media', 'tmp_crawler')
    shutil.rmtree(tmp_crawler_dir, ignore_errors=True)


def save_images_to_database(images, species_id):
    for image_path in images:
        image_name = os.path.basename(image_path)
        img_id, _ = os.path.splitext(image_name)
        img = InsectsImage.objects.create(img_id=img_id, url=os.path.join('images', image_name), insects_id=species_id)
        img.save()

