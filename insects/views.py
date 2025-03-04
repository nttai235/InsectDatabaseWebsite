import re

from django.shortcuts import redirect
from django.conf import settings
from .models import InsectsImage, Species, InsectsBbox, Genus, RequestDesc, Document, Class, Family, Order, Phylum
from insects.templatetags.forms import UserEditForm
from django.core.paginator import Paginator
from django.utils.text import slugify
from django.core.files.base import ContentFile
from django.http import Http404, HttpResponse, FileResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.contrib.auth.models import User, Group
from django.contrib.auth.hashers import make_password
from PIL import Image
import json
import zipfile
from django.contrib.auth import authenticate, login as django_login, logout, update_session_auth_hash
from .serializers import SpeciesSerializer, ImageSerializer, ImageBoxSerializer, BoundingBoxSerializer
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.parsers import MultiPartParser
from django.shortcuts import render, get_object_or_404
import os
# from .excel_export import export_species_data_to_csv
from .excel_export_1 import export_species_data_to_csv
from django.core.files.storage import default_storage
from django.http import JsonResponse, HttpResponseBadRequest
from .crawler import download_images, delete_tmp_images, save_images_to_database
from django.db.models import Q, OuterRef, Subquery
import uuid

# NQA
from django.db.models import Count


# End NQA


def convert_yolo_to_pixel(x, y, width, height, img_width, img_height):
    # Convert the center coordinates from relative to absolute pixel values
    x_center = x * img_width
    y_center = y * img_height

    # Convert the width and height from relative to absolute pixel values
    box_width = width * img_width
    box_height = height * img_height

    # Calculate the top left corner coordinates
    x_top_left = x_center - (box_width / 2)
    y_top_left = y_center - (box_height / 2)

    return x_top_left, y_top_left, box_width, box_height


# annotations section
def labelling(request):
    insect_id = request.GET.get('insectId')
    if insect_id:
        # Handle AJAX request
        images = InsectsImage.objects.filter(insects_id=insect_id).prefetch_related('bboxes')
        images_data = []
        for image in images:
            img_path = os.path.join(settings.MEDIA_ROOT, image.url)
            with Image.open(img_path) as img:
                img_width, img_height = img.size

            bboxes_data = []
            for bbox in image.bboxes.all():
                x_top_left, y_top_left, box_width, box_height = convert_yolo_to_pixel(
                    bbox.x, bbox.y, bbox.width, bbox.height, img_width, img_height)
                converted_bbox = {
                    'x': x_top_left, 'y': y_top_left,
                    'width': box_width, 'height': box_height
                }
                bboxes_data.append(converted_bbox)

            images_data.append({
                'img_id': image.img_id,  # Make sure this id exists and matches the model field
                'url': settings.MEDIA_URL + image.url,
                'width': img_width,
                'height': img_height,
                'insectsId': image.insects_id,
                'insectsName': image.insects.name,
                'bboxes': bboxes_data,
            })

        return JsonResponse({'images': images_data})

    # Handle non-AJAX request
    species_list = Species.objects.all()
    return render(request, 'Labelling.html', {'species_list': species_list})


def get_image_data(request):
    img_id = request.GET.get('imgId')
    image = InsectsImage.objects.filter(img_id=img_id).first()
    if image:
        # Construct the full path to the image file
        img_path = os.path.join(settings.MEDIA_ROOT, image.url)

        # Open the image to obtain its size
        try:
            with Image.open(img_path) as img:
                width, height = img.size
        except IOError:
            return JsonResponse({'error': 'Failed to open image file.'}, status=500)

        # Construct bounding boxes list
        bboxes = list(image.bboxes.values('x', 'y', 'width', 'height'))

        # Return all necessary data, including the image's width and height
        return JsonResponse({
            'url': image.get_absolute_url(),
            'bboxes': bboxes,
            'width': width,
            'height': height
        })
    else:
        return JsonResponse({'error': 'Image not found'}, status=404)


# def get_image_data(request):
#     img_id = request.GET.get('imgId')
#     image = InsectsImage.objects.filter(img_id=img_id).first()
#     if image:
#         bboxes = list(image.bboxes.values('x', 'y', 'width', 'height'))
#         return JsonResponse({'url': image.get_absolute_url(), 'bboxes': bboxes})
#     return JsonResponse({'error': 'Image not found'}, status=404)

@csrf_exempt
@require_POST
def save_bboxes(request):
    try:
        img_id = request.GET.get('imgId')
        data = json.loads(request.body)
        bboxes_data = data.get('bboxes', [])

        image = InsectsImage.objects.get(img_id=img_id)  # Ensure this matches your model's field name

        # Consider updating existing boxes rather than deleting
        InsectsBbox.objects.filter(img=image).delete()  # Caution: This deletes existing boxes!

        for bbox in bboxes_data:
            InsectsBbox.objects.create(
                x=bbox['x'],
                y=bbox['y'],
                width=bbox['width'],
                height=bbox['height'],
                img=image
            )
        return JsonResponse({'status': 'success'})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


def annotation(request):
    img_id = request.GET.get('imgId')
    context = {'img_id': img_id}
    return render(request, 'annotation.html', context)


# home.html section
def show_insect_images(request):
    page_number = request.GET.get('page', 1)  # Get the page number from the request
    images = InsectsImage.objects.all().prefetch_related('bboxes')
    paginator = Paginator(images, 20)  # Create a Paginator object with 20 images per page
    images = paginator.get_page(page_number)  # Get the images for the requested page

    # Convert the bounding box coordinates for each image
    for image in images:
        # Open the image and get its size
        img_path = os.path.join(settings.MEDIA_ROOT, image.url)
        with Image.open(img_path) as img:
            img_width, img_height = img.size

        image.width = img_width
        image.height = img_height

        for bbox in image.bboxes.all():
            bbox.x, bbox.y, bbox.width, bbox.height = convert_yolo_to_pixel(bbox.x, bbox.y, bbox.width, bbox.height,
                                                                            img_width, img_height)

    return render(request, 'home.html', {'images': images, 'MEDIA_URL': settings.MEDIA_URL})


def load_more_images(request):
    page_number = request.GET.get('page', 1)  # Get the page number from the request
    images = InsectsImage.objects.all().prefetch_related('bboxes', 'insects')  # Include the 'insects' related object
    paginator = Paginator(images, 20)  # Create a Paginator object with 20 images per page
    images = paginator.page(page_number).object_list  # Get the images for the requested page

    # Convert the images to a list of dictionaries
    images_data = []
    for image in images:
        # Open the image and get its size
        img_path = os.path.join(settings.MEDIA_ROOT, image.url)
        with Image.open(img_path) as img:
            img_width, img_height = img.size

        # Convert the bounding box coordinates for each image
        bboxes_data = []
        for bbox in image.bboxes.all():
            bbox.x, bbox.y, bbox.width, bbox.height = convert_yolo_to_pixel(bbox.x, bbox.y, bbox.width, bbox.height,
                                                                            img_width, img_height)
            bboxes_data.append({'x': bbox.x, 'y': bbox.y, 'width': bbox.width, 'height': bbox.height})

        image_data = {
            'url': image.url,
            'width': img_width,
            'height': img_height,
            'bboxes': bboxes_data,
            'insects': {
                'ename': image.insects.name,
                'slug': image.insects.slug
            },
        }
        images_data.append(image_data)

    return JsonResponse(images_data, safe=False)


def search_species(request):
    if request.method == 'GET':
        species = Species.objects.values_list('insects_id', 'name', 'slug', 'ename')
        return JsonResponse(list(species), safe=False)


# image search
def image_search(request):
    return render(request, 'image_search.html')


from .predict import predict_image


# def search_by_image(request):
#     context = {}
#     if request.method == 'POST' and request.FILES.get('insectImage'):
#         image_file = request.FILES['insectImage']
#         # Save the uploaded image temporarily
#         file_path = default_storage.save('tmp/' + image_file.name, image_file)
#         full_file_path = os.path.join(default_storage.base_location, file_path)
#
#         # Get predicted class name from the image
#         predicted_class_name = predict_image(full_file_path)
#
#         # Remove the temporary file after use
#         os.remove(full_file_path)
#
#         # Filter Species by name using case-insensitive partial match
#         species = Species.objects.filter(name__icontains=predicted_class_name).first()
#
#         if species:
#             context['species'] = species
#         else:
#             context['error'] = "No matching species found."
#
#     return render(request, 'image_search.html', context)

def search_by_image(request):
    context = {}
    if request.method == 'POST' and request.FILES.get('insectImage'):
        image_file = request.FILES['insectImage']
        # Save the uploaded image temporarily
        file_path = default_storage.save('tmp/' + image_file.name, image_file)
        full_file_path = os.path.join(default_storage.base_location, file_path)
        try:
            result_img_url, predicted_class_name = predict_image(full_file_path)
            context['result_img'] = result_img_url
            context['predicted_class'] = predicted_class_name
            os.remove(full_file_path)
            species = Species.objects.filter(name__icontains=predicted_class_name).first()
            if species:
                context['species'] = species
            else:
                context['error'] = "Không tìm thấy loài khớp với ảnh."
        except Exception as e:
            context['error'] = f"Lỗi khi tải ảnh: {str(e)}"
    return render(request, 'image_search.html', context)


# detail.html section
def detail(request, slug):
    species = Species.objects.filter(slug=slug).first()  # Use filter() and first() to handle multiple objects
    if not species:
        raise Http404("Không tìm thấy loài")

    images = InsectsImage.objects.filter(insects_id=species.insects_id).prefetch_related('bboxes')[
             :50]  # Fetch only the first 20 images

    # Convert the bounding box coordinates for each image
    for image in images:
        # Open the image and get its size
        img_path = os.path.join(settings.MEDIA_ROOT, image.url)
        with Image.open(img_path) as img:
            img_width, img_height = img.size

        image.width = img_width
        image.height = img_height

        for bbox in image.bboxes.all():
            bbox.x, bbox.y, bbox.width, bbox.height = convert_yolo_to_pixel(bbox.x, bbox.y, bbox.width, bbox.height,
                                                                            img_width, img_height)

    return render(request, 'detail.html', {'species': species, 'images': images, 'MEDIA_URL': settings.MEDIA_URL})


def load_more_insect_images(request, slug):
    page_number = request.GET.get('page', 1)  # Get the page number from the request
    species = get_object_or_404(Species, slug=slug)
    images = InsectsImage.objects.filter(insects_id=species.insects_id).prefetch_related('bboxes')
    paginator = Paginator(images, 50)  # Create a Paginator object with 50 images per page
    images = paginator.get_page(page_number)  # Get the images for the requested page

    # Convert the images to a list of dictionaries
    images_data = []
    for image in images:
        # Open the image and get its size
        img_path = os.path.join(settings.MEDIA_ROOT, image.url)
        with Image.open(img_path) as img:
            img_width, img_height = img.size

        # Convert the bounding box coordinates for each image
        bboxes_data = []
        for bbox in image.bboxes.all():
            bbox.x, bbox.y, bbox.width, bbox.height = convert_yolo_to_pixel(bbox.x, bbox.y, bbox.width, bbox.height,
                                                                            img_width, img_height)
            bboxes_data.append({'x': bbox.x, 'y': bbox.y, 'width': bbox.width, 'height': bbox.height})

        image_data = {
            'url': image.url,
            'width': img_width,
            'height': img_height,
            'bboxes': bboxes_data,
            'insects': {
                'ename': image.insects.name,  # Include the species name
            },
        }
        images_data.append(image_data)

    return JsonResponse(images_data, safe=False)


# 3d model
def threed_model(request, slug):
    species = Species.objects.filter(slug=slug).first()  # Use filter() and first() to handle multiple objects
    if not species:
        raise Http404("Không tìm thấy loài")

    return render(request, '3d_model.html', {'species': species, 'MEDIA_URL': settings.MEDIA_URL})


# login.html section
def login(request):
    context = {'error': False}
    if request.method == "POST":
        username = request.POST.get('username')
        password = request.POST.get('password')
        if not username or not password:
            context['error'] = True
            context['message'] = "Tên đăng nhập và mật khẩu không được để trống!"
        else:
            user = authenticate(request, username=username, password=password)
            if user is not None:
                django_login(request, user)
                return redirect('/')
            else:
                context['error'] = True
                context['message'] = "Tên đăng nhập hoặc mật khẩu không đúng!"

    return render(request, 'login.html', context)


def sign_up(request):
    message = None
    message_type = None

    if request.method == 'POST':
        lastname = request.POST.get('lastname')
        firstname = request.POST.get('firstname')
        email = request.POST.get('email')
        username = request.POST.get('username')
        password = request.POST.get('password')
        repassword = request.POST.get('repassword')

        email_regex = r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$'

        if not username or not password or not lastname or not firstname or not email or not repassword:
            message = "Các trường không được để trống!"
            message_type = 'error'
        elif User.objects.filter(username=username).exists():
            message = "Tên đăng nhập đã được đăng ký!"
            message_type = 'error'
        elif not re.match(email_regex, email):
            message = "Email không hợp lệ!"
            message_type = 'error'
        elif User.objects.filter(email=email).exists():
            message = "Email đã được một tài khoản khác đăng ký!"
            message_type = 'error'
        elif password != repassword:
            message = "Mật khẩu xác nhận không khớp!"
            message_type = 'error'
        else:
            # Create new user
            user = User.objects.create(
                username=username,
                password=make_password(password),
                first_name=firstname,
                last_name=lastname,
                email=email,
                is_staff=False,
                is_active=True
            )

            # Get or create the "Users" group
            group, created = Group.objects.get_or_create(name="Users")
            group.user_set.add(user)

            message = "Đăng ký thành công!"
            message_type = 'success'
            return render(request, 'sign_up.html', {'message': message, 'message_type': message_type})

    return render(request, 'sign_up.html', {'message': message, 'message_type': message_type})


# def login(request):
#     if request.method == "POST":
#         # Use .get to avoid MultiValueDictKeyError
#         username = request.POST.get('username')
#         password = request.POST.get('password')
#         if not username or not password:  # Check if either field is empty
#             return HttpResponse("Username and password are required.")

#         user = authenticate(request, username=username, password=password)
#         if user is not None:
#             django_login(request, user)  # Use the imported login function with a different name
#             return redirect('/')  # Redirect to homepage or dashboard
#         else:
#             return HttpResponse("Invalid username or password.")
#     return render(request, 'login.html')

@login_required
def auth_user(request):
    is_admin = request.user.groups.filter(name="Admins").exists()
    # Add other context data as needed
    return render(request, 'template.html', {'is_admin': is_admin})


@login_required
def logout_view(request):
    logout(request)
    # Redirect to homepage or login page after logout
    return redirect('login')


# import_data.html section
def import_data(request):
    species_list = Species.objects.all()
    return render(request, 'import_data.html', {'species_list': species_list})


# add_insect.html section
@login_required
def append_insect(request):
    genus_list = Genus.objects.all()
    return render(request, 'append_insect.html', {'genus_list': genus_list})


@login_required
def append_insect_handler(request):
    if request.method == 'POST':
        # Create the Request object
        new_request = Request(
            ename=request.POST.get('insectEname'),
            name=request.POST.get('insectName'),
            species_name=request.POST.get('insectSpecies'),
            eng_name=request.POST.get('insectName'),  # Assuming English name is the same
            slug="insect_" + slugify(request.POST.get('insectName').replace(' ', '_')),
            morphologic_feature=request.POST.get('feature'),
            distribution=request.POST.get('distribution'),
            characteristic=request.POST.get('characteristic'),
            behavior=request.POST.get('behavior'),
            protection_method=request.POST.get('method'),
            thumbnail=f'thumbnails/{request.FILES.get("thumbnail").name}' if request.FILES.get('thumbnail') else '',
            genus_id=request.POST.get('insectGenus'),
            user=request.user,  # Directly assign the logged-in user
            status='pending',
            verification_count=0
        )
        new_request.save()

        # If there is a thumbnail, handle the file upload
        if request.FILES.get('thumbnail'):
            handle_uploaded_file1(request.FILES['thumbnail'])

        return render(request, 'append_insect.html', {'success': True})
    else:
        return render(request, 'append_insect.html', {'success': False})


def handle_uploaded_file1(f):
    path = os.path.join(settings.MEDIA_ROOT, 'thumbnails', f.name)
    with open(path, 'wb+') as destination:
        for chunk in f.chunks():
            destination.write(chunk)


from django.contrib.auth import get_user_model

User = get_user_model()


def cv_verify(request):
    # Fetch requests and include related user data
    requests = Request.objects.select_related('user').filter(status='pending').values(
        'request_id', 'ename', 'user__username', 'status'
    )

    # Add an index to each request for display in the table
    requests = [
        {
            'index': idx + 1,
            'request_id': req['request_id'],  # Make sure to include request_id here
            'ename': req['ename'],
            'username': req.get('user__username', 'Anonymous'),
            'status': req['status']
        }
        for idx, req in enumerate(requests)
    ]

    return render(request, 'cv_verify.html', {'requests': requests})


def admin_verify(request):
    # Fetch requests with status 'Verified' and include related user data
    requests = Request.objects.select_related('user').exclude(status__in=['accepted', 'rejected']).values(
        'request_id', 'ename', 'user__username', 'status'
    )

    # Add an index to each request for display in the table
    requests = [
        {
            'index': idx + 1,
            'request_id': req['request_id'],
            'ename': req['ename'],
            'username': req.get('user__username', 'Anonymous'),  # Handle cases where username might be null
            'status': req['status']
        }
        for idx, req in enumerate(requests)
    ]

    return render(request, 'admin_verify.html', {'requests': requests})


# def verify_request(request, request_id):
#     request_item = get_object_or_404(Request, request_id=request_id)
#     return render(request, 'append_verify.html', {'request_item': request_item})
import math
from django.contrib import messages


def verify_request(request, request_id):
    request_item = get_object_or_404(Request, pk=request_id)

    if request.method == 'POST':
        # Assuming fields are in the form as shown in append_verify.html
        request_item.ename = request.POST.get('insectEname', request_item.ename)
        request_item.name = request.POST.get('insectName', request_item.name)
        request_item.species_name = request.POST.get('speciesName', request_item.species_name)
        request_item.behavior = request.POST.get('behavior', request_item.behavior)
        request_item.morphologic_feature = request.POST.get('morphologicFeature', request_item.morphologic_feature)
        request_item.distribution = request.POST.get('distribution', request_item.distribution)
        request_item.characteristic = request.POST.get('characteristic', request_item.characteristic)
        request_item.protection_method = request.POST.get('protectionMethod', request_item.protection_method)

        # Thumbnail handling (if updated)
        if 'thumbnail' in request.FILES:
            request_item.thumbnail = request.FILES['thumbnail']

        # Increment verification count
        request_item.verification_count = (request_item.verification_count or 0) + 1

        # Fetch the "CVs" group user count and calculate the threshold
        cvs_group = AuthGroup.objects.get(name='CVs')
        cvs_user_count = AuthUserGroups.objects.filter(group=cvs_group).count()
        threshold = math.ceil(0.8 * cvs_user_count)  # Use math.ceil to round up

        # Compare verification count with the calculated threshold
        if request_item.verification_count >= threshold:
            request_item.status = 'verified'

        request_item.save()
        messages.success(request, 'Xác thực thành công!')
        return render(request, 'append_verify.html', {'request_item': request_item})

    return render(request, 'append_verify.html', {'request_item': request_item})


def accept_request(request, request_id):
    request_item = get_object_or_404(Request, pk=request_id)

    if request.method == 'POST':
        # Create a new Species object
        new_species = Species(
            ename=request.POST.get('insectEname', request_item.ename),
            name=request.POST.get('insectName', request_item.name),
            species_name=request.POST.get('speciesName', request_item.species_name),
            eng_name=request.POST.get('insectName', request_item.name),  # Set eng_name as name
            slug="insect_" + slugify(request.POST.get('speciesName', request_item.species_name)),
            # Generate a slug from species_name
            morphologic_feature=request.POST.get('morphologicFeature', request_item.morphologic_feature),
            distribution=request.POST.get('distribution', request_item.distribution),
            characteristic=request.POST.get('characteristic', request_item.characteristic),
            genus=request.POST.get('genus', request_item.genus),
            behavior=request.POST.get('behavior', request_item.behavior),
            protection_method=request.POST.get('protectionMethod', request_item.protection_method),
            is_new=True  # Set is_new to True
        )

        # Handle thumbnail if uploaded
        if 'thumbnail' in request.FILES:
            new_species.thumbnail = request.FILES['thumbnail']

        new_species.save()
        messages.success(request, 'The insect has been successfully accepted and added to the species database.')

        # request_item.delete()  # If want to remove the request upon acceptance

        return render(request, 'accept_insect.html',
                      {'request_item': request_item})  # Redirect to a success page or another relevant page

    # For GET request, show the existing data
    return render(request, 'accept_insect.html', {'request_item': request_item})


from .models import Request, AuthUserGroups, AuthGroup


def upload_handler(request):
    if request.method == 'POST':
        insect_id = request.POST.get('insectSelect')
        image_only = 'imageOnly' in request.POST  # Check if the image only checkbox was checked

        try:
            insect = Species.objects.get(insects_id=insect_id)
        except Species.DoesNotExist:
            return HttpResponseBadRequest("Insect ID is not valid.")

        image_files = request.FILES.getlist('insectImage')
        if not image_files:
            return HttpResponseBadRequest("Image files are required.")

        for image_file in image_files:
            img_id_without_extension, _ = os.path.splitext(image_file.name)
            file_path = os.path.join(settings.MEDIA_ROOT, 'images', image_file.name)
            with open(file_path, 'wb+') as destination:
                for chunk in image_file.chunks():
                    destination.write(chunk)
            InsectsImage.objects.create(
                img_id=img_id_without_extension,
                url=os.path.join('images', image_file.name).replace('\\', '/'),
                insects=insect
            )

        if not image_only:
            label_files = request.FILES.getlist('insectLabel')
            if not label_files:
                return HttpResponseBadRequest("Cần phải nhập ảnh khi nhập cả ảnh và nhãn.")

            for label_file in label_files:
                img_id_without_extension, _ = os.path.splitext(label_file.name)
                try:
                    image_entry = InsectsImage.objects.get(img_id=img_id_without_extension)
                    label_file_path = os.path.join(settings.MEDIA_ROOT, 'images', label_file.name)

                    with open(label_file_path, 'wb+') as destination:
                        for chunk in label_file.chunks():
                            destination.write(chunk)

                    with open(label_file_path, 'r') as file:
                        label_data = file.read().strip().split('\n')

                    for line in label_data:
                        parts = line.split()
                        if len(parts) == 5:
                            _, x, y, width, height = map(float, parts)
                            InsectsBbox.objects.create(
                                x=x, y=y, width=width, height=height,
                                img=image_entry
                            )

                except InsectsImage.DoesNotExist:
                    return JsonResponse({'success': False,
                                         'message': f"InsectsImage does not exist for img_id: {img_id_without_extension}"})

        return JsonResponse({'success': True, 'message': "Upload thành công!"})

    else:
        return JsonResponse({'success': False, 'message': "Invalid request method."})


# import_folder.html section
def upload_folder_zip(request):
    if request.method == "POST":
        species_id = request.POST.get("insectSelect")
        files = request.FILES.getlist("insectImage")

        for f in files:
            if zipfile.is_zipfile(f):
                with zipfile.ZipFile(f) as z:
                    for filename in z.namelist():
                        if filename.endswith(('.png', '.jpg', '.jpeg', '.txt')):
                            with z.open(filename) as file_content:
                                handle_uploaded_file(filename, file_content, species_id)
            else:
                handle_uploaded_file(f.name, f, species_id)

        return JsonResponse({"success": True})

    else:
        species_list = Species.objects.all()
        return render(request, 'import_folder.html', {'species_list': species_list})


def handle_uploaded_file(filename, file_content, species_id):
    species = Species.objects.get(pk=species_id)
    base_name = os.path.basename(filename)
    name, ext = os.path.splitext(base_name)
    file_path = f'images/{base_name}'

    # Save the file in storage
    content = file_content.read() if not isinstance(file_content, ContentFile) else file_content
    save_file_to_storage(file_path, content)

    if ext.lower() in ['.png', '.jpg', '.jpeg']:
        InsectsImage.objects.update_or_create(
            img_id=name,
            defaults={'url': file_path, 'insects': species}
        )

    elif ext.lower() == '.txt':
        # Assuming content needs decoding
        content_str = content.decode('utf-8') if isinstance(content, bytes) else content
        lines = content_str.strip().split('\n')
        try:
            img = InsectsImage.objects.get(img_id=name)
            for line in lines:
                # Split the line and map to float, skipping the class identifier
                parts = line.split()
                if len(parts) == 5:
                    x, y, width, height = map(float, parts[1:])  # Correctly unpack the 4 values
                    InsectsBbox.objects.create(x=x, y=y, width=width, height=height, img=img)
        except InsectsImage.DoesNotExist:
            print(f"No matching image found for label: {name}. Label not imported.")


def save_file_to_storage(file_path, file_content):
    # Ensure reading the content if it's not already in bytes format
    content = file_content if isinstance(file_content, bytes) else file_content.read()
    file = ContentFile(content)
    default_storage.save(file_path, file)


# def handle_uploaded_file(filename, file_content, species_id):
#     base_name, ext = os.path.splitext(filename)
#     species = Species.objects.get(pk=species_id)

#     if ext.lower() in ['.png', '.jpg', '.jpeg']:
#         # Handling image file
#         image_path = f'images/{filename}'
#         image_file = ContentFile(file_content.read())
#         default_storage.save(image_path, image_file)

#         # Create InsectsImage record
#         InsectsImage.objects.create(
#             img_id=base_name,
#             url=image_path,
#             insects=species
#         )

#     elif ext.lower() == '.txt':
#         # Handling label file
#         content = file_content.read().decode('utf-8')
#         lines = content.strip().split('\n')
#         for line in lines:
#             _, x, y, width, height = map(float, line.split())
#             try:
#                 img = InsectsImage.objects.get(img_id=base_name)
#                 InsectsBbox.objects.create(x=x, y=y, width=width, height=height, img=img)
#             except InsectsImage.DoesNotExist:
#                 print(f"Image {base_name} not found for bbox import.")


# crawl.html
def data_crawler(request):
    if request.method == 'POST':
        insect_id = request.POST.get('insectSelect')
        quantity = int(request.POST.get('quantity', 1))

        # Get insect details
        insect = Species.objects.get(insects_id=insect_id)

        # Download images
        images = download_images(insect.ename, quantity)

        # Save images to database
        save_images_to_database(images, insect_id)

        # Fetch saved images
        images = InsectsImage.objects.filter(insects_id=insect_id)

        data = {
            'success': True,
            'images': [{
                'url': image.get_absolute_url(),
                'img_id': image.img_id,
            } for image in images]
        }
        return JsonResponse(data)
    else:
        species_list = Species.objects.all()
        return render(request, 'crawler.html', {'species_list': species_list})


def cancel_crawling(request):
    delete_tmp_images()
    return JsonResponse({'success': True})


# def data_crawler(request):
#     species_list = Species.objects.all()
#     context = {'species_list': species_list}

#     # Include flags based on session values or other conditions
#     if 'upload_success' in request.session:
#         context['upload_success'] = True
#         del request.session['upload_success']
#     elif 'cancelled' in request.session:
#         context['cancelled'] = True
#         del request.session['cancelled']

#     return render(request, 'crawler.html', context)


# def upload_crawled_images(request):
#     if request.method == 'POST':
#         # Logic to handle images upload
#         return JsonResponse({'success': True})
#     return JsonResponse({'success': False}, status=400)


# def cancel_crawled_images(request):
#     if request.method == 'POST':
#         # Logic to delete temporary images
#         return JsonResponse({'success': True})
#     return JsonResponse({'success': False}, status=400)


# def ajax_crawl_images(request):
#     if request.method == 'POST':
#         ename = request.POST.get('ename')
#         quantity = int(request.POST.get('quantity'))
#         unique_id = crawl_images(ename, quantity)
#         image_urls = get_image_urls(unique_id)  # Implement this function to return the list of image URLs from tmp_crawler

#         return JsonResponse({'image_urls': image_urls})

#     return JsonResponse({'error': 'This method is not allowed'}, status=405)
# download folder


from django.http import StreamingHttpResponse, HttpResponseNotFound


def iter_file(file_path, chunk_size=8192):
    with open(file_path, 'rb') as file:
        while True:
            chunk = file.read(chunk_size)
            if not chunk:
                break
            yield chunk


def download_folder(request):
    # Construct the full path to the zip file
    zip_path = os.path.join(settings.MEDIA_ROOT, 'images.zip')

    # Check if the zip file exists before attempting to serve it
    if not os.path.exists(zip_path):
        return HttpResponseNotFound("The requested zip file does not exist.")

    # Create a StreamingHttpResponse with the iter_file generator, set the appropriate content type
    response = StreamingHttpResponse(iter_file(zip_path), content_type='application/zip')

    # Set the Content-Disposition header to prompt a download dialog in the browser
    response['Content-Disposition'] = 'attachment; filename="images.zip"'

    return response


# Serializers

# Species API
@api_view(['GET', 'POST', 'PUT', 'DELETE'])
def species_list(request, format=None):
    if request.method == 'GET':
        species = Species.objects.all()
        serializer = SpeciesSerializer(species, many=True)
        return Response(serializer.data)

    elif request.method == "POST":
        serializer = SpeciesSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
    else:
        return Response({"detail": "Method not allowed"}, status=status.HTTP_405_METHOD_NOT_ALLOWED)


@api_view(['GET', 'PUT', 'DELETE'])
def species_details(request, lookup):
    # Attempt to distinguish between ID and name based on the lookup's data type
    try:
        lookup_as_int = int(lookup)
        # If conversion succeeds, lookup by pk
        species = get_object_or_404(Species, pk=lookup_as_int)
    except ValueError:
        # If conversion fails, it's a name or slug
        species = get_object_or_404(Species, Q(name=lookup) | Q(slug=lookup))

    if request.method == "GET":
        serializer = SpeciesSerializer(species)
        return Response(serializer.data)
    elif request.method == "PUT":
        serializer = SpeciesSerializer(species, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    elif request.method == "DELETE":
        species.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


# Insects_Image API
@api_view(['GET', 'PUT', 'DELETE'])
def image_details(request, img_id):
    try:
        image = InsectsImage.objects.get(img_id=img_id)
    except InsectsImage.DoesNotExist:
        return Response(status=status.HTTP_404_NOT_FOUND)

    if request.method == 'GET':
        serializer = ImageSerializer(image)
        return Response(serializer.data)
    elif request.method == 'PUT':
        serializer = ImageSerializer(image, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    elif request.method == 'DELETE':
        image.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


@api_view(['GET'])
def get_insect_images(request, lookup):
    # Attempt to distinguish between ID and name based on the lookup's data type
    try:
        lookup_as_int = int(lookup)
        species = get_object_or_404(Species, pk=lookup_as_int)
    except ValueError:
        # If conversion fails, it's a name or slug
        species = get_object_or_404(Species, Q(name=lookup) | Q(ename=lookup) | Q(slug=lookup))

    images = InsectsImage.objects.filter(insects=species)
    serializer = ImageSerializer(images, many=True)
    return Response(serializer.data)


@api_view(['GET', 'PUT', 'DELETE'])
def species_images(request, lookup):
    try:
        # Attempt to distinguish between ID and name based on the lookup's data type
        lookup_as_int = int(lookup)
        species = get_object_or_404(Species, pk=lookup_as_int)
    except ValueError:
        # If conversion fails, it's a name or slug
        species = get_object_or_404(Species, Q(name=lookup) | Q(ename=lookup))

    images = InsectsImage.objects.filter(insects=species)
    context = {'request': request}
    serializer = ImageBoxSerializer(images, many=True, context=context)
    return Response(serializer.data)


class ImageUploadAPI(APIView):
    parser_classes = [MultiPartParser]

    def post(self, request, *args, **kwargs):
        file = request.FILES.get('file')
        insects_id = request.data.get('insects_id')  # Get the insects_id from the request

        if not file:
            return JsonResponse({'error': 'No file provided'}, status=status.HTTP_400_BAD_REQUEST)

        # Extract filename without extension for img_id
        file_name, file_extension = os.path.splitext(file.name)
        img_id = file_name

        # Validate the insects_id
        if insects_id:
            try:
                species_instance = Species.objects.get(insects_id=insects_id)
            except Species.DoesNotExist:
                return JsonResponse({'error': 'Species with the given ID does not exist'},
                                    status=status.HTTP_404_NOT_FOUND)
        else:
            species_instance = None

        # Save the file to the media folder
        storage_path = f"images/{uuid.uuid4()}_{file.name}"  # Keep the UUID to ensure unique paths
        path = default_storage.save(storage_path, file)

        # Create a new instance of InsectsImage with species_instance
        img_instance = InsectsImage(
            img_id=img_id,
            url=path,
            insects=species_instance  # Link the image to the species
        )
        img_instance.save()

        # Serialize and return the new image instance
        serializer = ImageSerializer(img_instance)
        return JsonResponse(serializer.data, status=status.HTTP_201_CREATED)


@api_view(['GET', 'PUT', 'DELETE'])
def species_images_bbox(request, id):
    try:
        species = Species.objects.get(pk=id)
    except Species.DoesNotExist:
        return Response(status=status.HTTP_404_NOT_FOUND)

    if request.method == "GET":
        images = InsectsImage.objects.filter(insects=species)
        serializer = ImageBoxSerializer(images, many=True)
        return Response(serializer.data)


@api_view(['GET', 'PUT', 'DELETE'])
def bbox_details(request, img_id):
    try:
        image = InsectsImage.objects.get(img_id=img_id)
    except InsectsImage.DoesNotExist:
        return Response(status=status.HTTP_404_NOT_FOUND)

    if request.method == 'GET':
        bboxes = InsectsBbox.objects.filter(img=image)
        # Pass 'request' in the serializer context
        serializer = BoundingBoxSerializer(bboxes, many=True, context={'request': request})
        return Response(serializer.data)

    elif request.method == 'PUT':
        # Assuming you send bbox data as a list of bbox objects to update
        # This part needs a more complex logic to match and update each bbox
        # Here is a simplistic approach just for demonstration
        data = request.data
        for bbox_data in data:
            bbox_id = bbox_data.get('box_id')
            bbox = InsectsBbox.objects.get(pk=bbox_id, img=image)
            serializer = BoundingBoxSerializer(bbox, data=bbox_data)
            if serializer.is_valid():
                serializer.save()
            else:
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        return Response({"message": "Bounding boxes updated."})

    elif request.method == 'DELETE':
        # This will delete all bboxes associated with the image
        InsectsBbox.objects.filter(img=image).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


# Misc

def export_data(request):
    # Call the function to generate and export the CSV file
    file_path = export_species_data_to_csv()  # Make sure this matches your updated function name

    # Open the file for reading in binary mode
    with open(file_path, 'rb') as file:
        # Set the content type for CSV and specify the file name
        response = HttpResponse(file.read(), content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="IP102_data.csv"'

        # Cleanup if necessary
        # os.remove(file_path)

    return response

def home_view(request):
    return render(request, "template_v2.html", {})


def home_page(request):
    home_view(request)
    species_lst = Species.objects.all()
    for spc in species_lst:
        # Open the image and get its size
        if spc.thumbnail is None:
            spc.thumbnail = os.path.join(settings.MEDIA_ROOT, "thumbnails", "noimage.jpg")
            # img_path = os.path.join(settings.MEDIA_ROOT,os.path.normpath(spc.thumbnail))
            # with Image.open(img_path) as img:
            #    img_width, img_height = img.size

        spc.width = 40
        spc.height = 40
    return render(request, "home_page.html", {'species_lst': species_lst, 'MEDIA_URL': settings.MEDIA_URL})


# Description #
# annotations section
def add_desc(request):
    insect_id = request.GET.get('insectId')
    ##print(insect_id)
    if insect_id:
        # Handle AJAX request
        images = InsectsImage.objects.filter(insects_id=insect_id).prefetch_related('bboxes')
        images_data = []
        for image in images:
            img_path = os.path.join(settings.MEDIA_ROOT, image.url)
            with Image.open(img_path) as img:
                img_width, img_height = img.size

            bboxes_data = []
            for bbox in image.bboxes.all():
                x_top_left, y_top_left, box_width, box_height = convert_yolo_to_pixel(
                    bbox.x, bbox.y, bbox.width, bbox.height, img_width, img_height)
                converted_bbox = {
                    'x': x_top_left, 'y': y_top_left,
                    'width': box_width, 'height': box_height
                }
                bboxes_data.append(converted_bbox)

            images_data.append({
                'img_id': image.img_id,  # Make sure this id exists and matches the model field
                'url': settings.MEDIA_URL + image.url,
                'width': img_width,
                'height': img_height,
                'insectsId': image.insects_id,
                'insectsName': image.insects.name,
                'bboxes': bboxes_data,
            })

        return JsonResponse({'images': images_data})
    # Handle non-AJAX request
    species_list = Species.objects.all()
    return render(request, 'add_desc.html', {'species_list': species_list})


def add_desc_step2(request):
    img_id = request.GET.get('img_id')
    try:
        image = InsectsImage.objects.get(img_id=img_id)
        request_desc = RequestDesc.objects.filter(img_id=img_id, user=request.user)

    except InsectsImage.DoesNotExist:
        return Response(status=status.HTTP_404_NOT_FOUND)
    specie = Species.objects.filter(insects_id=image.insects_id).first()

    return render(request, 'add_desc_step2.html',
                  {'img_info': image, 'specie': specie, 'MEDIA_URL': settings.MEDIA_URL, 'request_desc': request_desc})


## add desc
def add_desc_handler(request, img_id):
    ##print("img_id",img_id)
    try:
        image = InsectsImage.objects.get(img_id=img_id)
        request_desc = RequestDesc.objects.filter(img_id=img_id, user=request.user)
    except InsectsImage.DoesNotExist:
        return Response(status=status.HTTP_404_NOT_FOUND)
    specie = Species.objects.filter(insects_id=image.insects_id).first()
    if request.method == 'POST':
        # Create the Request object
        new_request = RequestDesc(
            img_id=img_id,
            desc=request.POST.get('new_desc'),
            user=request.user,  # Directly assign the logged-in user
            status='pending',
            verification_count=0
        )
        new_request.save()
        messages.success(request, 'Thêm thành công!')
        return render(request, 'add_desc_step2.html',
                      {'img_info': image, 'specie': specie, 'MEDIA_URL': settings.MEDIA_URL,
                       'request_desc': request_desc})
    else:
        return render(request, 'add_desc_step2.html',
                      {'img_info': image, 'specie': specie, 'MEDIA_URL': settings.MEDIA_URL,
                       'request_desc': request_desc})


def cv_desc_verify(request):
    # Fetch requests and include related user data
    requests = RequestDesc.objects.select_related('user').filter(status='pending').values(
        'request_desc_id', 'img_id', 'user__username', 'status'
    )

    # Add an index to each request for display in the table
    requests = [
        {
            'index': idx + 1,
            'request_desc_id': req['request_desc_id'],  # Make sure to include request_id here
            'img_id': req['img_id'],
            'username': req.get('user__username', 'Anonymous'),
            'status': req['status']
        }
        for idx, req in enumerate(requests)
    ]

    return render(request, 'cv_desc_verify.html', {'requests': requests})


def verify_desc_request(request, request_desc_id):
    request_item = get_object_or_404(RequestDesc, pk=request_desc_id)
    image = InsectsImage.objects.get(img_id=request_item.img_id)
    specie = Species.objects.filter(insects_id=image.insects_id).first()
    if request.method == 'POST':
        # Assuming fields are in the form as shown in append_verify.html
        request_item.img_id = request.POST.get('img_id', request_item.img_id)
        request_item.desc = request.POST.get('desc', request_item.desc)

        request_item.verification_count = (request_item.verification_count or 0) + 1

        # Fetch the "CVs" group user count and calculate the threshold
        cvs_group = AuthGroup.objects.get(name='CVs')
        cvs_user_count = AuthUserGroups.objects.filter(group=cvs_group).count()
        threshold = math.ceil(0.8 * cvs_user_count)  # Use math.ceil to round up

        # Compare verification count with the calculated threshold
        if request_item.verification_count >= threshold:
            request_item.status = 'verified'

        request_item.save()
        messages.success(request, 'Xác thực thành công!')
        return render(request, 'add_desc_verify.html',
                      {'request_item': request_item, 'img_info': image, 'specie': specie,
                       'MEDIA_URL': settings.MEDIA_URL})

    return render(request, 'add_desc_verify.html',
                  {'request_item': request_item, 'img_info': image, 'specie': specie, 'MEDIA_URL': settings.MEDIA_URL})


def admin_desc_verify(request):
    # Fetch requests and include related user data
    requests = RequestDesc.objects.select_related('user').exclude(status__in=['accepted', 'rejected']).values(
        'request_desc_id', 'img_id', 'user__username', 'status'
    )

    if requests is not None:
        requests = [
            {
                'index': idx + 1,
                'request_desc_id': req['request_desc_id'],  # Make sure to include request_id here
                'img_id': req['img_id'],
                'username': req.get('user__username', 'Anonymous'),
                'status': req['status']
            }
            for idx, req in enumerate(requests)
        ]
    # print('requests', requests)
    return render(request, 'admin_desc_verify.html', {'requests': requests})


def accept_desc_request(request, request_desc_id):
    request_item = get_object_or_404(RequestDesc, pk=request_desc_id)
    image = InsectsImage.objects.get(img_id=request_item.img_id)
    specie = Species.objects.filter(insects_id=image.insects_id).first()
    if request.method == 'POST':

        action = request.POST.get('action')
        if action == 'accept':
            request_item.status = 'Accepted'
            request_item.save()
            image.desc = request_item.desc
            image.save()
            messages.success(request, 'Mô tả đã được chấp nhận và thêm vào ảnh.')
        elif action == 'reject':
            request_item.status = 'Rejected'
            request_item.save()
            messages.warning(request, 'Mô tả đã bị từ chối')
        return render(request, 'accept_desc.html',
                      {'request_item': request_item, 'img_info': image, 'specie': specie,
                       'MEDIA_URL': settings.MEDIA_URL})  # Redirect to a success page or another relevant page

    # For GET request, show the existing data
    return render(request, 'accept_desc.html',
                  {'request_item': request_item, 'img_info': image, 'specie': specie, 'MEDIA_URL': settings.MEDIA_URL})


def species_list(request):
    # page_number = request.GET.get('page', 1)  # Get the page number from the request
    species_lst = Species.objects.all()
    # paginator = Paginator(species_lst, 20)  # Create a Paginator object with 20 images per page
    # species_lst = paginator.get_page(page_number)  # Get the images for the requested page
    # print('thum',species_lst[1].thumbnail)
    for spc in species_lst:
        # Open the image and get its size
        if spc.thumbnail is None:
            spc.thumbnail = os.path.join("thumbnails", "noimage.jpg")
            # img_path = os.path.join(settings.MEDIA_ROOT,os.path.normpath(spc.thumbnail))
            # with Image.open(img_path) as img:
            #    img_width, img_height = img.size

        spc.width = 40
        spc.height = 40
    return render(request, 'species_list.html', {'species_lst': species_lst, 'MEDIA_URL': settings.MEDIA_URL})


def load_specie_image(request):
    page_number = request.GET.get('page', 1)  # Get the page number from the request
    spc_id = request.GET.get('specie_id', None)
    # print("spc_id",spc_id)
    images = InsectsImage.objects.filter(insects_id=spc_id).prefetch_related('bboxes')
    specie_info = Species.objects.filter(insects_id=spc_id).first()
    paginator = Paginator(images, 20)  # Create a Paginator object with 20 images per page
    page_obj = paginator.get_page(page_number)  # Get the images for the requested page
    # print("page_obj len",len(page_obj))
    # Convert the bounding box coordinates for each image
    for image in page_obj:
        # Open the image and get its size
        img_path = os.path.join(settings.MEDIA_ROOT, image.url)
        with Image.open(img_path) as img:
            img_width, img_height = img.size

        image.width = img_width
        image.height = img_height

        for bbox in image.bboxes.all():
            bbox.x, bbox.y, bbox.width, bbox.height = convert_yolo_to_pixel(bbox.x, bbox.y, bbox.width, bbox.height,
                                                                            img_width, img_height)

    return render(request, 'load_specie_image.html',
                  {'page_obj': page_obj, 'specie_id': spc_id, 'specie_info': specie_info,
                   'MEDIA_URL': settings.MEDIA_URL})

#document
def document_list(request):
    search_query = request.GET.get('search', '').strip()  # Lấy từ khóa tìm kiếm từ request
    documents = Document.objects.all()

    if search_query:
        documents = documents.filter(doc_name__icontains=search_query)  # Lọc theo tên tài liệu

    return render(request, 'document.html', {'documents': documents, 'search_query': search_query})


def view_document(request, doc_id):
    document = get_object_or_404(Document, doc_id=doc_id)
    return render(request, 'view_document.html', {'document': document, 'MEDIA_URL': settings.MEDIA_URL})

def download_document(request, doc_id):
    document = get_object_or_404(Document, pk=doc_id)
    file_path = os.path.join(settings.MEDIA_ROOT, str(document.url))

    return FileResponse(open(file_path, 'rb'), as_attachment=True)

#Manage user
@login_required()
def manage_user(request):
    users = User.objects.exclude(id=request.user.id)
    groups = Group.objects.all()

    #Xử lý tìm kiếm
    search_query = request.GET.get('search', '').strip()
    if search_query:
        users = users.filter(
            Q(username__icontains=search_query) |
            Q(first_name__icontains=search_query) |
            Q(last_name__icontains=search_query)
        )

    #Xử lý sắp xếp
    sort_by = request.GET.get('sort', 'username')  # Mặc định sắp xếp theo username
    sort_order = request.GET.get('order', 'asc')

    if sort_by == "group":
        subquery = Group.objects.filter(user=OuterRef('id')).values('name')[:1]
        users = users.annotate(group_name=Subquery(subquery))  # Lấy tên nhóm đầu tiên
        sort_by = "group_name"

    if sort_order == 'desc':
        users = users.order_by(f'-{sort_by}')
    else:
        users = users.order_by(sort_by)

    #Xử lý lọc
    filter_group = request.GET.get('group', '')
    if filter_group:
        users = users.filter(groups__name=filter_group)

    filter_last_login = request.GET.get('last_login', '')
    if filter_last_login:
        users = users.filter(last_login__date=filter_last_login)

    return render(request, 'manage_user.html', {
        'users': users,
        'groups': groups,
        'search_query': search_query,
        'sort_by': sort_by,
        'sort_order': sort_order,
        'filter_group': filter_group,
        'filter_last_login': filter_last_login
    })

@login_required()
def add_user(request):
    if request.method == "POST":
        username = request.POST.get("username")
        first_name = request.POST.get("first_name")
        last_name = request.POST.get("last_name")
        email = request.POST.get("email")
        password = request.POST.get("password")
        user_group = request.POST.get("user_group")

        if User.objects.filter(username=username).exists():
            messages.error(request, "Người dùng đã tồn tại!")
        elif User.objects.filter(email=email).exists():
            messages.error(request, "Email đã được người dùng khác đăng ký!")
        else:
            user = User.objects.create(
                username=username,
                first_name=first_name,
                last_name=last_name,
                email=email,
                password=make_password(password),
                is_active=True
            )

            if user_group:
                group = Group.objects.get(name=user_group)
                user.groups.add(group)
                if group.name == "Admins":
                    user.is_staff = True
                    user.save()

            messages.success(request, "Thêm người dùng thành công!")
        return redirect("add_user")

        # Lấy danh sách group để hiển thị trong form
    groups = Group.objects.all()
    return render(request, "add_user.html", {"groups": groups})

@login_required
def edit_user(request, user_id):
    user = get_object_or_404(User, id=user_id)
    success = False

    if request.method == "POST":
        form = UserEditForm(request.POST, instance=user)
        if form.is_valid():
            user = form.save(commit=False)
            user.groups.clear()

            if form.cleaned_data['groups']:
                selected_group = form.cleaned_data['groups']
                user.groups.set([selected_group])
                if selected_group.name == "Admins":
                    user.is_staff = True
                else:
                    user.is_staff = False
            user.save()
            success = True
    else:
        form = UserEditForm(instance=user)

    return render(request, 'edit_user.html', {'form': form, 'user': user, 'success': success})

@login_required()
def delete_user(request, user_id):
    user = get_object_or_404(User, id=user_id)

    if request.method == "POST":
        user.delete()
        messages.success(request, f"Đã xóa người dùng {user.username} thành công!")

    return redirect('manage_user')

#account_info
@login_required()
def account_info(request):
    user = request.user
    context = {
        "username": user.username,
        "last_name": user.last_name,
        "first_name": user.first_name,
        "email": user.email,
        "last_login": user.last_login,
        "groups": user.groups.all(),
    }
    # print(context)
    return render(request, "account_info.html", context)


@login_required
def edit_account(request):
    if request.method == "POST":
        user = request.user
        user.username = request.POST["username"]
        user.last_name = request.POST["last_name"]
        user.first_name = request.POST["first_name"]
        user.email = request.POST["email"]
        user.save()
        success_message = "Cập nhật thông tin thành công!"
        return render(request, "account_info.html", {
            "success_message": success_message,
            "username": user.username,
            "last_name": user.last_name,
            "first_name": user.first_name,
            "email": user.email,
            "last_login": user.last_login,
            "groups": user.groups.all(),
        })
    return redirect("account_info")


@login_required
def change_password(request):
    if request.method == "POST":
        user = request.user
        old_password = request.POST["old_password"]
        new_password = request.POST["new_password"]
        confirm_password = request.POST["confirm_password"]

        if not user.check_password(old_password):
            return render(request, "account_info.html", {
                "success_message": "Mật khẩu cũ không chính xác!",
                "username": user.username,
                "last_name": user.last_name,
                "first_name": user.first_name,
                "email": user.email,
                "last_login": user.last_login,
                "groups": user.groups.all(),
            })
        if new_password != confirm_password:
            return render(request, "account_info.html", {
                "success_message": "Mật khẩu mới không khớp!",
                "username": user.username,
                "last_name": user.last_name,
                "first_name": user.first_name,
                "email": user.email,
                "last_login": user.last_login,
                "groups": user.groups.all(),
            })

        user.set_password(new_password)
        user.save()
        update_session_auth_hash(request, user)  # Giữ người dùng đăng nhập
        return render(request, "account_info.html", {
            "success_message": "Thay đổi mật khẩu thành công!",
            "username": user.username,
            "last_name": user.last_name,
            "first_name": user.first_name,
            "email": user.email,
            "last_login": user.last_login,
            "groups": user.groups.all(),
        })

    return redirect("account_info")

#trang thong ke
@login_required()
def statistics_view(request):
    total_image = InsectsImage.objects.count()
    total_user = User.objects.count()
    total_class = Class.objects.count()
    total_order = Order.objects.count()
    total_family = Family.objects.count()
    total_genus = Genus.objects.count()
    total_species = Species.objects.count()

    user_groups = Group.objects.annotate(user_count=Count('user'))
    order_class = Class.objects.annotate(order_count=Count('order'))
    family_order = Order.objects.annotate(family_count=Count('family'))
    genus_family  = Family.objects.annotate(genus_count=Count('genus'))
    species_genus = Genus.objects.annotate(species_count=Count('species'))
    img_species = Species.objects.annotate(img_count=Count('insectsimage'))

    return render(request, "statistics.html", {
        'total_image': total_image,
        'total_user': total_user,
        'user_groups': user_groups,
        'total_class': total_class,
        'total_order': total_order,
        'total_family': total_family,
        'total_genus': total_genus,
        'total_species': total_species,
        'order_class': order_class,
        'family_order': family_order,
        'genus_family': genus_family,
        'species_genus': species_genus,
        'img_species': img_species,
    })

#thong ke anh con trung
@login_required()
def get_species_img_chart(request):
    Images_by_species = InsectsImage.objects.values('insects__name').annotate(count=Count('img_id')).order_by('-count')
    species_dict = {s['insects__name']: s['count'] for s in Images_by_species}

    colorPrimary = "#79aec8"

    response_data = {
        "title": "Số lượng ảnh của từng loài",
        "data": {
            "labels": list(species_dict.keys()),
            "datasets": [{
                "label": "Số lượng ảnh",
                "backgroundColor": colorPrimary,
                "borderColor": colorPrimary,
                "data": list(species_dict.values())
            }]
        }
    }
    return JsonResponse(response_data)


#thong ke nguoi dung
@login_required()
def user_by_group_chart(request):
    groups = Group.objects.all()
    labels = []
    data = []

    for group in groups:
        labels.append(group.name)
        data.append(group.user_set.count())

    response_data = {
        "title": "Thống kê số lượng tài khoản theo nhóm",
        "data": {
            "labels": labels,
            "datasets": [{
                "label": "Số lượng người dùng",
                "data": data,
                "backgroundColor": [
                    "#FF6384", "#36A2EB", "#FFCE56", "#4CAF50", "#9C27B0"
                ]
            }]
        }
    }
    return JsonResponse(response_data)

@login_required()
def order_by_class_chart(request):
    classes = Class.objects.annotate(count=Count('order')).order_by('-count')
    labels = []
    data = []

    for cls in classes:
        labels.append(cls.name)
        data.append(cls.count)

    response_data = {
        "title": "Thống kê số lượng bộ theo lớp",
        "data": {
            "labels": labels,
            "datasets": [{
                "label": "Số lượng bộ",
                "data": data,
                "backgroundColor": "#4BC0C0"
            }]
        }
    }
    return JsonResponse(response_data)

@login_required()
def family_by_order_chart(request):
    orders = Order.objects.annotate(count=Count('family')).order_by('-count')
    labels = []
    data = []

    for order in orders:
        labels.append(order.name)
        data.append(order.count)

    response_data = {
        "title": "Thống kê số lượng họ theo bộ",
        "data": {
            "labels": labels,
            "datasets": [{
                "label": "Số lượng họ",
                "data": data,
                "backgroundColor": "#FF9F40"
            }]
        }
    }
    return JsonResponse(response_data)

@login_required()
def genus_by_family_chart(request):
    families = Family.objects.annotate(count=Count('genus')).order_by('-count')
    labels = []
    data = []

    for family in families:
        labels.append(family.name)
        data.append(family.count)

    response_data = {
        "title": "Thống kê số lượng chi theo họ",
        "data": {
            "labels": labels,
            "datasets": [{
                "label": "Số lượng chi",
                "data": data,
                "backgroundColor": "#36A2EB"
            }]
        }
    }
    return JsonResponse(response_data)

@login_required()
def species_by_genus_chart(request):
    genera = Genus.objects.annotate(count=Count('species')).order_by('-count')
    labels = []
    data = []

    for genus in genera:
        labels.append(genus.name)
        data.append(genus.count)

    response_data = {
        "title": "Thống kê số lượng loài theo chi",
        "data": {
            "labels": labels,
            "datasets": [{
                "label": "Số lượng loài",
                "data": data,
                "backgroundColor": "#9966FF"
            }]
        }
    }
    return JsonResponse(response_data)

# manage insect
@login_required()
def manage_insect(request):
    classes = Class.objects.all()
    order = Order.objects.all()
    family = Family.objects.all()
    genus = Genus.objects.all()
    species = Species.objects.all()

    search_class_query = request.GET.get('search_class', '').strip()
    if search_class_query:
        classes = classes.filter(
            Q(ename__icontains=search_class_query) |
            Q(name__icontains=search_class_query)
        )

    search_order_query = request.GET.get('search_order', '').strip()
    if search_order_query:
        order = order.filter(
            Q(ename__icontains=search_order_query) |
            Q(name__icontains=search_order_query)
        )

    search_family_query = request.GET.get('search_family', '').strip()
    if search_family_query:
        family = family.filter(
            Q(ename__icontains=search_family_query) |
            Q(name__icontains=search_family_query)
        )

    search_genus_query = request.GET.get('search_genus', '').strip()
    if search_genus_query:
        genus = genus.filter(
            Q(ename__icontains=search_genus_query) |
            Q(name__icontains=search_genus_query)
        )

    search_species_query = request.GET.get('search_species', '').strip()
    if search_species_query:
        species = species.filter(
            Q(ename__icontains=search_species_query) |
            Q(name__icontains=search_species_query) |
            Q(species_name__icontains=search_species_query) |
            Q(eng_name__icontains=search_species_query) |
            Q(vi_name__icontains=search_species_query)
        )

    return render(request, 'manage_insect.html', {
        'classes': classes,
        'orders': order,
        'family': family,
        'genus': genus,
        'species': species,
        'search_class_query': search_class_query,
        'search_order_query': search_order_query,
        'search_family_query': search_family_query,
        'search_genus_query': search_genus_query,
        'search_species_query': search_species_query,
        'MEDIA_URL': settings.MEDIA_URL
    })