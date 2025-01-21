from rest_framework import serializers
from .models import Species, InsectsImage, InsectsBbox
from django.db import models
from PIL import Image as PilImage
from io import BytesIO
import requests
from django.shortcuts import render
import os
from django.conf import settings

class SpeciesSerializer(serializers.ModelSerializer):
    class Meta:
        model = Species
        fields = ['insects_id', 'ename', 'name', 'eng_name', 'slug', 'distribution', 'characteristic', 
                  'behavior', 'morphologic_feature', 'protection_method', 'thumbnail', 'genus']
        

class ImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = InsectsImage
        fields = ['img_id', 'url', 'insects']

        
class BoundingBoxSerializer(serializers.ModelSerializer):
    x = serializers.SerializerMethodField()
    y = serializers.SerializerMethodField()
    width = serializers.SerializerMethodField()
    height = serializers.SerializerMethodField()

    class Meta:
        model = InsectsBbox
        fields = ['box_id', 'x', 'y', 'width', 'height', 'img']

    def convert_yolo_to_pixel(self, value, img_dimension):
        return value * img_dimension

    def get_absolute_url(self):
        return os.path.join(settings.MEDIA_URL, self.img.url)

    def get_image_dimensions(self, url):
        if not url.startswith(('http://', 'https://')):
            # Assuming 'request' is correctly passed in the context to the serializer
            request = self.context.get('request')
            if request:
                url = request.build_absolute_uri(url)
            else:
                raise ValueError("Cannot build absolute URL without request context")
        response = requests.get(url)
        img = PilImage.open(BytesIO(response.content))
        return img.width, img.height


    def get_x(self, obj):
        img_width, _ = self.get_image_dimensions(obj.img.get_absolute_url())
        return self.convert_yolo_to_pixel(obj.x, img_width)

    def get_y(self, obj):
        _, img_height = self.get_image_dimensions(obj.img.get_absolute_url())
        return self.convert_yolo_to_pixel(obj.y, img_height)

    def get_width(self, obj):
        img_width, _ = self.get_image_dimensions(obj.img.get_absolute_url())
        return self.convert_yolo_to_pixel(obj.width, img_width)

    def get_height(self, obj):
        _, img_height = self.get_image_dimensions(obj.img.get_absolute_url())
        return self.convert_yolo_to_pixel(obj.height, img_height)


class ImageBoxSerializer(serializers.ModelSerializer):
    bboxes = BoundingBoxSerializer(many=True, read_only=True)

    class Meta:
        model = InsectsImage
        fields = ['img_id', 'url', 'insects', 'bboxes']