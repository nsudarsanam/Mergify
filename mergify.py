from flask import Flask, request
import requests
app = Flask(__name__)
import shopify
import webbrowser
import dateutil.parser
from dateutil import tz
import pytz
import datetime

API_KEY = 'aa41ca35415dda68349438aabcb0da3d'
SHARED_SECRET = '865ef2cb9f0b03b2627497b1c24b41a9'

@app.route('/shopify')
def shopify():
    print("here")
    print(request.args['shop'])
    print(buildShopifyPermissionsStoreUrl(request.args['shop']))
    webbrowser.open(buildShopifyPermissionsStoreUrl(request.args['shop']))

@app.route('/redirect')
def redirect():
    store = request.args['shop']
    code = request.args['code']
    hmac = request.args['hmac']
    print(code)
    print(hmac)
    print(store)
    print(request.args['timestamp'])
    authToken = getAuthToken(code,store,hmac)
    getOrders(store,authToken)
    return 'Success!'

def getOrders(store,authToken):
    orders = callShopify(getAdminStoreUrl(store) + "orders.json", authToken)
    for order in orders['orders']:
        if order['fulfillment_status'] == None:
            processedAtDate = dateutil.parser.parse(order['processed_at'])
        localDatetime = processedAtDate.astimezone(dateutil.tz.tzlocal())
        numDays =(datetime.datetime.now().date() - localDatetime.date()).days
        if numDays>= 2:
            print(f'Send a reminder, order has been unfulfilled for {numDays} days')
        else:
            print('Orders are all good')

def callShopify(url,authToken):
    try:
        print(url)
        response = requests.get(url, headers = {'X-Shopify-Access-Token': authToken})
        responseText = response.json()
        return responseText
    except requests.exceptions.RequestException as e:
        print(e)
        sys.exit(1)


def getAuthToken(code,storename,hmac):
    url = getAdminStoreUrl(storename) + 'oauth/access_token'
    print(url)
    data = {'client_id':API_KEY,'client_secret':SHARED_SECRET,'code':code, 'hmac':hmac}
    print(data)
    r = requests.post(url, data=data)
    print(r.text)
    print(r.json()['access_token'])
    return r.json()['access_token']
  
def buildShopifyPermissionsStoreUrl(storename):
    scope="read_customers,write_customers,read_orders,write_orders"
    return getAdminStoreUrl(storename) + '/oauth/authorize?client_id=' + API_KEY + '&scope='+ scope +'&redirect_uri=' + getRedirectUri() 

def getAdminStoreUrl(storename):
    return 'https://' + storename + '/admin/'

def getRedirectUri():
    return 'https://8d7e9a1e.ngrok.io/redirect'
   


# /*
# TODO:
## on callbacks
# # verify nonce
## verify hmac
## validate store name
# */


##STORE: https://8d7e9a1e.ngrok.io/shopify?shop=thoughtfoxstore.myshopify.com
