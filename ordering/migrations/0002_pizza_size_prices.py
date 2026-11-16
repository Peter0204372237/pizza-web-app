from decimal import Decimal

from django.db import migrations, models


def populate_size_prices(apps, schema_editor):
    Pizza = apps.get_model("ordering", "Pizza")
    database = schema_editor.connection.alias
    for pizza in Pizza.objects.using(database).all().iterator():
        pizza.medium_price = pizza.small_price + Decimal("10.00")
        pizza.large_price = pizza.small_price + Decimal("20.00")
        pizza.extra_large_price = pizza.small_price + Decimal("30.00")
        pizza.save(
            using=database,
            update_fields=("medium_price", "large_price", "extra_large_price"),
        )


class Migration(migrations.Migration):
    dependencies = [
        ("ordering", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="pizza",
            name="medium_price",
            field=models.DecimalField(decimal_places=2, default=30, max_digits=7),
        ),
        migrations.AddField(
            model_name="pizza",
            name="large_price",
            field=models.DecimalField(decimal_places=2, default=40, max_digits=7),
        ),
        migrations.AddField(
            model_name="pizza",
            name="extra_large_price",
            field=models.DecimalField(decimal_places=2, default=50, max_digits=7),
        ),
        migrations.RunPython(populate_size_prices, migrations.RunPython.noop),
    ]
