from datetime import timedelta
from decimal import Decimal
import logging

from django.core.management.base import BaseCommand
from django.core.mail import mail_admins
from django.db.models import F, Q, Sum, Value
from django.db.models.functions import Coalesce
from django.utils import timezone

from core.models import (
    AlertNotification,
    AlertSource,
    AlertType,
    BambooRecord,
    BambooRecordType,
    BlocksRecord,
    BlocksRecordType,
    CementRecord,
    CementRecordType,
    Sale,
    TransactionType,
)

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Process overdue and upcoming alerts and persist notification timeline records."

    def _process_sale_queryset(self, queryset, source_type, title_prefix, detail_label, active_signatures, today, upcoming_end, created_count, updated_count):
        for record in queryset:
            total_amount = getattr(record, "total_amount", None)
            if total_amount is None:
                total_amount = getattr(record, "sale_income", Decimal("0.00")) or Decimal("0.00")
            received_total = getattr(record, "received_total", None)
            if received_total is None:
                received_total = getattr(record, "paid_amount", Decimal("0.00")) or Decimal("0.00")

            if received_total >= total_amount:
                continue

            alert_type = None
            if record.due_date < today:
                alert_type = AlertType.OVERDUE
            elif today <= record.due_date <= upcoming_end:
                alert_type = AlertType.UPCOMING

            if not alert_type:
                continue

            signature = (alert_type, source_type, record.id, record.due_date)
            active_signatures.add(signature)

            customer_label = record.customer.name if record.customer else "Unassigned customer"
            title = f"{detail_label} {record.id} is {alert_type}" if source_type != AlertSource.SALE else f"Invoice {record.invoice_number} is {alert_type}"
            message = (
                f"Customer {customer_label} has outstanding {detail_label.lower()} sale {record.id} "
                f"due on {record.due_date}."
            )
            amount = total_amount - received_total
            if source_type == AlertSource.SALE:
                amount = total_amount - received_total
                title = f"Invoice {record.invoice_number} is {alert_type}"
                message = (
                    f"Customer {customer_label} has outstanding invoice {record.invoice_number} "
                    f"due on {record.due_date}."
                )

            _, created = AlertNotification.objects.update_or_create(
                alert_type=alert_type,
                source_type=source_type,
                source_id=record.id,
                due_date=record.due_date,
                defaults={
                    "customer": record.customer,
                    "amount": amount,
                    "title": title,
                    "message": message,
                    "is_active": True,
                    "resolved_at": None,
                },
            )
            if created:
                created_count += 1
                logger.info("Created %s alert notification for id=%s type=%s", title_prefix, record.id, alert_type)
            else:
                updated_count += 1

        return created_count, updated_count

    def handle(self, *args, **options):
        today = timezone.localdate()
        upcoming_end = today + timedelta(days=7)

        active_signatures = set()
        created_count = 0
        updated_count = 0

        sales_queryset = Sale.objects.select_related("customer").annotate(
            received_total=Coalesce(
                Sum("receipts__amount", filter=Q(receipts__type=TransactionType.INCOME)),
                Value(Decimal("0.00")),
            )
        ).filter(
            status="pending",
            alert_enabled=True,
            due_date__isnull=False,
        )

        created_count, updated_count = self._process_sale_queryset(
            sales_queryset,
            AlertSource.SALE,
            "sale",
            "invoice",
            active_signatures,
            today,
            upcoming_end,
            created_count,
            updated_count,
        )

        blocks_queryset = BlocksRecord.objects.select_related("customer").filter(
            record_type=BlocksRecordType.SALE,
            payment_status="pending",
            alert_enabled=True,
            due_date__isnull=False,
        )
        cement_queryset = CementRecord.objects.select_related("customer").filter(
            record_type=CementRecordType.SALE,
            payment_status="pending",
            alert_enabled=True,
            due_date__isnull=False,
        )
        bamboo_queryset = BambooRecord.objects.select_related("customer").filter(
            record_type=BambooRecordType.SALE,
            payment_status="pending",
            alert_enabled=True,
            due_date__isnull=False,
        )

        created_count, updated_count = self._process_sale_queryset(
            blocks_queryset,
            AlertSource.BLOCKS_SALE,
            "blocks",
            "Blocks",
            active_signatures,
            today,
            upcoming_end,
            created_count,
            updated_count,
        )
        created_count, updated_count = self._process_sale_queryset(
            cement_queryset,
            AlertSource.CEMENT_SALE,
            "cement",
            "Cement",
            active_signatures,
            today,
            upcoming_end,
            created_count,
            updated_count,
        )
        created_count, updated_count = self._process_sale_queryset(
            bamboo_queryset,
            AlertSource.BAMBOO_SALE,
            "bamboo",
            "Bamboo",
            active_signatures,
            today,
            upcoming_end,
            created_count,
            updated_count,
        )

        # Resolve any active notification whose source signature is no longer active.
        for notification in AlertNotification.objects.filter(
            is_active=True,
            source_type__in=[
                AlertSource.SALE,
                AlertSource.BLOCKS_SALE,
                AlertSource.CEMENT_SALE,
                AlertSource.BAMBOO_SALE,
            ],
        ):
            signature = (
                notification.alert_type,
                notification.source_type,
                notification.source_id,
                notification.due_date,
            )
            if signature not in active_signatures:
                notification.is_active = False
                notification.resolved_at = timezone.now()
                notification.save(update_fields=["is_active", "resolved_at", "updated_at"])

        summary = (
            f"Alert processing completed: created={created_count}, "
            f"updated={updated_count}, active={len(active_signatures)}"
        )
        logger.info(summary)
        self.stdout.write(self.style.SUCCESS(summary))

        if created_count > 0:
            try:
                mail_admins(
                    subject="Company Flow: New timeline alerts generated",
                    message=summary,
                    fail_silently=True,
                )
            except Exception as exc:  # pragma: no cover
                logger.warning("Unable to send alert summary email: %s", exc)
