import uuid

from django.core.validators import MinValueValidator
from django.db import models


def new_order_reference():
    return f"PS-{uuid.uuid4().hex[:12].upper()}"


class Category(models.Model):
    name = models.CharField(max_length=40, unique=True)
    slug = models.SlugField(max_length=50, unique=True)

    class Meta:
        ordering = ["name"]
        verbose_name_plural = "categories"

    def __str__(self):
        return self.name


class Pizza(models.Model):
    slug = models.SlugField(unique=True)
    name = models.CharField(max_length=100)
    category = models.ForeignKey(
        Category,
        related_name="pizzas",
        on_delete=models.PROTECT,
    )
    description = models.TextField()
    ingredients = models.JSONField(default=list)
    image = models.CharField(max_length=200)
    small_price = models.DecimalField(
        max_digits=7,
        decimal_places=2,
        default=20,
        validators=[MinValueValidator(0)],
    )
    medium_price = models.DecimalField(
        max_digits=7,
        decimal_places=2,
        default=30,
        validators=[MinValueValidator(0)],
    )
    large_price = models.DecimalField(
        max_digits=7,
        decimal_places=2,
        default=40,
        validators=[MinValueValidator(0)],
    )
    extra_large_price = models.DecimalField(
        max_digits=7,
        decimal_places=2,
        default=50,
        validators=[MinValueValidator(0)],
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name

    def price_for_size(self, size):
        price_fields = {
            "S": "small_price",
            "M": "medium_price",
            "L": "large_price",
            "XL": "extra_large_price",
        }
        return getattr(self, price_fields[size])


class MenuItem(models.Model):
    slug = models.SlugField(unique=True)
    name = models.CharField(max_length=100)
    category = models.ForeignKey(
        Category,
        related_name="menu_items",
        on_delete=models.PROTECT,
    )
    description = models.TextField()
    image = models.CharField(
        max_length=200,
        help_text="Static image filename/path or an absolute image URL.",
    )
    price = models.DecimalField(
        max_digits=7,
        decimal_places=2,
        validators=[MinValueValidator(0)],
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class Deal(models.Model):
    class PromotionType(models.TextChoices):
        NONE = "none", "Informational only"
        BUNDLE = "bundle", "Fixed-price bundle"
        CATEGORY_PAIR = "category_pair", "Fixed price for two category pizzas"
        PIZZA_PRICE = "pizza_price", "Fixed price for one pizza"

    class Schedule(models.TextChoices):
        ANY_DAY = "any_day", "Any day"
        TUESDAY = "tuesday", "Tuesday only"
        WEEKEND = "weekend", "Saturday and Sunday"

    title = models.CharField(max_length=100)
    badge = models.CharField(max_length=40, blank=True)
    description = models.TextField()
    image = models.CharField(max_length=200)
    image_alt = models.CharField(max_length=150)
    offer_text = models.CharField(max_length=80)
    previous_price = models.DecimalField(
        max_digits=7,
        decimal_places=2,
        null=True,
        blank=True,
    )
    button_text = models.CharField(max_length=40, default="Browse menu")
    button_url = models.CharField(max_length=250, default="menu.html")
    is_featured = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    sort_order = models.PositiveSmallIntegerField(default=0)
    promotion_type = models.CharField(
        max_length=20,
        choices=PromotionType.choices,
        default=PromotionType.NONE,
    )
    promotion_price = models.DecimalField(
        max_digits=7,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(0)],
    )
    promotion_schedule = models.CharField(
        max_length=10,
        choices=Schedule.choices,
        default=Schedule.ANY_DAY,
    )
    eligible_category = models.ForeignKey(
        Category,
        related_name="deals",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
    )
    eligible_pizzas = models.ManyToManyField(
        Pizza,
        related_name="deals",
        blank=True,
    )

    class Meta:
        ordering = ["-is_featured", "sort_order", "title"]

    def __str__(self):
        return self.title


class Order(models.Model):
    class Status(models.TextChoices):
        RECEIVED = "received", "Order received"
        PREPARING = "preparing", "Preparing"
        IN_OVEN = "in_oven", "In the oven"
        OUT_FOR_DELIVERY = "out_for_delivery", "Out for delivery"
        DELIVERED = "delivered", "Delivered"
        CANCELLED = "cancelled", "Cancelled"

    reference = models.CharField(
        max_length=15,
        unique=True,
        default=new_order_reference,
        editable=False,
    )
    customer_name = models.CharField(max_length=120)
    phone = models.CharField(max_length=15, db_index=True)
    address = models.CharField(max_length=250)
    city = models.CharField(max_length=100)
    instructions = models.CharField(max_length=500, blank=True)
    payment_method = models.CharField(max_length=30, default="Cash on delivery")
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.RECEIVED,
    )
    subtotal = models.DecimalField(max_digits=9, decimal_places=2, default=0)
    discount_total = models.DecimalField(max_digits=9, decimal_places=2, default=0)
    discounts = models.JSONField(default=list)
    total = models.DecimalField(max_digits=9, decimal_places=2)
    placed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-placed_at"]

    def __str__(self):
        return self.reference


class OrderItem(models.Model):
    order = models.ForeignKey(Order, related_name="items", on_delete=models.CASCADE)
    pizza = models.ForeignKey(
        Pizza,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
    )
    menu_item = models.ForeignKey(
        MenuItem,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
    )
    pizza_name = models.CharField(max_length=100)
    quantity = models.PositiveSmallIntegerField()
    unit_price = models.DecimalField(max_digits=7, decimal_places=2)
    options = models.JSONField(default=dict)

    def __str__(self):
        return f"{self.quantity} x {self.pizza_name}"
