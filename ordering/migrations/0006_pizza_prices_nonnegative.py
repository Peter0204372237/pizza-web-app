import django.core.validators
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("ordering", "0005_checkout_promotions"),
    ]

    operations = [
        migrations.AlterField(
            model_name="pizza",
            name="small_price",
            field=models.DecimalField(
                decimal_places=2,
                default=20,
                max_digits=7,
                validators=[django.core.validators.MinValueValidator(0)],
            ),
        ),
        migrations.AlterField(
            model_name="pizza",
            name="medium_price",
            field=models.DecimalField(
                decimal_places=2,
                default=30,
                max_digits=7,
                validators=[django.core.validators.MinValueValidator(0)],
            ),
        ),
        migrations.AlterField(
            model_name="pizza",
            name="large_price",
            field=models.DecimalField(
                decimal_places=2,
                default=40,
                max_digits=7,
                validators=[django.core.validators.MinValueValidator(0)],
            ),
        ),
        migrations.AlterField(
            model_name="pizza",
            name="extra_large_price",
            field=models.DecimalField(
                decimal_places=2,
                default=50,
                max_digits=7,
                validators=[django.core.validators.MinValueValidator(0)],
            ),
        ),
    ]
