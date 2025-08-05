# --- File: app/management/commands/create_waste_operations.py ---
from django.core.management.base import BaseCommand
from app.utils.elasticsearch_client import get_elasticsearch_client

class Command(BaseCommand):
    help = "Create Elasticsearch index for WasteOperationsPermits"

    def handle(self, *args, **kwargs):
        es = get_elasticsearch_client()
        index_name = "waste_operations"

        if es.indices.exists(index=index_name):
            self.stdout.write(self.style.WARNING(f"Index '{index_name}' already exists."))
            return

        mapping = {
            "mappings": {
                "properties": {
                    "id": {"type": "integer"},
                    "waste_destination_name": {"type": "text"},
                    "waste_destination_postcode": {"type": "keyword"},
                    "waste_destination_address": {"type": "text"},
                    "waste_destination_permit_no": {"type": "keyword"},
                    "waste_destination_permit_status": {"type": "keyword"},
                    "waste_destination_permit_effective_date": {"type": "date"},
                    "waste_destination_permit_surrendered_date": {"type": "date"},
                    "waste_destination_permit_revoked_date": {"type": "date"},
                    "waste_destination_permit_suspended_date": {"type": "date"}
                }
            }
        }

        es.indices.create(index=index_name, body=mapping)
        self.stdout.write(self.style.SUCCESS(f"Created index '{index_name}'"))