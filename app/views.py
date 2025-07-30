import csv
import io
import logging
import os
import re
from datetime import datetime, timedelta, date, time

import boto3
import requests
from dateutil.relativedelta import relativedelta
from dotenv import load_dotenv
from django import forms
from django.conf import settings
from django.db import IntegrityError, transaction
from django.db.models import (
    Case, Count, F, FloatField, IntegerField, OuterRef, Q, Subquery, Sum, Value, When, TextField, Min
)
from django.db.models.functions import Concat
from django.http import Http404, HttpResponse, JsonResponse
from django.urls import reverse_lazy
from django.utils import timezone
from django.utils.dateparse import parse_date
from django.utils.timezone import make_aware, now
from django.views.generic.edit import FormView
from rest_framework import filters, generics, mixins, status
from rest_framework.exceptions import ValidationError
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from django.conf import settings
from .models import *
from .serializers import *


# Load environment variables from .env file
load_dotenv()
    


############################################    COMMON ####################################
class CountryListCreateAPI(generics.ListCreateAPIView):
    queryset = Country.objects.all()
    serializer_class = CountrySerializer
    permission_classes = [IsAuthenticated]

class CountryRetrieveUpdateDestroyAPI(generics.RetrieveUpdateDestroyAPIView):
    queryset = Country.objects.all()
    serializer_class = CountrySerializer
    permission_classes = [IsAuthenticated]

# Region CRUD Views
class RegionListCreateAPI(generics.ListCreateAPIView):
    serializer_class = RegionSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = Region.objects.all()
        country_id = self.request.query_params.get('country_id')
        if country_id is not None:
            queryset = queryset.filter(country_id=country_id)
        return queryset

class RegionRetrieveUpdateDestroyAPI(generics.RetrieveUpdateDestroyAPIView):
    queryset = Region.objects.all()
    serializer_class = RegionSerializer
    permission_classes = [IsAuthenticated]

# City CRUD Views
class CityListCreateAPI(generics.ListCreateAPIView):
    serializer_class = CitySerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = City.objects.all()
        region_id = self.request.query_params.get('region_id')
        if region_id is not None:
            queryset = queryset.filter(region_id=region_id)
        return queryset

class CityRetrieveUpdateDestroyAPI(generics.RetrieveUpdateDestroyAPIView):
    queryset = City.objects.all()
    serializer_class = CitySerializer
    permission_classes = [IsAuthenticated]

# Building CRUD Views
class BuildingListCreateAPI(generics.ListCreateAPIView):
    serializer_class = BuildingSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = Building.objects.all()
        city_id = self.request.query_params.get('city_id')
        if city_id is not None:
            queryset = queryset.filter(city_id=city_id)
        return queryset

class BuildingRetrieveUpdateDestroyAPI(generics.RetrieveUpdateDestroyAPIView):
    queryset = Building.objects.all()
    serializer_class = BuildingSerializer
    permission_classes = [IsAuthenticated]




#################################   AUTHENTICATION ##############################

class UserSignUpAPI(generics.CreateAPIView):
    queryset = CustomUser.objects.all()
    serializer_class = UserSerializer

    def perform_create(self, serializer):
        user = serializer.save()
        client = boto3.client('cognito-idp', region_name=settings.AWS_COGNITO_REGION)
        
        try:
            response = client.sign_up(
                ClientId=settings.AWS_COGNITO_APP_CLIENT_ID,
                Username=user.email,  # Using email as the username
                Password=serializer.validated_data['password'],
                UserAttributes=[
                    {'Name': 'email', 'Value': user.email}
                    # Remove email_verified here, as Cognito will handle verification
                ]
            )
            user.cognito_sub = response['UserSub']
            user.save()
        except client.exceptions.UsernameExistsException:
            raise ValueError("Email already exists in Cognito")
        
#User Details api
class UserDetailAPI(generics.RetrieveUpdateDestroyAPIView):
    queryset = CustomUser.objects.all()
    serializer_class = UserSerializer
    lookup_field = 'id'  # Use 'id' as the primary key for lookup

    def get_object(self):
        user = super().get_object()
        # Optionally sync with Cognito if needed
        self.sync_with_cognito(user)
        return user

    def sync_with_cognito(self, user):
        client = boto3.client('cognito-idp', region_name=settings.AWS_COGNITO_REGION)
        try:
            response = client.admin_get_user(
                UserPoolId=settings.AWS_COGNITO_USER_POOL_ID,
                Username=user.email
            )
            # Update user attributes from Cognito to Django if necessary
            for attribute in response['UserAttributes']:
                if attribute['Name'] == 'email_verified':
                    user.email_verified = attribute['Value'] == 'true'
            user.save()
        except client.exceptions.UserNotFoundException:
            pass

    def perform_update(self, serializer):
        user = serializer.save()
        self.update_cognito_user(user)

    def update_cognito_user(self, user):
        client = boto3.client('cognito-idp', region_name=settings.AWS_COGNITO_REGION)
        attributes = [
            {'Name': 'email', 'Value': user.email},
            {'Name': 'email_verified', 'Value': 'true' if user.email_verified else 'false'}
        ]
        try:
            client.admin_update_user_attributes(
                UserPoolId=settings.AWS_COGNITO_USER_POOL_ID,
                Username=user.email,
                UserAttributes=attributes
            )
        except client.exceptions.UserNotFoundException:
            raise ValueError("User not found in Cognito")

    def perform_destroy(self, instance):
        self.delete_cognito_user(instance)
        super().perform_destroy(instance)

    def delete_cognito_user(self, user):
        client = boto3.client('cognito-idp', region_name=settings.AWS_COGNITO_REGION)
        try:
            client.admin_delete_user(
                UserPoolId=settings.AWS_COGNITO_USER_POOL_ID,
                Username=user.email
            )
        except client.exceptions.UserNotFoundException:
            pass



# Verify Email API
class VerifyEmailAPI(APIView):
    serializer_class = VerifyEmailSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)

        email = serializer.validated_data['email']
        otp = serializer.validated_data['otp']

        client = boto3.client('cognito-idp', region_name=settings.AWS_COGNITO_REGION)
        try:
            # Confirm the user's email verification in Cognito
            client.confirm_sign_up(
                ClientId=settings.AWS_COGNITO_APP_CLIENT_ID,
                Username=email,
                ConfirmationCode=otp
            )

            # Update email_verified field in Django's database
            user = CustomUser.objects.filter(email=email).first()
            if user:
                user.email_verified = True
                user.save()

            return Response({"message": "Email verified successfully"}, status=status.HTTP_200_OK)

        except client.exceptions.CodeMismatchException:
            return Response({"error": "Invalid OTP"}, status=status.HTTP_400_BAD_REQUEST)
        except client.exceptions.UserNotFoundException:
            return Response({"error": "User not found"}, status=status.HTTP_404_NOT_FOUND)

        
class ResendConfirmationCodeAPI(generics.CreateAPIView):
    """
    Resend the confirmation code to the user's email if they haven't verified their email.
    """
    serializer_class = ResendCodeSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        email = serializer.validated_data['email']
        client = boto3.client('cognito-idp', region_name=settings.AWS_COGNITO_REGION)
        
        try:
            # Resend confirmation code via Cognito
            client.resend_confirmation_code(
                ClientId=settings.AWS_COGNITO_APP_CLIENT_ID,
                Username=email
            )
            return Response({"message": "Confirmation code resent successfully"}, status=status.HTTP_200_OK)

        except client.exceptions.UserNotFoundException:
            return Response({"error": "User not found"}, status=status.HTTP_404_NOT_FOUND)
        except client.exceptions.InvalidParameterException as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        



# Login API view
class LoginAPI(generics.CreateAPIView):
    """
    Authenticate the user using AWS Cognito and return tokens if successful.
    """
    serializer_class = LoginSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        email = serializer.validated_data['email']
        password = serializer.validated_data['password']
        client = boto3.client('cognito-idp', region_name=settings.AWS_COGNITO_REGION)

        try:
            # Authenticate the user using AWS Cognito
            response = client.initiate_auth(
                ClientId=settings.AWS_COGNITO_APP_CLIENT_ID,
                AuthFlow='USER_PASSWORD_AUTH',
                AuthParameters={
                    'USERNAME': email,
                    'PASSWORD': password
                }
            )
            # Return tokens if authentication is successful
            return Response({
                "message": "Login successful",
                "access_token": response['AuthenticationResult']['AccessToken'],
                "id_token": response['AuthenticationResult']['IdToken'],
                "refresh_token": response['AuthenticationResult']['RefreshToken']
            }, status=status.HTTP_200_OK)

        except client.exceptions.NotAuthorizedException:
            return Response({"error": "Invalid credentials"}, status=status.HTTP_401_UNAUTHORIZED)
        except client.exceptions.UserNotFoundException:
            return Response({"error": "User not found"}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        

class ListUsersAPI(APIView):
    """
    Retrieve a list of all users in the AWS Cognito User Pool,
    with additional fields from Django database.
    """
    def get(self, request, *args, **kwargs):
        client = boto3.client('cognito-idp', region_name=settings.AWS_COGNITO_REGION)
        try:
            # Use list_users to fetch all users in the user pool
            response = client.list_users(
                UserPoolId=settings.AWS_COGNITO_USER_POOL_ID,
                Limit=60  # Adjust the limit if needed
            )
            
            users = []
            for user in response['Users']:
                email = next((attr['Value'] for attr in user['Attributes'] if attr['Name'] == 'email'), None)
                email_verified = any(attr['Value'] == 'true' for attr in user['Attributes'] if attr['Name'] == 'email_verified')
                
                # Retrieve additional fields from Django database if they exist
                try:
                    custom_user = CustomUser.objects.get(email=email)
                    user_data = {
                        'id': custom_user.id,
                        'email': email,
                        
                        'email_verified': email_verified
                    }
                except CustomUser.DoesNotExist:
                    # If user details don't exist in Django, default values
                    user_data = {
                        'id': None,
                        'email': email,
                        'email_verified': email_verified
                    }
                
                users.append(user_data)
            
            serializer = UserListSerializer(users, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)

        except client.exceptions.ResourceNotFoundException:
            return Response({"error": "User pool not found"}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        

############################################  APP DELIVERY NOTE BEST MATCH INVOICE ##############################################################

logger = logging.getLogger(__name__)

class BestMatchAPIView(generics.GenericAPIView,
                       mixins.ListModelMixin,
                       mixins.CreateModelMixin,
                       mixins.RetrieveModelMixin,
                       mixins.UpdateModelMixin,
                       mixins.DestroyModelMixin):
    queryset = BestMatch.objects.all()
    serializer_class = BestMatchSerializer
    lookup_field = 'pk'

    # External API URL and Authorization
    API_BASE_URL =  os.getenv("API_BASE_URL")
    API_URL = os.getenv("API_BASE_URL")+"/get_best_match/"
    API_HEADERS = {
        "Authorization": "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbl90eXBlIjoiYWNjZXNzIiwiZXhwIjoxNzM3NzE1OTM3LCJpYXQiOjE3Mzc2Mjk1MzcsImp0aSI6ImFjNDNlMjIzNzM1YzQ0MzFhNGNhOTdmYTk0ZjBlNzcyIiwidXNlcl9pZCI6NjYzMX0.oOKQyBPumcMZrjMqlAgQiXPzYKCM40eQiPCItsfl70I"
    }
    TOKEN_API_HEADERS = {
         "Authorization": "Bearer "+os.getenv("DEVELOPER_TOKEN")
    }
    
    @classmethod
    def access_token(self):
        try:
            
            response = requests.get(
                self.API_BASE_URL + "/token/getapitoken/",
                headers={
                     "Authorization": "Bearer " + os.getenv("DEVELOPER_TOKEN")
                    }
                )
            
            
            if response.status_code == 200:
                current_time = datetime.now()
                current_time_aware = timezone.make_aware(current_time, timezone.get_current_timezone())
                expiration_time = current_time_aware + timedelta(hours=24)
                token_data = response.json()
                token = token_data.get("api_token")
                Refresh_Token = token_data.get("refresh_token")


                if BestAPIToken.objects.exists(): 
                    record=BestAPIToken.objects.first()
                    record.TokenName="BEST ACCESS TOKEN"
                    record.TokenValue=token
                    record.RefreshToken=Refresh_Token,
                    record.TokenExpiryTime=expiration_time

                    record.save()

                else:
                
                    try:
                        BestAPIToken.objects.create(
                        TokenName="BEST ACCESS TOKEN",
                        TokenValue=token,
                        RefreshToken=Refresh_Token,
                        TokenExpiryTime=expiration_time
                        )
                    except IntegrityError as e:
                        logger.error(f"IntegrityError occurred: {e}")
                    except Exception as e:
                        logger.error(f"An error occurred while creating the token: {e}")       



                return token
        except:
            logger.error("Error occured While Generating Token")

    def is_token_expired(self,tokenexpirytime):
        now = timezone.now()
        if tokenexpirytime is not None:
            if tokenexpirytime is None:
                tokenexpirytime = timezone.make_aware(tokenexpirytime)
            if tokenexpirytime < now:
                return False  # Token has expired
            else:
                return True  # Token is still valid
        else:
            return False
    @classmethod
    def refresh_token(self):
        try:
            if BestAPIToken.objects.exists():
                    tokens = BestAPIToken.objects.all()
                    for token in tokens:
                        refresh_token = token.RefreshToken
            api_payload={
                "refresh":refresh_token
            }
            response = requests.post(
                self.API_BASE_URL + "/token/refresh/",
                json=api_payload
                )
            if response.status_code == 200:
                current_time = datetime.now()
                current_time_aware = timezone.make_aware(current_time, timezone.get_current_timezone())
                expiration_time = current_time_aware + timedelta(hours=24)
                token_data = response.json()
                token = token_data.get("api_token")
                Refresh_Token = token_data.get("refresh_token")

                record=BestAPIToken.objects.first()
                record.TokenName="REFRESHED BEST ACCESS TOKEN"
                record.TokenValue=token
                record.RefreshToken=Refresh_Token,
                record.TokenExpiryTime=expiration_time

                record.save()
                return token
        except:
            logger.error("Error occured While Generating Token")

    def convert_date_format(self, date_str):
        """Convert date from DD/MM/YYYY to YYYY-MM-DD format."""
        try:
            return datetime.strptime(date_str, "%d/%m/%Y").strftime("%Y-%m-%d")
        except ValueError:
            logger.error(f"Invalid date format: {date_str}")
            return None




    def process_unprocessed_records(self):
        unprocessed_records = BestMatch.objects.filter(Q(processed=False, approved=False, error_code=0) | Q(processed=False, approved=True, error_code=0) | Q(processed=True, approved=True, error_code=0))

        logger.info(f"Found {unprocessed_records.count()} unprocessed records")

        for record in unprocessed_records:
            if record.delivery_note_date:
                # Convert delivery_note_date to string before passing to convert_date_format
                converted_date = self.convert_date_format(record.delivery_note_date.strftime("%d/%m/%Y"))
                if converted_date:
                    record.delivery_note_date = converted_date
                else:
                    logger.error(f"Skipping record ID {record.id} due to invalid date format.")
                    continue
            product_desc = record.revised_product_description if record.revised_product_description else record.product_description
            api_payload = {
                "input_items": [product_desc + " " + record.delivery_country],
                "include_product_data": True,
                "include_material_data": True
            }
            try:
                if BestAPIToken.objects.exists():
                    tokens = BestAPIToken.objects.all()
                    for token in tokens:
                        if self.is_token_expired(token.TokenExpiryTime):
                            access_token = token.TokenValue
                        else:
                            access_token= self.access_token()
                else:
                    access_token=self.access_token()
                response = requests.post(self.API_URL, json=api_payload, headers={
                            "Authorization": "Bearer " + access_token
                            })
                logger.info(f"API response status code: {response.status_code}")

                if response.status_code == 200:
                    api_data = response.json()
                    # print("api_data",api_data)
                    quality_info = api_data.get("results",{}).get(product_desc + " " + record.delivery_country, {}).get("quantity_info", {})
                    product_info = api_data.get("results.best_product", {}).get(product_desc + " " + record.delivery_country, {})
                    for key, item in api_data.get('results', {}).items():
                        best_product = item.get('best_product', {})
                        best_product[key] = {
                            'product_name': best_product.get('product_name'),
                            'company_name': best_product.get('product_company_name'),
                            'manufacturing_emissions_intensity': best_product.get('product_manufacturing_emissions_intensity_factor'),
                            'manufacturing_emissions_per_kg': best_product.get('product_manufacturing_emissions_per_kg'),
                            'product_url': best_product.get('product_url'),
                            'match_score': best_product.get('product_match_score')
                        }

                        best_material = item.get('best_material',{})
                        best_material[key] = {
                            'material_name': best_material.get('material_name'),
                            'material_manufacturing_emissions_intensity_factor':  best_material.get('material_manufacturing_emissions_intensity_factor'),
                            'material_manufacturing_emissions_intensity_unit':best_material.get('material_manufacturing_emissions_intensity_unit'),
                            'material_data_source':best_material.get('material_data_source'),
                            'material_id':best_material.get('material_id'),
                            'material_match_score':best_material.get('material_match_score')

                        }


                        materialName = item.get('classification',{})
                        materialName[key] = {
                            'material_name': materialName.get('material_type')
                        }
                    material_facts = api_data.get("results",{}).get(product_desc + " " + record.delivery_country, {}).get("best_product", {}).get("product_data", {}).get("material_facts", {})
                    scaling_factors = material_facts.get("scaling_factors", {})
                    user_id = record.revised_user_id if record.revised_user_id else record.user_id

                    result=Users.objects.filter(User_ID=user_id).first()
                    if result is not None:
                        customerref=result.customer_ref
                    else:
                        customerref=""
                    unit_of_measure = record.revised_unit_of_measure if record.revised_unit_of_measure else record.unit_of_measure
                    record.product_name = best_product.get("product_name") 
                    record.material_name = materialName.get("material_type")
                    record.product_company_name = best_product.get("product_company_name")
                    record.product_match_score = best_product.get("product_match_score")
                    record.global_warming_potential_fossil = material_facts.get("global_warming_potential_fossil", {}).get("A1A2A3")
                    record.declared_unit = material_facts.get("declared_unit")
                    record.scaling_factor = scaling_factors.get(record.unit_of_measure, {}).get("value")
                    if record.revised_product_description:
                        record.scaling_factor = scaling_factors.get(record.revised_unit_of_measure, {}).get("value")
                    else:
                        record.scaling_factor = scaling_factors.get(record.unit_of_measure, {}).get("value")
                    if record.scaling_factor is None or not record.scaling_factor:
                            error_code = 4

                    print(record.scaling_factor)
                    record.data_source = material_facts.get("data_source")
                    record.processed = True
                    record.processed_timestamp = timezone.now() 
                    record.customer_ref=customerref
                    record.package_unit_item_height = best_material.get('material_data',{}).get('thickness',{}) or None
                    record.density =  best_product.get('product_data',{}).get('density') or None
                    record.package_unit_item_dimension_uom = best_material.get('material_data',{}).get('length_units') or None
                    record.mass_per_declared_unit =  best_product.get('product_data',{}).get('material_facts',{}).get('mass_per_declared_unit',{}) or None
                    record.linear_density = best_product.get('product_data',{}).get('linear_density',{}) or None
                    if quality_info :
                        record.package_type = quality_info.get('package', {}).get('type') or None
                        record.package_unit_type =  quality_info.get('item_details', {}).get('base_unit') or None
                        record.package_unit_item_count = quality_info.get('package', {}).get('item_count') or None
                        record.package_unit_item_length = quality_info.get('item_details', {}).get('length') or None
                        record.package_unit_item_width = quality_info.get('item_details', {}).get('width') or None
                        record.package_unit_item_dimension_uom = quality_info.get('item_details',{}).get('length_units') or None
                        record.package_unit_item_area = quality_info.get('item_details', {}).get('area') or None
                        record.package_unit_item_area_uom = quality_info.get('item_details', {}).get('area_units') or None
                        record.package_unit_item_volume = None
                        record.package_unit_item_volume_uom = None
                        if(record.package_unit_item_height is None):
                            record.package_unit_item_height = quality_info.get('item_details', {}).get('thickness') or None

                    # break


                    


                    gia_values =  Building.objects.extra(select={'gia': 'gia'}).filter(id=record.building_id).values_list('gia', flat=True).first()
                    #comment to check scaling facor

                    error_code = 0  # Default to 0 (no error)
                    valid_units = Unit_of_Measure.objects.values_list('name', flat=True)
                    valid_units_lower = {unit.lower() for unit in valid_units}
                    print(record.id,record.scaling_factor)
                   
                    try:
                        record.quantity = float(record.revised_quantity) if record.revised_quantity is not None else (float(record.quantity) if record.quantity else None)
                    except ValueError:
                        error_code = 2  
                    
                    # # Calculate kgco2_per_m2 and assign it to kgco2
                    if record.global_warming_potential_fossil and record.scaling_factor and record.quantity:
                        kgco2_per_m2 = (float(record.global_warming_potential_fossil) / float(record.scaling_factor)) * (float(record.quantity) / gia_values) # (gia) 5000 should come from app_buildingtable
                        record.kgco2 = kgco2_per_m2
                        record.exception=""
                    else:
                        record.kgco2 = 0
                        record.exception="Scaling factor is missing"
                        record.scaling_factor=0
                        error_code = 4
                    try:
                        record.error_code=error_code
                        record.approved = False
                        print(error_code)
                        record.save()
                    except Exception as e:
                        logger.info(f"Errored ocuured for ID {record.id} The error is {e}.")
                        
                    logger.info(f"Record with ID {record.id} has been updated and saved check.")
                

                    # Fetch Phase instance
                    try:
                        phase_id = record.revised_phase_id if record.revised_phase_id else record.phase_id
                        phase_instance = Phase.objects.get(pk=phase_id) if phase_id else None
                    except Phase.DoesNotExist:
                        phase_instance = None
                        logger.error(f"Phase with ID {phase_id} does not exist for record ID {record.id}")

                    # Copy data to InvoiceData model
                    if record.scaling_factor != 0:
                        InvoiceData.objects.create(
                            delivery_note_ref_no=record.delivery_note_ref_no,
                            supplier_name=record.supplier_name,
                            data_source=record.data_source,
                            product_description=product_desc,
                            material_name=record.material_name,
                            entry_time=record.entry_time.date() if record.entry_time else timezone.now().date(),
                            quantity=record.quantity,
                            unit_of_measure=record.unit_of_measure,
                            phase_name=phase_instance,  # Assign the Phase instance
                            kgco2=record.kgco2,
                            product_manufacturing_company=record.product_company_name,
                        )

                        logger.info(f"Data copied to InvoiceData for record ID {record.id}")
                else:
                    error_code=1
                    record.error_code=error_code
                    record.approved = False
                    record.save()
                    logger.error(f"API request failed for record ID {record.id}: {response.status_code} - {response.text}")

            except requests.RequestException as e:
                error_code=1
                record.error_code=error_code
                record.approved =False
                record.save()
                logger.error(f"RequestException for record ID {record.id}: {e}")

    def get(self, request, pk=None):
        self.process_unprocessed_records()
        if pk:
            return self.retrieve(request, pk)
        return self.list(request)

    def post(self, request):
        self.process_unprocessed_records()
        return Response({"message": "All unprocessed records have been processed."}, status=status.HTTP_200_OK)

    def put(self, request, pk=None):
        return self.update(request, pk)

    def delete(self, request, pk=None):
        return self.destroy(request, pk)





class CustomSearchFilter(filters.SearchFilter):
    def get_search_terms(self, request):
        """
        Override get_search_terms to split the query into individual keywords
        based on commas and strip spaces.
        """
        params = request.query_params.get(self.search_param, '')
        terms = [param.strip() for param in params.split(',') if param.strip()]
        logger.debug(f"Search terms: {terms}")
        return terms

    def filter_queryset(self, request, queryset, view):
        search_terms = self.get_search_terms(request)
        if not search_terms:
            return queryset

        # Prepare queries for each term across all specified search fields
        combined_queries = Q()
        for search_term in search_terms:
            # Initialize a query for each term
            query = Q()
            for search_field in self.get_search_fields(view, request):
                # Construct query for each field using 'icontains' for case-insensitive partial matches
                condition = {f"{search_field}__icontains": search_term}
                query |= Q(**condition)
            combined_queries |= query  # Use OR to combine queries for different terms
            logger.debug(f"Building query for term '{search_term}': {query}")

        final_queryset = queryset.filter(combined_queries)
        logger.debug(f"Final queryset count: {final_queryset.count()}")
        return final_queryset


class  InvoiceDataView(generics.ListAPIView):
    # queryset = InvoiceData.objects.all()
    
    queryset = InvoiceData.objects.select_related('phase_name').all()
    serializer_class = InvoiceDataSerializer
    filter_backends = (CustomSearchFilter, OrderingFilter)
    search_fields = ('country_name', 'region_name', 'city_name', 'building_name', 'supplier_name','phase_name__name', 'data_source', 'entry_time', 'product_description', 'material_name')

    def list(self, request, *args, **kwargs):
        email = request.query_params.get('email', None)
        result=Users.objects.filter(User_ID=email).first()
        customerref=result.customer_ref
        queryset = self.filter_queryset(self.get_queryset())

        if customerref:
            queryset = queryset.filter(customer_ref=customerref)

        # Aggregate overall totals
        aggregate_data = queryset.aggregate(
            total_kgco2=Sum('kgco2')
        )

        # Aggregate totals by material name (corrected)
        material_name_aggregates = queryset.values('material_name').annotate(
            total_kgco2=Sum('kgco2')
        ).order_by('material_name')

        # Aggregate carbon and kgco2 based on the status of 'Estimate' and 'Actual'
        carbon_status_sums = queryset.aggregate(
            estimate_kgco2=Sum(Case(
                When(data_source='EPD', then='kgco2'),
                output_field=IntegerField(),
            )),
            actual_kgco2=Sum(Case(
                When(data_source='Average', then='kgco2'),
                output_field=IntegerField(),
            )),
        )

        # Calculate percentages if total_kgco2 is not zero
        total_kgco2 = aggregate_data['total_kgco2'] or 0  # Avoid division by zero
        if total_kgco2 > 0:
            estimate_percentage = (carbon_status_sums['estimate_kgco2'] or 0) / total_kgco2 * 100
            actual_percentage = (carbon_status_sums['actual_kgco2'] or 0) / total_kgco2 * 100
        else:
            estimate_percentage = 0
            actual_percentage = 0

        # Aggregate by region
        region_aggregates = queryset.values('region_name').annotate(
            total_kgco2=Sum('kgco2')
        ).order_by('region_name')

        # Aggregate by city
        city_aggregates = queryset.values('city_name').annotate(
            total_kgco2=Sum('kgco2')
        ).order_by('city_name')

        # Aggregate by building name
        building_aggregates = queryset.values('building_name').annotate(
            total_kgco2=Sum('kgco2')
        ).order_by('building_name')

        # Nested aggregation structure
        nested_structure = []
        for region in queryset.values('region_name').distinct():
            region_queryset = queryset.filter(region_name=region['region_name'])
            region_total = region_queryset.aggregate(
                total_kgco2=Sum('kgco2')
            )
            
            cities_data = []
            for city in region_queryset.values('city_name').distinct():
                city_queryset = region_queryset.filter(city_name=city['city_name'])
                city_total = city_queryset.aggregate(
                    total_kgco2=Sum('kgco2')
                )
                
                buildings_data = []
                for building in city_queryset.values('building_name').distinct():
                    building_queryset = city_queryset.filter(building_name=building['building_name'])
                    building_total = building_queryset.aggregate(
                        total_kgco2=Sum('kgco2')
                    )
                    
                    phases_data = building_queryset.values('phase_name__name').annotate(
                        total_kgco2=Sum('kgco2')
                    ).order_by('phase_name__name')
                    
                    buildings_data.append({
                        'building_name': building['building_name'],
                        'total_kgco2': building_total['total_kgco2'],
                        'phases': list(phases_data)
                    })
                
                cities_data.append({
                    'city_name': city['city_name'],
                    'total_kgco2': city_total['total_kgco2'],
                    'buildings': buildings_data
                })
            
            nested_structure.append({
                'region_name': region['region_name'],
                'total_kgco2': region_total['total_kgco2'],
                'cities': cities_data
            })

        serializer = self.get_serializer(queryset, many=True)
        return Response({
            'results': serializer.data,
            'overall_aggregates': aggregate_data,
            'material_name_aggregates': list(material_name_aggregates),
            'carbon_status_totals': {
                'estimate': {
                    'total_kgco2': carbon_status_sums['estimate_kgco2'] or 0
                },
                'actual': {
                    'total_kgco2': carbon_status_sums['actual_kgco2'] or 0
                }
            },
            'carbon_status_percentage': {
                'EPD': estimate_percentage,
                'average': actual_percentage,
            },
            'region_aggregates': list(region_aggregates),
            'city_aggregates': list(city_aggregates),
            'building_aggregates': list(building_aggregates),
            'nested_structure': nested_structure  # Nested structure by region, city, building, and phases
        })


######################## Works with Token ########################################
# class  InvoiceDataView(generics.ListAPIView):
#     # queryset = InvoiceData.objects.all()
    
#     queryset = InvoiceData.objects.select_related('phase_name').all()
#     serializer_class = InvoiceDataSerializer
#     filter_backends = (CustomSearchFilter, OrderingFilter)
#     search_fields = ('country_name', 'region_name', 'city_name', 'building_name', 'supplier_name','phase_name__name', 'data_source', 'entry_time', 'product_description', 'material_name')

#     def list(self, request, *args, **kwargs):
#         # Get the logged-in user's email
#         user_email = self.request.user.email

#         # Fetch the corresponding customer_ref from the Users table
#         try:
#             user = Users.objects.get(User_ID=user_email)
#         except Users.DoesNotExist:
#             raise Http404("User not found in Users table")

#         # Initial filter by customer_ref
#         queryset = InvoiceData.objects.filter(customer_ref=user.customer_ref)

#         # Aggregate overall totals
#         aggregate_data = queryset.aggregate(
#             total_kgco2=Sum('kgco2')
#         )

#         # Aggregate totals by material name (corrected)
#         material_name_aggregates = queryset.values('material_name').annotate(
#             total_kgco2=Sum('kgco2')
#         ).order_by('material_name')

#         # Aggregate carbon and kgco2 based on the status of 'Estimate' and 'Actual'
#         carbon_status_sums = queryset.aggregate(
#             estimate_kgco2=Sum(Case(
#                 When(data_source='EPD', then='kgco2'),
#                 output_field=IntegerField(),
#             )),
#             actual_kgco2=Sum(Case(
#                 When(data_source='Average', then='kgco2'),
#                 output_field=IntegerField(),
#             )),
#         )

#         # Calculate percentages if total_kgco2 is not zero
#         total_kgco2 = aggregate_data['total_kgco2'] or 0  # Avoid division by zero
#         if total_kgco2 > 0:
#             estimate_percentage = (carbon_status_sums['estimate_kgco2'] or 0) / total_kgco2 * 100
#             actual_percentage = (carbon_status_sums['actual_kgco2'] or 0) / total_kgco2 * 100
#         else:
#             estimate_percentage = 0
#             actual_percentage = 0

#         # Aggregate by region
#         region_aggregates = queryset.values('region_name').annotate(
#             total_kgco2=Sum('kgco2')
#         ).order_by('region_name')

#         # Aggregate by city
#         city_aggregates = queryset.values('city_name').annotate(
#             total_kgco2=Sum('kgco2')
#         ).order_by('city_name')

#         # Aggregate by building name
#         building_aggregates = queryset.values('building_name').annotate(
#             total_kgco2=Sum('kgco2')
#         ).order_by('building_name')

#         # Nested aggregation structure
#         nested_structure = []
#         for region in queryset.values('region_name').distinct():
#             region_queryset = queryset.filter(region_name=region['region_name'])
#             region_total = region_queryset.aggregate(
#                 total_kgco2=Sum('kgco2')
#             )
            
#             cities_data = []
#             for city in region_queryset.values('city_name').distinct():
#                 city_queryset = region_queryset.filter(city_name=city['city_name'])
#                 city_total = city_queryset.aggregate(
#                     total_kgco2=Sum('kgco2')
#                 )
                
#                 buildings_data = []
#                 for building in city_queryset.values('building_name').distinct():
#                     building_queryset = city_queryset.filter(building_name=building['building_name'])
#                     building_total = building_queryset.aggregate(
#                         total_kgco2=Sum('kgco2')
#                     )
                    
#                     phases_data = building_queryset.values('phase_name__name').annotate(
#                         total_kgco2=Sum('kgco2')
#                     ).order_by('phase_name__name')
                    
#                     buildings_data.append({
#                         'building_name': building['building_name'],
#                         'total_kgco2': building_total['total_kgco2'],
#                         'phases': list(phases_data)
#                     })
                
#                 cities_data.append({
#                     'city_name': city['city_name'],
#                     'total_kgco2': city_total['total_kgco2'],
#                     'buildings': buildings_data
#                 })
            
#             nested_structure.append({
#                 'region_name': region['region_name'],
#                 'total_kgco2': region_total['total_kgco2'],
#                 'cities': cities_data
#             })

#         serializer = self.get_serializer(queryset, many=True)
#         return Response({
#             'results': serializer.data,
#             'overall_aggregates': aggregate_data,
#             'material_name_aggregates': list(material_name_aggregates),
#             'carbon_status_totals': {
#                 'estimate': {
#                     'total_kgco2': carbon_status_sums['estimate_kgco2'] or 0
#                 },
#                 'actual': {
#                     'total_kgco2': carbon_status_sums['actual_kgco2'] or 0
#                 }
#             },
#             'carbon_status_percentage': {
#                 'EPD': estimate_percentage,
#                 'average': actual_percentage,
#             },
#             'region_aggregates': list(region_aggregates),
#             'city_aggregates': list(city_aggregates),
#             'building_aggregates': list(building_aggregates),
#             'nested_structure': nested_structure  # Nested structure by region, city, building, and phases
#         })


class DesignDataAPIView(generics.GenericAPIView, mixins.ListModelMixin, mixins.CreateModelMixin,
                        mixins.UpdateModelMixin, mixins.RetrieveModelMixin, mixins.DestroyModelMixin):

    queryset = DesignData.objects.all().order_by('id')
    serializer_class = DesignDataSerializer

    def get_object(self, id):
        try:
            return DesignData.objects.get(id=id)
        except DesignData.DoesNotExist:
            raise Http404

    def get(self, request, id=None, *args, **kwargs):
        email = request.query_params.get('email', None)
        resultdata = {}

        if email:
            result = Users.objects.filter(User_ID=email).first()
            customerref = result.customer_ref

        if id:
            id_obj = self.get_object(id)
            serializer = DesignDataSerializer(id_obj)
            return Response(serializer.data)

        else:
            alldata = DesignData.objects.filter(customer_ref=customerref)

            final_data = []

            # Initialize all totals
            totals = {
                "substructure_total": 0,
                "superstructure_total": 0,
                "facade_total": 0,
                "internal_walls_partitions_total": 0,
                "internal_finishes_total": 0,
                "ff_fe_total": 0,
                "frame_total": 0,
                "upper_floors_total": 0,
                "roofs_total": 0,
                "stairs_and_ramps_total": 0,
                "external_walls_total": 0,
                "windows_and_external_walls_total": 0,
                "internal_doors_total": 0,
                "wall_finishes_total": 0,
                "floor_finishes_total": 0,
                "ceiling_finishes_total": 0,
            }

            for data in alldata:
                try:
                    building = Building.objects.get(id=data.building_id)
                    city_name = building.city.name
                    region_name = Region.objects.get(id=building.region_id).name
                    country_name = Country.objects.get(id=building.country_id).name

                    # Update totals with null-safety
                    totals["substructure_total"] += data.substructure or 0
                    totals["superstructure_total"] += data.superstructure or 0
                    totals["facade_total"] += data.façade or 0
                    totals["internal_walls_partitions_total"] += data.internal_walls_partitions or 0
                    totals["internal_finishes_total"] += data.internal_finishes or 0
                    totals["ff_fe_total"] += data.ff_fe or 0
                    totals["frame_total"] += data.frame or 0
                    totals["upper_floors_total"] += data.upper_floors or 0
                    totals["roofs_total"] += data.roofs or 0
                    totals["stairs_and_ramps_total"] += data.stairs_and_ramps or 0
                    totals["external_walls_total"] += data.external_walls or 0
                    totals["windows_and_external_walls_total"] += data.windows_and_external_walls or 0
                    totals["internal_doors_total"] += data.internal_doors or 0
                    totals["wall_finishes_total"] += data.wall_finishes or 0
                    totals["floor_finishes_total"] += data.floor_finishes or 0
                    totals["ceiling_finishes_total"] += data.ceiling_finishes or 0

                    total = (
                        (data.substructure or 0) +
                        (data.superstructure or 0) +
                        (data.façade or 0) +
                        (data.internal_walls_partitions or 0) +
                        (data.internal_finishes or 0) +
                        (data.ff_fe or 0)
                    )

                    total_new = (
                        (data.substructure or 0) +
                        (data.internal_walls_partitions or 0) +
                        (data.ff_fe or 0) +
                        (data.frame or 0) +
                        (data.upper_floors or 0) +
                        (data.roofs or 0) +
                        (data.stairs_and_ramps or 0) +
                        (data.external_walls or 0) +
                        (data.windows_and_external_walls or 0) +
                        (data.internal_doors or 0) +
                        (data.wall_finishes or 0) +
                        (data.floor_finishes or 0) +
                        (data.ceiling_finishes or 0)
                    )

                    final_data.append({
                        "id": data.id,
                        "region": region_name,
                        "city": city_name,
                        "country": country_name,
                        "building_name": data.building_name,
                        "substructure": data.substructure,
                        "superstructure": data.superstructure,
                        "façade": data.façade,
                        "internal_walls_partitions": data.internal_walls_partitions,
                        "internal_finishes": data.internal_finishes,
                        "ff_fe": data.ff_fe,
                        "frame": data.frame,
                        "upper_floors": data.upper_floors,
                        "roofs": data.roofs,
                        "stairs_and_ramps": data.stairs_and_ramps,
                        "external_walls": data.external_walls,
                        "windows_and_external_walls": data.windows_and_external_walls,
                        "internal_doors": data.internal_doors,
                        "wall_finishes": data.wall_finishes,
                        "floor_finishes": data.floor_finishes,
                        "ceiling_finishes": data.ceiling_finishes,
                        "gia": data.gia,
                        "customer_ref": data.customer_ref,
                        "total": total,
                        "total_new": total_new,
                    })

                except Building.DoesNotExist:
                    continue

            # Calculate grand total
            omit_keys = ["superstructure_total", "facade_total", "internal_finishes_total"]
            grand_total = sum(value for key, value in totals.items() if key not in omit_keys)

            return Response({
                "data": final_data,
                "totals": totals,
                "grand_total": grand_total
            }, status=status.HTTP_200_OK)


    def post(self, request, *args, **kwargs):
        data = request.data
        serializer = DesignDataSerializer(data=data)
        if serializer.is_valid(raise_exception=True):
            data = serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def put(self, request, id=None, *args, **kwargs):
        agent_type = self.get_object(id)
        serializer = DesignDataSerializer(agent_type, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, id=None, *args, **kwargs):
        try:
            DesignData.objects.filter(id=id).delete()
            message = {"success": "successfully deleted"}
            return Response(message, status=status.HTTP_200_OK)
        except Exception as e:
            error = getattr(e, 'message', repr(e))
            return Response(error, status=status.HTTP_400_BAD_REQUEST)





class YourMaterialAPIView(generics.GenericAPIView,mixins.ListModelMixin, mixins.CreateModelMixin,mixins.UpdateModelMixin,mixins.RetrieveModelMixin, mixins.DestroyModelMixin):

    queryset = YourMaterial.objects.all().order_by('id')
    serializer_class = YourMaterialSerializer

    def get_object(self, id):
        try:

            return YourMaterial.objects.get(id=id)
        except YourMaterial.DoesNotExist:
            raise Http404

    def get(self, request,id=None, *args, **kwargs):
        if id:
            id_obj = self.get_object(id)
            serializer = YourMaterialSerializer(id_obj)
            return Response(serializer.data)
        else:
            alldata = YourMaterial.objects.all()
            serializer = YourMaterialSerializer(alldata, many=True)
            return Response(serializer.data)

    def post(self, request, *args, **kwargs):
        data = request.data
        serializer = YourMaterialSerializer(data=data)
        if serializer.is_valid(raise_exception=True):
            data = serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def put(self, request,id=None, *args, **kwargs):
        agent_type = self.get_object(id)
        serializer = YourMaterialSerializer(agent_type, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            # data = serializer.data
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, id=None, *args, **kwargs):
        try:
            YourMaterial.objects.filter(id=id).delete()
            message = {"success": "sucessfully deleted"}
            return Response(message, status=status.HTTP_200_OK)
        except Exception as e:
            error = getattr(e, 'message', repr(e))
            return Response(error, status=status.HTTP_400_BAD_REQUEST)
        



class YourMaterialEmissionAPIView(generics.GenericAPIView,mixins.ListModelMixin, mixins.CreateModelMixin,mixins.UpdateModelMixin,mixins.RetrieveModelMixin, mixins.DestroyModelMixin):

    queryset = YourMaterialEmission.objects.all().order_by('id')
    serializer_class = YourMaterialEmissionSerializer

    def get_object(self, id):
        try:

            return YourMaterialEmission.objects.get(id=id)
        except YourMaterialEmission.DoesNotExist:
            raise Http404

    def get(self, request,id=None, *args, **kwargs):
        if id:
            id_obj = self.get_object(id)
            serializer = YourMaterialEmissionSerializer(id_obj)
            return Response(serializer.data)
        else:
            alldata = YourMaterialEmission.objects.all()
            serializer = YourMaterialEmissionSerializer(alldata, many=True)
            return Response(serializer.data)

    def post(self, request, *args, **kwargs):
        data = request.data
        serializer = YourMaterialEmissionSerializer(data=data)
        if serializer.is_valid(raise_exception=True):
            data = serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def put(self, request,id=None, *args, **kwargs):
        agent_type = self.get_object(id)
        serializer = YourMaterialEmissionSerializer(agent_type, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            # data = serializer.data
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, id=None, *args, **kwargs):
        try:
            YourMaterialEmission.objects.filter(id=id).delete()
            message = {"success": "sucessfully deleted"}
            return Response(message, status=status.HTTP_200_OK)
        except Exception as e:
            error = getattr(e, 'message', repr(e))
            return Response(error, status=status.HTTP_400_BAD_REQUEST)
        

class EcoMaterialAPIView(generics.GenericAPIView,mixins.ListModelMixin, mixins.CreateModelMixin,mixins.UpdateModelMixin,mixins.RetrieveModelMixin, mixins.DestroyModelMixin):

    queryset = EcoMaterial.objects.all().order_by('id')
    serializer_class = EcoMaterialSerializer

    def get_object(self, id):
        try:

            return EcoMaterial.objects.get(id=id)
        except EcoMaterial.DoesNotExist:
            raise Http404

    def get(self, request,id=None, *args, **kwargs):
        if id:
            id_obj = self.get_object(id)
            serializer = EcoMaterialSerializer(id_obj)
            return Response(serializer.data)
        else:
            alldata = EcoMaterial.objects.all()
            serializer = EcoMaterialSerializer(alldata, many=True)
            return Response(serializer.data)

    def post(self, request, *args, **kwargs):
        data = request.data
        serializer = EcoMaterialSerializer(data=data)
        if serializer.is_valid(raise_exception=True):
            data = serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def put(self, request,id=None, *args, **kwargs):
        agent_type = self.get_object(id)
        serializer = EcoMaterialSerializer(agent_type, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            # data = serializer.data
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, id=None, *args, **kwargs):
        try:
            EcoMaterial.objects.filter(id=id).delete()
            message = {"success": "sucessfully deleted"}
            return Response(message, status=status.HTTP_200_OK)
        except Exception as e:
            error = getattr(e, 'message', repr(e))
            return Response(error, status=status.HTTP_400_BAD_REQUEST)
        

class EcoMaterialEmissionAPIView(generics.GenericAPIView,mixins.ListModelMixin, mixins.CreateModelMixin,mixins.UpdateModelMixin,mixins.RetrieveModelMixin, mixins.DestroyModelMixin):

    queryset = EcoMaterialEmission.objects.all().order_by('id')
    serializer_class = EcoMaterialEmissionSerializer

    def get_object(self, id):
        try:

            return EcoMaterialEmission.objects.get(id=id)
        except EcoMaterialEmission.DoesNotExist:
            raise Http404

    def get(self, request,id=None, *args, **kwargs):
        if id:
            id_obj = self.get_object(id)
            serializer = EcoMaterialEmissionSerializer(id_obj)
            return Response(serializer.data)
        else:
            alldata = EcoMaterialEmission.objects.all()
            serializer = EcoMaterialEmissionSerializer(alldata, many=True)
            return Response(serializer.data)

    def post(self, request, *args, **kwargs):
        data = request.data
        serializer = EcoMaterialEmissionSerializer(data=data)
        if serializer.is_valid(raise_exception=True):
            data = serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def put(self, request,id=None, *args, **kwargs):
        agent_type = self.get_object(id)
        serializer = EcoMaterialEmissionSerializer(agent_type, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            # data = serializer.data
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, id=None, *args, **kwargs):
        try:
            EcoMaterialEmission.objects.filter(id=id).delete()
            message = {"success": "sucessfully deleted"}
            return Response(message, status=status.HTTP_200_OK)
        except Exception as e:
            error = getattr(e, 'message', repr(e))
            return Response(error, status=status.HTTP_400_BAD_REQUEST)

class VolumeAPIView(generics.GenericAPIView,mixins.ListModelMixin, mixins.CreateModelMixin,mixins.UpdateModelMixin,mixins.RetrieveModelMixin, mixins.DestroyModelMixin):

    queryset = Volume.objects.all().order_by('id')
    serializer_class = VolumeSerializer

    def get_object(self, id):
        try:

            return Volume.objects.get(id=id)
        except Volume.DoesNotExist:
            raise Http404

    def get(self, request,id=None, *args, **kwargs):
        if id:
            id_obj = self.get_object(id)
            serializer = VolumeSerializer(id_obj)
            return Response(serializer.data)
        else:
            alldata = Volume.objects.all()
            serializer = VolumeSerializer(alldata, many=True)
            return Response(serializer.data)

    def post(self, request, *args, **kwargs):
        data = request.data
        serializer = VolumeSerializer(data=data)
        if serializer.is_valid(raise_exception=True):
            data = serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def put(self, request,id=None, *args, **kwargs):
        agent_type = self.get_object(id)
        serializer = VolumeSerializer(agent_type, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            # data = serializer.data
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, id=None, *args, **kwargs):
        try:
            Volume.objects.filter(id=id).delete()
            message = {"success": "sucessfully deleted"}
            return Response(message, status=status.HTTP_200_OK)
        except Exception as e:
            error = getattr(e, 'message', repr(e))
            return Response(error, status=status.HTTP_400_BAD_REQUEST)
        


class CompareCarbonInputAPIView(generics.GenericAPIView,mixins.ListModelMixin, mixins.CreateModelMixin,mixins.UpdateModelMixin,mixins.RetrieveModelMixin, mixins.DestroyModelMixin):

    queryset = CompareCarbon.objects.all().order_by('id')
    serializer_class = CompareCarbonInputSerializer

    def get_object(self, id):
        try:

            return CompareCarbon.objects.get(id=id)
        except CompareCarbon.DoesNotExist:
            raise Http404

    def get(self, request,id=None, *args, **kwargs):
        if id:
            id_obj = self.get_object(id)
            serializer = CompareCarbonInputSerializer(id_obj)
            return Response(serializer.data)
        else:
            alldata = CompareCarbon.objects.all()
            serializer = CompareCarbonInputSerializer(alldata, many=True)
            return Response(serializer.data)

    def post(self, request, *args, **kwargs):
        data = request.data
        serializer = CompareCarbonInputSerializer(data=data)
        if serializer.is_valid(raise_exception=True):
            data = serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def put(self, request,id=None, *args, **kwargs):
        agent_type = self.get_object(id)
        serializer = CompareCarbonInputSerializer(agent_type, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            # data = serializer.data
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, id=None, *args, **kwargs):
        try:
            CompareCarbon.objects.filter(id=id).delete()
            message = {"success": "sucessfully deleted"}
            return Response(message, status=status.HTTP_200_OK)
        except Exception as e:
            error = getattr(e, 'message', repr(e))
            return Response(error, status=status.HTTP_400_BAD_REQUEST)




class CompareCarbonAPIView(generics.GenericAPIView,mixins.ListModelMixin, mixins.CreateModelMixin,mixins.UpdateModelMixin,mixins.RetrieveModelMixin, mixins.DestroyModelMixin):

    queryset = CompareCarbon.objects.all().order_by('id')
    serializer_class = CompareCarbonSerializer
    # filter_backends = (CustomSearchFilter, OrderingFilter)
    # search_fields= '__all__'
    def get_object(self, id):
        try:

            return CompareCarbon.objects.get(id=id)
        except CompareCarbon.DoesNotExist:
            raise Http404

    def get(self, request,id=None, *args, **kwargs):
        if id:
            id_obj = self.get_object(id)
            serializer = CompareCarbonSerializer(id_obj)
            return Response(serializer.data)
        else:
            alldata = CompareCarbon.objects.all()
            serializer = CompareCarbonSerializer(alldata, many=True)
            return Response(serializer.data)
    


######################################   THOUFIQ ###############################################


class GetOptionsAPI(generics.GenericAPIView,
                    mixins.ListModelMixin, 
                    mixins.CreateModelMixin, 
                    mixins.UpdateModelMixin,
                    mixins.RetrieveModelMixin, 
                    mixins.DestroyModelMixin):

    def get_Options(self, customer_domain, selected_region=None, selected_city=None):
        try:
            customer_reference = (
                CustomerMaster.objects.only("Customer_Ref")
                .filter(Domain_Name=customer_domain)
                .values_list('Customer_Ref', flat=True)
                .first()
            )

            if not customer_reference:
                return {"error": "Customer not found"}

            region_ids = list(Building.objects
                              .filter(customer_ref=customer_reference)
                              .values_list('region_id', flat=True)
                              .order_by("id")
                              .distinct())
            if selected_region:
                regions = list(Region.objects.filter(id__in=selected_region).order_by("id"))
            else:
                regions = list(Region.objects.filter(id__in=region_ids).order_by("id"))
            cities = []
            countries = set()  

            for region in regions:
                region_name = region.name
                country_name = region.country.name.lower()  
                cities.append({"value": region.id, "name": region_name.strip()})
                countries.add((region.country.id, country_name))  
                cities = [{"value": city.id, "name": city.name} for city in City.objects.filter(region_id=region.id)]
           
            query = Building.objects.all()

            if selected_region:
                buildings = list(query.filter(region_id=selected_region).values_list('id', 'name').order_by("id"))
            else:
                buildings = list(query.values_list('id', 'name').order_by("id"))
            if selected_city:
                cities = [{"value": city.id, "name": city.name} for city in City.objects.filter(id=selected_city).order_by("id")]
                query = query.filter(city_id=selected_city)
            if selected_region and selected_city:
                buildings = list(query.filter(city_id=selected_city).values_list('id', 'name').order_by("id"))

            phases = list(Phase.objects.all().values_list('id', 'name').order_by("id"))
            response_data = {
                "Regions": [{"value": region.id, "name": region.name} for region in (regions or [])],
                "Cities": cities or [],
                "Countries": [{"value": country[0], "name": country[1]} for country in (countries or [])],
                "Buildings": [{"value": building[0], "name": building[1]} for building in (buildings or [])],
                "Phases": [{"value": phase[0], "name": phase[1]} for phase in (phases or [])],
            }


            return response_data

        except Exception as e:
            print("Error:", e)
            return {"error": str(e)}

    def get(self, request, pk=None):
        # Extract domain name from query params
        customer_domain = request.query_params.get('domain', None)
        selected_region = request.query_params.get('region', None)
        selected_city = request.query_params.get('city', None)
        
        if not customer_domain:
            return Response({"error": "Domain name is required in query params."}, status=400)

        options_data = self.get_Options(customer_domain, selected_region, selected_city)

        return Response(options_data)



class Get_App_Deleivery_Note_API(generics.GenericAPIView,
                    mixins.ListModelMixin, 
                    mixins.CreateModelMixin, 
                    mixins.UpdateModelMixin,
                    mixins.RetrieveModelMixin, 
                    mixins.DestroyModelMixin):

    def get_app_deleivery_Note(self, customer_domain,start_date,end_date):
        try:
            customer_reference = (
                CustomerMaster.objects.only("Customer_Ref")
                .filter(Domain_Name=customer_domain)
                .values_list('Customer_Ref', flat=True)
                .first()
            )
            buildings = list(Building.objects.filter(customer_ref=customer_reference).values_list('id', 'name'))
            building_ids = [building[0] for building in buildings]  # Extract only the IDs

            filter_kwargs = {"building_id__in": building_ids,"account_number": "W"}

            if start_date:
                filter_kwargs["entry_time__gte"] = datetime.combine(datetime.strptime(start_date, '%Y-%m-%d'), time(0, 0, 0))

            if end_date:
                filter_kwargs["entry_time__lte"] = datetime.combine(datetime.strptime(end_date, '%Y-%m-%d'), time(23, 59, 59))

            App_Deleivery_Note_Data = list(BestMatch.objects.filter(**filter_kwargs).values("delivery_note_ref_no", "id", "building_id", "phase_id", "processed", "entry_time", "filename", "account_number").distinct('delivery_note_ref_no').order_by('delivery_note_ref_no', 'id'))


            building_ids = {item["building_id"] for item in App_Deleivery_Note_Data if item["building_id"]}
            phase_ids = {item["phase_id"] for item in App_Deleivery_Note_Data if item["phase_id"]}

            buildings = {b.id: b.name for b in Building.objects.filter(id__in=building_ids)}
            phases = {p.id: p.name for p in Phase.objects.filter(id__in=phase_ids)}

            for item in App_Deleivery_Note_Data:
                item["building_name"] = buildings.get(item.get("building_id"))
                item["phase_name"] = phases.get(item.get("phase_id"))
                fileName = item.get("filename")
                match = re.search(r'_(\d+)\.pdf$', fileName)
                

                if match:
                    fileId = match.group(1)
                    delivery_note_file = DeliveryNoteFile.objects.filter(id=fileId).first() if match else ""
                    item['filename'] = delivery_note_file.file_name if delivery_note_file else ""
                else:
                    item['filename'] = ""


            if not customer_reference:
                return {"error": "Customer not found"}

            response_data = {
                "result": App_Deleivery_Note_Data 
            }

            return response_data

        except Exception as e:
            print("Error:", e)
            return {"error": str(e)}

    def get(self, request, pk=None):
        customer_domain = request.query_params.get('domain', None)
        start_date = request.query_params.get('start_date', None)
        end_date = request.query_params.get('end_date', None)
       
        if not customer_domain:
            return Response({"error": "Domain name is required in query params."}, status=400)

        options_data = self.get_app_deleivery_Note(customer_domain,start_date,end_date)

        return Response(options_data)
    


class Get_Building_User_API(generics.GenericAPIView,
                    mixins.ListModelMixin, 
                    mixins.CreateModelMixin, 
                    mixins.UpdateModelMixin,
                    mixins.RetrieveModelMixin, 
                    mixins.DestroyModelMixin):

    

    def get_Building_User(self, email): 

        try:
            Building_ids = UserBuilding.objects.filter(user_id=email, status=True).values_list("building_id", flat=True)

            response = list(
                    Building.objects.filter(id__in=Building_ids,status=True)
                    .annotate(buildingId=F("id"), buildingName=F("name"))
                        .values("buildingId", "buildingName")
                    .order_by("id")
                    )
            

            return {"result": response}

        except Exception as e:
            print("Error:", e)
            return {"error": str(e)}

            
      

       

    def get(self, request, pk=None):
        email = request.query_params.get('email', None)
       
        if not email:
            return Response({"error": "Email is required in query params."}, status=400)

        options_data = self.get_Building_User(email)

        return Response(options_data)





class getCount(generics.ListAPIView):

    def get(self, request):
        email = request.query_params.get('email', None)
       
        if not email:
            return Response({"error": "Email is required in query params."}, status=400)

        result = self.data(email)  # Get serialized data
        return Response(result)  # Wrap it in a Response

    def data(self,email):

     try:

        result=Users.objects.filter(User_ID=email).first()
        customerref=result.customer_ref
        
        today = datetime.now().date()

# Get the first and last day of the previous month
        first_day_last_month = today.replace(day=1) - relativedelta(months=1)
        last_day_last_month = today.replace(day=1) - timedelta(days=1)

# Ensure first day starts at 12:00 AM and last day ends at 11:59:59 PM
        first_day_last_month = make_aware(datetime.combine(first_day_last_month, datetime.min.time()))
        last_day_last_month = make_aware(datetime.combine(last_day_last_month, datetime.max.time()))

# Print the results


        delivery_notes_grouped = (
    BestMatch.objects.filter(entry_time__date__range=[first_day_last_month, last_day_last_month],customer_ref=customerref)
    .values("delivery_note_ref_no")  # Group by delivery note reference
    .annotate(total_count=Count("id"))  # Count records per delivery note
)
        
        total_unique_delivery_notes = delivery_notes_grouped.count()

        

        first_day_this_month = make_aware(datetime.combine(today.replace(day=1), datetime.min.time()))
        last_day_this_month = make_aware(datetime.combine(today, datetime.max.time()))

# Query to count records grouped by delivery_note_Ref_no for this month
        delivery_notes_this_month = (
    BestMatch.objects.filter(entry_time__date__range=[first_day_this_month, last_day_this_month],customer_ref=customerref)
    .values("delivery_note_ref_no")  # Group by delivery note reference
    .annotate(total_count=Count("id"))  # Count records per delivery note
)
        

        first_day_this_year = make_aware(datetime.combine(today.replace(month=1, day=1), datetime.min.time()))
        last_day_this_year = make_aware(datetime.combine(today, datetime.max.time()))

        delivery_notes_this_year = (
    BestMatch.objects.filter(entry_time__date__range=[first_day_this_year, last_day_this_year],customer_ref=customerref)
    .values("delivery_note_ref_no")  # Group by delivery note reference
    .annotate(total_count=Count("id"))  # Count records per delivery note
)
        
        

        delivery_notes_webapp = (
    BestMatch.objects.filter(account_number='W',customer_ref=customerref)
    .values("delivery_note_ref_no")  # Group by delivery note reference
    .annotate(total_count=Count("id"))  # Count records per delivery note
)
        

        delivery_notes_mobileapp = (
    BestMatch.objects.exclude(account_number='W').filter(customer_ref=customerref)
    .values("delivery_note_ref_no")  # Group by delivery note reference
    .annotate(total_count=Count("id"))  # Count records per delivery note
)
       

        building_count = (
            AppBuilding.objects.filter(customer_ref=customerref)
        ).count()


        responsedata={
            "total_delivery_notes_uploaded_last_month":total_unique_delivery_notes,
            "total_delivery_notes_uploaded_this_month":delivery_notes_this_month.count(),
            "total_delivery_notes_uploaded_this_year":delivery_notes_this_year.count(),
            "total_delivery_notes_uploaded_through_web":delivery_notes_webapp.count(),
            "total_delivery_notes_uploaded_through_mobile":delivery_notes_mobileapp.count(),
            "building_count":building_count
            
        }

        return responsedata
# Print results
     except Exception as e :
         return {"error": str(e)}
        # return customer_ref


class Get_Phases_API(generics.GenericAPIView, 
                     mixins.ListModelMixin, 
                     mixins.CreateModelMixin, 
                     mixins.UpdateModelMixin, 
                     mixins.RetrieveModelMixin, 
                     mixins.DestroyModelMixin):
    
    queryset = Phase.objects.all().order_by('id')  # Define the queryset
    serializer_class = PhaseSerializer  # Specify the serializer class

    def get(self, request):
        result = self.get_all_phases()  # Get all phases
        return Response(result)

    def get_all_phases(self):
        phases = Phase.objects.all().order_by('id')  # Fetch all records
        serializer = PhaseSerializer(phases, many=True)  # Serialize data
        return serializer.data  # Return serialized data

class Get_UnitofMeasure_API(generics.GenericAPIView, 
                            mixins.ListModelMixin, 
                            mixins.CreateModelMixin, 
                            mixins.UpdateModelMixin, 
                            mixins.RetrieveModelMixin, 
                            mixins.DestroyModelMixin):
    
    queryset = Unit_of_Measure.objects.all().order_by('id')  

    def get(self, request):
        result = self.get_all_unitofmeasure()  
        return Response(result)

    def get_all_unitofmeasure(self):
        unit_of_measures = Unit_of_Measure.objects.all().values().order_by('id')   
        return list(unit_of_measures)  

class UpdateDeliveryNoteAPI(APIView):

    def post(self, request):
        data = request.data
        print("data",data)
        delivery_note_ref_no = data.get("delivery_note_ref_no")
        item_no = data.get("item_no")
        revised_phase_id = data.get("revised_phase_id")
        revised_product_description = data.get("revised_product_description")
        revised_unit_of_measure = data.get("revised_unit_of_measure")
        revised_quantity = data.get("revised_quantity")
        revised_user_id = data.get("revised_user_id")
        current_timestamp = now()

        if not delivery_note_ref_no or not item_no:
            return Response({"error": "delivery_note_ref_no and item_no are required"}, status=400)

        try:
            # Fetch existing record
            delivery_note = BestMatch.objects.get(delivery_note_ref_no=delivery_note_ref_no, item_no=item_no)
        except AppDeliveryNoteData.DoesNotExist:
            return Response({"error": "Record not found"}, status=404)

        # Store old values
        old_phase_id = delivery_note.phase_id
        old_desc = delivery_note.product_description
        old_uom = delivery_note.unit_of_measure
        old_qty = delivery_note.quantity
        approved = delivery_note.approved
        customer_ref =delivery_note.customer_ref
        user_id=delivery_note.user_id
        old_delivery_note_ref= delivery_note.delivery_note_ref_no
        old_item_id = delivery_note.item_no
        old_revised_phase_id = delivery_note.revised_phase_id
        old_revised_product_description = delivery_note.revised_product_description
        old_revised_unit_of_measure = delivery_note.revised_unit_of_measure
        old_revised_quantity = delivery_note.revised_quantity

        # Validate Unit_of_measure (case-insensitive check)
        valid_units = Unit_of_Measure.objects.values_list('name', flat=True)
        valid_units_lower = {unit.lower() for unit in valid_units}

        error_code = 0  # Default to 0 (no error)
        if revised_unit_of_measure and revised_unit_of_measure.lower() not in valid_units_lower:
            error_code = 1  # Unit_of_measure not valid

        # Validate Quantity
        try:
            revised_quantity = float(revised_quantity) if revised_quantity else None
        except ValueError:
            error_code = 2  # Invalid quantity

        # Track if fields were updated test
        updated_fields = []
        if old_revised_phase_id:
            if revised_phase_id and revised_phase_id != old_revised_phase_id:
                 delivery_note.revised_phase_id = revised_phase_id
                 updated_fields.append("revised_phase_id")
        elif revised_phase_id and revised_phase_id != old_phase_id:
            delivery_note.revised_phase_id = revised_phase_id
            updated_fields.append("revised_phase_id")
        if old_revised_product_description:
                if revised_product_description and revised_product_description != old_revised_product_description : #check revised also
                    delivery_note.revised_product_description = revised_product_description
                    updated_fields.append("revised_product_description")
        elif revised_product_description and revised_product_description != old_desc : #check revised also
                    delivery_note.revised_product_description = revised_product_description
                    updated_fields.append("revised_product_description")
        if old_revised_unit_of_measure:
            if revised_unit_of_measure and revised_unit_of_measure.lower() != (old_revised_unit_of_measure.lower() if old_revised_unit_of_measure else ""):
                delivery_note.revised_unit_of_measure = revised_unit_of_measure
                updated_fields.append("revised_unit_of_measure")
        elif revised_unit_of_measure and revised_unit_of_measure.lower() != (old_uom.lower() if old_uom else ""):
                delivery_note.revised_unit_of_measure = revised_unit_of_measure
                updated_fields.append("revised_unit_of_measure")
        if old_revised_quantity:
            if revised_quantity and revised_quantity != old_revised_quantity:
                delivery_note.revised_quantity = revised_quantity
                updated_fields.append("revised_quantity")
        elif revised_quantity and revised_quantity != old_qty:
                delivery_note.revised_quantity = revised_quantity
                updated_fields.append("revised_quantity")
        if updated_fields:
            delivery_note.revised_user_id = revised_user_id
            delivery_note.revised_date = current_timestamp
            updated_fields.append("revised_user_id")
            updated_fields.append("revised_date")

            if revised_phase_id or revised_product_description or revised_unit_of_measure or revised_quantity:
                delivery_note.approved = True
                updated_fields.append("approved")

            delivery_note.error_code = error_code
            updated_fields.append("error_code")
            with transaction.atomic():
                print("update")
                delivery_note.save(update_fields=updated_fields)

                # Insert into ProductMapping
                if revised_product_description and revised_product_description.strip():
                    is_duplicate = ProductMapping.objects.filter(
                        customer_ref=customer_ref,
                        product_description=old_desc,
                        mapped_product_description=revised_product_description
                    ).exists()
                    if is_duplicate:
                        return Response({
                            "error": "Duplicate mapped_product_description already exists for this customer_ref and product_description"
                        }, status=409)
                    if not is_duplicate:
                        ProductMapping.objects.create(
                            customer_ref=customer_ref,
                            product_description=old_desc,
                            mapped_product_description=revised_product_description,
                            user_id=revised_user_id
                        )
                    try:
                        last_log = AppDeliveryNoteChangeLog.objects.latest('id')
                        new_id = last_log.id + 1
                    except AppDeliveryNoteChangeLog.DoesNotExist:
                        new_id = 1 
                # Insert into AppDeliveryNoteChangeLog
                    AppDeliveryNoteChangeLog.objects.create(
                        id=new_id,
                        delivery_note_ref_no = old_delivery_note_ref,
                        item_id = old_item_id,
                        product_description = old_desc,
                        unit_of_measure = old_uom,
                        quantity = old_qty,
                        phase_id=old_phase_id,
                        revised_product_description=revised_product_description,
                        revised_unit_of_measure=revised_unit_of_measure,
                        revised_quantity = revised_quantity,
                        revised_phase_id=revised_phase_id,
                        revised_user_id =revised_user_id,
                        revised_date = delivery_note.revised_date,
                        customer_ref_no = customer_ref,
                    )
                    return Response({"message": "Record updated successfully", "error_code": error_code})
                else:
                    return Response({"message": "revised_product_description is null", "error_code": 400})


class ProductMappingListAPI(generics.ListAPIView):

    def get_queryset(self):
        product_description = self.request.query_params.get('product_description', None)
        
        if product_description:
            return ProductMapping.objects.filter(product_description__iexact=product_description)
        
        return ProductMapping.objects.all().order_by('id')   # Return all if no filter is provided

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        
        # Convert queryset to a list of dictionaries without using serializers
        result = list(queryset.values("id", "customer_ref", "product_description", "mapped_product_description"))

        return Response(result, status=status.HTTP_200_OK)

class DeliveryNoteListByCustomerRefAPI(generics.GenericAPIView, mixins.ListModelMixin):

    queryset = BestMatch.objects.all().order_by('id')

    def get(self, request):
        user_email = request.GET.get('user_email')

        from_date = request.GET.get('from_date')
        to_date = request.GET.get('to_date')

        if not user_email:
            return Response({"error": "useremail is required"}, status=400)

        if not (from_date and to_date):
            return Response({"error": "from_date and to_date are required"}, status=400)

        result = Users.objects.filter(User_ID=user_email).first()
        if not result:
            return Response({"error":"Customer not found"}, status=400)
        customer_ref=result.customer_ref
       
        # print(customer_ref)

        # Fetch delivery notes with aggregation
        delivery_notes = (
    BestMatch.objects.filter(
        customer_ref=customer_ref,
        entry_time__date__range=[from_date, to_date]
    )
    .values(
        'delivery_note_ref_no',
        'supplier_name',
        'entry_time',
        'filename',
        'customer_ref',
        'user_id',
        'building_id'
    )
    .annotate(
        total_KgCO2=Sum('kgco2'),
        error_code=Sum('error_code'),
        site_address=Concat(
            F('delivery_address_line_1'), Value(', '),
            F('delivery_city'), Value(', '),
            F('delivery_post_code'), Value(', '),
            F('delivery_country'),
            output_field=TextField()
        ),
        earliest_id=Min('id') 
    )
    .order_by('earliest_id')  
)


        
        

        # Fetch building details
        building_map = {
            b["id"]: {
                "name": b["name"],  # Fetch building_name instead of id
                "address": f"{b['address_line_1']}, {b['address_line_2']}",
                "city_id": b["city_id"],
                "region_id": b["region_id"]
            }
            for b in AppBuilding.objects.values("id", "name", "address_line_1", "address_line_2", "city_id", "region_id")
        }

        # Fetch city details
        city_map = {c["id"]: c["name"] for c in City.objects.values("id", "name")}

        # Fetch region details
        region_map = {r["id"]: r["name"] for r in Region.objects.values("id", "name")}

        # Add building name, site address, and totals
        for note in delivery_notes:
            building_info = building_map.get(note["building_id"], {})
            city_name = city_map.get(building_info.get("city_id"), "Unknown City")
            region_name = region_map.get(building_info.get("region_id"), "Unknown Region")

            note["building_name"] = building_info.get("name", "N/A")
            # note["site_address"] = f"{building_info.get('address', 'N/A')}, {city_name}, {region_name}"
            note.pop("building_id", None)  # Remove building_id as it's no longer needed
            if note["total_KgCO2"] is not None:
                note["total_KgCO2"] = str(note["total_KgCO2"])

        return Response(list(delivery_notes))


class DeliveryNoteListByDeliveryNoteRefNoAPI(generics.GenericAPIView, mixins.ListModelMixin):
    queryset = BestMatch.objects.all().order_by('id')

    def get(self, request):
        delivery_note_ref_no = request.GET.get('delivery_note_ref_no')
        user_email = request.GET.get('user_email')

        # Base queryset
        delivery_notes = BestMatch.objects.all().order_by('id')

        # Apply filters dynamically
        if delivery_note_ref_no:
            delivery_notes = delivery_notes.filter(delivery_note_ref_no=delivery_note_ref_no)
        if user_email:
            delivery_notes = delivery_notes.filter(user_id=user_email)

        # Annotate with additional fields
        delivery_notes = delivery_notes.annotate(
            delivery_address=Concat(
                F('delivery_address_line_1'), Value(', '), F('delivery_city'), Value(', '),
                F('delivery_post_code'), Value(', '), F('delivery_country'), output_field=TextField()
            ),
            supplier_address=Concat(
                F('supplier_address_line_1'), Value(', '), F('supplier_city'), Value(', '),
                F('supplier_post_code'), Value(', '), F('supplier_country'), output_field=TextField()
            ),
            building_name=Subquery(
                AppBuilding.objects.filter(id=OuterRef('building_id')).values('name')[:1]
            ),
            phase_name=Subquery(
                Phase.objects.filter(id=OuterRef('phase_id')).values('name')[:1]
            ),
            revised_phase_name=Subquery(
                Phase.objects.filter(id=OuterRef('revised_phase_id')).values('name')[:1]
            )
        ).values()

        return Response(list(delivery_notes))



class DeliveryNoteListByUserAPI(generics.GenericAPIView, mixins.ListModelMixin):
    def get(self, request):
        user_email = request.GET.get('email')
        from_date = request.GET.get('from_date')
        to_date = request.GET.get('to_date')

        if not user_email or not from_date or not to_date:
            return Response(
                {"error": "Missing one or more required query parameters: email, from_date, to_date"},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            from_date_obj = datetime.strptime(from_date, "%Y-%m-%d")
            to_date_obj = datetime.strptime(to_date, "%Y-%m-%d").replace(hour=23, minute=59, second=59)
        except ValueError as ve:
            return Response({"error": f"Invalid date format: {ve}"}, status=status.HTTP_400_BAD_REQUEST)



        # Step 4: Final Query
        matches = BestMatch.objects.filter(
            user_id=user_email,
            entry_time__range=(from_date_obj, to_date_obj)
        ).values(
            'delivery_note_ref_no',
            'supplier_name',
            'entry_time',
            'building_id'
        ).order_by('entry_time').distinct('entry_time')

        # Step 2: Get related buildings (in bulk to reduce DB hits)
        building_ids = [match['building_id'] for match in matches]
        buildings = Building.objects.filter(id__in=building_ids).values('id', 'name', 'city_id', 'region_id')
        building_map = {b['id']: b for b in buildings}

        # Step 3: Get all needed city and region IDs
        city_ids = {b['city_id'] for b in buildings}
        region_ids = {b['region_id'] for b in buildings}

        cities = City.objects.filter(id__in=city_ids).values('id', 'name')
        regions = Region.objects.filter(id__in=region_ids).values('id', 'name')

        city_map = {c['id']: c['name'] for c in cities}
        region_map = {r['id']: r['name'] for r in regions}

        # Step 4: Combine all into final response
        response = []
        for match in matches:
            building = building_map.get(match['building_id'], {})
            city_name = city_map.get(building.get('city_id'), '')
            region_name = region_map.get(building.get('region_id'), '')

            response.append({
                'delivery_note_ref_no': match['delivery_note_ref_no'],
                'supplier_name': match['supplier_name'],
                'entry_time': match['entry_time'],
                'building_name': building.get('name', ''),
                'city_name': city_name,
                'region_name': region_name
            })

        # print(response)

        return Response(list(response))

class AssignUniqueNumberAPI(APIView):

    def post(self, request):
        file_name = request.data.get("file_name")

        if not file_name:
            return Response({"error": "file_name is required."}, status=400)

        # Check if the file_name already exists
        try:
            existing = DeliveryNoteFile.objects.get(file_name=file_name)
            return Response({
                "message": "file_name already exists",
                "file_name": existing.file_name,
                "unique_number": existing.id,
            }, status=200)

        except DeliveryNoteFile.DoesNotExist:
            try:
                new_entry = DeliveryNoteFile.objects.create(file_name=file_name)
                return Response({
                    "file_name": new_entry.file_name,
                    "unique_number": new_entry.id
                }, status=201)
            except IntegrityError:
                return Response({"error": "file_name already exists."}, status=400)

class GetFileNameAPI(APIView):

    def get(self, request):
        unique_number = request.query_params.get('unique_number')

        if not unique_number:
            return Response({"error": "unique_number is required."}, status=400)

        try:
            record = DeliveryNoteFile.objects.get(id=unique_number)
            return Response({
                "unique_number": record.id,
                "file_name": record.file_name
            }, status=200)

        except DeliveryNoteFile.DoesNotExist:
            return Response({"error": "No record found for given unique_number."}, status=404)


##############################################    WASTE TRANSFER NOTE ###############################
     
           
class WasteTransferNoteAPIView(
    generics.GenericAPIView,
    mixins.ListModelMixin,
    mixins.CreateModelMixin,
    mixins.UpdateModelMixin,
    mixins.RetrieveModelMixin,
    mixins.DestroyModelMixin
):
    serializer_class = WasteTransferNoteSerializer

    def get_queryset(self):
        # Get the logged-in user's email
        user_email = self.request.user.email

        # Fetch the corresponding customer_ref from the Users table
        try:
            user = Users.objects.get(User_ID=user_email)
        except Users.DoesNotExist:
            raise Http404("User not found in Users table")

        # Initial filter by customer_ref
        queryset = WasteTransferNote.objects.filter(customer_ref=user.customer_ref)

        # Optional: filter by date range
        from_date_str = self.request.GET.get('from_date')
        to_date_str = self.request.GET.get('to_date')

        if from_date_str and to_date_str:
            from_date = parse_date(from_date_str)
            to_date = parse_date(to_date_str)

        # Validate format
            if not from_date or not to_date:
                raise ValidationError("Both 'from_date' and 'to_date' must be in YYYY-MM-DD format.")

        # Optional: Check if from_date is after to_date
            if from_date > to_date:
                raise ValidationError("'from_date' must be earlier than or equal to 'to_date'.")

            queryset = queryset.filter(waste_note_upload_date__date__range=(from_date, to_date))
        
        approved = self.request.GET.get('approved', 'All').strip().lower()

        if approved == 'yes':
            queryset = queryset.filter(approved_date__isnull=False)
        elif approved == 'no':
            queryset = queryset.filter(approved_date__isnull=True)
        elif approved != 'all':
            raise ValidationError("Invalid value for 'approved'. Use 'Yes', 'No', or 'All'.")

        return queryset.order_by('-waste_note_upload_date')

        

    def get_object(self, id):
        try:
            return self.get_queryset().get(id=id)
        except WasteTransferNote.DoesNotExist:
            raise Http404("WasteTransferNote not found")

    def get(self, request, id=None, *args, **kwargs):
        if id:
            note = self.get_object(id)
            serializer = WasteTransferNoteSerializer(note)
            return Response(serializer.data)
        else:
            notes = self.get_queryset()
            serializer = WasteTransferNoteSerializer(notes, many=True)
            return Response(serializer.data)

    def post(self, request, *args, **kwargs):
        serializer = WasteTransferNoteSerializer(data=request.data)
        if serializer.is_valid(raise_exception=True):
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def put(self, request, id=None, *args, **kwargs):
        instance = self.get_object(id)
        serializer = WasteTransferNoteSerializer(instance, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, id=None, *args, **kwargs):
        try:
            self.get_queryset().filter(id=id).delete()
            return Response({"success": "Successfully deleted"}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response(str(e), status=status.HTTP_400_BAD_REQUEST)
        




class WasteTransferNoteExtraAPIView(
    generics.GenericAPIView,
    mixins.ListModelMixin,
    mixins.CreateModelMixin,
    mixins.UpdateModelMixin,
    mixins.RetrieveModelMixin,
    mixins.DestroyModelMixin
):
    queryset = WasteTransferNote.objects.all().order_by('id')
    serializer_class = WasteTransferNoteExtraSerializer

    def get_object(self, id):
        try:
            return WasteTransferNote.objects.get(id=id)
        except WasteTransferNote.DoesNotExist:
            raise Http404

    def get(self, request, id=None, *args, **kwargs):
        if id:
            note = self.get_object(id)
            serializer = WasteTransferNoteExtraSerializer(note)
            return Response(serializer.data)
        else:
            notes = WasteTransferNote.objects.all()
            serializer = WasteTransferNoteExtraSerializer(notes, many=True)
            return Response(serializer.data)

    def post(self, request, *args, **kwargs):
        serializer = WasteTransferNoteExtraSerializer(data=request.data)
        if serializer.is_valid(raise_exception=True):
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def put(self, request, id=None, *args, **kwargs):
        instance = self.get_object(id)
        serializer = WasteTransferNoteExtraSerializer(instance, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, id=None, *args, **kwargs):
        try:
            WasteTransferNote.objects.filter(id=id).delete()
            return Response({"success": "Successfully deleted"}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response(str(e), status=status.HTTP_400_BAD_REQUEST)





class WasteTransferNoteMobileAPIView(
    generics.GenericAPIView,
    mixins.ListModelMixin,
    mixins.CreateModelMixin,
    mixins.UpdateModelMixin,
    mixins.RetrieveModelMixin,
    mixins.DestroyModelMixin
):
    serializer_class = WasteTransferNoteMobileSerializer

    def get_queryset(self):
        # Get the logged-in user's email
        user_email = self.request.user.email

        # Filter by records uploaded by the logged-in user
        queryset = WasteTransferNote.objects.filter(waste_note_uploaded_by=user_email)

        # Optional: filter by date range
        from_date = self.request.GET.get('from_date')
        to_date = self.request.GET.get('to_date')

        if from_date and to_date:
            from_dt = parse_date(from_date)
            to_dt = parse_date(to_date)

            if not from_dt or not to_dt:
                raise ValidationError("Invalid date format. Use YYYY-MM-DD for both from_date and to_date.")

            queryset = queryset.filter(waste_note_upload_date__date__range=(from_dt, to_dt))

        return queryset.order_by('-waste_note_upload_date')

    def get_object(self, id):
        try:
            return self.get_queryset().get(id=id)
        except WasteTransferNote.DoesNotExist:
            raise Http404("WasteTransferNote not found")

    def get(self, request, id=None, *args, **kwargs):
        if id:
            note = self.get_object(id)
            serializer = self.serializer_class(note)
            return Response(serializer.data)
        else:
            notes = self.get_queryset()
            serializer = self.serializer_class(notes, many=True)
            return Response(serializer.data)

    def post(self, request, *args, **kwargs):
        serializer = self.serializer_class(data=request.data)
        if serializer.is_valid(raise_exception=True):
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def put(self, request, id=None, *args, **kwargs):
        instance = self.get_object(id)
        serializer = self.serializer_class(instance, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, id=None, *args, **kwargs):
        try:
            self.get_queryset().filter(id=id).delete()
            return Response({"success": "Successfully deleted"}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response(str(e), status=status.HTTP_400_BAD_REQUEST)
        


class WasteDisposalAPIView(
    generics.GenericAPIView,
    mixins.ListModelMixin,
    mixins.CreateModelMixin,
    mixins.UpdateModelMixin,
    mixins.RetrieveModelMixin,
    mixins.DestroyModelMixin
):
    queryset = WasteDisposal.objects.all().order_by('id')
    serializer_class = WasteDisposalSerializer

    def get_object(self, id):
        try:
            return WasteDisposal.objects.get(id=id)
        except WasteDisposal.DoesNotExist:
            raise Http404

    def get(self, request, id=None, *args, **kwargs):
        if id:
            note = self.get_object(id)
            serializer = WasteDisposalSerializer(note)
            return Response(serializer.data)
        else:
            notes = WasteDisposal.objects.all()
            serializer = WasteDisposalSerializer(notes, many=True)
            return Response(serializer.data)

    def post(self, request, *args, **kwargs):
        serializer = WasteDisposalSerializer(data=request.data)
        if serializer.is_valid(raise_exception=True):
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def put(self, request, id=None, *args, **kwargs):
        instance = self.get_object(id)
        serializer = WasteDisposalSerializer(instance, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, id=None, *args, **kwargs):
        try:
            WasteTransferNote.objects.filter(id=id).delete()
            return Response({"success": "Successfully deleted"}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response(str(e), status=status.HTTP_400_BAD_REQUEST)
        



class WastePhaseAPIView(
    generics.GenericAPIView,
    mixins.ListModelMixin,
    mixins.CreateModelMixin,
    mixins.UpdateModelMixin,
    mixins.RetrieveModelMixin,
    mixins.DestroyModelMixin
):
    queryset = WastePhase.objects.all().order_by('id')
    serializer_class = WastePhaseSerializer

    def get_object(self, id):
        try:
            return WastePhase.objects.get(id=id)
        except WastePhase.DoesNotExist:
            raise Http404

    def get(self, request, id=None, *args, **kwargs):
        if id:
            note = self.get_object(id)
            serializer = WastePhaseSerializer(note)
            return Response(serializer.data)
        else:
            notes = WastePhase.objects.all()
            serializer = WastePhaseSerializer(notes, many=True)
            return Response(serializer.data)

    def post(self, request, *args, **kwargs):
        serializer = WastePhaseSerializer(data=request.data)
        if serializer.is_valid(raise_exception=True):
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def put(self, request, id=None, *args, **kwargs):
        instance = self.get_object(id)
        serializer = WastePhaseSerializer(instance, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, id=None, *args, **kwargs):
        try:
            WasteTransferNote.objects.filter(id=id).delete()
            return Response({"success": "Successfully deleted"}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response(str(e), status=status.HTTP_400_BAD_REQUEST)
        

from rapidfuzz import fuzz
from elasticsearch import Elasticsearch 
from elasticsearch import NotFoundError 
# class WasteCarriersBrokersDealersAPIView(
#     generics.GenericAPIView,
#     mixins.ListModelMixin,
#     mixins.CreateModelMixin,
#     mixins.UpdateModelMixin,
#     mixins.RetrieveModelMixin,
#     mixins.DestroyModelMixin
# ):
#     queryset = WasteCarriersBrokersDealers.objects.all().order_by('id')
#     serializer_class = WasteCarriersBrokersDealersSerializer

#     def get_object(self, id):
#         try:
#             return WasteCarriersBrokersDealers.objects.get(id=id)
#         except WasteCarriersBrokersDealers.DoesNotExist:
#             raise Http404

#     def get(self, request, id=None, *args, **kwargs):
#         if id:
#             id_obj = self.get_object(id)
#             serializer = WasteCarriersBrokersDealersSerializer(id_obj)
#             return Response(serializer.data)

#         name = request.query_params.get("waste_carrier_name", "").strip()
#         postcode = request.query_params.get("waste_carrier_postcode", "").strip()

#         queryset = WasteCarriersBrokersDealers.objects.all()

#         # Filter by postcode if provided (exact match)
#         if postcode:
#             queryset = queryset.filter(waste_carrier_postcode__iexact=postcode)

#         # Apply fuzzy name match using RapidFuzz
#         if name:
#             # Limit to top 100 candidates before applying fuzzy match
#             candidates = queryset[:100]
#             # Annotate with fuzzy match score
#             results = sorted(
#                 candidates,
#                 key=lambda x: fuzz.ratio(name.lower(), (x.waste_carrier_name or "").lower()),
#                 reverse=True
#             )[:10]
#         else:
#             # No fuzzy name match, return top 10
#             results = queryset[:10]

#         serializer = WasteCarriersBrokersDealersSerializer(results, many=True)
#         return Response(serializer.data)

#     def post(self, request, *args, **kwargs):
#         serializer = WasteCarriersBrokersDealersSerializer(data=request.data)
#         if serializer.is_valid(raise_exception=True):
#             serializer.save()
#             return Response(serializer.data, status=status.HTTP_201_CREATED)
#         return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

#     def put(self, request, id=None, *args, **kwargs):
#         instance = self.get_object(id)
#         serializer = WasteCarriersBrokersDealersSerializer(instance, data=request.data, partial=True)
#         if serializer.is_valid():
#             serializer.save()
#             return Response(serializer.data)
#         return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

#     def delete(self, request, id=None, *args, **kwargs):
#         try:
#             WasteCarriersBrokersDealers.objects.filter(id=id).delete()
#             return Response({"success": "successfully deleted"}, status=status.HTTP_200_OK)
#         except Exception as e:
#             return Response(str(e), status=status.HTTP_400_BAD_REQUEST)
class WasteCarriersBrokersDealersAPIView(
    generics.GenericAPIView,
    mixins.ListModelMixin,
    mixins.CreateModelMixin,
    mixins.UpdateModelMixin,
    mixins.RetrieveModelMixin,
    mixins.DestroyModelMixin
):
    queryset = WasteCarriersBrokersDealers.objects.all().order_by('id')
    serializer_class = WasteCarriersBrokersDealersSerializer

    def get_object(self, id):
        try:
            return WasteCarriersBrokersDealers.objects.get(id=id)
        except WasteCarriersBrokersDealers.DoesNotExist:
            raise Http404

    def get(self, request, id=None, *args, **kwargs):
        if id:
            obj = self.get_object(id)
            serializer = WasteCarriersBrokersDealersSerializer(obj)
            return Response(serializer.data)

        input_name = request.query_params.get("waste_carrier_name", "").strip()
        input_postcode = request.query_params.get("waste_carrier_postcode", "").strip()

        # Fallback to DB if no search term
        if not input_name and not input_postcode:
            queryset = WasteCarriersBrokersDealers.objects.all().order_by('-id')[:10]
            serializer = WasteCarriersBrokersDealersSerializer(queryset, many=True)
            return Response(serializer.data)

        # Use ELASTICSEARCH_HOST from .env, fallback to Docker service name
        es_host = getattr(settings, "ELASTICSEARCH_HOST", "http://elasticsearch:9200")
        es = Elasticsearch(
            es_host,
            headers={
                "Accept": "application/vnd.elasticsearch+json; compatible-with=8",
                "Content-Type": "application/vnd.elasticsearch+json; compatible-with=8"
            }
        )

        # Build fuzzy query
        query = {
            "bool": {
                "must": [
                    {
                        "match": {
                            "waste_carrier_name": {
                                "query": input_name,
                                "fuzziness": "AUTO"
                            }
                        }
                    }
                ],
                "filter": [
                    {
                        "term": {
                            "waste_carrier_postcode": input_postcode
                        }
                    }
                ] if input_postcode else []
            }
        }

        try:
            response = es.search(index="waste_carriers", query=query, size=10)
            results = [hit["_source"] for hit in response["hits"]["hits"]]
            return Response(results)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def post(self, request, *args, **kwargs):
        serializer = WasteCarriersBrokersDealersSerializer(data=request.data)
        if serializer.is_valid(raise_exception=True):
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def put(self, request, id=None, *args, **kwargs):
        instance = self.get_object(id)
        serializer = WasteCarriersBrokersDealersSerializer(instance, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, id=None, *args, **kwargs):
        try:
            # Delete from DB
            WasteCarriersBrokersDealers.objects.filter(id=id).delete()

            # Also delete from Elasticsearch
            es_host = getattr(settings, "ELASTICSEARCH_HOST", "http://elasticsearch:9200")
            es = Elasticsearch(
                es_host,
                headers={
                    "Accept": "application/vnd.elasticsearch+json; compatible-with=8",
                    "Content-Type": "application/vnd.elasticsearch+json; compatible-with=8"
                }
            )
            try:
                es.delete(index="waste_carriers", id=id)
            except NotFoundError:
                pass  # It's okay if it wasn't found in ES

            return Response({"success": "Successfully deleted"}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response(str(e), status=status.HTTP_400_BAD_REQUEST)



# class CompanyHouseAPIView(
#     generics.GenericAPIView,
#     mixins.ListModelMixin,
# ):
#     def get(self, request, *args, **kwargs):
#         company_name = request.query_params.get("company_name")
#         location = request.query_params.get("location")

#         if not company_name or not location:
#             return Response(
#                 {"error": "Missing required parameters: company_name and location"},
#                 status=status.HTTP_400_BAD_REQUEST,
#             )

#         url = "https://api.company-information.service.gov.uk/advanced-search/companies"
#         params = {
#             "company_name_includes": company_name,
#             "location": location,
#         }
#         response = requests.get(
#             url,
#             params=params,
#             auth=(settings.COMPANY_HOUSE_API_KEY, '')
#         )

#         if response.status_code != 200:
#             return Response(
#                 {"error": "Failed to fetch company data", "details": response.text},
#                 status=response.status_code,
#             )

#         return Response(response.json(), status=status.HTTP_200_OK)



class CompanyHouseAPIView(
    generics.GenericAPIView,
    mixins.ListModelMixin,
):
    def get(self, request, *args, **kwargs):
        company_name = request.query_params.get("company_name")
        location = request.query_params.get("location")

        # Prepare API endpoint
        url = "https://api.company-information.service.gov.uk/advanced-search/companies"

        # Build params only if provided
        params = {}
        if company_name:
            params["company_name_includes"] = company_name
        if location:
            params["location"] = location

        if not params:
            return Response(
                {"error": "Please provide at least one query parameter: company_name or location"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Make the API request with Basic Auth (API key as username, empty password)
        try:
            response = requests.get(
                url,
                params=params,
                auth=(settings.COMPANY_HOUSE_API_KEY, '')
            )
            response.raise_for_status()
            return Response(response.json(), status=status.HTTP_200_OK)

        except requests.exceptions.RequestException as e:
            return Response(
                {"error": "Error fetching data from Companies House", "details": str(e)},
                status=status.HTTP_502_BAD_GATEWAY
            )
###################################   CSV UPLOADS | DO NOT DELETE COMMENTED BELOW | SAVED FOR LATER USE ######################################

# class FileUploadForm(forms.Form):
#     file = forms.FileField()

# class CSVUploadViewDesign(FormView):
#     template_name = 'app/upload_design.html'
#     form_class = FileUploadForm
#     success_url = reverse_lazy('upload_design')  # Redirect after POST

#     def form_valid(self, form):
#         csv_file = form.cleaned_data['file']
#         if not csv_file.name.endswith('.csv'):
#             return HttpResponse("Invalid file format. Please upload a CSV file.", status=400)

#         data_set = csv_file.read().decode('UTF-8')
#         io_string = io.StringIO(data_set)
#         next(io_string)  # Skip header row
#         for row in csv.reader(io_string, delimiter=',', quotechar='"'):
#             try:
#                 DesignData.objects.create(
#                     region=row[0],
#                     city=row[1],
#                     building_name=row[2],
#                     substructure=row[3],
#                     superstructure=row[4],
#                     façade=row[5],
#                     internal_walls_partitions=row[6],
#                     internal_finishes=row[7],
#                     ff_fe=row[8],
#                     gia=row[9],
                    
#                 )
#             except ValueError as e:
#                 return HttpResponse(f"Error parsing CSV: {str(e)}", status=400)

#         return super().form_valid(form)


# class CSVUploadViewYourMaterial(FormView):
#     template_name = 'app/upload_your_material.html'
#     form_class = FileUploadForm
#     success_url = reverse_lazy('upload_your_material')  # Redirect after POST

#     def form_valid(self, form):
#         csv_file = form.cleaned_data['file']
#         if not csv_file.name.endswith('.csv'):
#             return HttpResponse("Invalid file format. Please upload a CSV file.", status=400)

#         data_set = csv_file.read().decode('UTF-8')
#         io_string = io.StringIO(data_set)
#         next(io_string)  # Skip header row
#         for row in csv.reader(io_string, delimiter=',', quotechar='"'):
#             try:
#                 # Ensure row has at least one column
#                 if len(row) < 1:
#                     continue  # Skip empty rows

#                 YourMaterial.objects.create(
#                     name=row[0],
#                 )
#             except IndexError:
#                 return HttpResponse("CSV format error: Missing required data in some rows.", status=400)
#             except ValueError as e:
#                 return HttpResponse(f"Error parsing CSV: {str(e)}", status=400)

#         return super().form_valid(form)


# class CSVUploadViewYourMaterialEmission(FormView):
#     template_name = 'app/upload_your_material_emission.html'
#     form_class = FileUploadForm
#     success_url = reverse_lazy('upload_your_material_emission')  # Redirect after POST

#     def form_valid(self, form):
#         csv_file = form.cleaned_data['file']
#         if not csv_file.name.endswith('.csv'):
#             return HttpResponse("Invalid file format. Please upload a CSV file.", status=400)

#         data_set = csv_file.read().decode('UTF-8')
#         io_string = io.StringIO(data_set)
#         next(io_string)  # Skip header row
#         for row in csv.reader(io_string, delimiter=',', quotechar='"'):
#             try:
#                 name_id=int(row[1])
#                 country_instance=YourMaterial.objects.get(pk=name_id)
#                 # date_added = datetime.strptime(row[4], '%m/%d/%Y').date()  # Assume Date is still at the 4th index
#                 YourMaterialEmission.objects.create(
#                     emission=row[0],
#                     name=country_instance
#                 )
#             except ValueError as e:
#                 return HttpResponse(f"Error parsing CSV: {str(e)}", status=400)

#         return super().form_valid(form)

# class CSVUploadViewEcoMaterial(FormView):
#     template_name = 'app/upload_eco_material.html'
#     form_class = FileUploadForm
#     success_url = reverse_lazy('upload_eco_material')  # Redirect after POST

#     def form_valid(self, form):
#         csv_file = form.cleaned_data['file']
#         if not csv_file.name.endswith('.csv'):
#             return HttpResponse("Invalid file format. Please upload a CSV file.", status=400)

#         data_set = csv_file.read().decode('UTF-8')
#         io_string = io.StringIO(data_set)
#         next(io_string)  # Skip header row
#         for row in csv.reader(io_string, delimiter=',', quotechar='"'):
#             try:
#                 # date_added = datetime.strptime(row[4], '%m/%d/%Y').date()  # Assume Date is still at the 4th index
#                 EcoMaterial.objects.create(
#                     name=row[0],
#                 )
#             except ValueError as e:
#                 return HttpResponse(f"Error parsing CSV: {str(e)}", status=400)

#         return super().form_valid(form)


# class CSVUploadViewEcoMaterialEmission(FormView):
#     template_name = 'app/upload_eco_material_emission.html'
#     form_class = FileUploadForm
#     success_url = reverse_lazy('upload_eco_material_emission')  # Redirect after POST

#     def form_valid(self, form):
#         csv_file = form.cleaned_data['file']
#         if not csv_file.name.endswith('.csv'):
#             return HttpResponse("Invalid file format. Please upload a CSV file.", status=400)

#         data_set = csv_file.read().decode('UTF-8')
#         io_string = io.StringIO(data_set)
#         next(io_string)  # Skip header row
#         for row in csv.reader(io_string, delimiter=',', quotechar='"'):
#             try:
#                 name_id=int(row[1])
#                 country_instance=EcoMaterial.objects.get(pk=name_id)
#                 # date_added = datetime.strptime(row[4], '%m/%d/%Y').date()  # Assume Date is still at the 4th index
#                 EcoMaterialEmission.objects.create(
#                     emission=row[0],
#                     name=country_instance
#                 )
#             except ValueError as e:
#                 return HttpResponse(f"Error parsing CSV: {str(e)}", status=400)

#         return super().form_valid(form)

# class CSVUploadViewCompareCarbon(FormView):
#     template_name = 'app/upload_compare_carbon.html'
#     form_class = FileUploadForm
#     success_url = reverse_lazy('upload_compare_carbon')  # Redirect after POST

#     def form_valid(self, form):
#         csv_file = form.cleaned_data['file']
#         if not csv_file.name.endswith('.csv'):
#             return HttpResponse("Invalid file format. Please upload a CSV file.", status=400)

#         data_set = csv_file.read().decode('UTF-8')
#         io_string = io.StringIO(data_set)
#         next(io_string)  # Skip header row
#         for row in csv.reader(io_string, delimiter=',', quotechar='"'):
#             try:
#                 name_id=int(row[1])
#                 country_instance=Country.objects.get(pk=name_id)
#                 # date_added = datetime.strptime(row[4], '%m/%d/%Y').date()  # Assume Date is still at the 4th index
#                 CompareCarbon.objects.create(
#                     emission=row[0],
#                     name=country_instance
#                 )
#             except ValueError as e:
#                 return HttpResponse(f"Error parsing CSV: {str(e)}", status=400)

#         return super().form_valid(form)
    

# class CSVUploadViewCountry(FormView):
#     template_name = 'app/upload_country.html'
#     form_class = FileUploadForm
#     success_url = reverse_lazy('upload_country')  # Redirect after POST

#     def form_valid(self, form):
#         csv_file = form.cleaned_data['file']
#         if not csv_file.name.endswith('.csv'):
#             return HttpResponse("Invalid file format. Please upload a CSV file.", status=400)

#         data_set = csv_file.read().decode('UTF-8')
#         io_string = io.StringIO(data_set)
#         next(io_string)  # Skip header row
#         for row in csv.reader(io_string, delimiter=',', quotechar='"'):
#             if len(row) < 1:
#                 return HttpResponse("Invalid CSV format.", status=400)
#             try:
#                 Country.objects.create(name=row[0])
#             except ValueError as e:
#                 return HttpResponse(f"Error parsing CSV: {str(e)}", status=400)

#         return super().form_valid(form)


# class CSVUploadViewRegion(FormView):
#     template_name = 'app/upload_region.html'
#     form_class = FileUploadForm
#     success_url = reverse_lazy('upload_region')  # Redirect after POST

#     def form_valid(self, form):
#         csv_file = form.cleaned_data['file']
#         if not csv_file.name.endswith('.csv'):
#             return HttpResponse("Invalid file format. Please upload a CSV file.", status=400)

#         try:
#             data_set = csv_file.read().decode('UTF-8')
#             io_string = io.StringIO(data_set)
#             next(io_string)  # Skip header row

#             for row in csv.reader(io_string, delimiter=',', quotechar='"'):
#                 # Skip empty rows
#                 if len(row) < 2:  # Adjust based on the number of expected columns
#                     continue

#                 try:
#                     country_id = int(row[1])
#                     country_instance = Country.objects.get(pk=country_id)

#                     Region.objects.create(
#                         name=row[0],
#                         country=country_instance
#                     )
#                 except Country.DoesNotExist:
#                     return HttpResponse(f"Country with ID {row[1]} does not exist.", status=400)
#                 except ValueError as e:
#                     return HttpResponse(f"Error parsing row: {str(e)}", status=400)

#         except Exception as e:
#             return HttpResponse(f"An error occurred while processing the CSV file: {str(e)}", status=400)

#         return super().form_valid(form)

    
# class CSVUploadViewCity(FormView):
#     template_name = 'app/upload_city.html'
#     form_class = FileUploadForm
#     success_url = reverse_lazy('upload_city')  # Redirect after POST

#     def form_valid(self, form):
#         csv_file = form.cleaned_data['file']
#         if not csv_file.name.endswith('.csv'):
#             return HttpResponse("Invalid file format. Please upload a CSV file.", status=400)

#         data_set = csv_file.read().decode('UTF-8')
#         io_string = io.StringIO(data_set)
#         next(io_string)  # Skip header row
#         for row in csv.reader(io_string, delimiter=',', quotechar='"'):
#             try:
#                 region_id=int(row[1])
#                 region_instance=Region.objects.get(pk=region_id)
#                 # date_added = datetime.strptime(row[4], '%m/%d/%Y').date()  # Assume Date is still at the 4th index
#                 City.objects.create(
#                     name=row[0],
#                     region=region_instance
#                 )
#             except ValueError as e:
#                 return HttpResponse(f"Error parsing CSV: {str(e)}", status=400)

#         return super().form_valid(form)

# class CSVUploadViewBuilding(FormView):
#     template_name = 'app/upload_building.html'
#     form_class = FileUploadForm
#     success_url = reverse_lazy('upload_building')

#     def form_valid(self, form):
#         csv_file = form.cleaned_data['file']
#         if not csv_file.name.endswith('.csv'):
#             return HttpResponse("Invalid file format. Please upload a CSV file.", status=400)

#         try:
#             data_set = csv_file.read().decode('UTF-8')
#             io_string = io.StringIO(data_set)
#             next(io_string)  # Skip header row

#             for row in csv.reader(io_string, delimiter=',', quotechar='"'):
#                 if len(row) < 2:  # Skip malformed rows
#                     continue

#                 try:
#                     city_id = int(row[1])  # City ID from the second column
#                     city_instance = City.objects.get(pk=city_id)
#                     Building.objects.create(
#                         name=row[0],  # Building name from the first column
#                         city=city_instance
#                     )
#                 except City.DoesNotExist:
#                     return HttpResponse(f"City with ID {row[1]} does not exist.", status=400)
#                 except ValueError as e:
#                     return HttpResponse(f"Error parsing row: {str(e)}", status=400)

#         except Exception as e:
#             return HttpResponse(f"An error occurred while processing the CSV file: {str(e)}", status=400)

#         return super().form_valid(form)




# class CSVUploadView(FormView):
#     template_name = 'app/upload_invoice.html'
#     form_class = FileUploadForm
#     success_url = reverse_lazy('upload_csv')  # Redirect after successful POST

#     def form_valid(self, form):
#         csv_file = form.cleaned_data['file']
#         if not csv_file.name.endswith('.csv'):
#             return HttpResponse("Invalid file format. Please upload a CSV file.", status=400)

#         data_set = csv_file.read().decode('UTF-8')
#         io_string = io.StringIO(data_set)
#         next(io_string)  # Skip the header row

#         for row in csv.reader(io_string, delimiter=',', quotechar='"'):
#             try:
#                 # Parse the date with mm/dd/yyyy format
#                 date_added = datetime.strptime(row[6], '%m/%d/%Y').date()

#                 # Retrieve or create the Phase instance
#                 phase_instance, _ = Phase.objects.get_or_create(name=row[13])

#                 # Create the InvoiceData instance
#                 InvoiceData.objects.create(
#                     customer_ref=int(row[0]) if row[0] else None,
#                     delivery_note_ref_no=int(row[1]) if row[1] else None,
#                     supplier_name=row[2],
#                     data_source=row[3],
#                     product_description=row[4],
#                     material_name=row[5],
#                     entry_time=date_added,
#                     quantity=int(row[7]) if row[7] else None,
#                     unit_of_measure=row[8],
#                     country_name=row[9],
#                     region_name=row[10],
#                     city_name=row[11],
#                     building_name=row[12],
#                     phase_name=phase_instance,
#                     kgco2=int(row[14]) if row[14] else None,
#                 )
#             except (ValueError, IndexError) as e:
#                 return HttpResponse(f"Error parsing CSV: {str(e)}", status=400)

#         return super().form_valid(form)

###################################  CSV UPLOAD END  ##########################################################################