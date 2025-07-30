from django.test import TestCase

# Create your tests here.
import requests

def lambda_handler(event, context):
    try:
        response = requests.get("https://www.google.com", timeout=5)
        print("✅ Internet is working. Status code:", response.status_code)
    except Exception as e:
        print("Internet not working. Error:", str(e))