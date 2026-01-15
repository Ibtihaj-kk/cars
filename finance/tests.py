from django.test import TestCase

from admin_panel.models import AdminSetting
from decimal import Decimal
from parts.views import _get_country_standard_tax_rate


class TaxSettingsTest(TestCase):
    def test_country_standard_tax_rate_prefers_country_specific_setting(self):
        AdminSetting.objects.create(
            key='tax_SA_standard',
            value='10.00',
            value_type='float',
        )

        self.assertEqual(_get_country_standard_tax_rate('SA'), Decimal('0.1000'))

    def test_country_standard_tax_rate_accepts_lowercase_country_key(self):
        AdminSetting.objects.create(
            key='tax_sa_standard',
            value='7.50',
            value_type='float',
        )

        self.assertEqual(_get_country_standard_tax_rate('SA'), Decimal('0.0750'))
