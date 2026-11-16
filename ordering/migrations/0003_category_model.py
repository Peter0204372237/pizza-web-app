from django.db import migrations, models
import django.db.models.deletion
from django.utils.text import slugify


def move_pizza_categories(apps, schema_editor):
    Category = apps.get_model("ordering", "Category")
    Pizza = apps.get_model("ordering", "Pizza")
    database = schema_editor.connection.alias
    category_names = (
        Pizza.objects.using(database)
        .order_by()
        .values_list("category", flat=True)
        .distinct()
        .order_by("category")
    )
    categories = {}
    used_slugs = set()
    categories_by_name = {}

    for existing_name in category_names:
        name = existing_name or "Uncategorized"
        category = categories_by_name.get(name)
        if category is None:
            base_slug = slugify(name) or "uncategorized"
            category_slug = base_slug
            suffix = 2
            while category_slug in used_slugs:
                category_slug = f"{base_slug}-{suffix}"
                suffix += 1
            used_slugs.add(category_slug)
            category = Category.objects.using(database).create(
                name=name,
                slug=category_slug,
            )
            categories_by_name[name] = category
        categories[existing_name] = category.pk

    for existing_name, category_id in categories.items():
        Pizza.objects.using(database).filter(category=existing_name).update(
            category_ref_id=category_id
        )


class Migration(migrations.Migration):
    dependencies = [
        ("ordering", "0002_pizza_size_prices"),
    ]

    operations = [
        migrations.CreateModel(
            name="Category",
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
                ("name", models.CharField(max_length=40, unique=True)),
                ("slug", models.SlugField(max_length=50, unique=True)),
            ],
            options={
                "ordering": ["name"],
                "verbose_name_plural": "categories",
            },
        ),
        migrations.AddField(
            model_name="pizza",
            name="category_ref",
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="pizzas",
                to="ordering.category",
            ),
        ),
        migrations.RunPython(move_pizza_categories, migrations.RunPython.noop),
        migrations.RemoveField(
            model_name="pizza",
            name="category",
        ),
        migrations.RenameField(
            model_name="pizza",
            old_name="category_ref",
            new_name="category",
        ),
        migrations.AlterField(
            model_name="pizza",
            name="category",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name="pizzas",
                to="ordering.category",
            ),
        ),
    ]
