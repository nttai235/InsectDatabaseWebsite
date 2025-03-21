# Generated by Django 5.0.2 on 2024-03-30 04:09

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('insects', '0002_alter_class_options_alter_family_options_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='Genus',
            fields=[
                ('genus_id', models.AutoField(primary_key=True, serialize=False)),
                ('ename', models.CharField(db_column='eName', max_length=100)),
                ('name', models.CharField(max_length=100)),
                ('slug', models.CharField(max_length=100)),
            ],
            options={
                'db_table': 'genus',
                'managed': False,
            },
        ),
        migrations.AlterModelOptions(
            name='class',
            options={'managed': False},
        ),
        migrations.AlterModelOptions(
            name='family',
            options={'managed': False},
        ),
        migrations.AlterModelOptions(
            name='insectsbbox',
            options={'managed': False},
        ),
        migrations.AlterModelOptions(
            name='insectsimage',
            options={'managed': False},
        ),
        migrations.AlterModelOptions(
            name='kingdom',
            options={'managed': False},
        ),
        migrations.AlterModelOptions(
            name='order',
            options={'managed': False},
        ),
        migrations.AlterModelOptions(
            name='phylum',
            options={'managed': False},
        ),
        migrations.AlterModelOptions(
            name='species',
            options={'managed': False},
        ),
    ]
