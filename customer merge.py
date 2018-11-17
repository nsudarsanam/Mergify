#https://2e39fa71414dc511c0e60585e9f9bdf1:f04a32f09923ba06f837dec6d8afc628@thoughtfoxstore.myshopify.com/admin/orders.json
import shopify
import json
import requests
import sys
import base64
import dateutil.parser
from dateutil import tz
import pytz
import datetime

# merge happens automatically if the same phone number is used
# handle pagination
# handle since date
# when an order comes in, see if there is a duplicate customer, add tag on the dupe, upate email with dupe

API_KEY = '2e39fa71414dc511c0e60585e9f9bdf1'
API_PWD = 'f04a32f09923ba06f837dec6d8afc628'
STORE_URL = 'https://thoughtfoxstore.myshopify.com/admin/'


def main():
    getOrders()


def getOrders():
        orders = makeShopifyUrl(STORE_URL + "orders.json")
        for order in orders['orders']:
            if order['fulfillment_status'] == None:
                processedAtDate = dateutil.parser.parse(order['processed_at'])
                localDatetime = processedAtDate.astimezone(dateutil.tz.tzlocal())
                numDays =(datetime.datetime.now().date() - localDatetime.date()).days
                if numDays>= 2:
                    print(f'Send a reminder, order has been unfulfilled for {numDays} days')
                else:
                    print('Orders are all good')
                

 
def makeShopifyUrl(url):
    try:
        print(url)
        key = (base64.b64encode((API_KEY + ':'  + API_PWD).encode('utf-8'))).decode('ascii')
        response = requests.get(url, headers = {'Authorization': 'Basic ' + key})
        responseText = response.json()
        return responseText
    except requests.exceptions.RequestException as e:
        print(e)
        sys.exit(1)



if __name__ == '__main__':
    main()


