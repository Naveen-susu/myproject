# --- File: app/management/commands/index_waste_carriers.py ---
from django.core.management.base import BaseCommand
from app.models import WasteCarriersBrokersDealers
from app.utils.elasticsearch_client import get_elasticsearch_client

class Command(BaseCommand):
    help = "Index WasteCarriersBrokersDealers to Elasticsearch"

    def handle(self, *args, **kwargs):
        es = get_elasticsearch_client()
        index_name = "waste_carriers"

        for instance in WasteCarriersBrokersDealers.objects.all():
            doc = {
                "id": instance.id,
                "waste_carrier_license_no": instance.waste_carrier_license_no,
                "waste_carrier_name": instance.waste_carrier_name,
                "company_no": instance.company_no,
                "waste_carrier_license_issue_date": instance.waste_carrier_license_issue_date,
                "waste_carrier_expiry_date": instance.waste_carrier_expiry_date,
                "waste_carrier_address": instance.waste_carrier_address,
                "waste_carrier_postcode": instance.waste_carrier_postcode
            }
            es.index(index=index_name, id=instance.id, document=doc)

        self.stdout.write(self.style.SUCCESS(f"✅ Indexed all WasteCarriersBrokersDealers into '{index_name}'"))
