from django.contrib import admin, messages

from .bs_date_utils import parse_calendar_date_input
from .calendar_mode import CALENDAR_MODE_BS, get_calendar_mode

from .models import (
    AlertNotification,
    BambooRecord,
    BambooRecordType,
    BlocksRecord,
    BlocksRecordType,
    BlocksUnitType,
    Customer,
    CustomerPayment,
    CementRecord,
    CementRecordType,
    CementUnitType,
    JCBRecord,
    PaymentAllocation,
    Sale,
    TipperItem,
    TipperRecord,
    Transaction,
    TransactionCategory,
)


@admin.register(TransactionCategory)
class TransactionCategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "is_predefined")
    list_filter = ("is_predefined",)
    search_fields = ("name",)
    ordering = ("name",)


class CalendarAwareAdminMixin:
    date_filter_fields: tuple[str, ...] = ()

    def _calendar_normalized_get(self, request):
        if get_calendar_mode(request) != CALENDAR_MODE_BS:
            return

        updated_get = request.GET.copy()
        changed = False

        for field_name in self.date_filter_fields:
            prefixes = (f"{field_name}", f"{field_name}__")
            for key in list(updated_get.keys()):
                if not key.startswith(prefixes):
                    continue

                raw_value = (updated_get.get(key) or "").strip()
                if not raw_value:
                    continue

                parsed_date, parse_error = parse_calendar_date_input(raw_value, CALENDAR_MODE_BS)
                if parse_error:
                    messages.error(request, f"Admin filter {key}: {parse_error}")
                    continue
                if parsed_date:
                    updated_get[key] = parsed_date.isoformat()
                    changed = True

        if changed:
            request.GET = updated_get

    def changelist_view(self, request, extra_context=None):
        self._calendar_normalized_get(request)
        return super().changelist_view(request, extra_context=extra_context)


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "phone",
        "type",
        "opening_balance",
        "credit_balance",
        "manual_due_amount",
        "created_at",
    )
    list_filter = ("type", "created_at")
    search_fields = ("name", "phone", "address", "credit_terms")
    ordering = ("name",)
    fieldsets = (
        ("Basic Information", {"fields": ("name", "phone", "address", "type")}),
        ("Financial Information", {"fields": ("opening_balance", "credit_balance", "credit_terms", "manual_due_amount")}),
        ("Additional Notes", {"fields": ("profile_notes",)}),
    )


@admin.register(Transaction)
class TransactionAdmin(CalendarAwareAdminMixin, admin.ModelAdmin):
    date_filter_fields = ("date",)
    list_display = (
        "date",
        "customer",
        "sale",
        "bamboo_record",
        "cement_record",
        "jcb_record",
        "tipper_record",
        "type",
        "payment_method",
        "category",
        "amount",
    )
    list_filter = ("type", "payment_method", "date", "category", "sale", "bamboo_record", "cement_record", "jcb_record", "tipper_record")
    search_fields = (
        "customer__name",
        "category__name",
        "description",
    )
    autocomplete_fields = ("customer", "sale", "bamboo_record", "cement_record", "jcb_record", "tipper_record", "category")
    date_hierarchy = "date"
    ordering = ("-date",)


@admin.register(Sale)
class SaleAdmin(CalendarAwareAdminMixin, admin.ModelAdmin):
    date_filter_fields = ("date", "due_date")
    list_display = (
        "invoice_number",
        "date",
        "customer",
        "total_amount",
        "paid_amount",
        "due_date",
        "status",
        "alert_enabled",
    )
    list_filter = ("status", "date", "due_date")
    search_fields = ("invoice_number", "customer__name", "notes")
    autocomplete_fields = ("customer",)
    date_hierarchy = "date"
    ordering = ("-date",)


@admin.register(AlertNotification)
class AlertNotificationAdmin(CalendarAwareAdminMixin, admin.ModelAdmin):
    date_filter_fields = ("due_date",)
    list_display = (
        "alert_type",
        "source_type",
        "source_id",
        "customer",
        "due_date",
        "amount",
        "is_active",
        "is_read",
    )
    list_filter = ("alert_type", "source_type", "is_active", "is_read", "due_date")
    search_fields = ("title", "message", "customer__name")
    autocomplete_fields = ("customer",)


@admin.register(CustomerPayment)
class CustomerPaymentAdmin(CalendarAwareAdminMixin, admin.ModelAdmin):
    date_filter_fields = ("payment_date",)
    list_display = (
        "payment_date",
        "customer",
        "amount",
        "payment_method",
        "allocated_amount",
        "unallocated_amount",
    )
    list_filter = ("payment_method", "payment_date")
    search_fields = ("customer__name", "notes")
    autocomplete_fields = ("customer",)
    date_hierarchy = "payment_date"
    ordering = ("-payment_date", "-created_at")


@admin.register(PaymentAllocation)
class PaymentAllocationAdmin(admin.ModelAdmin):
    list_display = ("customer_payment", "sale", "amount", "transaction", "created_at")
    search_fields = ("sale__invoice_number", "customer_payment__customer__name")
    autocomplete_fields = ("customer_payment", "sale", "transaction")


@admin.register(JCBRecord)
class JCBRecordAdmin(CalendarAwareAdminMixin, admin.ModelAdmin):
    date_filter_fields = ("date",)
    list_display = (
        "date",
        "site_name",
        "start_time",
        "end_time",
        "total_work_hours",
        "rate",
        "total_amount",
        "status",
        "expense_item",
        "expense_amount",
    )
    list_filter = ("status", "date")
    search_fields = ("site_name", "expense_item")
    date_hierarchy = "date"
    ordering = ("-date", "-created_at")


@admin.register(TipperItem)
class TipperItemAdmin(admin.ModelAdmin):
    list_display = ("name",)
    search_fields = ("name",)
    ordering = ("name",)


@admin.register(TipperRecord)
class TipperRecordAdmin(CalendarAwareAdminMixin, admin.ModelAdmin):
    date_filter_fields = ("date",)
    list_display = ("date", "item", "record_type", "description", "amount")
    list_filter = ("record_type", "item", "date")
    search_fields = ("item__name", "description")
    autocomplete_fields = ("item",)
    date_hierarchy = "date"
    ordering = ("-date", "-created_at")


@admin.register(BlocksRecord)
class BlocksRecordAdmin(CalendarAwareAdminMixin, admin.ModelAdmin):
    date_filter_fields = ("date",)
    list_display = (
        "date",
        "record_type",
        "payment_status",
        "unit_type",
        "quantity",
        "investment",
        "sale_income",
    )
    list_filter = ("record_type", "payment_status", "unit_type", "date")
    search_fields = ("notes",)
    date_hierarchy = "date"
    ordering = ("-date", "-created_at")
    fieldsets = (
        ("Record Information", {"fields": ("date", "record_type", "payment_status", "notes")}),
        ("Financial Fields", {"fields": ("investment", "sale_income")}),
        ("Stock Fields", {"fields": ("unit_type", "quantity", "price_per_unit")}),
    )


@admin.register(CementRecord)
class CementRecordAdmin(CalendarAwareAdminMixin, admin.ModelAdmin):
    date_filter_fields = ("date",)
    list_display = (
        "date",
        "record_type",
        "payment_status",
        "unit_type",
        "quantity",
        "investment",
        "sale_income",
    )
    list_filter = ("record_type", "payment_status", "unit_type", "date")
    search_fields = ("notes",)
    date_hierarchy = "date"
    ordering = ("-date", "-created_at")
    fieldsets = (
        ("Record Information", {"fields": ("date", "record_type", "payment_status", "notes")}),
        ("Financial Fields", {"fields": ("investment", "sale_income")}),
        ("Stock Fields", {"fields": ("unit_type", "quantity", "price_per_unit")}),
    )


@admin.register(BambooRecord)
class BambooRecordAdmin(CalendarAwareAdminMixin, admin.ModelAdmin):
    date_filter_fields = ("date",)
    list_display = (
        "date",
        "record_type",
        "payment_status",
        "quantity",
        "investment",
        "sale_income",
    )
    list_filter = ("record_type", "payment_status", "date")
    search_fields = ("notes",)
    date_hierarchy = "date"
    ordering = ("-date", "-created_at")
    fieldsets = (
        ("Record Information", {"fields": ("date", "record_type", "payment_status", "notes")}),
        ("Financial Fields", {"fields": ("investment", "sale_income")}),
        ("Stock Fields", {"fields": ("quantity", "price_per_unit")}),
    )
