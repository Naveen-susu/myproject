from rest_framework import serializers
from .models import *
from datetime import datetime
import pytz
from rest_framework import serializers
from .models import UserBuilding



#######################   COMMON ######################################

class CountrySerializer(serializers.ModelSerializer):
    class Meta:
        model = Country
        fields = '__all__'

class RegionSerializer(serializers.ModelSerializer):
    country = serializers.CharField(source='country.name')
    class Meta:
        model = Region
        fields = ['id','name','country']  # Adjust fields if you need to filter some out

class CitySerializer(serializers.ModelSerializer):
    region = serializers.CharField(source='region.name')
    class Meta:
        model = City
        fields = ['id','name','region'] 


class BuildingSerializer(serializers.ModelSerializer):
    city=serializers.CharField(source='city.name')
    class Meta:
        model = Building
        fields = '__all__'



class UserBuildingSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserBuilding
        fields = ['id', 'building_id', 'user_id', 'status']
#######################################################################################

class UserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=False)
    confirm_password = serializers.CharField(write_only=True, required=False)



    class Meta:
        model = CustomUser
        fields = ['id', 'email', 'password', 'confirm_password','email_verified']

    def validate(self, data):
        if 'password' in data and 'confirm_password' in data:
            if data['password'] != data['confirm_password']:
                raise serializers.ValidationError("Passwords do not match")
        return data

    def create(self, validated_data):
        validated_data.pop('confirm_password', None)
        user = CustomUser.objects.create(
            email=validated_data['email'],
        )
        if 'password' in validated_data:
            user.set_password(validated_data['password'])
        user.save()
        return user

    def update(self, instance, validated_data):
        if 'password' in validated_data:
            instance.set_password(validated_data.pop('password'))
        return super().update(instance, validated_data)


class VerifyEmailSerializer(serializers.Serializer):
    email = serializers.EmailField()
    otp = serializers.CharField(max_length=6)

class ResendCodeSerializer(serializers.Serializer):
    email = serializers.EmailField(required=True)



class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField(required=True)
    password = serializers.CharField(write_only=True, required=True)


class UserListSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    email = serializers.EmailField()
    email_verified = serializers.BooleanField(default=False)


############################################################################    


class BestMatchSerializer(serializers.ModelSerializer):
    # Computed fields
    carbon = serializers.SerializerMethodField()
    kgco2_per_m2 = serializers.SerializerMethodField()

    class Meta:
        model = BestMatch
        fields = [
            "id",
            "delivery_note_ref_no",
            "item_no",
            "product_description",
            "unit_of_measure",
            "quantity",
            "product_name",
            "material_name",
            "product_company_name",
            "product_match_score",
            "global_warming_potential_fossil",
            "declared_unit",
            "scaling_factor",
            "data_source",
            "processed",
            "processed_timestamp",
           # "gia",
            "carbon",
            "kgco2_per_m2",
            "building_id"
        ]
        read_only_fields = [
            "product_name",
            "material_name",
            "product_company_name",
            "product_match_score",
            "global_warming_potential_fossil",
            "declared_unit",
            "scaling_factor",
            "data_source",
            "processed",
            "processed_timestamp",
            "carbon",
            "kgco2_per_m2"
        ]

    def get_carbon(self, obj):
        try:
            if obj.global_warming_potential_fossil and obj.scaling_factor:
                return float(obj.global_warming_potential_fossil) / float(obj.scaling_factor)
        except (ValueError, TypeError):
            return None
        return None

    def get_kgco2_per_m2(self, obj):
        try:
            if obj.global_warming_potential_fossil and obj.scaling_factor and obj.quantity:
                return (float(obj.global_warming_potential_fossil) / float(obj.scaling_factor)) * (float(obj.quantity) / float(5000))
        except (ValueError, TypeError):
            return None
        return None

    def to_representation(self, instance):
        data = super().to_representation(instance)
        processed_timestamp = instance.processed_timestamp

        if processed_timestamp:
            # Format the date-time to the desired format
            formatted_date = processed_timestamp.strftime("%Y-%m-%d %H:%M:%S.%f%z")
            # Replace +0000 with +00 to represent UTC
            formatted_date = formatted_date[:-5] + "+00"
            data['processed_timestamp'] = formatted_date

        return data

class InvoiceDataSerializer(serializers.ModelSerializer):
    phase_name = serializers.CharField(source='phase_name.name', read_only=True)
    class Meta:
        model = InvoiceData
        fields = '__all__'

class DesignDataSerializer(serializers.ModelSerializer):
    total = serializers.SerializerMethodField()
    building_name = serializers.CharField(source='building.building_name', read_only=True)
    city = serializers.CharField(source='building.city.name', read_only=True)
    region = serializers.CharField(source='building.region.name', read_only=True)

    class Meta:
        model = DesignData
        fields = [
            'id', 'region', 'city', 'building_name',
            'substructure', 'superstructure', 'façade',
            'internal_walls_partitions', 'internal_finishes', 'ff_fe',
            'gia', 'customer_ref', 'total'
        ]

    def get_total(self, obj):
        return (
            (obj.substructure or 0) +
            (obj.superstructure or 0) +
            (obj.façade or 0) +
            (obj.internal_walls_partitions or 0) +
            (obj.internal_finishes or 0) +
            (obj.ff_fe or 0)
        )


class YourMaterialSerializer(serializers.ModelSerializer):
    class Meta:
        model = YourMaterial
        fields = '__all__'  # Adjust fields if you need to filter some out


class YourMaterialEmissionSerializer(serializers.ModelSerializer):
    name = serializers.CharField(source='name.name')
    class Meta:
        model = YourMaterialEmission
        fields = '__all__'  # Adjust fields if you need to filter some out


class EcoMaterialSerializer(serializers.ModelSerializer):
    class Meta:
        model = EcoMaterial
        fields = '__all__'  # Adjust fields if you need to filter some out


class EcoMaterialEmissionSerializer(serializers.ModelSerializer):
    name = serializers.CharField(source='name.name')
    class Meta:
        model = EcoMaterialEmission
        fields = '__all__'  # Adjust fields if you need to filter some out


class VolumeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Volume
        fields = '__all__'  # Adjust fields if you need to filter some out

class CompareCarbonInputSerializer(serializers.ModelSerializer):
    class Meta:
        model = CompareCarbon
        fields = ('id','country','region','your_material_emission','eco_material_emission','volume')
    # def validate(self, data):
    #     your_material = data.get('your_material')
    #     your_material_emission = data.get('your_material_emission')
        
    #     if your_material and your_material_emission:
    #         if your_material_emission.name != your_material:
    #             raise serializers.ValidationError("The emission does not match the selected material.")
            #     return data






class CompareCarbonSerializer(serializers.ModelSerializer):
    country_name = serializers.CharField(source='region.country')
    region_name=serializers.CharField(source='region.name')
    material_name=serializers.CharField(source='your_material_emission.name')
    material_emission_value=serializers.CharField(source='your_material_emission.emission')
    eco_material_name=serializers.CharField(source='eco_material_emission.name')
    eco_emission_value=serializers.CharField(source='eco_material_emission.emission')
    volume_value=serializers.IntegerField(source='volume.value')
    total_reduction_potential = serializers.IntegerField()
    reduction_potential = serializers.IntegerField()
    trees_planted = serializers.IntegerField()
    energy_used = serializers.IntegerField()
    car_journeys = serializers.IntegerField()
    class Meta:
        model = CompareCarbon
        fields = ('country_name','region_name','material_name','material_emission_value','eco_material_name','eco_emission_value','volume_value','total_reduction_potential','reduction_potential','trees_planted','energy_used','car_journeys')





class PhaseSerializer(serializers.ModelSerializer):
    class Meta:
        model = Phase  # Specify the model
        fields = '__all__'  # Include all fields (or specify specific fields)


################################## WASTE TRANSFER NOTE ####################################


class WasteTransferNoteSerializer(serializers.ModelSerializer):
    building_name = serializers.SerializerMethodField()
    building_address = serializers.SerializerMethodField()

    class Meta:
        model = WasteTransferNote
        # fields = '__all__'
        fields = ['id', 'waste_tracking_note_code', 'waste_transfer_note_date', 'approved_date', 'waste_note_uploaded_by', 'waste_note_upload_date', 'waste_carrier_name', 'kgco2', 'filename','building_name', 'building_address']
        # extra_fields = ['building_name', 'building_address']

    def get_building_name(self, obj):
        building = AppBuilding.objects.filter(id=obj.building_id).first()
        return building.name if building else None

    def get_building_address(self, obj):
        building = AppBuilding.objects.filter(id=obj.building_id).first()
        if not building:
            return None

        # Get city name if city_id exists
        city = City.objects.filter(id=building.city_id).first()
        city_name = city.name if city else ''

        address_parts = [
            building.address_line_1,
            building.address_line_2,
            city_name,
            building.postcode
        ]
        return ', '.join([part for part in address_parts if part])

class WasteTransferNoteExtraSerializer(serializers.ModelSerializer):
    building_name = serializers.SerializerMethodField()
    building_address = serializers.SerializerMethodField()

    class Meta:
        model = WasteTransferNote
        # fields = '__all__'
        fields = ['id','waste_tracking_note_code', 'waste_transfer_note_date', 'ewc_code', 'sic_code', 'waste_quantity', 'container_size', 'number_of_containers','waste_transferor_name', 'waste_transferor_address', 'waste_transferor_postcode', 'waste_destination_name', 'waste_destination_address', 'waste_destination_postcode', 'destination_permit_no', 'destination_exemption_no', 'destination_permit_issue_date', 'destination_permit_status', 'waste_carrier_name', 'waste_carrier_address', 'waste_carrier_postcode', 'waste_carrier_license_no', 'waste_carrier_license_issue_date', 'waste_carrier_license_expiry_date', 'building_name', 'building_address', 'waste_disposal_code', 'waste_phase_code']
        # extra_fields = ['building_name', 'building_address']

    def get_building_name(self, obj):
        building = AppBuilding.objects.filter(id=obj.building_id).first()
        return building.name if building else None

    def get_building_address(self, obj):
        building = AppBuilding.objects.filter(id=obj.building_id).first()
        if not building:
            return None

        # Get city name if city_id exists
        city = City.objects.filter(id=building.city_id).first()
        city_name = city.name if city else ''

        address_parts = [
            building.address_line_1,
            building.address_line_2,
            city_name,
            building.postcode
        ]
        return ', '.join([part for part in address_parts if part])



class WasteTransferNoteMobileSerializer(serializers.ModelSerializer):
    building_name = serializers.SerializerMethodField()
    city_name = serializers.SerializerMethodField()
    region_name = serializers.SerializerMethodField()
    # building_address = serializers.SerializerMethodField()

    class Meta:
        model = WasteTransferNote
        fields = ['id', 'waste_tracking_note_code', 'waste_transfer_note_date', 'waste_carrier_name', 'building_name', 'city_name', 'region_name'] 
        #extra_fields = ('building_name', 'city_name', 'region_name')

    def get_building_name(self, obj):
        building = AppBuilding.objects.filter(id=obj.building_id).first()
        return building.name if building else None

    def get_city_name(self, obj):
        building = AppBuilding.objects.filter(id=obj.building_id).first()
        if building and building.city_id:
            city = City.objects.filter(id=building.city_id).first()
            return city.name if city else None
        return None

    def get_region_name(self, obj):
        building = AppBuilding.objects.filter(id=obj.building_id).first()
        if building and building.region_id:
            region = Region.objects.filter(id=building.region_id).first()
            return region.name if region else None
        return None

    # def get_building_address(self, obj):
    #     building = AppBuilding.objects.filter(id=obj.building_id).first()
    #     if not building:
    #         return None
    #     parts = filter(None, [building.address_line_1, building.address_line_2, building.postcode])
    #     return ', '.join(parts)


class WasteDisposalSerializer(serializers.ModelSerializer):
    class Meta:
        model = WasteDisposal
        fields = '__all__'


class WastePhaseSerializer(serializers.ModelSerializer):
    class Meta:
        model = WastePhase
        fields = '__all__'


class WasteCarriersBrokersDealersSerializer(serializers.ModelSerializer):
    class Meta:
        model = WasteCarriersBrokersDealers
        fields = '__all__'