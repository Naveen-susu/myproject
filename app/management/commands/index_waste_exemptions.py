# --- File: app/management/commands/index_waste_exemptions.py ---
from django.core.management.base import BaseCommand
from app.models import WasteExemptionCertificates
from app.utils.elasticsearch_client import get_elasticsearch_client

class Command(BaseCommand):
    help = "Index WasteExemptionCertificates to Elasticsearch"

    def handle(self, *args, **kwargs):
        es = get_elasticsearch_client()
        index_name = "waste_exemptions"

        for obj in WasteExemptionCertificates.objects.all():
            doc = {
                "id": obj.id,
                "company_name": obj.company_name,
                "waste_exemption_no": obj.waste_exemption_no,
                "waste_site_address": obj.waste_site_address,
                "waste_site_postcode": obj.waste_site_postcode,
                "issue_date": obj.issue_date,
                "expiry_date": obj.expiry_date
            }
            es.index(index=index_name, id=obj.id, document=doc)

        self.stdout.write(self.style.SUCCESS(f"✅ Indexed all WasteExemptionCertificates into '{index_name}'"))