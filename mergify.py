from flask import Flask, request,jsonify, make_response, render_template,redirect
import requests
import json
import string
import io
import csv
import sys
import atexit
import os
import logging
import dateutil.parser

API_KEY = 'aa41ca35415dda68349438aabcb0da3d'
SHARED_SECRET = '865ef2cb9f0b03b2627497b1c24b41a9'
NUM_CUSTOMERS_PER_PAGE = 50
NUM_ORDERS_PER_PAGE = 50
HOST_NAME ='https://persephone.us/'
HOST_NAME_DEV ='https://ef2ff400.ngrok.io/'
tokenFilename = 'tokens.json'

def writeAuthTokens(tokens):
    with open(tokenFilename,'w') as tokenFile:
        tokenFile.write(json.dumps(tokens))

def readAuthTokens():
    tokens = {}
    if os.path.isfile(tokenFilename):
        with open(tokenFilename) as file:
            tokens = json.load(file)
    return tokens

def updateTokensDict(store,token):
    tokens = readAuthTokens()
    tokens[store] = token
    writeAuthTokens(tokens)

def create_app():
    logging.basicConfig(filename='mergify.log',level=logging.DEBUG)
    return Flask(__name__)

app = create_app()

@app.route('/')
def root():
    return jsonify(success=True)

@app.route('/shopify')
def shopify():
    logging.info(request.args['shop'])
    store = request.args['shop']
    logging.info(buildShopifyPermissionsStoreUrl(store))
    return redirect(buildShopifyPermissionsStoreUrl(store),code="302")

@app.route('/redirectShop')
def redirectShop():
    store = request.args['shop']
    code = request.args['code']
    hmac = request.args['hmac']
    logging.info(code)
    logging.info(hmac)
    logging.info(store)
    logging.info(request.args['timestamp'])
    authToken = getAuthToken(code,store,hmac)
    updateTokensDict(store,authToken)
    return render_template('confirmation.html')

@app.route('/duplicates/orders/export')
def findOrdersPlacedByDuplicateCustomersExport():
    store = request.args['shop']
    tokens = readAuthTokens()
    dupeCusts = getDuplicateCustomers(store,tokens)
    si = io.StringIO()
    cw = csv.writer(si, delimiter=',', quotechar='"', quoting=csv.QUOTE_MINIMAL)
    cw.writerow(['Order Name', 'Order Link','Duplicate Customer', 'Original Customer', 'Duplicate Customer Link','Original Customer Link'])

    if len(dupeCusts) > 0:
        orders = getPaginatedOrders(store,tokens)
        for order in orders:
            if 'customer' in order:
                customer = order['customer']
                if customer['id'] in dupeCusts:
                    pair = dupeCusts[customer['id']]                    
                    cw.writerow([order['name'],getOrderLink(store,order['id']),getCustomerName(pair[0]),getCustomerName(pair[1]),getCustomerLink(store,pair[0]['id']),getCustomerLink(store,pair[1]['id'])])
    else:
        cw.writerow('No duplicate customers found!','','','','','')
    
    output = make_response(si.getvalue())
    output.headers["Content-Disposition"] = "attachment; filename=orders_placed_by_duplicate_customers.csv"
    output.headers["Content-type"] = "text/csv"
    return output        

@app.route('/duplicates/orders')
def findDuplicateOrders():
    store = request.args['shop']
    tokens = readAuthTokens()
    dupeCusts = getDuplicateCustomers(store,tokens)
    link = HOST_NAME + ("duplicates/orders/export?shop={0}").format(store)
    return render_template('orders.html',count=len(dupeCusts),link=link)
    
@app.route('/duplicates/customers')
def findDuplicateCustomers():
    store = request.args['shop']
    tokens = readAuthTokens()
    dupeCusts = getDuplicateCustomers(store,tokens)
    link = HOST_NAME + ("duplicates/customers/export?shop={0}").format(store)
    return render_template('customers.html',count=len(dupeCusts),link=link)

@app.route('/duplicates/customers/export')
def findDuplicateCustomersExport():
    store = request.args['shop']
    tokens = readAuthTokens()
    dupeCusts = getDuplicateCustomers(store,tokens)
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
   
def getDuplicateCustomers(store,tokens):
    dupes = {}
    if store in tokens:
        customers = getPaginatedCustomers(store,tokens)
        for i in range(0,len(customers)):  
            firstCustomer = customers[i]
            origCustomer = firstCustomer
            for j in range(0,len(customers)): 
                if i == j:
                    continue
                origCreatedAt = dateutil.parser.parse(origCustomer['created_at'])    
                secondCustomer = customers[j]
                if areDuplicateCustomers(firstCustomer,secondCustomer):
                    secondCustomerCreatedAt = dateutil.parser.parse(secondCustomer['created_at'])
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

def getPaginatedCustomers(store,tokens):
    logging.info(tokens[store])
    logging.info(callShopify(getAdminStoreUrl(store) + "customers/count.json", tokens[store]))
    numCustomers = callShopify(getAdminStoreUrl(store) + "customers/count.json", tokens[store])['count']
    numPages = int(numCustomers/NUM_CUSTOMERS_PER_PAGE) + 1
    logging.info(numPages)
    allCustomers = []
    for i in range(1,numPages + 1):
        pageUrl = "?page={0}".format(i)
        customers = callShopify(getAdminStoreUrl(store) + "customers.json" + pageUrl, tokens[store])['customers']
        allCustomers.extend(customers)
    return allCustomers

def getPaginatedOrders(store,tokens):
    numOrders = callShopify(getAdminStoreUrl(store) + "orders/count.json?status=any", tokens[store])['count']
    numPages = int(numOrders/NUM_ORDERS_PER_PAGE) + 1
    logging.info(numPages)
    allOrders = []
    for i in range(1,numPages + 1):
        pageUrl = "?page={0}&status=any".format(i)
        orders = callShopify(getAdminStoreUrl(store) + "orders.json" + pageUrl, tokens[store])['orders']
        allOrders.extend(orders)
    return allOrders

def areDuplicateCustomers(firstCustomer, secondCustomer):
    # if 2 people have the same phone number OR same address - 1) tag as duplicate 2) add note 3) apply metadata field
    translator = str.maketrans('','',string.punctuation + string.whitespace)
    if firstCustomer['phone'] != None and secondCustomer['phone'] != None and firstCustomer['phone'].translate(translator) == secondCustomer['phone'].translate(translator):
        logging.info('Customer {0} and Customer {1} have the same phone number'.format(firstCustomer['id'],secondCustomer['id']))
        return true
    else:
        firstCustomer_address1 = xstr(firstCustomer['default_address']['address1']).lower()
        secondCustomer_address1= xstr(secondCustomer['default_address']['address1']).lower()
        firstCustomer_address2 = xstr(firstCustomer['default_address']['address2']).lower()
        secondCustomer_address2= xstr(secondCustomer['default_address']['address2']).lower()
        firstCustomer_city = xstr(firstCustomer['default_address']['city']).lower()
        secondCustomer_city= xstr(secondCustomer['default_address']['city']).lower()
        firstCustomer_province = xstr(firstCustomer['default_address']['province']).lower()
        secondCustomer_province= xstr(secondCustomer['default_address']['province']).lower()
        firstCustomer_country = xstr(firstCustomer['default_address']['country']).lower()
        secondCustomer_country= xstr(secondCustomer['default_address']['country']).lower()
        firstCustomer_zip = xstr(firstCustomer['default_address']['zip']).lower()
        secondCustomer_zip = xstr(secondCustomer['default_address']['zip']).lower()
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
        logging.info(e)
        sys.exit(1)


def getAuthToken(code,storename,hmac):
    url = getAdminStoreUrl(storename) + 'oauth/access_token'
    data = {'client_id':API_KEY,'client_secret':SHARED_SECRET,'code':code, 'hmac':hmac}
    logging.info(data)
    r = requests.post(url, data=data)
    logging.info(r.text)
    logging.info(r.json()['access_token'])
    return r.json()['access_token']

def buildShopifyPermissionsStoreUrl(storename):
    scope="read_customers,write_customers,read_orders,write_orders"
    return getAdminStoreUrl(storename) + 'oauth/authorize?client_id=' + API_KEY + '&scope='+ scope +'&redirect_uri=' + getRedirectUri() 

def getRedirectUri():
    return HOST_NAME + 'redirectShop'

def getAdminStoreUrl(store):
    return 'https://' + store + '/admin/'

def xstr(s):
    return '' if s is None else s


# /*
# TODO:
## testing more than 1 store

#V1.1:
## on callbacks
    # # verify nonce
    ## verify hmac
    ## validate store name
## use past 60 orders
## redo tokens.json

#V1.5
    ##library between bulkcreate and mergify
#V2
## loadtest apis
 # tag the later customer as dupe of oldest
# add note on customer
# add metadata on customer
# tag later order 

#To change domain
# - change appsettings in admin
# - change hostname headers
# - change redirects in admin
# */


##STORE: https://b84f132c.ngrok.io/shopify?shop=thoughtfoxstore.myshopify.com
##STORE: https://persephone.us/shopify?shop=thoughtfoxstore.myshopify.com
