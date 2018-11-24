
import sys
import json
from faker import Faker
import json
import requests
import random
import time
from faker_e164.providers import E164Provider

#reuses token from mergify
TOKEN_FILENAME = 'tokens.json'
STORE = "thoughtfoxstore.myshopify.com"
STORE_URL = "https://thoughtfoxstore.myshopify.com/admin/"
TOTAL_CUSTOMERS = 60 #50 dupes, 10 uniques
TOTAL_ORDERS = 120 # 
tokens = {}


def createCustomers():
    for i in range(1,26):
        customer = getFakeCustomer()
        postCustomerToShopify(customer)
        time.sleep(3)
        postCustomerToShopify(cloneFakeCustomer(customer))
        time.sleep(3)
    for i in range(1,11):
        customer = getFakeCustomer()
        postCustomerToShopify(customer)
        time.sleep(3)

def createOrders():
    # get all customers
    # for every customer, create and assign to TOTAL_ORDERS/len(all customers)

def postCustomerToShopify(customer):
    customerContainer = {}    
    customerContainer["customer"] = customer
    responseText = postToShopify(STORE_URL + "customers.json",tokens[STORE],customerContainer)
    print(responseText)

def getFakeCustomer():
    customer = {}
    fake = Faker()
    fake.add_provider(E164Provider)
    customer['first_name'] = fake.first_name()
    customer['last_name'] = fake.last_name()
    customer['email'] = fake.profile()['username'] + '@gmail.com'
    customer['verified_email'] = True
    addresses = []
    address = {}
    address['address1'] = fake.street_address() 
    address['city'] = fake.city()
    address['province'] = fake.state_abbr()
    address['zip'] = fake.postcode()
    address['first_name'] = fake.first_name()
    address['last_name'] = fake.last_name()
    address['country'] = 'US'
    addresses.append(address)
    customer['addresses'] = addresses

    print(customer['email'])
    return customer

def cloneFakeCustomer(customer):
    fake = Faker()
    fake.add_provider(E164Provider)
    customer['first_name'] = fake.first_name()
    customer['last_name'] = fake.last_name()
    customer['email'] = fake.profile()['username'] + '@gmail.com'
    return customer

def main():
    global tokens
    with open(TOKEN_FILENAME) as file:
        tokens = json.load(file)

    if sys.argv[1] == 'cc':
        createCustomers()
    if sys.argv[1] == 'co':
        createOrders()
  

def postToShopify(url,authToken,payload):
    responseText = ''
    try:
        response = requests.post(url, headers = {'X-Shopify-Access-Token': authToken},json=payload)
        responseText = response.text
        return responseText
    except requests.exceptions.RequestException as e:
        responseText = e


if __name__ == '__main__':
    main()

