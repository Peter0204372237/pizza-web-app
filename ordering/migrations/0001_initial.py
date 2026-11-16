import django.db.models.deletion
import ordering.models
from django.db import migrations, models


PIZZAS = [
    {
        "slug": "margherita",
        "name": "Margherita",
        "category": "Classic",
        "description": "A simple Italian favorite with bright tomato, creamy mozzarella, and fresh basil.",
        "ingredients": ["San Marzano tomato", "fresh mozzarella", "basil", "olive oil"],
        "image": "Pizza-Margheritta.webp",
    },
    {
        "slug": "pepperoni-classic",
        "name": "Pepperoni Classic",
        "category": "Classic",
        "description": "Mozzarella and crisp-edge pepperoni baked over our rich tomato sauce.",
        "ingredients": ["tomato sauce", "mozzarella", "pepperoni"],
        "image": "pepperoni-pizza.jpg",
    },
    {
        "slug": "four-cheese",
        "name": "Four Cheese",
        "category": "Classic",
        "description": "A rich, melty blend of four cheeses on a golden crust.",
        "ingredients": ["mozzarella", "cheddar", "parmesan", "gorgonzola"],
        "image": "four-cheese.jpg",
    },
    {
        "slug": "truffle-mushroom",
        "name": "Truffle Mushroom",
        "category": "Signature",
        "description": "Earthy wild mushrooms meet fragrant truffle cream, thyme, and parmesan.",
        "ingredients": ["wild mushrooms", "truffle cream", "thyme", "parmesan"],
        "image": "mushroom-pizza.jpg",
    },
    {
        "slug": "prosciutto-arugula",
        "name": "Prosciutto Arugula",
        "category": "Signature",
        "description": "Savory prosciutto, peppery fresh arugula, parmesan, and a balsamic finish.",
        "ingredients": ["prosciutto", "fresh arugula", "shaved parmesan", "balsamic glaze"],
        "image": "proscito.jpg",
    },
    {
        "slug": "hot-honey-salami",
        "name": "Hot Honey Salami",
        "category": "Signature",
        "description": "Spicy salami and chili flakes mellowed with mozzarella and a honey drizzle.",
        "ingredients": ["spicy salami", "chili flakes", "mozzarella", "hot honey"],
        "image": "hot%20honey.jpg",
    },
    {
        "slug": "chicago-deep-dish",
        "name": "Chicago Deep Dish",
        "category": "Deep dish",
        "description": "A buttery deep-dish crust layered with cheese, sausage, and chunky tomato.",
        "ingredients": ["buttery crust", "layered cheese", "sausage", "chunky tomato"],
        "image": "chicago%20pizza.jpg",
    },
    {
        "slug": "detroit-pan",
        "name": "Detroit Pan",
        "category": "Deep dish",
        "description": "Thick pan-baked dough with caramelized cheese edges, pepperoni, and sauce on top.",
        "ingredients": ["pan dough", "caramelized cheese", "pepperoni", "tomato sauce"],
        "image": "detroit.webp",
    },
    {
        "slug": "meat-lovers",
        "name": "Meat Lovers",
        "category": "Meat lovers",
        "description": "A hearty combination of five favorite meats, baked with mozzarella and tomato sauce.",
        "ingredients": ["pepperoni", "sausage", "bacon", "ham", "ground beef", "mozzarella"],
        "image": "meatlover.jpg",
    },
    {
        "slug": "bbq-chicken-smash",
        "name": "BBQ Chicken Smash",
        "category": "Meat lovers",
        "description": "Grilled chicken, smoky bacon, and red onion with BBQ sauce and mozzarella.",
        "ingredients": ["grilled chicken", "bacon", "red onion", "BBQ sauce", "mozzarella"],
        "image": "chickenpiz.jpg",
    },
    {
        "slug": "garden-veggie",
        "name": "Garden Veggie",
        "category": "Plant-based",
        "description": "A colorful garden mix of peppers, mushrooms, olives, onion, and tomato.",
        "ingredients": ["peppers", "mushrooms", "olives", "onion", "tomato"],
        "image": "viggies.jpg",
    },
    {
        "slug": "vegan-pesto",
        "name": "Vegan Pesto",
        "category": "Plant-based",
        "description": "Basil pesto, plant-based cheese, zucchini, and cherry tomato on a vegan-friendly base.",
        "ingredients": ["basil pesto", "plant-based cheese", "zucchini", "cherry tomato"],
        "image": "vegan.jpg",
    },
]


def seed_pizzas(apps, schema_editor):
    Pizza = apps.get_model("ordering", "Pizza")
    Pizza.objects.using(schema_editor.connection.alias).bulk_create(
        [Pizza(**pizza) for pizza in PIZZAS]
    )


class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="Order",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("reference", models.CharField(default=ordering.models.new_order_reference, editable=False, max_length=15, unique=True)),
                ("customer_name", models.CharField(max_length=120)),
                ("phone", models.CharField(db_index=True, max_length=15)),
                ("address", models.CharField(max_length=250)),
                ("city", models.CharField(max_length=100)),
                ("instructions", models.CharField(blank=True, max_length=500)),
                ("payment_method", models.CharField(default="Cash on delivery", max_length=30)),
                ("status", models.CharField(choices=[("received", "Order received"), ("preparing", "Preparing"), ("in_oven", "In the oven"), ("out_for_delivery", "Out for delivery"), ("delivered", "Delivered"), ("cancelled", "Cancelled")], default="received", max_length=20)),
                ("total", models.DecimalField(decimal_places=2, max_digits=9)),
                ("placed_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={"ordering": ["-placed_at"]},
        ),
        migrations.CreateModel(
            name="Pizza",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("slug", models.SlugField(unique=True)),
                ("name", models.CharField(max_length=100)),
                ("category", models.CharField(max_length=40)),
                ("description", models.TextField()),
                ("ingredients", models.JSONField(default=list)),
                ("image", models.CharField(max_length=200)),
                ("small_price", models.DecimalField(decimal_places=2, default=20, max_digits=7)),
                ("is_active", models.BooleanField(default=True)),
            ],
            options={"ordering": ["name"]},
        ),
        migrations.CreateModel(
            name="OrderItem",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("pizza_name", models.CharField(max_length=100)),
                ("quantity", models.PositiveSmallIntegerField()),
                ("unit_price", models.DecimalField(decimal_places=2, max_digits=7)),
                ("options", models.JSONField(default=dict)),
                ("order", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="items", to="ordering.order")),
                ("pizza", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to="ordering.pizza")),
            ],
        ),
        migrations.RunPython(seed_pizzas, migrations.RunPython.noop),
    ]
