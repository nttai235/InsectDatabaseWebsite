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
    columns = ['item_id', 'image_id', 'name', 'description', 'category', 'category_name']
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
            species.ename if species else None,
            'A photo of ' + species.name if species else None,
            image.insects_id if species else None,
            species.name if species else None
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