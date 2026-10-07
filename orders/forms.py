import re

from django import forms

from store.models import StoreSettings

from .models import Order

PK_CITIES = [
    "Bahawalpur", "Lahore", "Karachi", "Islamabad", "Rawalpindi", "Multan", "Faisalabad",
    "Peshawar", "Quetta", "Sialkot", "Gujranwala", "Hyderabad", "Rahim Yar Khan",
    "Sargodha", "Sahiwal", "Bahawalnagar", "Dera Ghazi Khan", "Lodhran", "Vehari",
]


def normalize_pk_mobile(value):
    """Accept 03xx-xxxxxxx, +92 3xx xxxxxxx, 923xxxxxxxxx; return 03xxxxxxxxx."""
    digits = re.sub(r"\D", "", value or "")
    if digits.startswith("92") and len(digits) == 12:
        digits = "0" + digits[2:]
    if not re.fullmatch(r"03\d{9}", digits):
        raise forms.ValidationError("Enter a Pakistani mobile number like 0300 1234567.")
    return digits


class CheckoutForm(forms.ModelForm):
    # Hidden from people; bots tend to fill it in.
    website = forms.CharField(required=False, widget=forms.TextInput(attrs={
        "tabindex": "-1", "autocomplete": "off", "class": "hp",
    }))

    class Meta:
        model = Order
        fields = ["full_name", "phone", "email", "city", "address", "notes",
                  "payment_method", "transaction_id"]
        labels = {
            "full_name": "Full name",
            "phone": "Mobile number",
            "email": "Email (optional)",
            "address": "Full delivery address",
            "notes": "Anything we should know? (optional)",
            "payment_method": "How will you pay?",
            "transaction_id": "Transaction ID",
        }
        widgets = {
            "full_name": forms.TextInput(attrs={"autocomplete": "name"}),
            "phone": forms.TextInput(attrs={"autocomplete": "tel", "inputmode": "tel",
                                            "placeholder": "0300 1234567"}),
            "email": forms.EmailInput(attrs={"autocomplete": "email"}),
            "city": forms.TextInput(attrs={"autocomplete": "address-level2", "list": "pk-cities"}),
            "address": forms.Textarea(attrs={"rows": 3, "autocomplete": "street-address",
                                             "placeholder": "House, street, area, nearby landmark"}),
            "notes": forms.Textarea(attrs={"rows": 2}),
            "payment_method": forms.RadioSelect,
            "transaction_id": forms.TextInput(attrs={"placeholder": "From your JazzCash / EasyPaisa / bank SMS"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        shop = StoreSettings.load()
        choices = []
        if shop.cod_enabled:
            choices.append(Order.Payment.COD)
        if shop.jazzcash_number:
            choices.append(Order.Payment.JAZZCASH)
        if shop.easypaisa_number:
            choices.append(Order.Payment.EASYPAISA)
        if shop.bank_details.strip():
            choices.append(Order.Payment.BANK)
        if not choices:
            choices = [Order.Payment.COD]
        self.fields["payment_method"].choices = [(c.value, c.label) for c in choices]
        self.fields["payment_method"].initial = choices[0].value
        self.fields["transaction_id"].required = False

    def clean_phone(self):
        return normalize_pk_mobile(self.cleaned_data.get("phone"))

    def clean_full_name(self):
        name = " ".join(self.cleaned_data["full_name"].split())
        if len(name) < 3:
            raise forms.ValidationError("Enter the full name for delivery.")
        return name

    def clean_address(self):
        address = self.cleaned_data["address"].strip()
        if len(address) < 10:
            raise forms.ValidationError("Add house number, street and area so the rider can find you.")
        return address

    def clean(self):
        data = super().clean()
        if data.get("website"):
            raise forms.ValidationError("Could not place the order. Please try again.")
        method = data.get("payment_method")
        if method and method != Order.Payment.COD and not (data.get("transaction_id") or "").strip():
            self.add_error("transaction_id", "Send the payment first, then enter the transaction ID from the SMS.")
        return data


class TrackOrderForm(forms.Form):
    number = forms.CharField(label="Order number", max_length=20,
                             widget=forms.TextInput(attrs={"placeholder": "LM-2610-ABCD"}))
    phone = forms.CharField(label="Mobile number used for the order", max_length=20,
                            widget=forms.TextInput(attrs={"inputmode": "tel", "placeholder": "0300 1234567"}))

    def clean_number(self):
        return self.cleaned_data["number"].strip().upper()

    def clean_phone(self):
        return normalize_pk_mobile(self.cleaned_data["phone"])
