# -------------------- app/utils/elasticsearch_client.py --------------------
from elasticsearch import Elasticsearch
from django.conf import settings

def get_elasticsearch_client():
    es_host = getattr(settings, "ELASTICSEARCH_HOST", "http://elasticsearch:9200")
    return Elasticsearch(
        es_host,
        headers={
            "Accept": "application/vnd.elasticsearch+json; compatible-with=8",
            "Content-Type": "application/vnd.elasticsearch+json; compatible-with=8"
        }
    )