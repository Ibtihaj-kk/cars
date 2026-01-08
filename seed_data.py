import argparse
import os
import subprocess
import sys


def _run(cmd: list[str]) -> None:
    subprocess.check_call(cmd)


def _env(name: str) -> str | None:
    value = os.environ.get(name)
    if value is None:
        return None
    value = value.strip()
    return value or None


def _require_env(name: str) -> str:
    value = _env(name)
    if not value:
        raise SystemExit(f"Missing required environment variable: {name}")
    return value


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--skip-pip", action="store_true")
    parser.add_argument("--skip-migrate", action="store_true")
    parser.add_argument("--skip-locations", action="store_true")
    parser.add_argument("--skip-currencies", action="store_true")
    parser.add_argument("--skip-users", action="store_true")
    args = parser.parse_args()

    project_root = os.path.dirname(os.path.abspath(__file__))
    manage_py = os.path.join(project_root, "manage.py")
    requirements_txt = os.path.join(project_root, "requirements.txt")

    if not args.skip_pip and os.path.exists(requirements_txt):
        _run([sys.executable, "-m", "pip", "install", "-r", requirements_txt])

    if not args.skip_migrate:
        _run([sys.executable, manage_py, "migrate", "--noinput"])

    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "yallamotor_project.settings")
    import django

    django.setup()

    from django.contrib.auth import get_user_model
    from core.models import Currency
    from parts.models import Country, City
    from business_partners.models import BusinessPartner, BusinessPartnerRole, VendorProfile

    if not args.skip_locations:
        countries_data = [
            {"code": "AE", "name": "United Arab Emirates", "name_ar": "الإمارات العربية المتحدة"},
            {"code": "SA", "name": "Saudi Arabia", "name_ar": "المملكة العربية السعودية"},
            {"code": "QA", "name": "Qatar", "name_ar": "قطر"},
            {"code": "OM", "name": "Oman", "name_ar": "سلطنة عمان"},
            {"code": "BH", "name": "Bahrain", "name_ar": "مملكة البحرين"},
            {"code": "PK", "name": "Pakistan", "name_ar": "باكستان"},
        ]

        cities_data = {
            "AE": ["Abu Dhabi", "Dubai", "Sharjah", "Ajman", "Umm Al Quwain", "Ras Al Khaimah", "Fujairah", "Al Ain"],
            "SA": ["Riyadh", "Jeddah", "Mecca", "Medina", "Dammam", "Khobar", "Dhahran", "Taif", "Tabuk", "Abha"],
            "QA": ["Doha", "Al Rayyan", "Al Wakrah", "Al Khor", "Umm Salal", "Al Daayen", "Mesaieed"],
            "OM": ["Muscat", "Salalah", "Sohar", "Nizwa", "Sur", "Ibri", "Barka", "Rustaq"],
            "BH": ["Manama", "Muharraq", "Riffa", "Hamad Town", "Aali", "Isa Town", "Sitra", "Budaiya"],
            "PK": ["Karachi", "Lahore", "Islamabad", "Rawalpindi", "Faisalabad", "Multan", "Peshawar", "Quetta", "Gujranwala", "Sialkot"],
        }

        for row in countries_data:
            country, _ = Country.objects.update_or_create(
                code=row["code"],
                defaults={"name": row["name"], "name_ar": row.get("name_ar") or None, "is_active": True},
            )
            for city_name in cities_data.get(country.code, []):
                City.objects.get_or_create(country=country, name=city_name, defaults={"is_active": True})

    if not args.skip_currencies:
        usd, _ = Currency.objects.update_or_create(
            code="USD",
            defaults={
                "name": "US Dollar",
                "symbol": "$",
                "symbol_position": "left",
                "decimal_places": 2,
                "thousands_separator": ",",
                "decimal_separator": ".",
                "is_active": True,
                "is_base": True,
            },
        )

        currencies_to_create = [
            ("AED", "UAE Dirham", "د.إ", "right"),
            ("SAR", "Saudi Riyal", "﷼", "right"),
            ("QAR", "Qatari Riyal", "﷼", "right"),
            ("OMR", "Omani Rial", "ر.ع.", "right"),
            ("BHD", "Bahraini Dinar", ".د.ب", "right"),
            ("PKR", "Pakistani Rupee", "₨", "left"),
        ]

        for code, name, symbol, position in currencies_to_create:
            Currency.objects.update_or_create(
                code=code,
                defaults={
                    "name": name,
                    "symbol": symbol,
                    "symbol_position": position,
                    "decimal_places": 2,
                    "thousands_separator": ",",
                    "decimal_separator": ".",
                    "is_active": True,
                    "is_base": False,
                },
            )

        Currency.objects.exclude(id=usd.id).filter(is_base=True).update(is_base=False)

    if not args.skip_users:
        User = get_user_model()

        admin_email = _env("SEED_ADMIN_EMAIL") or "admin@carsyncro.com"
        vendor_email = _env("SEED_VENDOR_EMAIL") or "ibtihaj555@outlook.com"
        client_email = _env("SEED_CLIENT_EMAIL") or "kaimikhurramkaimi@gmail.com"

        admin_password = _require_env("SEED_ADMIN_PASSWORD") or "CarSyncro2026"
        vendor_password = _require_env("SEED_VENDOR_PASSWORD") or "CarSyncroVendor2026"
        client_password = _require_env("SEED_CLIENT_PASSWORD") or "CarSyncroUser2026"

        admin_user, created = User.objects.get_or_create(email=admin_email, defaults={"is_staff": True, "is_superuser": True, "role": "admin"})
        if created:
            admin_user.set_password(admin_password)
            admin_user.is_active = True
            admin_user.save(update_fields=["password", "is_active"])

        vendor_user, created = User.objects.get_or_create(email=vendor_email, defaults={"is_staff": False, "is_superuser": False, "role": "seller"})
        if created:
            vendor_user.set_password(vendor_password)
            vendor_user.is_active = True
            vendor_user.save(update_fields=["password", "is_active"])

        client_user, created = User.objects.get_or_create(email=client_email, defaults={"is_staff": False, "is_superuser": False, "role": "client"})
        if created:
            client_user.set_password(client_password)
            client_user.is_active = True
            client_user.save(update_fields=["password", "is_active"])

        vendor_bp, _ = BusinessPartner.objects.get_or_create(
            user=vendor_user,
            defaults={"name": "Default Vendor", "status": "active", "created_by": admin_user},
        )
        BusinessPartnerRole.objects.get_or_create(business_partner=vendor_bp, role_type="vendor")
        VendorProfile.objects.get_or_create(business_partner=vendor_bp, defaults={"user": vendor_user})

        client_bp, _ = BusinessPartner.objects.get_or_create(
            user=client_user,
            defaults={"name": "Default Customer", "status": "active", "created_by": admin_user},
        )
        BusinessPartnerRole.objects.get_or_create(business_partner=client_bp, role_type="customer")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

