# app/management/commands/create_index.py

from django.core.management.base import BaseCommand
from app.utils.elasticsearch_client import get_elasticsearch_client

class Command(BaseCommand):
    help = "Create waste_carriers index in Elasticsearch"

    def handle(self, *args, **kwargs):
        es = get_elasticsearch_client()
        index_name = "waste_carriers"

        if es.indices.exists(index=index_name):
            self.stdout.write(self.style.WARNING("Index already exists."))
            return

        mapping = {
            "mappings": {
                "properties": {
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


class Command(BaseCommand):
    help = "Create indices for new waste models"

    def handle(self, *args, **kwargs):
        es = get_elasticsearch_client()

        indices = {
            "waste_exemptions": {
                "properties": {
                    "company_name": {"type": "text"},
                    "waste_exemption_no": {"type": "keyword"},
                    "waste_site_address": {"type": "text"},
                    "waste_site_postcode": {"type": "keyword"},
                    "issue_date": {"type": "date"},
                    "expiry_date": {"type": "date"}
                }
            },
            "waste_operations": {
                "properties": {
                    "waste_destination_name": {"type": "text"},
                    "waste_destination_address": {"type": "text"} ,
                    "waste_destination_postcode": {"type": "keyword"},
                    "waste_destination_permit_no": {"type": "keyword"},
                    "waste_destination_permit_status": {"type": "keyword"},
                    "waste_destination_permit_effective_date": {"type": "date"},
                    "waste_destination_permit_surrendered_date": {"type": "date"},
                    "waste_destination_permit_revoked_date": {"type": "date"},
                    "waste_destination_permit_suspended_date": {"type": "date"}
                }
            }
        }

        for index_name, mapping in indices.items():
            if es.indices.exists(index=index_name):
                self.stdout.write(self.style.WARNING(f"Index '{index_name}' already exists."))
                continue
            es.indices.create(index=index_name, body={"mappings": mapping})
            self.stdout.write(self.style.SUCCESS(f"Created index '{index_name}'"))