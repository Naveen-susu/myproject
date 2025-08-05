# --- File: app/management/commands/index_waste_operations.py ---
from django.core.management.base import BaseCommand
from app.models import WasteOperationsPermits
from app.utils.elasticsearch_client import get_elasticsearch_client

class Command(BaseCommand):
    help = "Index WasteOperationsPermits to Elasticsearch"

    def handle(self, *args, **kwargs):
        es = get_elasticsearch_client()
        index_name = "waste_operations"

        for obj in WasteOperationsPermits.objects.all():
            doc = {
                "id": obj.id,
                "waste_destination_name": obj.waste_destination_name,
                "waste_destination_postcode": obj.waste_destination_postcode,
                "waste_destination_address": obj.waste_destination_address,
                "waste_destination_permit_no": obj.waste_destination_permit_no,
                "waste_destination_permit_status": obj.waste_destination_permit_status,
                "waste_destination_permit_effective_date": obj.waste_destination_permit_effective_date,
                "waste_destination_permit_surrendered_date": obj.waste_destination_permit_surrendered_date,
                "waste_destination_permit_revoked_date": obj.waste_destination_permit_revoked_date,
                "waste_destination_permit_suspended_date": obj.waste_destination_permit_suspended_date
            }
            es.index(index=index_name, id=obj.id, document=doc)

        self.stdout.write(self.style.SUCCESS(f"✅ Indexed all WasteOperationsPermits into '{index_name}'"))


        