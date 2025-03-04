from django.urls import path, register_converter
from . import views
from django.conf import settings
from django.conf.urls.static import static
from rest_framework.urlpatterns import format_suffix_patterns
from .views import ImageUploadAPI

class SlugWithParenthesesConverter:
    regex = '[\w-]+(\([\w\s]+\))?'

    def to_python(self, value):
        return str(value)

    def to_url(self, value):
        return str(value)

register_converter(SlugWithParenthesesConverter, 'customslug')


#URL Configurations
urlpatterns = [
    #path('', views.home_view, name='home_view'),
    path('', views.home_page, name='home_page'),
    path('show_insect_images/', views.show_insect_images, name='show_insect_images'),
    path('load_more_images/', views.load_more_images, name='load_more_images'),
    path('detail/<customslug:slug>/', views.detail, name='detail'),
    path('detail/<customslug:slug>/load_more_images/', views.load_more_insect_images, name='load_more_insect_images'),
    path('3d_model/<customslug:slug>/', views.threed_model, name='3d_model'),
    path('search/', views.search_species, name='search_species'),
    path('image_search/', views.image_search, name='image_search'),
    path('search_by_image/', views.search_by_image, name='search_by_image'),
    path('export_data/', views.export_data, name='export_data'),
    path('document/', views.document_list, name='document_list'),
    path('view_document/<int:doc_id>/', views.view_document, name='view_document'),
    path('download/<int:doc_id>/', views.download_document, name='download_document'),
    # manage insect
    path('manage_insect/', views.manage_insect, name='manage_insect'),
    #manage_account
    path('account_info/', views.account_info, name='account_info'),
    path('edit_account/', views.edit_account, name='edit_account'),
    path('change_password/', views.change_password, name='change_password'),
    #manage user
    path('manage_user/', views.manage_user, name='manage_user'),
    path('manage_user/add/', views.add_user, name='add_user'),
    path('manage_user/delete/<int:user_id>/', views.delete_user, name='delete_user'),
    path('manage_user/edit/<int:user_id>/', views.edit_user, name='edit_user'),
    # import data
    path('import_data/', views.import_data, name='import_data'),
    path('upload_handler/', views.upload_handler, name='upload_handler'),
    # login
    path('login/', views.login, name='login'),
    path('logout/', views.logout_view, name='logout'),
    # sign up
    path('sign_up/', views.sign_up, name='sign_up'),
    # folder upload
    path('upload_folder_zip/', views.upload_folder_zip, name='upload_folder_zip'),
    # statistics
    path('statistics/', views.statistics_view, name='shop-statistics'),  # new
    path('chart/image_by_species/', views.get_species_img_chart, name='get_species_chart'),
    path('chart/user_by_group/', views.user_by_group_chart, name='user_by_group_chart'),
    path('chart/order_by_class/', views.order_by_class_chart, name='order_by_class_chart'),
    path('chart/family_by_order/', views.family_by_order_chart, name='family_by_order_chart'),
    path('chart/genus_by_family/', views.genus_by_family_chart, name='genus_by_family_chart'),
    path('chart/species_by_genus/', views.species_by_genus_chart, name='species_by_genus_chart'),

    path('species_list/', views.species_list, name='species_list'),
    path('load_specie_image/', views.load_specie_image, name='load_specie_image'),




    # crawler
    # path('data_crawler/', views.data_crawler, name='data_crawler'),
    # path('upload_crawled_images/', views.upload_crawled_images, name='upload_crawled_images'),
    # path('cancel_crawled_images/', views.cancel_crawled_images, name='cancel_crawled_images'),
    # path('ajax/crawl_images/', views.ajax_crawl_images, name='crawl_images'),
    path('data_crawler/', views.data_crawler, name='data_crawler'),
    path('cancel_crawling/', views.cancel_crawling, name='cancel_crawling'),

    # annotations
    path('Labelling/', views.labelling, name='Labelling'),
    path('get_image_data/', views.get_image_data, name='get_image_data'),
    path('save_bboxes/', views.save_bboxes, name='save_bboxes'),
    path('annotation/', views.annotation, name='annotation'),
    # download
    path('download_images/', views.download_folder, name='download_folder'),
    # append insect
    path('append_insect/', views.append_insect, name='append_insect'),
    path('append_insect_handler/', views.append_insect_handler, name='append_insect_handler'),

    #verify insects
    path('cv_verify/', views.cv_verify, name='cv_verify'),
    path('admin_verify/', views.admin_verify, name='admin_verify'),
    path('verify_request/<int:request_id>/', views.verify_request, name='verify_request'),
    path('accept_request/<int:request_id>/', views.accept_request, name='accept_request'),

    ## Description
    path('cv_desc_verify/', views.cv_desc_verify, name='cv_desc_verify'),
    path('add_desc/', views.add_desc, name='add_desc'),  # new
    path('add_desc_step2/', views.add_desc_step2, name='add_desc_step2'),
    path('add_desc_handler/<str:img_id>/', views.add_desc_handler, name='append_desc_handler'),
    path('admin_desc_verify/', views.admin_desc_verify, name='admin_desc_verify'),
    path('verify_desc_request/<int:request_desc_id>/', views.verify_desc_request, name='verify_desc_request'),
    path('accept_desc_request/<int:request_desc_id>/', views.accept_desc_request, name='accept_desc_request'),


    # APIs
    path('api/species_list/', views.species_list),
    path('api/species_details/<str:lookup>/', views.species_details),
    path('api/image_details/<str:img_id>/', views.image_details),
    path('api/insect_images/<str:lookup>/', views.get_insect_images, name='get_insect_images'),
    path('api/upload_images/', ImageUploadAPI.as_view(), name='upload_images'),
    path('api/species_images/<str:lookup>/', views.species_images),
    path('api/species_images_bbox/<int:id>/', views.species_images_bbox),
    path('api/bbox_details/<str:img_id>/', views.bbox_details, name='bbox_details'),
]

urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)