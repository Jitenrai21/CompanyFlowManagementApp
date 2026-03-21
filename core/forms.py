from django import forms
from django.core.exceptions import ValidationError
from decimal import Decimal, InvalidOperation
from datetime import datetime

from .models import Customer, Sale, Transaction
from .models import RecordStatus


def _decorate_widget(field_name, field):
    existing_class = field.widget.attrs.get("class", "")
    if field_name in {"description", "profile_notes", "address", "items"}:
        field.widget.attrs["class"] = f"textarea textarea-bordered w-full {existing_class}".strip()
    elif field_name in {"type", "payment_method", "customer", "status", "sale"}:
        field.widget.attrs["class"] = f"select select-bordered w-full {existing_class}".strip()
    elif field_name == "attachment":
        field.widget.attrs["class"] = f"file-input file-input-bordered w-full {existing_class}".strip()
    else:
        field.widget.attrs["class"] = f"input input-bordered w-full {existing_class}".strip()


class CustomerForm(forms.ModelForm):
    class Meta:
        model = Customer
        fields = [
            "name",
            "phone",
            "address",
            "credit_terms",
            "profile_notes",
            "type",
            "opening_balance",
        ]

    def clean_name(self):
        name = self.cleaned_data["name"].strip()
        if len(name) < 2:
            raise forms.ValidationError("Customer name must be at least 2 characters.")
        return name

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            _decorate_widget(field_name, field)
        self.fields["address"].widget.attrs["rows"] = 1


class SaleForm(forms.ModelForm):
    @staticmethod
    def _generate_invoice_number(prefix="INV"):
        counter = 1
        today_stamp = datetime.now().strftime("%Y%m%d")
        while True:
            candidate = f"{prefix}-{today_stamp}-{counter:03d}"
            if not Sale.objects.filter(invoice_number=candidate).exists():
                return candidate
            counter += 1

    class Meta:
        model = Sale
        fields = [
            "invoice_number",
            "date",
            "customer",
            "status",
            "items",
            "notes",
            "total_amount",
            "due_date",
        ]
        widgets = {
            "date": forms.DateInput(attrs={"type": "date"}),
            "due_date": forms.DateInput(attrs={"type": "date"}),
            "items": forms.HiddenInput(),
            "notes": forms.Textarea(attrs={"rows": 3}),
        }

        help_texts = {
            "items": "Add items with name and price using the item table.",
        }

    def clean_total_amount(self):
        total_amount = self.cleaned_data["total_amount"]
        if total_amount <= 0:
            raise forms.ValidationError("Total amount must be greater than 0.")
        return total_amount

    def clean_invoice_number(self):
        invoice_number = (self.cleaned_data.get("invoice_number") or "").strip()

        if invoice_number:
            return invoice_number

        # Keep existing invoice number on edit if user leaves this blank.
        if self.instance and self.instance.pk and self.instance.invoice_number:
            return self.instance.invoice_number

        return self._generate_invoice_number()

    def clean_items(self):
        items = self.cleaned_data.get("items")
        if not items:
            raise ValidationError("At least one item is required.")
        if not isinstance(items, list):
            raise ValidationError("Items must be a JSON list.")

        normalized_items = []
        for index, item in enumerate(items, start=1):
            if not isinstance(item, dict):
                raise ValidationError(f"Item #{index} must be an object.")
            item_name = str(item.get("item", "")).strip()
            if not item_name:
                raise ValidationError(f"Item #{index} must include 'item'.")

            price = item.get("price")
            if price in (None, ""):
                raise ValidationError(f"Item #{index} must include price.")

            quantity = item.get("quantity", 1)
            try:
                quantity_number = Decimal(str(quantity))
                price_number = Decimal(str(price))
            except (TypeError, ValueError, InvalidOperation):
                raise ValidationError(f"Item #{index} quantity and price must be numbers.")

            if quantity_number <= 0 or price_number < 0:
                raise ValidationError(
                    f"Item #{index} quantity must be > 0 and price cannot be negative."
                )

            amount_number = (quantity_number * price_number).quantize(Decimal("0.01"))
            normalized_items.append(
                {
                    "item": item_name,
                    "quantity": float(quantity_number),
                    "price": float(price_number),
                    "amount": float(amount_number),
                }
            )

        return normalized_items

    def clean(self):
        cleaned_data = super().clean()
        status = cleaned_data.get("status")
        due_date = cleaned_data.get("due_date")

        if status == RecordStatus.PAID:
            cleaned_data["due_date"] = None
        elif not due_date:
            self.add_error("due_date", "Due date is required when sale status is Pending.")

        return cleaned_data

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["invoice_number"].required = False
        self.fields["invoice_number"].widget.attrs["placeholder"] = "Leave blank to auto-generate"
        self.fields["customer"].required = False
        for field_name, field in self.fields.items():
            _decorate_widget(field_name, field)
        self.fields["customer"].widget.attrs["data-customer-autocomplete"] = "true"


class TransactionForm(forms.ModelForm):
    class Meta:
        model = Transaction
        fields = [
            "date",
            "amount",
            "type",
            "payment_method",
            "category",
            "description",
            "customer",
            "sale",
            "attachment",
        ]
        widgets = {
            "date": forms.DateInput(attrs={"type": "date"}),
            "description": forms.Textarea(attrs={"rows": 3}),
        }

    def clean_amount(self):
        amount = self.cleaned_data["amount"]
        if amount <= 0:
            raise forms.ValidationError("Amount must be greater than 0.")
        return amount

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["customer"].required = False
        for field_name, field in self.fields.items():
            _decorate_widget(field_name, field)
        self.fields["customer"].widget.attrs["data-customer-autocomplete"] = "true"
        self.fields["sale"].required = False


class SaleReceiptForm(forms.ModelForm):
    class Meta:
        model = Transaction
        fields = [
            "date",
            "amount",
            "payment_method",
            "category",
            "description",
        ]
        widgets = {
            "date": forms.DateInput(attrs={"type": "date"}),
            "description": forms.Textarea(attrs={"rows": 2}),
        }

    def clean_amount(self):
        amount = self.cleaned_data["amount"]
        if amount <= 0:
            raise forms.ValidationError("Receipt amount must be greater than 0.")
        return amount

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            _decorate_widget(field_name, field)
