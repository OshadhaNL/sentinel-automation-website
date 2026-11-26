"""A fresh, clearly named transaction using explicitly supplied disposable parties."""
from uuid import uuid4


def fill_new_transaction(transaction, seller, buyer):
    address = 'QA Workflow Property ' + uuid4().hex[:12]
    transaction.open_add_modal()
    transaction.choose_or_create_property(address)
    transaction.select_option('propertyType', 'Residential')
    transaction.select_option('paymentMethod', 'Bank Transfer')
    transaction.select_currency('AUD')
    transaction.fill_field('propertyValue', '250000')
    transaction.fill_field('amount', '25000')
    transaction.select_valid_form_date_for_test()
    transaction.select_party('seller', seller)
    transaction.select_party('buyer', buyer)
    return address


def create_transaction(transaction, seller, buyer):
    address = fill_new_transaction(transaction, seller, buyer)
    transaction.submit_modal()
    return transaction.find_by_address(address)['id'], address
