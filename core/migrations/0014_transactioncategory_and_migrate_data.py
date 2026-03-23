# Generated manually for category migration

import django.db.models.deletion
from django.db import migrations, models


def create_categories_and_migrate(apps, schema_editor):
    """Create TransactionCategory records and migrate existing Transaction data"""
    Transaction = apps.get_model('core', 'Transaction')
    TransactionCategory = apps.get_model('core', 'TransactionCategory')
    
    # Get all unique categories from existing transactions
    existing_categories = Transaction.objects.values_list('category', flat=True).distinct()
    existing_categories = [c for c in existing_categories if c]  # Filter out None/empty
    
    # Predefined categories
    predefined_categories = [
        "Utility payment - Itta",
        "Utility payment - Rod",
        "Utility payment - Cement",
        "Utility payment - Diesel",
        "Company Inventory",
        "Sales",
        "Constructions and Supply",
        "Uncle - handover",
        "Vehicle Expense - Tripper",
        "Vehicle Expense - Nissan",
    ]
    
    # Create predefined categories
    for cat_name in predefined_categories:
        TransactionCategory.objects.get_or_create(
            name=cat_name,
            defaults={'is_predefined': True}
        )
    
    # For existing categories not in predefined list, create as custom (is_predefined=False)
    for cat_name in existing_categories:
        if cat_name not in predefined_categories:
            TransactionCategory.objects.get_or_create(
                name=cat_name,
                defaults={'is_predefined': False}
            )
    
    # Now update Transaction records to point to the new TransactionCategory using raw SQL
    # since the field is being transformed
    from django.db import connection
    with connection.cursor() as cursor:
        for transaction in Transaction.objects.all():
            if transaction.category:
                try:
                    cat_obj = TransactionCategory.objects.get(name=transaction.category)
                    cursor.execute(
                        "UPDATE core_transaction SET category_new_id = %s WHERE id = %s",
                        [cat_obj.id, transaction.id]
                    )
                except TransactionCategory.DoesNotExist:
                    pass


def reverse_migrate(apps, schema_editor):
    """Reverse the migration - restore category as char field"""
    Transaction = apps.get_model('core', 'Transaction')
    TransactionCategory = apps.get_model('core', 'TransactionCategory')
    
    # Restore category name from TransactionCategory
    for transaction in Transaction.objects.select_related('category').all():
        if transaction.category:
            transaction.category_id = transaction.category.name
    Transaction.objects.bulk_update(Transaction.objects.all(), ['category_id'], batch_size=100)


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0013_sale_alert_enabled"),
    ]

    operations = [
        # Create the TransactionCategory model
        migrations.CreateModel(
            name="TransactionCategory",
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
                ("name", models.CharField(max_length=100, unique=True)),
                (
                    "is_predefined",
                    models.BooleanField(
                        default=True,
                        help_text="If True, this is a system-defined category",
                    ),
                ),
            ],
            options={
                "ordering": ["name"],
            },
        ),
        # Add the new ForeignKey field (initially nullable)
        migrations.AddField(
            model_name="transaction",
            name="category_new",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="transactions",
                to="core.transactioncategory",
            ),
        ),
        # Data migration
        migrations.RunPython(create_categories_and_migrate, reverse_migrate),
        # Remove old category field
        migrations.RemoveField(
            model_name="transaction",
            name="category",
        ),
        # Rename the new field to category
        migrations.RenameField(
            model_name="transaction",
            old_name="category_new",
            new_name="category",
        ),
    ]
