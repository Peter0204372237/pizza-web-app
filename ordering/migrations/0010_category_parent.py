from django.db import migrations, models
import django.db.models.deletion


def create_pizza_parent_category(apps, schema_editor):
    Category = apps.get_model("ordering", "Category")
    database = schema_editor.connection.alias
    pizza_category, _created = Category.objects.using(database).get_or_create(
        slug="pizza",
        defaults={"name": "Pizza"},
    )
    Category.objects.using(database).filter(
        pizzas__isnull=False,
    ).exclude(
        pk=pizza_category.pk,
    ).update(parent_id=pizza_category.pk)


class Migration(migrations.Migration):

    dependencies = [
        ("ordering", "0009_alter_orderitem_pizza_menuitem_orderitem_menu_item"),
    ]

    operations = [
        migrations.AddField(
            model_name="category",
            name="parent",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="children",
                to="ordering.category",
            ),
        ),
        migrations.RunPython(
            create_pizza_parent_category,
            migrations.RunPython.noop,
        ),
    ]
