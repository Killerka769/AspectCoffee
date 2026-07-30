# File: /opt/aspectcoffee/apps/orders/cdek_integration.py
"""
CDEK integration for address passing.
Automatically pre-fills CDEK widget with address from checkout form.
"""

import json
import logging
from django.conf import settings

logger = logging.getLogger(__name__)


class CDEKIntegration:
    """Handle CDEK delivery integration."""

    def __init__(self):
        self.account = settings.CDEK_ACCOUNT
        self.password = settings.CDEK_PASSWORD
        self.test_mode = settings.CDEK_TEST_MODE

    def get_widget_config(self, address_data=None):
        """
        Generate CDEK widget configuration with pre-filled address.

        Args:
            address_data: dict with keys: street, house, city, postal_code

        Returns:
            dict with CDEK widget configuration
        """
        config = {
            "account": self.account,
            "test_mode": self.test_mode,
            "currency": "RUB",
            "lang": "ru",
            "type": 1,  # Delivery type
        }

        if address_data:
            # Pre-fill address fields
            if address_data.get('city'):
                config['city'] = address_data['city']

            if address_data.get('postal_code'):
                config['postal_code'] = address_data['postal_code']

            # Build full address string
            address_parts = []
            if address_data.get('street'):
                address_parts.append(address_data['street'])
            if address_data.get('house'):
                address_parts.append(f"д. {address_data['house']}")

            if address_parts:
                config['address'] = ', '.join(address_parts)

        return config

    def calculate_tariff(self, from_city, to_city, weight, dimensions=None):
        """
        Calculate delivery tariff using CDEK API.

        Args:
            from_city: sender city code
            to_city: recipient city code
            weight: package weight in grams
            dimensions: dict with length, width, height in cm

        Returns:
            dict with tariff info
        """
        # This would call CDEK API
        # Placeholder for actual implementation
        pass


# JavaScript snippet for HTML template to pass address to CDEK widget
CDEK_WIDGET_JS = """
<script>
// Pre-fill CDEK widget with address from form
document.addEventListener('DOMContentLoaded', function() {
    const cdekWidget = window.cdekWidget;

    if (cdekWidget) {
        // Get address from form fields
        const addressData = {
            city: document.querySelector('[name="delivery_city"]')?.value || '',
            street: document.querySelector('[name="delivery_street"]')?.value || '',
            house: document.querySelector('[name="delivery_house"]')?.value || '',
            postal_code: document.querySelector('[name="delivery_postal_code"]')?.value || '',
        };

        // Update CDEK widget with address
        if (addressData.city) {
            cdekWidget.setCity(addressData.city);
        }

        // Listen for address changes in form and update widget
        document.querySelectorAll('[name^="delivery_"]').forEach(field => {
            field.addEventListener('change', function() {
                const updatedData = {
                    city: document.querySelector('[name="delivery_city"]')?.value || '',
                    street: document.querySelector('[name="delivery_street"]')?.value || '',
                    house: document.querySelector('[name="delivery_house"]')?.value || '',
                    postal_code: document.querySelector('[name="delivery_postal_code"]')?.value || '',
                };

                if (updatedData.city) {
                    cdekWidget.setCity(updatedData.city);
                }
            });
        });
    }
});
</script>
"""


# Add to checkout template or order form:
"""
{% load static %}

<form method="post" id="checkout-form">
    {% csrf_token %}

    <!-- Address fields -->
    <div class="address-section">
        <input type="text" name="delivery_city" placeholder="Город" value="{{ order.delivery_city }}">
        <input type="text" name="delivery_street" placeholder="Улица" value="{{ order.delivery_street }}">
        <input type="text" name="delivery_house" placeholder="Дом" value="{{ order.delivery_house }}">
        <input type="text" name="delivery_postal_code" placeholder="Индекс" value="{{ order.delivery_postal_code }}">
    </div>

    <!-- CDEK Widget -->
    <div id="cdek-widget"></div>

    <!-- CDEK Widget Script -->
    <script src="https://widget.cdek.ru/v1/widget.js"></script>
    <script>
        window.cdekWidget = new CDEKWidget({
            account: "{{ cdek_account }}",
            test_mode: {{ cdek_test_mode|lower }},
            type: 1,
            currency: "RUB",
            lang: "ru",
            defaultLocation: {
                city: "{{ order.delivery_city }}"
            }
        });
    </script>

    {{ cdek_widget_js|safe }}

    <button type="submit">Оформить заказ</button>
</form>
"""


# View to handle address passing:
"""
from django.shortcuts import render
from django.http import JsonResponse
from .cdek_integration import CDEKIntegration

def checkout(request):
    cdek = CDEKIntegration()

    if request.method == 'POST':
        # Process checkout
        pass

    # Get address from user profile or session
    address_data = {
        'city': request.user.city if request.user.is_authenticated else '',
        'street': request.session.get('delivery_street', ''),
        'house': request.session.get('delivery_house', ''),
        'postal_code': request.session.get('delivery_postal_code', ''),
    }

    context = {
        'cdek_account': cdek.account,
        'cdek_test_mode': cdek.test_mode,
        'cdek_widget_js': CDEK_WIDGET_JS,
        'address_data': address_data,
    }

    return render(request, 'orders/checkout.html', context)
"""
