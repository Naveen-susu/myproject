# app/management/commands/index_data.py

from django.core.management.base import BaseCommand
from app.models import WasteCarriersBrokersDealers, WasteExemptionCertificates, WasteOperationsPermits

from app.utils.elasticsearch_client import get_elasticsearch_client

class Command(BaseCommand):
    help = "Index existing waste carrier records to Elasticsearch"

    def handle(self, *args, **kwargs):
        es = get_elasticsearch_client()
        for instance in WasteCarriersBrokersDealers.objects.all():
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

        self.stdout.write(self.style.SUCCESS("✅ All records indexed successfully for waste_carrier_brokers_dealers."))


class Command(BaseCommand):
    help = "Index WasteExemptionCertificates and WasteOperationsPermits"

    def handle(self, *args, **kwargs):
        es = get_elasticsearch_client()

        for obj in WasteExemptionCertificates.objects.all():
            doc = {
                "company_name": obj.company_name,
                "waste_exemption_no": obj.waste_exemption_no,
                "waste_site_address": obj.waste_site_address,
                "waste_site_postcode": obj.waste_site_postcode,
                "issue_date": obj.issue_date,
                "expiry_date": obj.expiry_date
            }
            es.index(index="waste_exemptions", id=obj.id, document=doc)

        for obj in WasteOperationsPermits.objects.all():
            doc = {
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
            es.index(index="waste_operations", id=obj.id, document=doc)

        self.stdout.write(self.style.SUCCESS("✅ Indexed all WasteExemptionCertificates and WasteOperationsPermits"))



        