from datetime import timedelta
from django.db import models
from django.contrib.auth.models import AbstractUser

class CustomUser(AbstractUser):
    username = None  # Remove the default username field
    email = models.EmailField(unique=True)  # Set email as unique identifier
    cognito_sub = models.CharField(max_length=100, unique=True, null=True, blank=True)
    email_verified = models.BooleanField(default=False)

    USERNAME_FIELD = 'email'  # Set email as the primary identifier
    REQUIRED_FIELDS = []  # No additional required fields

    def __str__(self):
        return self.email

class BestMatch(models.Model):
    delivery_note_ref_no = models.CharField(db_column='Delivery_Note_Ref_No',max_length=300, null=True, blank=True)
    supplier_name = models.TextField(db_column='Supplier_Name', null=True, blank=True)
    supplier_address_line_1 = models.TextField(db_column='Supplier_Address_Line_1', null=True, blank=True)
    supplier_city = models.TextField(db_column='Supplier_City', null=True, blank=True)
    supplier_post_code = models.TextField(db_column='Supplier_Post_code',null=True, blank=True)
    supplier_country = models.TextField(db_column='Supplier_Country', null=True, blank=True)
    delivery_to = models.TextField(db_column='Delivery_to', null=True, blank=True)
    delivery_address_line_1 = models.TextField(db_column='Delivery_Address_Line_1', null=True, blank=True)
    delivery_city = models.TextField(db_column='Delivery_City',null=True, blank=True)
    delivery_post_code = models.TextField(db_column='Delivery_Post_code',null=True, blank=True)
    delivery_country = models.TextField(db_column='Delivery_Country', null=True, blank=True)
    delivery_note_date = models.DateField(db_column='Delivery_Note_Date', null=True, blank=True)
    email = models.TextField(db_column='Email', null=True, blank=True)
    phone = models.TextField(db_column='Phone', null=True, blank=True)
    purchase_order_no = models.TextField(db_column='Purchase_Order_No',null=True, blank=True)
    filename = models.TextField(db_column='Filename', null=True, blank=True)
    account_number = models.TextField(db_column='account_number',null=True, blank=True)
    item_no = models.BigIntegerField(db_column='Item_No', null=True, blank=True)
    phase_id = models.BigIntegerField(db_column='Phase_ID', null=True, blank=True)
    product_description = models.TextField(db_column='Product_Description', null=True, blank=True)
    unit_of_measure = models.TextField(db_column='Unit_of_Measure', null=True, blank=True)
    quantity = models.FloatField(db_column='Quantity', null=True, blank=True)
    building_id = models.BigIntegerField(db_column='Building_ID',null=True, blank=True)
    entry_time = models.DateTimeField(db_column='entry_time', null=True, blank=True)
    user_id = models.TextField(db_column='User_ID', null=True, blank=True)
    product_name = models.TextField(db_column='Product_Name', null=True, blank=True)
    material_name = models.TextField(db_column='Material_Name',null=True, blank=True)
    product_company_name = models.TextField(db_column='Product_Company_Name', null=True, blank=True)
    product_match_score = models.FloatField(db_column='Product_Match_Score', null=True, blank=True)
    global_warming_potential_fossil = models.FloatField(db_column='global_warming_potential_fossil', null=True, blank=True)
    declared_unit = models.TextField(db_column='Declared_Unit', null=True, blank=True)
    scaling_factor = models.FloatField(db_column='Scaling_factor', null=True, blank=True)
    data_source = models.TextField(db_column='Data_Source', null=True, blank=True)
    processed = models.BooleanField(db_column='Processed', default=False, null=True, blank=True)
    processed_timestamp = models.DateTimeField(db_column='Processed_Timestamp', null=True, blank=True)
    kgco2 = models.FloatField(db_column='KgCO2', null=True, blank=True)
    customer_ref=models.TextField(db_column='customer_ref', null=True, blank=True)
    exception=models.TextField(db_column="exception",null=True,blank=True)
    revised_product_description=models.TextField(db_column = "revised_product_description",null=True,blank=True)
    revised_unit_of_measure=models.TextField(db_column = "revised_unit_of_measure",null=True,blank=True)
    revised_quantity = models.DecimalField(db_column='revised_quantity', max_digits=20, decimal_places=10, null=True, blank=True)
    revised_phase_id= models.TextField(db_column = "revised_phase_id",null=True,blank=True)
    revised_user_id = models.TextField(db_column = "revised_user_id",null=True,blank=True)
    revised_date = models.DateTimeField(auto_now_add=True, blank=True, null=True) 
    approved = models.BooleanField(db_column='approved', default=True, null=True, blank=True)
    error_code = models.BigIntegerField(db_column='error_code',null=True, blank=True)
    package_type = models.TextField(db_column='package_type', null=True, blank=True)
    package_unit_type = models.TextField(db_column='package_unit_type', null=True, blank=True)
    package_unit_item_count = models.BigIntegerField(db_column='package_unit_item_count', null=True, blank=True)
    package_unit_item_length = models.FloatField(db_column='package_unit_item_length', null=True, blank=True)
    package_unit_item_width = models.FloatField(db_column='package_unit_item_width', null=True, blank=True)
    package_unit_item_height = models.FloatField(db_column='package_unit_item_height', null=True, blank=True)
    package_unit_item_dimension_uom = models.TextField(db_column='package_unit_item_dimension_uom', null=True, blank=True)
    package_unit_item_area = models.FloatField(db_column='package_unit_item_area', null=True, blank=True)
    package_unit_item_area_uom = models.TextField(db_column='package_unit_item_area_uom', null=True, blank=True)
    mass_per_declared_unit = models.FloatField(db_column='mass_per_declared_unit', null=True, blank=True)
    density = models.FloatField(db_column='density', null=True, blank=True)
    linear_density = models.FloatField(db_column='linear_density', null=True, blank=True)
    package_unit_item_volume = models.FloatField(db_column='package_unit_item_volume', null=True, blank=True)
    package_unit_item_volume_uom = models.TextField(db_column='package_unit_item_volume_uom', null=True, blank=True)


    class Meta:
        db_table = 'app_deliverynote_data'

class Phase(models.Model):
    name = models.CharField(max_length=300)

    def __str__(self):
        return self.name

class InvoiceData(models.Model):
    customer_ref = models.BigIntegerField(default=12346, null=True, blank=True)
    delivery_note_ref_no = models.BigIntegerField(null=True, blank=True)
    supplier_name = models.CharField(max_length=300, null=True, blank=True)
    data_source = models.CharField(max_length=300, null=True, blank=True)
    product_description = models.CharField(max_length=1000, null=True, blank=True)
    material_name = models.CharField(max_length=500)
    entry_time = models.DateField(null=True, blank=True)
    quantity = models.IntegerField(null=True, blank=True)
    unit_of_measure = models.CharField(max_length=300, null=True, blank=True)
    country_name = models.CharField(max_length=300, default='UK', null=True, blank=True,db_index=True)
    region_name = models.CharField(max_length=300, default='London', null=True, blank=True,db_index=True)
    city_name = models.CharField(max_length=300, default='Westminster', null=True, blank=True,db_index=True)
    building_name = models.CharField(max_length=300, default='John Wood Hospital', null=True, blank=True,db_index=True)
    phase_name = models.ForeignKey(Phase, null=True, blank=True, on_delete=models.CASCADE)
    kgco2 = models.BigIntegerField(null=True, blank=True)
    product_manufacturing_company = models.CharField(max_length=300, null=True, blank=True)

    def __str__(self):
        return f"Invoice {self.customer_ref}"

    class Meta:
        db_table = 'invoice_data'

#####################################  Common ############################
class Country(models.Model):
    name = models.CharField(max_length=100)

    def __str__(self):
        return self.name

class Region(models.Model):
    name = models.CharField(max_length=100)
    country = models.ForeignKey(Country, on_delete=models.CASCADE, related_name='regions')

    def __str__(self):
        return f"{self.name}, {self.country.name}"
    
class City(models.Model):
    name = models.CharField(max_length=100)
    region = models.ForeignKey(Region, on_delete=models.CASCADE, related_name='cities')

    def __str__(self):
        return f"{self.name}, {self.region.name}"

class Building(models.Model):
    name = models.CharField(max_length=100)
    city = models.ForeignKey(City, on_delete=models.CASCADE, related_name='buildings')
    customer_ref = models.CharField(max_length=255)
    region_id =models.CharField(max_length=100)
    country_id =models.CharField(max_length=100)
    status=models.BooleanField(default=True)

    def __str__(self):
        return f"{self.name}, {self.city.name}"

class AppBuilding(models.Model):
    id = models.AutoField(primary_key=True)  # Use uppercase ID as primary key
    name = models.TextField(max_length=255)
    address_line_1 = models.TextField(max_length=255)
    address_line_2 = models.TextField(max_length=255)
    city_id = models.BigIntegerField(null=True, blank=True)
    region_id= models.BigIntegerField(null=True, blank=True)
    customer_ref= models.TextField(max_length=255)
    postcode = models.TextField(max_length=255)

    class Meta:
        managed = False  # This prevents Django from trying to manage the table
        db_table = 'app_building'


#############################################################################
class DesignData(models.Model):
    region = models.CharField(max_length=300)
    city = models.CharField(max_length=300)
    building_name = models.CharField(max_length=300)
    substructure =models.IntegerField()
    superstructure=models.IntegerField()
    façade =models.IntegerField()
    internal_walls_partitions =models.IntegerField()
    internal_finishes =models.IntegerField()
    ff_fe =models.IntegerField()
    gia = models.IntegerField()
    customer_ref = models.CharField(max_length=255)
    building_id = models.CharField(db_column='building_id', max_length=255, null=True, blank=True)
    frame = models.IntegerField(db_column='frame')
    upper_floors = models.IntegerField(db_column='upper_floors')
    roofs = models.IntegerField(db_column='roofs')
    stairs_and_ramps = models.IntegerField(db_column='stairs_and_ramps')
    external_walls = models.IntegerField(db_column='external_walls')
    windows_and_external_walls = models.IntegerField(db_column='windows_and_external_walls')
    internal_doors = models.IntegerField(db_column='internal_doors')
    wall_finishes = models.IntegerField(db_column='wall_finishes')
    floor_finishes = models.IntegerField(db_column='floor_finishes')
    ceiling_finishes = models.IntegerField(db_column='ceiling_finishes')


    def __str__(self):
        return self.name

####################################  Compare Carbon ############################

class YourMaterial(models.Model):
    name = models.CharField(max_length=300)
    class Meta:
        db_table = 'your_material_table'

    def __str__(self):
        return self.name
class YourMaterialEmission(models.Model):
    name=models.ForeignKey(YourMaterial,null=True,on_delete=models.CASCADE)
    emission=models.IntegerField(null=True)
    class Meta:
        db_table = 'your_material_emission_table'

    def __str__(self):
        return str(self.name)

class EcoMaterial(models.Model):
    name=models.CharField(max_length=300)
    class Meta:
        db_table = 'eco_material_table'

    def __str__(self):
        return self.name

class EcoMaterialEmission(models.Model):
    name=models.ForeignKey(EcoMaterial,null=True,on_delete=models.CASCADE)
    emission=models.IntegerField(null=True)
    class Meta:
        db_table = 'eco_material_emission_table'

    def __str__(self):
        return str(self.name)

class Volume(models.Model):
    value=models.IntegerField(null=True)
    class Meta:
        db_table = 'volume_table'

    def __str__(self):
        return str(self.value)


class CompareCarbon(models.Model):
    country=models.ForeignKey(Country,null=True,on_delete=models.CASCADE)
    region=models.ForeignKey(Region,null=True,on_delete=models.CASCADE)
    #your_material=models.ForeignKey(YourMaterial,null=True,related_name="carbon_table",on_delete=models.CASCADE)
    your_material_emission=models.ForeignKey(YourMaterialEmission,null=True,related_name="carbon_table",on_delete=models.CASCADE)
    #eco_material=models.ForeignKey(EcoMaterial,null=True,related_name="carbon_table",on_delete=models.CASCADE)
    eco_material_emission=models.ForeignKey(EcoMaterialEmission,null=True,related_name="carbon_table",on_delete=models.CASCADE)
    volume=models.ForeignKey(Volume,null=True,on_delete=models.CASCADE)

    @property
    def total_reduction_potential(self):
        return (self.volume.value)*((self.your_material_emission.emission)-(self.eco_material_emission.emission))
    
    @property
    def reduction_potential(self):
        return (self.total_reduction_potential)/((self.your_material_emission.emission)*(self.volume.value))*100
    
    @property
    def trees_planted(self):
        return (self.total_reduction_potential)/(58.8)
    
    @property
    def energy_used(self):
        return (self.total_reduction_potential)/(10000)
    
    @property
    def car_journeys(self):
        return (self.total_reduction_potential)/(0.25)

    class Meta:
        db_table = 'carbon_table'

######################################  Thoufiq ####################################

class BestAPIToken(models.Model):
    TokenName = models.CharField(max_length=255, null=True)  
    TokenValue = models.CharField(max_length=255, null=True)
    TokenExpirationTime = models.CharField(max_length=255, null=True)
    TokenExpiryTime = models.DateTimeField(null=True)
    RefreshToken =  models.CharField(max_length=255, null=True)
    CreatedOn = models.DateTimeField(auto_now_add=True) 
    
    def __str__(self):
        return self.TokenName or "Unnamed Token"

    class Meta:
        db_table = 'best_token_table'
    

    def __str__(self):
        return str(self.value)
    
class CustomerMaster(models.Model):
    ID = models.AutoField(primary_key=True)  # Use uppercase ID as primary key
    Customer_Ref = models.CharField(max_length=255)
    Domain_Name = models.CharField(max_length=255)

    class Meta:
        managed = False  # This prevents Django from trying to manage the table
        db_table = 'Customer_Master'

class DeliveryNoteFile(models.Model):
    id = models.AutoField(primary_key=True)  # Use uppercase ID as primary key
    file_name = models.CharField(max_length=255)

    class Meta:
        managed = False  # This prevents Django from trying to manage the table
        db_table = 'delivery_note_file'


class UserBuilding(models.Model):
    id = models.AutoField(primary_key=True)  # Use uppercase ID as primary key
    building_id = models.BigIntegerField(null=True, blank=True)
    user_id = models.TextField(max_length=255)
    status=models.BooleanField(default=False, null=True, blank=True)

    class Meta:
        managed = False  # This prevents Django from trying to manage the table
        db_table = 'User_Buildings'

class Users(models.Model):
    ID = models.AutoField(primary_key=True)  # Use uppercase ID as primary key
    User_ID = models.TextField(max_length=255)
    verification_status = models.TextField(max_length=255)
    customer_ref=models.TextField(max_length=255)

    class Meta:
        managed = False  # This prevents Django from trying to manage the table
        db_table = 'Users'
    
    def __str__(self):
        return self.User_ID



class Unit_of_Measure(models.Model):
    id = models.AutoField(primary_key=True)  # Use uppercase ID as primary key
    name = models.TextField(max_length=255)

    class Meta:
        managed = False  # This prevents Django from trying to manage the table
        db_table = 'unit_of_measure'

class ProductMapping(models.Model):
    id = models.AutoField(primary_key=True)  # Use uppercase ID as primary key
    customer_ref = models.TextField(max_length=255)
    product_description = models.TextField(max_length=255)
    mapped_product_description = models.TextField(max_length = 255)
    user_id = models.TextField(max_length = 255)
    creation_date = models.DateTimeField(auto_now_add=True) 


    class Meta:
        managed = False  # This prevents Django from trying to manage the table
        db_table = 'product_mapping'

class AppDeliveryNoteChangeLog(models.Model):
    id = models.AutoField(primary_key=True)  # Use uppercase ID as primary key
    delivery_note_ref_no = models.TextField(max_length=255)
    item_id = models.TextField(max_length=255)
    product_description = models.TextField(max_length = 255)
    unit_of_measure = models.TextField(max_length = 255)
    quantity = models.DecimalField(db_column='quantity', max_digits=20, decimal_places=10, null=True, blank=True)
    phase_id=models.BigIntegerField(null=True, blank=True)
    revised_product_description=models.TextField(max_length = 255)
    revised_unit_of_measure=models.TextField(max_length = 255)
    revised_quantity = models.DecimalField(db_column='revised_quantity', max_digits=20, decimal_places=10, null=True, blank=True)
    revised_phase_id=models.BigIntegerField(null=True, blank=True)
    revised_user_id =models.TextField(null=True,blank=True)
    revised_date = models.DateTimeField(null=True) 
    customer_ref_no = models.TextField(max_length = 255)



    class Meta:
        managed = False  # This prevents Django from trying to manage the table
        db_table = 'app_deliverynote_change_log'



################################################### Waste Transfer Note ##########################################################################

class WasteDisposal(models.Model):
    description = models.TextField(max_length=300)
    class Meta:
        managed = False
        db_table = 'waste_disposal'

    def __str__(self):
        return self.description


class WastePhase(models.Model):
    description = models.TextField(max_length=300)
    class Meta:
        managed = False
        db_table = 'waste_phase'

    def __str__(self):
        return self.description



class WasteTransferNote(models.Model):
    waste_tracking_note_code = models.TextField(db_column='waste_tracking_note_code', null=True, blank=True)
    waste_transfer_note_date = models.TextField(db_column='waste_transfer_note_date',max_length=300, null=True, blank=True)
    waste_transferor_name = models.TextField(db_column='waste_transferor_name',max_length=300, null=True, blank=True)
    waste_transferor_address = models.TextField(db_column='waste_transferor_address',max_length=300, null=True, blank=True)
    waste_transferor_postcode = models.TextField(db_column='waste_transferor_postcode',max_length=300, null=True, blank=True)
    waste_production_process = models.TextField(db_column='waste_production_process',max_length=300, null=True, blank=True)
    customer_person_name = models.TextField(db_column='customer_person_name',max_length=300, null=True, blank=True)
    ewc_code = models.TextField(db_column='ewc_code',max_length=300, null=True, blank=True)
    sic_code = models.TextField(db_column='sic_code',max_length=300, null=True, blank=True)
    waste_quantity = models.TextField(db_column='waste_quantity',max_length=300, null=True, blank=True)
    waste_destination_name = models.TextField(db_column='waste_destination_name',max_length=300, null=True, blank=True)
    waste_destination_address = models.TextField(db_column='waste_destination_address',max_length=300, null=True, blank=True)
    waste_destination_postcode = models.TextField(db_column='waste_destination_postcode',max_length=300, null=True, blank=True)
    waste_arrival_date = models.TextField(db_column='waste_arrival_date',max_length=300, null=True, blank=True)
    waste_arrival_time = models.TextField(db_column='waste_arrival_time',max_length=300, null=True, blank=True)
    destination_permit_no = models.TextField(db_column='destination_permit_no',max_length=300, null=True, blank=True)
    destination_exemption_no = models.TextField(db_column='destination_exemption_no',max_length=300, null=True, blank=True)
    waste_carrier_name = models.TextField(db_column='waste_carrier_name',max_length=300, null=True, blank=True)
    waste_carrier_address = models.TextField(db_column='waste_carrier_address',max_length=300, null=True, blank=True)
    waste_carrier_postcode = models.TextField(db_column='waste_carrier_postcode',max_length=300, null=True, blank=True)
    waste_carrier_license_no = models.TextField(db_column='waste_carrier_license_no',max_length=300, null=True, blank=True)
    vehicle_reg_no = models.TextField(db_column='vehicle_reg_no',max_length=300, null=True, blank=True)
    container_type = models.TextField(db_column='container_type',max_length=300, null=True, blank=True)
    container_size = models.TextField(db_column='container_size',max_length=300, null=True, blank=True)
    number_of_containers = models.TextField(db_column='number_of_containers',max_length=300, null=True, blank=True)
    waste_note_upload_date = models.DateTimeField(db_column='waste_note_upload_date', null=True, blank=True)
    waste_note_uploaded_by = models.TextField(db_column='waste_note_uploaded_by',max_length=300, null=True, blank=True)
    building_id = models.BigIntegerField(db_column='building_id', null=True, blank=True)
    doc_source= models.TextField(db_column='doc_source',max_length=300, null=True, blank=True)
    filename = models.TextField(db_column='filename',max_length=300, null=True, blank=True)
    customer_ref = models.TextField(db_column='customer_ref',max_length=300, null=True, blank=True)
    error_code = models.BigIntegerField(db_column='error_code', null=True, blank=True)
    approved_date = models.DateTimeField(db_column='approved_date', null=True, blank=True)
    approved_by = models.TextField(db_column='approved_by',max_length=300, null=True, blank=True)
    volume = models.FloatField(db_column='volume', null=True, blank=True)
    waste_disposal_code = models.ForeignKey(WasteDisposal,null=True,blank=True,on_delete=models.CASCADE,db_column='waste_disposal_code')
    waste_phase_code = models.ForeignKey(WastePhase,null=True,blank=True,on_delete=models.CASCADE,db_column='waste_phase_code')
    kgco2 = models.FloatField(db_column='kgco2', null=True, blank=True)
    destination_permit_issue_date = models.DateField(db_column='destination_permit_issue_date',max_length=300, null=True, blank=True)
    destination_permit_status = models.TextField(db_column='destination_permit_status',max_length=300, null=True, blank=True)
    waste_carrier_license_issue_date = models.DateField(db_column='waste_carrier_license_issue_date',max_length=300, null=True, blank=True)
    waste_carrier_license_expiry_date = models.DateField(db_column='waste_carrier_license_expiry_date',max_length=300, null=True, blank=True)


    class Meta:
        managed = False  # This prevents Django from trying to manage the table
        db_table = 'waste_transfer_note_data'



class WasteCarriersBrokersDealers(models.Model):
    waste_carrier_license_no = models.TextField(db_column='waste_carrier_license_no',max_length=300, null=True, blank=True)
    waste_carrier_name = models.TextField(db_column='waste_carrier_name',max_length=300, null=True, blank=True)
    company_no = models.TextField(db_column='company_no',max_length=300, null=True, blank=True)
    waste_carrier_license_issue_date = models.TextField(db_column='waste_carrier_license_issue_date',max_length=300, null=True, blank=True)
    waste_carrier_expiry_date = models.TextField(db_column='waste_carrier_expiry_date',max_length=300, null=True, blank=True)
    waste_carrier_address = models.TextField(db_column='waste_carrier_address',max_length=300, null=True, blank=True)
    waste_carrier_postcode = models.TextField(db_column='waste_carrier_postcode',max_length=300, null=True, blank=True)
    class Meta:
        managed = False
        db_table = 'waste_carriers_brokers_dealers'



class WasteExemptionCertificates(models.Model):
    waste_exemption_no= models.TextField(db_column='waste_exemption_no',max_length=300, null=True, blank=True)
    company_name= models.TextField(db_column='company_name',max_length=300, null=True, blank=True)
    company_address= models.TextField(db_column='company_address',max_length=300, null=True, blank=True)
    company_postcode= models.TextField(db_column='company_postcode',max_length=300, null=True, blank=True)
    waste_site_address= models.TextField(db_column='waste_site_address',max_length=300, null=True, blank=True)
    waste_site_postcode= models.TextField(db_column='waste_site_postcode',max_length=300, null=True, blank=True)
    exemption_types= models.TextField(db_column='exemption_types',max_length=300, null=True, blank=True)
    exemption_codes= models.TextField(db_column='exemption_codes',max_length=300, null=True, blank=True)
    issue_date= models.DateField(db_column='issue_date',max_length=300, null=True, blank=True)
    expiry_date= models.DateField(db_column='expiry_date',max_length=300, null=True, blank=True)
    
    class Meta:
        managed = False
        db_table = 'waste_exemption_certificates'


class WasteOperationsPermits(models.Model):
    waste_destination_permit_no= models.TextField(db_column='waste_destination_permit_no',max_length=300, null=True, blank=True)
    waste_management_license_no= models.TextField(db_column='waste_management_license_no',max_length=300, null=True, blank=True)
    pre_ea_permit_ref= models.TextField(db_column='pre_ea_permit_ref',max_length=300, null=True, blank=True)
    license_holder_name= models.TextField(db_column='license_holder_name',max_length=300, null=True, blank=True)
    license_holder_trading_name= models.TextField(db_column='license_holder_trading_name',max_length=300, null=True, blank=True)
    waste_destination_name= models.TextField(db_column='waste_destination_name',max_length=300, null=True, blank=True)
    waste_destination_type= models.TextField(db_column='waste_destination_type',max_length=300, null=True, blank=True)
    waste_destination_address= models.TextField(db_column='waste_destination_address',max_length=300, null=True, blank=True)
    waste_destination_postcode= models.TextField(db_column='waste_destination_postcode',max_length=300, null=True, blank=True)
    waste_destination_local_authority= models.TextField(db_column='waste_destination_local_authority',max_length=300, null=True, blank=True)
    waste_destination_permit_status= models.TextField(db_column='waste_destination_permit_status',max_length=300, null=True, blank=True)
    waste_destination_permit_issue_date= models.DateField(db_column='waste_destination_permit_issue_date',max_length=300, null=True, blank=True)
    waste_destination_permit_variation_date= models.DateField(db_column='waste_destination_permit_variation_date',max_length=300, null=True, blank=True)
    waste_destination_permit_transfer_date= models.DateField(db_column='waste_destination_permit_transfer_date',max_length=300, null=True, blank=True)
    waste_destination_permit_effective_date= models.DateField(db_column='waste_destination_permit_effective_date',max_length=300, null=True, blank=True)
    waste_destination_permit_surrendered_date= models.DateField(db_column='waste_destination_permit_surrendered_date',max_length=300, null=True, blank=True)
    waste_destination_permit_revoked_date= models.DateField(db_column='waste_destination_permit_revoked_date',max_length=300, null=True, blank=True)
    waste_destination_permit_suspended_date= models.DateField(db_column='waste_destination_permit_suspended_date',max_length=300, null=True, blank=True)
    
    class Meta:
        managed = False
        db_table = 'waste_operations_permits'


class WasteEWCCodes(models.Model):
    ewc_code = models.TextField(db_column='ewc_code',max_length=300, null=True, blank=True)
    description= models.TextField(db_column='description',max_length=300, null=True, blank=True)
    density_conversion_factor=models.FloatField(db_column='density_conversion_factor',max_length=300, null=True, blank=True)
    
    class Meta:
        managed = False
        db_table = 'waste_ewc_codes'

#########################################################################################################################