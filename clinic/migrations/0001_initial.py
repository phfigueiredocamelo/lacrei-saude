# Generated manually because Django is unavailable in this environment.

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="Professional",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("is_active", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("deleted_at", models.DateTimeField(blank=True, null=True)),
                ("social_name", models.CharField(max_length=150)),
                ("slug", models.SlugField(max_length=170, unique=True)),
                ("profession", models.CharField(max_length=120)),
                ("address", models.CharField(max_length=255)),
                ("contact", models.CharField(max_length=120)),
            ],
            options={
                "ordering": ["social_name"],
            },
        ),
        migrations.CreateModel(
            name="Appointment",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("is_active", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("deleted_at", models.DateTimeField(blank=True, null=True)),
                ("date", models.DateTimeField()),
                ("customer_name", models.CharField(max_length=150)),
                ("customer_document", models.CharField(max_length=40)),
                ("price", models.DecimalField(decimal_places=2, max_digits=10)),
                (
                    "payment_status",
                    models.CharField(
                        choices=[
                            ("PENDING", "Pending"),
                            ("CREATED", "Created"),
                            ("PAID", "Paid"),
                            ("FAILED", "Failed"),
                            ("CANCELED", "Canceled"),
                        ],
                        default="PENDING",
                        max_length=20,
                    ),
                ),
                ("asaas_payment_id", models.CharField(blank=True, max_length=80)),
                ("asaas_customer_id", models.CharField(blank=True, max_length=80)),
                ("asaas_split", models.JSONField(blank=True, default=list)),
                (
                    "professional",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="appointments",
                        to="clinic.professional",
                    ),
                ),
            ],
            options={
                "ordering": ["date", "id"],
            },
        ),
    ]
