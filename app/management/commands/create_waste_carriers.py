# --- File: app/management/commands/create_waste_carriers.py ---
from django.core.management.base import BaseCommand
from app.utils.elasticsearch_client import get_elasticsearch_client

class Command(BaseCommand):
    help = "Create Elasticsearch index for WasteCarriersBrokersDealers"

    def handle(self, *args, **kwargs):
        es = get_elasticsearch_client()
        index_name = "waste_carriers"

        if es.indices.exists(index=index_name):
            self.stdout.write(self.style.WARNING(f"Index '{index_name}' already exists."))
            return

        mapping = {
            "mappings": {
                "properties": {
                    "id": {"type": "integer"},
                    "waste_carrier_license_no": {"type": "text"},
                    "waste_carrier_name": {"type": "text"},
                    "company_no": {"type": "keyword"},
                    "waste_carrier_license_issue_date": {"type": "text"},
                    "waste_carrier_expiry_date": {"type": "text"},
                    "waste_carrier_address": {"type": "text"},
                    "waste_carrier_postcode": {"type": "keyword"}
                }
            }
        }

        es.indices.create(index=index_name, body=mapping)
        self.stdout.write(self.style.SUCCESS(f"Created index '{index_name}'"))