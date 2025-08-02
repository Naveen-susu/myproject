from django.db.models.signals import post_delete
from django.dispatch import receiver
from .models import CustomUser
import boto3
from django.conf import settings
from django.db.models.signals import post_save
from .models import WasteCarriersBrokersDealers, WasteExemptionCertificates, WasteOperationsPermits
from app.utils.elasticsearch_client import get_elasticsearch_client



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
    es = get_elasticsearch_client()
    doc = {
        "waste_carrier_license_no": instance.waste_carrier_license_no,
        "waste_carrier_name": instance.waste_carrier_name,
        "company_no": instance.company_no,
        "waste_carrier_license_issue_date": instance.waste_carrier_license_issue_date,
        "waste_carrier_expiry_date": instance.waste_carrier_expiry_date,
        "waste_carrier_address": instance.waste_carrier_address,
        "waste_carrier_postcode": instance.waste_carrier_postcode
    }
    try:
        es.index(index="waste_carriers", id=instance.id, document=doc)
    except Exception as e:
        pass  # Optionally log

@receiver(post_delete, sender=WasteCarriersBrokersDealers)
def delete_from_elasticsearch(sender, instance, **kwargs):
    es = get_elasticsearch_client()
    try:
        es.delete(index="waste_carriers", id=instance.id)
    except Exception:
        pass



@receiver(post_save, sender=WasteExemptionCertificates)
def index_waste_exemption(sender, instance, **kwargs):
    es = get_elasticsearch_client()
    doc = {
        "company_name": instance.company_name,
        "waste_exemption_no": instance.waste_exemption_no,
        "waste_site_address": instance.waste_site_address,
        "waste_site_postcode": instance.waste_site_postcode,
        "issue_date": instance.issue_date,
        "expiry_date": instance.expiry_date
    }
    es.index(index="waste_exemptions", id=instance.id, document=doc)

@receiver(post_delete, sender=WasteExemptionCertificates)
def delete_waste_exemption(sender, instance, **kwargs):
    es = get_elasticsearch_client()
    es.delete(index="waste_exemptions", id=instance.id, ignore=[404])


@receiver(post_save, sender=WasteOperationsPermits)
def index_waste_operations(sender, instance, **kwargs):
    es = get_elasticsearch_client()
    doc = {
        "waste_destination_name": instance.waste_destination_name,
        "waste_destination_postcode": instance.waste_destination_postcode,
        "waste_destination_permit_no": instance.waste_destination_permit_no,
        "waste_destination_permit_status": instance.waste_destination_permit_status,
        "waste_destination_permit_effective_date": instance.waste_destination_permit_effective_date,
        "waste_destination_permit_surrendered_date": instance.waste_destination_permit_surrendered_date,
        "waste_destination_permit_revoked_date": instance.waste_destination_permit_revoked_date,
        "waste_destination_permit_suspended_date": instance.waste_destination_permit_suspended_date
    }
    es.index(index="waste_operations", id=instance.id, document=doc)

@receiver(post_delete, sender=WasteOperationsPermits)
def delete_waste_operations(sender, instance, **kwargs):
    es = get_elasticsearch_client()
    es.delete(index="waste_operations", id=instance.id, ignore=[404])