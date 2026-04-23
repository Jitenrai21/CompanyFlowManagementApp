import json
from pathlib import Path

from django.core.management.base import BaseCommand

from core.models import (
    AlertNotification,
    BambooRecord,
    BlocksRecord,
    CementRecord,
    CustomerPayment,
    JCBRecord,
    Sale,
    TipperRecord,
    Transaction,
)


class Command(BaseCommand):
    help = "Export current AD date values for migration audit and BS backfill validation."

    def add_arguments(self, parser):
        parser.add_argument(
            "--output",
            default="ad_date_inventory.json",
            help="Output JSON file path (default: ad_date_inventory.json)",
        )

    def handle(self, *args, **options):
        output_path = Path(options["output"])

        payload = {
            "transactions": [
                {"id": row.id, "date": row.date.isoformat() if row.date else None}
                for row in Transaction.objects.only("id", "date")
            ],
            "sales": [
                {
                    "id": row.id,
                    "date": row.date.isoformat() if row.date else None,
                    "due_date": row.due_date.isoformat() if row.due_date else None,
                }
                for row in Sale.objects.only("id", "date", "due_date")
            ],
            "jcb_records": [
                {"id": row.id, "date": row.date.isoformat() if row.date else None}
                for row in JCBRecord.objects.only("id", "date")
            ],
            "tipper_records": [
                {"id": row.id, "date": row.date.isoformat() if row.date else None}
                for row in TipperRecord.objects.only("id", "date")
            ],
            "alert_notifications": [
                {"id": row.id, "due_date": row.due_date.isoformat() if row.due_date else None}
                for row in AlertNotification.objects.only("id", "due_date")
            ],
            "customer_payments": [
                {
                    "id": row.id,
                    "payment_date": row.payment_date.isoformat() if row.payment_date else None,
                }
                for row in CustomerPayment.objects.only("id", "payment_date")
            ],
            "blocks_records": [
                {"id": row.id, "date": row.date.isoformat() if row.date else None}
                for row in BlocksRecord.objects.only("id", "date")
            ],
            "cement_records": [
                {"id": row.id, "date": row.date.isoformat() if row.date else None}
                for row in CementRecord.objects.only("id", "date")
            ],
            "bamboo_records": [
                {"id": row.id, "date": row.date.isoformat() if row.date else None}
                for row in BambooRecord.objects.only("id", "date")
            ],
        }

        output_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

        self.stdout.write(self.style.SUCCESS(f"AD date inventory exported to {output_path}"))
        self.stdout.write(
            "Counts: "
            f"transactions={len(payload['transactions'])}, "
            f"sales={len(payload['sales'])}, "
            f"jcb={len(payload['jcb_records'])}, "
            f"tipper={len(payload['tipper_records'])}, "
            f"alerts={len(payload['alert_notifications'])}, "
            f"customer_payments={len(payload['customer_payments'])}, "
            f"blocks={len(payload['blocks_records'])}, "
            f"cement={len(payload['cement_records'])}, "
            f"bamboo={len(payload['bamboo_records'])}"
        )
