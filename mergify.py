from flask import Flask, request,jsonify, make_response
import requests
import webbrowser
from datetime import datetime, date, time
import json
import string
import io
import csv
import sys
import atexit

API_KEY = 'aa41ca35415dda68349438aabcb0da3d'
SHARED_SECRET = '865ef2cb9f0b03b2627497b1c24b41a9'
tokenFilename = 'tokens.json'
tokens = {}

def writeAuthTokens():
    with open(tokenFilename,'w') as tokenFile:
        tokenFile.write(json.dumps(tokens))

atexit.register(writeAuthTokens)

def startup():
    global tokens
    with open(tokenFilename) as file:
        tokens = json.load(file)

def create_app():
    startup()
    return Flask(__name__)

app = create_app()

@app.route('/shopify')
def shopify():
    print(request.args['shop'])
    store = request.args['shop']
    print(buildShopifyPermissionsStoreUrl(store))
    webbrowser.open(buildShopifyPermissionsStoreUrl(store))
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
    tokens[store] = getAuthToken(code,store,hmac)
    return jsonify(success=True)

@app.route('/duplicates/orders')
def findOrdersPlacedByDuplicateCustomers():
    store = request.args['shop']
    dupeCusts = getDuplicateCustomers(store)
    si = io.StringIO()
    cw = csv.writer(si, delimiter=',', quotechar='"', quoting=csv.QUOTE_MINIMAL)
    cw.writerow(['Order Name', 'Order Link','Duplicate Customer', 'Original Customer', 'Duplicate Customer Link','Original Customer Link'])

    if len(dupeCusts) > 0:
        orders = callShopify(getAdminStoreUrl(store) + 'orders.json', tokens[store])['orders']
        for order in orders:
            customer = order['customer']
            if customer != None:
                if customer['id'] in dupeCusts:
                    pair = dupeCusts[customer['id']]                    
                    cw.writerow([order['name'],getOrderLink(store,order['id']),getCustomerName(pair[0]),getCustomerName(pair[1]),getCustomerLink(store,pair[0]['id']),getCustomerLink(store,pair[1]['id'])])
    else:
        cw.writerow('No duplicate customers found!','','','','','')
    
    output = make_response(si.getvalue())
    output.headers["Content-Disposition"] = "attachment; filename=orders_placed_by_duplicate_customers.csv"
    output.headers["Content-type"] = "text/csv"
    return output        
    

@app.route('/duplicates/customers')
def findDuplicateCustomers():
    store = request.args['shop']
    dupeCusts = getDuplicateCustomers(store)
    si = io.StringIO()
    cw = csv.writer(si, delimiter=',', quotechar='"', quoting=csv.QUOTE_MINIMAL)
    cw.writerow(['Duplicate Customer', 'Original Customer', 'Duplicate Customer Link','Original Customer Link'])

    if len(dupeCusts) == 0:
        cw.writerow('No duplicate customers found!','','','')

    for customerid,customerPair in dupeCusts.items():
        currentCustomerName = getCustomerName(customerPair[0])
        origCustomerName = getCustomerName(customerPair[1])
        currentCustomerUrl = getCustomerLink(store,customerPair[0]['id'])
        origCustomerUrl = getCustomerLink(store,customerPair[1]['id']) 
        cw.writerow([currentCustomerName,origCustomerName,currentCustomerUrl,origCustomerUrl])

    output = make_response(si.getvalue())
    output.headers["Content-Disposition"] = "attachment; filename=duplicate_customers.csv"
    output.headers["Content-type"] = "text/csv"
    return output

def getDuplicateCustomers(store):
    dupes = {}

    if store in tokens:
        customers = callShopify(getAdminStoreUrl(store) + "customers.json", tokens[store])['customers']
        for i in range(0,len(customers)):  
            firstCustomer = customers[i]
            origCustomer = firstCustomer
            for j in range(0,len(customers)): 
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
                dupes[firstCustomer['id']] = [firstCustomer,origCustomer]
    return dupes

def getCustomerLink(store,custId):
    return getAdminStoreUrl(store) + 'customers/' + str(custId)

def getCustomerName(customer):
    return customer['first_name'] + ' ' + customer['last_name']

def getOrderLink(store,orderId):
    return getAdminStoreUrl(store) + 'orders/' + str(orderId)

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
    url = getAdminStoreUrl(storename) + 'oauth/access_token'
    data = {'client_id':API_KEY,'client_secret':SHARED_SECRET,'code':code, 'hmac':hmac}
    print(data)
    r = requests.post(url, data=data)
    print(r.text)
    print(r.json()['access_token'])
    return r.json()['access_token']

def buildShopifyPermissionsStoreUrl(storename):
    scope="read_customers,write_customers,read_orders,write_orders"
    return getAdminStoreUrl(storename) + '/oauth/authorize?client_id=' + API_KEY + '&scope='+ scope +'&redirect_uri=' + getRedirectUri() 

def getRedirectUri():
    return 'https://c5a11afa.ngrok.io/redirect'

def getAdminStoreUrl(store):
        return 'https://' + store + '/admin/'

   


# /*
# TODO:
## pagination of apis
    ## bulk create and delete customers
## add buttons for export
## add unit tests
## testing more than 1 store

#V1.1:
## on callbacks
    # # verify nonce
    ## verify hmac
    ## validate store name
## use past 60 orders

#V2
## loadtest apis
 # tag the later customer as dupe of oldest
# add note on customer
# add metadata on customer
# tag later order 

# */


##STORE: https://b84f132c.ngrok.io/shopify?shop=thoughtfoxstore.myshopify.com
