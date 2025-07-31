# app/management/commands/index_data.py

from django.core.management.base import BaseCommand
from app.models import WasteCarriersBrokersDealers
from elasticsearch import Elasticsearch
from django.conf import settings

class Command(BaseCommand):
    help = "Index existing waste carrier records to Elasticsearch"

    def handle(self, *args, **kwargs):
        es_host = getattr(settings, "ELASTICSEARCH_HOST", "http://elasticsearch:9200")
        es = Elasticsearch(
            es_host,
            headers={
                "Accept": "application/vnd.elasticsearch+json; compatible-with=8",
                "Content-Type": "application/vnd.elasticsearch+json; compatible-with=8"
            }
        )

        for instance in WasteCarriersBrokersDealers.objects.all():
            doc = {
                "waste_carrier_license_no": instance.waste_carrier_license_no,
                "waste_carrier_name": instance.waste_carrier_name,
                "company_no": instance.company_no,
                "waste_carrier_license_issue_date": instance.waste_carrier_license_issue_date,
                "waste_carrier_expiry_date": instance.waste_carrier_expiry_date,
                "waste_carrier_address": instance.waste_carrier_address,
                "waste_carrier_postcode": instance.waste_carrier_postcode
            }

            es.index(index="waste_carriers", id=instance.id, document=doc)

        self.stdout.write(self.style.SUCCESS("✅ All records indexed successfully."))