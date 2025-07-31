from django.db.models.signals import post_delete
from django.dispatch import receiver
from .models import CustomUser
import boto3
from django.conf import settings
from django.db.models.signals import post_save
from elasticsearch import Elasticsearch
from .models import WasteCarriersBrokersDealers






@receiver(post_delete, sender=CustomUser)
def delete_user_in_cognito(sender, instance, **kwargs):
    """
    Deletes the user from AWS Cognito when they are deleted in Django.
    """
    client = boto3.client('cognito-idp', region_name=settings.AWS_COGNITO_REGION)
    try:
        client.admin_delete_user(
            UserPoolId=settings.AWS_COGNITO_USER_POOL_ID,
            Username=instance.email
        )
    except client.exceptions.UserNotFoundException:
        pass  # User was already deleted in Cognito



@receiver(post_save, sender=WasteCarriersBrokersDealers)
def index_to_elasticsearch(sender, instance, **kwargs):
    es_host = getattr(settings, "ELASTICSEARCH_HOST", "http://elasticsearch:9200")
    es = Elasticsearch(
        es_host,
        headers={
            "Accept": "application/vnd.elasticsearch+json; compatible-with=8",
            "Content-Type": "application/vnd.elasticsearch+json; compatible-with=8"
        }
    )

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



