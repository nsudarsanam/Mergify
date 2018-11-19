from flask import Flask, request,jsonify, make_response
import requests
app = Flask(__name__)
import webbrowser
from datetime import datetime, date, time
import json
import string
import io
import csv
import sys

API_KEY = 'aa41ca35415dda68349438aabcb0da3d'
SHARED_SECRET = '865ef2cb9f0b03b2627497b1c24b41a9'

class ShopifySession:
    def __init__(self):
        self.token = ""
        self.store = ""
    
    def setToken(self,token):
        self.token = token

    def setStore(self,store):
        self.store = store

    def getAdminStoreUrl(self):
        return 'https://' + self.store + '/admin/'

class ShopifyCustomer:
    def __init__(self,customer):
        self.__dict__ = customer

currentSession = ShopifySession()

@app.route('/shopify')
def shopify():
    print(request.args['shop'])
    currentSession.setStore(request.args['shop'])
    print(buildShopifyPermissionsStoreUrl(currentSession.store))
    webbrowser.open(buildShopifyPermissionsStoreUrl(currentSession.store))
    return jsonify(success=True)

@app.route('/redirect')
def redirect():
    store = request.args['shop']
    code = request.args['code']
    hmac = request.args['hmac']
    print(code)
    print(hmac)
    print(store)
    print(request.args['timestamp'])
    currentSession.setToken(getAuthToken(code,currentSession.store,hmac))
    return jsonify(success=True)

@app.route('/duplicates/customers')
def findDuplicateCustomers():
    customers = callShopify(currentSession.getAdminStoreUrl() + "customers.json", currentSession.token)['customers']
    si = io.StringIO()
    cw = csv.writer(si, delimiter=',', quotechar='"', quoting=csv.QUOTE_MINIMAL)
    cw.writerow(['Duplicate Customer', 'Original Customer', 'Duplicate Customer Link','Original Customer Link'])
    foundDupes = False
    for i in range(0,len(customers)):  # 0, 1, 2
        firstCustomer = customers[i]
        origCustomer = firstCustomer
        for j in range(0,len(customers)): #1,2,3
            if i == j:
                continue
            origCreatedAt = datetime.strptime(origCustomer['created_at'], "%Y-%m-%dT%H:%M:%SZ")  
            secondCustomer = customers[j]
            if areDuplicateCustomers(firstCustomer,secondCustomer):
                secondCustomerCreatedAt = datetime.strptime(secondCustomer['created_at'], "%Y-%m-%dT%H:%M:%SZ")
                if secondCustomerCreatedAt <= origCreatedAt:
                    origCustomer = secondCustomer
                    foundDupes = True
        if origCustomer['id'] != firstCustomer['id']:
            cw.writerow(generateDuplicateCustomer(firstCustomer,origCustomer))

    if foundDupes:
        output = make_response(si.getvalue())
        output.headers["Content-Disposition"] = "attachment; filename=duplicate_customers.csv"
        output.headers["Content-type"] = "text/csv"
        return output
    else:
        return jsonify(success=True)

def generateDuplicateCustomer(currentCustomer,origCustomer):
    # t1 = datetime.strptime(firstCustomer['created_at'], "%Y-%m-%dT%H:%M:%SZ")
    # t2 = datetime.strptime(secondCustomer['created_at'], "%Y-%m-%dT%H:%M:%SZ")
    currentCustomerName = currentCustomer['first_name'] + ' ' + currentCustomer['last_name']
    origCustomerName = origCustomer['first_name'] + ' ' + origCustomer['last_name']
    currentCustomerUrl = currentSession.getAdminStoreUrl() + 'customers/' + str(currentCustomer['id'])
    origCustomerUrl = currentSession.getAdminStoreUrl() + 'customers/' + str(origCustomer['id'])

    return [currentCustomerName,origCustomerName,currentCustomerUrl,origCustomerUrl]
    # if t1 <= t2:
    #     #customer2 is duplicate of customer1
    #     return [secondCustomerName,firstCustomerName,secondCustomerUrl,firstCustomerUrl]
    # else:
    #     #customer1 is duplicate of customer2
    #     #Duplicate customer name, Original Customer name, Duplicate customer url, Original customer url
    #     return [firstCustomerName,secondCustomerName,firstCustomerUrl,secondCustomerUrl]

#[{"DuplicateCustomerName","OriginalCustomerName","DuplicateCustomerUrl","OriginalCustomerUrl"}]
def areDuplicateCustomers(firstCustomer, secondCustomer):
    # if 2 people have the same phone number OR same address - 1) tag as duplicate 2) add note 3) apply metadata field
    translator = str.maketrans('','',string.punctuation + string.whitespace)
    if firstCustomer['phone'] != None and secondCustomer['phone'] != None and firstCustomer['phone'].translate(translator) == secondCustomer['phone'].translate(translator):
        print('Customer {0} and Customer {1} have the same phone number'.format(firstCustomer['id'],secondCustomer['id']))
        return true
    else:
        firstCustomer_address1 = firstCustomer['default_address']['address1'].lower()
        secondCustomer_address1= secondCustomer['default_address']['address1'].lower()
        firstCustomer_address2 = firstCustomer['default_address']['address2'].lower()
        secondCustomer_address2= secondCustomer['default_address']['address2'].lower()
        firstCustomer_city = firstCustomer['default_address']['city'].lower()
        secondCustomer_city= secondCustomer['default_address']['city'].lower()
        firstCustomer_province = firstCustomer['default_address']['province'].lower()
        secondCustomer_province= secondCustomer['default_address']['province'].lower()
        firstCustomer_country = firstCustomer['default_address']['country'].lower()
        secondCustomer_country= secondCustomer['default_address']['country'].lower()
        firstCustomer_zip = firstCustomer['default_address']['zip'].lower()
        secondCustomer_zip = secondCustomer['default_address']['zip'].lower()
        return ((firstCustomer_address1.translate(translator) == secondCustomer_address1.translate(translator)) and
               (firstCustomer_address2.translate(translator) == secondCustomer_address2.translate(translator)) and
               (firstCustomer_city.translate(translator) == secondCustomer_city.translate(translator)) and 
               (firstCustomer_province.translate(translator) == secondCustomer_province.translate(translator))and
               (firstCustomer_country.translate(translator) == secondCustomer_country.translate(translator)) and
               (firstCustomer_zip.translate(translator) == secondCustomer_zip.translate(translator)))
        

def callShopify(url,authToken):
    try:
        response = requests.get(url, headers = {'X-Shopify-Access-Token': authToken})
        responseText = response.json()
        return responseText
    except requests.exceptions.RequestException as e:
        print(e)
        sys.exit(1)


def getAuthToken(code,storename,hmac):
    url = currentSession.getAdminStoreUrl() + 'oauth/access_token'
    data = {'client_id':API_KEY,'client_secret':SHARED_SECRET,'code':code, 'hmac':hmac}
    print(data)
    r = requests.post(url, data=data)
    print(r.text)
    print(r.json()['access_token'])
    return r.json()['access_token']
  
def buildShopifyPermissionsStoreUrl(storename):
    scope="read_customers,write_customers,read_orders,write_orders"
    return currentSession.getAdminStoreUrl() + '/oauth/authorize?client_id=' + API_KEY + '&scope='+ scope +'&redirect_uri=' + getRedirectUri() 

# def getAdminStoreUrl(storename):
#     return 'https://' + storename + '/admin/'

def getRedirectUri():
    return 'https://8026c3ee.ngrok.io/redirect'
   


# /*
# TODO:
## on callbacks
# # verify nonce
## verify hmac
## validate store name
## load test apis
## pagination of apis

#V2
 # tag the later customer as dupe of oldest
    # add note
    # add metadata
   
# */


##STORE: https://b84f132c.ngrok.io/shopify?shop=thoughtfoxstore.myshopify.com
