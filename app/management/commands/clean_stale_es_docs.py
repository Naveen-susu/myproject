# app/management/commands/clean_stale_es_docs.py
from django.core.management.base import BaseCommand
from app.models import WasteCarriersBrokersDealers
from app.utils.elasticsearch_client import get_elasticsearch_client  # ✅ use central client utility

class Command(BaseCommand):
    help = "Remove stale documents in Elasticsearch that no longer exist in the DB"

    def handle(self, *args, **kwargs):
        es = get_elasticsearch_client()  # ✅ consistent config
        index_name = "waste_carriers"

        db_ids = set(WasteCarriersBrokersDealers.objects.values_list('id', flat=True))
        es_ids = set()

        # ⚠️ NOTE: this loads up to 10,000 docs — adjust for larger datasets (e.g., scroll API)
        result = es.search(index=index_name, query={"match_all": {}}, size=10000)
        for hit in result["hits"]["hits"]:
            try:
                es_ids.add(int(hit["_id"]))
            except ValueError:
                continue  # Skip non-integer IDs if any

        stale_ids = es_ids - db_ids
        for stale_id in stale_ids:
            es.delete(index=index_name, id=stale_id)
            self.stdout.write(self.style.WARNING(f"Deleted stale document with id {stale_id}"))

        self.stdout.write(self.style.SUCCESS("✅ Stale cleanup complete."))