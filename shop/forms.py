from django import forms

from .models import Order


class AddToCartForm(forms.Form):
    quantity = forms.IntegerField(min_value=1, initial=1)


class CartLineForm(forms.Form):
    """One cart line's quantity; 0 removes the line."""

    quantity = forms.IntegerField(
        min_value=0, widget=forms.NumberInput(attrs={"aria-label": "Quantity"})
    )

    def __init__(self, *args, **kwargs):
        # Every line posts the same field name, so no line renders an HTML id.
        super().__init__(*args, auto_id=False, **kwargs)


class CheckoutForm(forms.ModelForm):
    class Meta:
        model = Order
        fields = ["customer_name", "email", "shipping_address"]
        labels = {"customer_name": "Name"}
        widgets = {"shipping_address": forms.Textarea(attrs={"rows": 3})}
