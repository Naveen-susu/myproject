# --- File: app/management/commands/create_waste_exemptions.py ---
from django.core.management.base import BaseCommand
from app.utils.elasticsearch_client import get_elasticsearch_client

class Command(BaseCommand):
    help = "Create Elasticsearch index for WasteExemptionCertificates"

    def handle(self, *args, **kwargs):
        es = get_elasticsearch_client()
        index_name = "waste_exemptions"

        if es.indices.exists(index=index_name):
            self.stdout.write(self.style.WARNING(f"Index '{index_name}' already exists."))
            return

        mapping = {
            "mappings": {
                "properties": {
                    "id": {"type": "integer"},
                    "company_name": {"type": "text"},
                    "waste_exemption_no": {"type": "keyword"},
                    "waste_site_address": {"type": "text"},
                    "waste_site_postcode": {"type": "keyword"},
                    "issue_date": {"type": "date"},
                    "expiry_date": {"type": "date"}
                }
            }
        }

        es.indices.create(index=index_name, body=mapping)
        self.stdout.write(self.style.SUCCESS(f"Created index '{index_name}'"))