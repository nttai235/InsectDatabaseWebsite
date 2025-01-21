from django.contrib import admin
from .models import Kingdom, Phylum, Class, Order, Family, Genus, Species, InsectsImage, InsectsBbox
from django.utils.html import format_html
from django.conf import settings
from django import forms

# Register your models here.


@admin.register(Kingdom)
class KingdomAdmin(admin.ModelAdmin):
    list_display = ['kingdom_id', 'ename' , 'name' , 'slug']

# Phylums table
# class PhylumAdminForm(forms.ModelForm):
#     kingdom = forms.ModelChoiceField(
#         queryset=Kingdom.objects.all(),
#         label='Kingdom',
#         to_field_name='ename',  # This specifies which field to use for the label
#         required=False
#     )

#     class Meta:
#         model = Phylum
#         fields = '__all__'

# class PhylumAdmin(admin.ModelAdmin):
#     form = PhylumAdminForm
#     list_display = ('phylum_id', 'ename', 'name', 'get_kingdom_ename')

#     def get_kingdom_ename(self, obj):
#         return obj.kingdom.ename
#     get_kingdom_ename.short_description = 'Kingdom'

# admin.site.register(Phylum, PhylumAdmin)

@admin.register(Phylum)
class PhylumAdmin(admin.ModelAdmin):
    list_display = ['phylum_id', 'ename' , 'name' , 'slug', 'kingdom']

# Class table
# class ClassAdminForm(forms.ModelForm):
#     phylum = forms.ModelChoiceField(
#         queryset=Phylum.objects.all(),
#         label='Phylum',
#         to_field_name='ename',
#         required=False
#     )
#     class Meta:
#         model = Order
#         fields = '__all__'

# class ClassAdmin(admin.ModelAdmin):
#     forms = ClassAdminForm
#     list_display = ['class_id', 'ename', 'name', 'slug', 'get_phylum_ename']

#     def get_phylum_ename(self, obj):
#         return obj.phylum.ename
#     get_phylum_ename.short_description = 'Phylum'

# admin.site.register(Class, ClassAdmin)

@admin.register(Class)
class ClassAdmin(admin.ModelAdmin):
    list_display = ['class_id', 'ename' , 'name' , 'slug', 'phylum']

# Order table
# class OrderAdminForm(forms.ModelForm):
#     cls = forms.ModelChoiceField(
#         queryset=Class.objects.all(),
#         label='Class',
#         to_field_name='ename',
#         required=False
#     )
#     class Meta:
#         model = Class
#         fields = '__all__'

# class OrderAdmin(admin.ModelAdmin):
#     forms = OrderAdminForm
#     list_display = ['order_id', 'ename', 'name', 'slug', 'class_field']
#     def get_class_ename(self, obj):
#         return obj.order.ename
#     get_class_ename.short_description = 'class'

# admin.site.register(Order, OrderAdmin)

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ['order_id', 'ename' , 'name' , 'slug', 'class_field']


# Family table
@admin.register(Family)
class FamilyAdmin(admin.ModelAdmin):
    list_display = ['family_id', 'ename', 'name', 'slug', 'order']


@admin.register(Genus)
class GenusAdmin(admin.ModelAdmin):
    list_display = ['genus_id', 'ename', 'name', 'slug', 'family']


@admin.register(Species)
class SpeciesAdmin(admin.ModelAdmin):
    list_display = ['insects_id', 'ename', 'name', 'eng_name', 'species_name', 
                    'eng_name', 'slug', 'characteristic', 'distribution', 'morphologic_feature', 
                    'behavior', 'protection_method', 'thumbnail', 'genus']


@admin.register(InsectsImage)
class InsectImageAdmin(admin.ModelAdmin):
    list_display = ['img_id', 'image_tag', 'insects']

    def image_tag(self, obj):
        if obj.url:
            full_url = f"{settings.MEDIA_URL}{obj.url}"
            return format_html('<img src="{}" width="150" height="auto" />', full_url)
        return "-"
    image_tag.short_description = 'url'


@admin.register(InsectsBbox)
class InsectsBboxAdmin(admin.ModelAdmin):
    list_display = ['box_id', 'x', 'y', 'width', 'height', 'img']
# # Species table
# @admin.register(Species)
# class SpiecesAdmin(admin.ModelAdmin):
#     list_display = ['insects_id', 'ename', 'name', 'eng_name', 'slug', 'distribution', 
#                     'characteristic', 'behavior', 'protection_method', 'thumbnail', 'family']
    
# # insects_image table
# @admin.register(InsectsImage)
# class ImageAdmin(admin.ModelAdmin):
#     list_display = ['img_id', 'url', 'subset', 'insects']

