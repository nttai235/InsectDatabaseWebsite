import os

from django import forms
from django.contrib.auth.models import User, Group
from django.core.files.storage import FileSystemStorage

from insects.models import Species, Phylum, Class, Order, Family, Genus, InsectsImage

# form user
class UserEditForm(forms.ModelForm):
    groups = forms.ModelChoiceField(
        queryset=Group.objects.all(),
        widget=forms.RadioSelect,
        required=False,
        label="Phân quyền"
    )

    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'email', 'groups']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            groups = self.instance.groups.all()
            if groups.exists():
                self.initial['groups'] = groups.first()


# Form lớp
class ClassesEditForm(forms.ModelForm):
    phylum = forms.ModelChoiceField(
        queryset=Phylum.objects.all(),
        widget=forms.Select(attrs={'class': 'form-select', 'id': 'phylum'}),
        empty_label=None,
        label="Ngành"
    )

    class Meta:
        model = Class
        fields = ['class_id', 'ename', 'name', 'phylum']

    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.slug = f"class_{instance.ename.replace(' ', '_')}"
        if commit:
            instance.save()
        return instance

# Form bộ
class OrderEditForm(forms.ModelForm):
    class_field = forms.ModelChoiceField(
        queryset=Class.objects.all(),
        widget=forms.Select(attrs={'class': 'form-select', 'id': 'class_field'}),
        empty_label=None,
        label="Lớp"
    )

    class Meta:
        model = Order
        fields = ['order_id', 'ename', 'name', 'class_field']

    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.slug = f"order_{instance.ename.replace(' ', '_')}"
        if commit:
            instance.save()
        return instance

# Form họ
class FamilyEditForm(forms.ModelForm):
    order = forms.ModelChoiceField(
        queryset=Order.objects.all(),
        widget=forms.Select(attrs={'class': 'form-select', 'id': 'order'}),
        empty_label=None,
        label="Bộ"
    )

    class Meta:
        model = Family
        fields = ['family_id', 'ename', 'name', 'order']

    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.slug = f"family_{instance.ename.replace(' ', '_')}"
        if commit:
            instance.save()
        return instance

# Form chi
class GenusEditForm(forms.ModelForm):
    family = forms.ModelChoiceField(
        queryset=Family.objects.all(),
        widget=forms.Select(attrs={'class': 'form-select', 'id': 'family'}),
        empty_label=None,
        label="Họ"
    )

    class Meta:
        model = Genus
        fields = ['genus_id', 'ename', 'name', 'family']

    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.slug = f"genus_{instance.ename.replace(' ', '_')}"
        if commit:
            instance.save()
        return instance


# Form loài
class SpeciesEditForm(forms.ModelForm):
    genus = forms.ModelChoiceField(
        queryset=Genus.objects.all(),
        widget=forms.Select(attrs={'class': 'form-select', 'id': 'genus'}),
        empty_label=None,
        label="Chi"
    )

    class Meta:
        model = Species
        fields = ['insects_id', 'ename', 'name', 'species_name', 'eng_name', 'vi_name', 'morphologic_feature', 'distribution', 'characteristic', 'behavior', 'protection_method', 'thumbnail', 'genus']

    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.slug = f"species_{instance.ename.replace(' ', '_')}"
        if commit:
            instance.save()
        return instance


class InsectsImageForm(forms.ModelForm):
    class Meta:
        model = InsectsImage
        fields = ["desc"]
        widgets = {
            "desc": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
        }