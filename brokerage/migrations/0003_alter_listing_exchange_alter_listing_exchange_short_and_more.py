# Generated by Django 5.0.3 on 2024-04-19 08:01

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        (
            "brokerage",
            "0002_alter_listing_exchange_alter_listing_exchange_short_and_more",
        ),
    ]

    operations = [
        migrations.AlterField(
            model_name="listing",
            name="exchange",
            field=models.CharField(blank=True, max_length=20, null=True),
        ),
        migrations.AlterField(
            model_name="listing",
            name="exchange_short",
            field=models.CharField(blank=True, max_length=20, null=True),
        ),
        migrations.AlterField(
            model_name="listing",
            name="listing_type",
            field=models.CharField(blank=True, max_length=20, null=True),
        ),
        migrations.AlterField(
            model_name="listing",
            name="name",
            field=models.CharField(blank=True, max_length=100, null=True),
        ),
        migrations.AlterField(
            model_name="listing",
            name="price",
            field=models.DecimalField(
                blank=True, decimal_places=2, max_digits=10, null=True
            ),
        ),
        migrations.AlterField(
            model_name="listing",
            name="symbol",
            field=models.CharField(blank=True, max_length=20, null=True),
        ),
    ]
