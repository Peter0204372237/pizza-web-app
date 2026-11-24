from django.db import migrations


DEALS = [
    {
        "title": "Shrimp Pizza",
        "badge": "50% OFF",
        "description": "A savory shrimp pizza offered at half price.",
        "image": "pizz.jpg",
        "image_alt": "Pizza with assorted colorful toppings",
        "offer_text": "GH₵57.50 – GH₵122.50",
        "previous_price": None,
        "button_text": "Browse menu",
        "button_url": "menu.html",
        "is_featured": False,
        "is_active": True,
        "sort_order": 5,
    },
    {
        "title": "Ten-Topping",
        "badge": "50% OFF",
        "description": "Pepperoni, sausage, beef, chicken, onion, tomato, olive, red pepper, mushroom, pineapple, and corn.",
        "image": "chickenpiz.jpg",
        "image_alt": "Pizza topped with a variety of meats and vegetables",
        "offer_text": "GH₵55 – GH₵120",
        "previous_price": None,
        "button_text": "Browse menu",
        "button_url": "menu.html",
        "is_featured": False,
        "is_active": True,
        "sort_order": 6,
    },
    {
        "title": "Fruity Pizza",
        "badge": "50% OFF",
        "description": "A sweet pizza topped with pineapple, peaches, apple, and raisin.",
        "image": "hawaipic.webp",
        "image_alt": "Hawaiian-style pizza topped with pineapple",
        "offer_text": "GH₵49 – GH₵105",
        "previous_price": None,
        "button_text": "Browse menu",
        "button_url": "menu.html",
        "is_featured": False,
        "is_active": True,
        "sort_order": 7,
    },
    {
        "title": "4 Cheese Margherita",
        "badge": "50% OFF",
        "description": "A four-cheese take on the classic Margherita.",
        "image": "four-cheese.jpg",
        "image_alt": "Four-cheese pizza",
        "offer_text": "GH₵49 – GH₵107.50",
        "previous_price": None,
        "button_text": "Browse menu",
        "button_url": "menu.html",
        "is_featured": False,
        "is_active": True,
        "sort_order": 8,
    },
    {
        "title": "Steak House",
        "badge": "50% OFF",
        "description": "A hearty steak pizza topped with Angus and sirloin.",
        "image": "meatlover.jpg",
        "image_alt": "Hearty meat-topped pizza",
        "offer_text": "GH₵49 – GH₵107.50",
        "previous_price": None,
        "button_text": "Browse menu",
        "button_url": "menu.html",
        "is_featured": False,
        "is_active": True,
        "sort_order": 9,
    },
]


def add_half_price_deals(apps, schema_editor):
    Deal = apps.get_model("ordering", "Deal")
    database = schema_editor.connection.alias
    for deal in DEALS:
        Deal.objects.using(database).get_or_create(
            title=deal["title"],
            defaults=deal,
        )


def remove_half_price_deals(apps, schema_editor):
    Deal = apps.get_model("ordering", "Deal")
    database = schema_editor.connection.alias
    for deal in DEALS:
        Deal.objects.using(database).filter(
            title=deal["title"],
            badge="50% OFF",
            sort_order=deal["sort_order"],
        ).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("ordering", "0006_pizza_prices_nonnegative"),
    ]

    operations = [
        migrations.RunPython(add_half_price_deals, remove_half_price_deals),
    ]
