from decimal import Decimal

from django.db import migrations, models


DEALS = [
    {
        "title": "Family Feast",
        "badge": "Best value",
        "description": "Meat Lovers, Four Cheese and Margherita together. Enough for the whole table.",
        "image": "meatlover.jpg",
        "image_alt": "Meat lovers pizza",
        "offer_text": "GH₵50",
        "previous_price": Decimal("60.00"),
        "button_text": "Order this deal",
        "button_url": "menu.html",
        "is_featured": True,
        "sort_order": 0,
    },
    {
        "title": "Two Classics",
        "badge": "Every day",
        "description": "Any two Classic and Traditional pizzas for one lower price.",
        "image": "pepperoni-pizza.jpg",
        "image_alt": "Pepperoni pizza",
        "offer_text": "GH₵35",
        "previous_price": Decimal("40.00"),
        "button_text": "View classics",
        "button_url": "menu.html#classic",
        "is_featured": False,
        "sort_order": 1,
    },
    {
        "title": "Veggie Tuesday",
        "badge": "Tuesdays",
        "description": "Our Garden Veggie pizza at a special price every Tuesday.",
        "image": "viggies.jpg",
        "image_alt": "Garden veggie pizza",
        "offer_text": "GH₵15",
        "previous_price": Decimal("20.00"),
        "button_text": "View veggie",
        "button_url": "menu.html#plant-based",
        "is_featured": False,
        "sort_order": 2,
    },
    {
        "title": "Cheese Weekend",
        "badge": "Weekends",
        "description": "Mozzarella, cheddar, parmesan and gorgonzola, a little cheaper on Saturday and Sunday.",
        "image": "four-cheese.jpg",
        "image_alt": "Four cheese pizza",
        "offer_text": "GH₵18",
        "previous_price": Decimal("20.00"),
        "button_text": "View pizza",
        "button_url": "menu.html#classic",
        "is_featured": False,
        "sort_order": 3,
    },
    {
        "title": "Student Special",
        "badge": "Students",
        "description": "Show a valid student ID when you order and get 10% off any pizza.",
        "image": "Pizza-Margheritta.webp",
        "image_alt": "Margherita pizza",
        "offer_text": "10% off",
        "previous_price": None,
        "button_text": "Browse menu",
        "button_url": "menu.html",
        "is_featured": False,
        "sort_order": 4,
    },
]


def create_initial_deals(apps, schema_editor):
    Deal = apps.get_model("ordering", "Deal")
    Deal.objects.using(schema_editor.connection.alias).bulk_create(
        [Deal(**deal) for deal in DEALS]
    )


class Migration(migrations.Migration):
    dependencies = [
        ("ordering", "0003_category_model"),
    ]

    operations = [
        migrations.CreateModel(
            name="Deal",
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
                ("title", models.CharField(max_length=100)),
                ("badge", models.CharField(blank=True, max_length=40)),
                ("description", models.TextField()),
                ("image", models.CharField(max_length=200)),
                ("image_alt", models.CharField(max_length=150)),
                ("offer_text", models.CharField(max_length=80)),
                (
                    "previous_price",
                    models.DecimalField(
                        blank=True,
                        decimal_places=2,
                        max_digits=7,
                        null=True,
                    ),
                ),
                ("button_text", models.CharField(default="Browse menu", max_length=40)),
                ("button_url", models.CharField(default="menu.html", max_length=250)),
                ("is_featured", models.BooleanField(default=False)),
                ("is_active", models.BooleanField(default=True)),
                ("sort_order", models.PositiveSmallIntegerField(default=0)),
            ],
            options={
                "ordering": ["-is_featured", "sort_order", "title"],
            },
        ),
        migrations.RunPython(create_initial_deals, migrations.RunPython.noop),
    ]
