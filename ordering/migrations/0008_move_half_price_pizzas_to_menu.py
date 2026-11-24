from decimal import Decimal

from django.db import migrations


PIZZAS = [
    {
        "slug": "shrimp-pizza",
        "name": "Shrimp Pizza",
        "description": "A savory pizza topped with shrimp.",
        "ingredients": ["Shrimp"],
        "image": "pizz.jpg",
        "small_price": Decimal("57.50"),
        "medium_price": Decimal("79.00"),
        "large_price": Decimal("101.00"),
        "extra_large_price": Decimal("122.50"),
    },
    {
        "slug": "ten-topping",
        "name": "Ten-Topping",
        "description": "Pepperoni, sausage, beef, chicken, onion, tomato, olive, red pepper, mushroom, pineapple, and corn.",
        "ingredients": [
            "Pepperoni",
            "Sausage",
            "Beef",
            "Chicken",
            "Onion",
            "Tomato",
            "Olive",
            "Red pepper",
            "Mushroom",
            "Pineapple",
            "Corn",
        ],
        "image": "chickenpiz.jpg",
        "small_price": Decimal("55.00"),
        "medium_price": Decimal("76.50"),
        "large_price": Decimal("98.50"),
        "extra_large_price": Decimal("120.00"),
    },
    {
        "slug": "fruity-pizza",
        "name": "Fruity Pizza",
        "description": "A sweet pizza topped with pineapple, peaches, apple, and raisin.",
        "ingredients": ["Pineapple", "Peaches", "Apple", "Raisin"],
        "image": "hawaipic.webp",
        "small_price": Decimal("49.00"),
        "medium_price": Decimal("67.50"),
        "large_price": Decimal("86.50"),
        "extra_large_price": Decimal("105.00"),
    },
    {
        "slug": "four-cheese-margherita",
        "name": "4 Cheese Margherita",
        "description": "A Margherita-style pizza made with four cheeses.",
        "ingredients": ["Tomato sauce", "Four cheeses"],
        "image": "four-cheese.jpg",
        "small_price": Decimal("49.00"),
        "medium_price": Decimal("68.50"),
        "large_price": Decimal("88.00"),
        "extra_large_price": Decimal("107.50"),
    },
    {
        "slug": "steak-house",
        "name": "Steak House",
        "description": "A hearty steak pizza topped with Angus and sirloin.",
        "ingredients": ["Angus", "Sirloin"],
        "image": "meatlover.jpg",
        "small_price": Decimal("49.00"),
        "medium_price": Decimal("68.50"),
        "large_price": Decimal("88.00"),
        "extra_large_price": Decimal("107.50"),
    },
]

DEAL_TITLES = [pizza["name"] for pizza in PIZZAS]


def move_half_price_pizzas_to_menu(apps, schema_editor):
    Category = apps.get_model("ordering", "Category")
    Deal = apps.get_model("ordering", "Deal")
    Pizza = apps.get_model("ordering", "Pizza")
    database = schema_editor.connection.alias
    category_id = Category.objects.using(database).get(slug="signature").pk

    for data in PIZZAS:
        pizza_data = {
            **data,
            "category_id": category_id,
            "is_active": True,
        }
        pizza, created = Pizza.objects.using(database).get_or_create(
            slug=data["slug"],
            defaults=pizza_data,
        )
        if not created and not pizza.is_active:
            pizza.is_active = True
            pizza.save(using=database, update_fields=("is_active",))

    Deal.objects.using(database).filter(title__in=DEAL_TITLES).update(
        is_active=False
    )


def restore_half_price_deals(apps, schema_editor):
    Deal = apps.get_model("ordering", "Deal")
    Pizza = apps.get_model("ordering", "Pizza")
    database = schema_editor.connection.alias

    Pizza.objects.using(database).filter(
        slug__in=[pizza["slug"] for pizza in PIZZAS]
    ).update(is_active=False)
    Deal.objects.using(database).filter(title__in=DEAL_TITLES).update(
        is_active=True
    )


class Migration(migrations.Migration):
    dependencies = [
        ("ordering", "0007_half_price_pizza_deals"),
    ]

    operations = [
        migrations.RunPython(
            move_half_price_pizzas_to_menu,
            restore_half_price_deals,
        ),
    ]
