import os
import pandas as pd
from django.conf import settings
from .models import InsectsImage
import uuid
import csv 

def export_species_data_to_csv():  
    # Prefetch related data
    images_data = InsectsImage.objects.select_related(
        'insects',
        'insects__genus',
        'insects__genus__family',
        'insects__genus__family__order',
        'insects__genus__family__order__class_field',
        'insects__genus__family__order__class_field__phylum',
        'insects__genus__family__order__class_field__phylum__kingdom'
    )

    # Define column names and initialize a list for data rows
    columns = ['insect_id', 'image_id', 'url', 'Tên khoa học', 'Tên Việt Nam', 'Kingdom', 'Phylum (Ngành)', 
    'Class (Lớp)', 'Order (Bộ)', 'Family (Họ)', 'Genus (Chi)', 'Đặc điểm sinh học', 'Phân bố', 'Hình Thái', 'Tập tính sinh hoạt', 'Biện pháp phòng trừ']
    data_rows = []

    # Populate data rows
    for image in images_data:
        species = image.insects
        genus = species.genus if species else None
        family = genus.family if genus else None
        order = family.order if family else None
        class_field = order.class_field if order else None
        phylum = class_field.phylum if class_field else None
        kingdom = phylum.kingdom if phylum else None

        data_rows.append([
            species.insects_id if species else None,
            image.img_id,
            image.url,
            species.ename if species else None,
            species.name if species else None,
            kingdom.ename if kingdom else None,
            phylum.ename if phylum else None,
            class_field.ename if class_field else None,
            order.ename if order else None,
            family.ename if family else None,
            genus.ename if genus else None,
            species.characteristic if species else None,
            species.distribution if species else None,
            species.morphologic_feature if species else None,
            species.behavior if species else None,
            species.protection_method if species else None
        ])


    # Create DataFrame from data
    df = pd.DataFrame(data_rows, columns=columns)
    
    # Replace \n with ' | ' in the DataFrame
    df.replace('\n', ' ', regex=True, inplace=True)

    # Get media root directory and file path
    media_root = settings.MEDIA_ROOT
    unique_filename = f"IP102_data_{uuid.uuid4()}.csv"
    file_path = os.path.join(media_root, unique_filename)

    # Write DataFrame to CSV file, ensuring all fields are quoted without 'line_terminator'
    df.to_csv(file_path, index=True, encoding='utf-8-sig', quoting=csv.QUOTE_NONNUMERIC)

    # Return the file path
    return file_path