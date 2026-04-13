from django.db import migrations, models


def forwards(apps, schema_editor):
	BlocksRecord = apps.get_model("core", "BlocksRecord")
	BlocksRecord.objects.filter(record_type="financial").update(record_type="investment")


def backwards(apps, schema_editor):
	BlocksRecord = apps.get_model("core", "BlocksRecord")
	BlocksRecord.objects.filter(record_type="investment").update(record_type="financial")


class Migration(migrations.Migration):

	dependencies = [
		("core", "0019_blocksrecord_transaction_blocks_record"),
	]

	operations = [
		migrations.RunPython(forwards, backwards),
		migrations.AlterField(
			model_name="blocksrecord",
			name="record_type",
			field=models.CharField(
				choices=[
					("investment", "Investment"),
					("stock", "Stock (Addition)"),
					("sale", "Sale"),
				],
				help_text="Type of record: investment, stock inventory update, or sale",
				max_length=20,
			),
		),
	]