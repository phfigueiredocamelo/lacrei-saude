from decimal import Decimal

from django.db import models
from django.utils import timezone
from django.utils.text import slugify


class ActiveQuerySet(models.QuerySet):
    def active(self):
        return self.filter(is_active=True)

    def delete(self):
        deleted_at = timezone.now()
        count = self.update(
            is_active=False,
            deleted_at=deleted_at,
            updated_at=deleted_at,
        )
        return count, {self.model._meta.label: count}


class ActiveManager(models.Manager.from_queryset(ActiveQuerySet)):
    def get_queryset(self):
        return super().get_queryset().active()


class AllObjectsManager(models.Manager.from_queryset(ActiveQuerySet)):
    def get_queryset(self):
        return ActiveQuerySet(self.model, using=self._db)


class SoftDeleteModel(models.Model):
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    deleted_at = models.DateTimeField(blank=True, null=True)

    objects = ActiveManager()
    all_objects = AllObjectsManager()

    class Meta:
        abstract = True

    def delete(self, using=None, keep_parents=False):
        self.is_active = False
        self.deleted_at = timezone.now()
        self.save(update_fields=["is_active", "deleted_at", "updated_at"])
        return 1, {self._meta.label: 1}


class Professional(SoftDeleteModel):
    social_name = models.CharField(max_length=150)
    slug = models.SlugField(max_length=170, unique=True)
    profession = models.CharField(max_length=120)
    address = models.CharField(max_length=255)
    contact = models.CharField(max_length=120)

    class Meta:
        ordering = ["social_name"]

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.social_name)
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return self.social_name


class Appointment(SoftDeleteModel):
    class PaymentStatus(models.TextChoices):
        PENDING = "PENDING", "Pending"
        CREATED = "CREATED", "Created"
        PAID = "PAID", "Paid"
        FAILED = "FAILED", "Failed"
        CANCELED = "CANCELED", "Canceled"

    date = models.DateTimeField()
    professional = models.ForeignKey(
        Professional,
        on_delete=models.PROTECT,
        related_name="appointments",
    )
    customer_name = models.CharField(max_length=150)
    customer_document = models.CharField(max_length=40)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    payment_status = models.CharField(
        max_length=20,
        choices=PaymentStatus.choices,
        default=PaymentStatus.PENDING,
    )
    asaas_payment_id = models.CharField(max_length=80, blank=True)
    asaas_customer_id = models.CharField(max_length=80, blank=True)
    asaas_split = models.JSONField(default=list, blank=True)

    class Meta:
        ordering = ["date", "id"]

    @property
    def external_reference(self) -> str:
        return f"appointment:{self.id}"

    @property
    def price_as_decimal(self):
        return Decimal(self.price)

    def __str__(self) -> str:
        appointment_date = self.date.strftime("%Y-%m-%d %H:%M")
        return f"{self.customer_name} with {self.professional} on {appointment_date}"
