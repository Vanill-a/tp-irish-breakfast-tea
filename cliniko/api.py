# This is the main wrapper for the Cliniko API
import os
import requests
import base64
import json
from dotenv import load_dotenv

load_dotenv()


def get_data(data_name: str, query: str):
    objOutput = []
    strURL = os.environ["CLINIKO_BASE_URL"] + query

    while True:
        # Get page of results
        objRequest = get_request(strURL) # What if error?
        objData = objRequest.json()
        objOutput.extend(objData[data_name])

        # Break if all results retrieved
        if "next" in objData["links"]:
            strURL = objData["links"]["next"]
        else:
            break
    
    print(str(objData["total_entries"]) + " total entries")
    return objOutput


def get_data_item(query: str):
    strURL = os.environ["CLINIKO_BASE_URL"] + query
    objRequest = get_request(strURL)
    objOutput = objRequest.json()
    return objOutput


def get_request_data(url: str):
    objRequest = get_request(url)
    objOutput = objRequest.json()
    return objOutput


def get_request(url: str):
    print("Executing API call (GET): " + url)
    objHeaders = get_headers()
    objOutput = requests.get(url=url, headers=objHeaders)
    print("Call status: " + str(objOutput.status_code))
    return objOutput


def put_data_item(query: str, data):
    strURL = os.environ["CLINIKO_BASE_URL"] + query
    objRequest = put_request(url=strURL, data=data)
    objOutput = objRequest.json()
    return objOutput


def put_request(url: str, data):
    print("Executing API call (PUT): " + url)
    objHeaders = get_headers()
    strData = json.dumps(data)
    objRequest = requests.put(url=url, data=strData, headers=objHeaders)
    print("Call status: " + str(objRequest.status_code))
    return objRequest


def post_data_item(query: str, data):
    strURL = os.environ["CLINIKO_BASE_URL"] + query
    objRequest = post_request(url=strURL, data=data)
    objOutput = objRequest.json()
    return objOutput


def post_request(url: str, data):
    print("Executing API call (POST): " + url)
    objHeaders = get_headers()
    strData = json.dumps(data)
    objRequest = requests.post(url=url, data=strData, headers=objHeaders)
    print("Call status: " + str(objRequest.status_code))
    return objRequest


def get_headers():
    # Retrieve header environment variables
    strKey = os.environ["CLINIKO_API_KEY"]
    strUser = os.environ["CLINIKO_USER"]

    # Convert API key to base64
    btaKeyBytes = strKey.encode("ascii")
    btaKeyEnc = base64.b64encode(btaKeyBytes)
    strKeyEnc = btaKeyEnc.decode("ascii")
    strAuth = "Basic " + strKeyEnc

    # Create header object
    objOutput = {
        "authorization": strAuth,
        "content-type": "application/json",
        "user-agent": strUser
    }

    return objOutput


def get_base_url_len():
    return len(os.environ["CLINIKO_BASE_URL"])