from django.core.management.base import BaseCommand
from elasticsearch import Elasticsearch
from django.conf import settings

class Command(BaseCommand):
    help = "Create waste_carriers index in Elasticsearch"

    def handle(self, *args, **kwargs):
        es_host = getattr(settings, "ELASTICSEARCH_HOST", "http://elasticsearch:9200")
        es = Elasticsearch(
            es_host,
            headers={
                "Accept": "application/vnd.elasticsearch+json; compatible-with=8",
                "Content-Type": "application/vnd.elasticsearch+json; compatible-with=8"
            }
        )

        index_name = "waste_carriers"

        if es.indices.exists(index=index_name):
            self.stdout.write(self.style.WARNING("Index already exists."))
            return

        # Define index structure (mapping)
        mapping = {
            "mappings": {
                "properties": {
                    "waste_carrier_license_no": {"type": "text"},
                    "waste_carrier_name": {"type": "text"},
                    "company_no": {"type": "text"},
                    "waste_carrier_license_issue_date": {"type": "text"},
                    "waste_carrier_expiry_date": {"type": "text"},
                    "waste_carrier_address": {"type": "text"},
                    "waste_carrier_postcode": {"type": "text"}
                }
            }
        }

        es.indices.create(index=index_name, body=mapping)
        self.stdout.write(self.style.SUCCESS(f"Created index '{index_name}'"))
