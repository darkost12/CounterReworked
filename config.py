#!/usr/bin/env python
import json
import sys
import os
from web3 import Web3
from eth_account import Account


def getenv_or_exit(name):
    """ Gets the required variable from the environment. Closes the application
    with error if it's not set.
    Args:
        name (string) - The name of required environment variable.
    Return:
        var (respective type) - The value of the variable.
        """
    var = os.getenv(name)
    if var is None:
        sys.exit("Please set the environment variable {}".format(name))
    else:
        return var


# Establishes the web3 provider. Also gets the average gas price.
web3 = Web3(Web3.HTTPProvider(getenv_or_exit("RPC")))
if web3.isConnected():
    print("Connected to the network!")
else:
    sys.exit("Could not connect to network. Check your RPC settings.")


CONFIRMATIONS = int(getenv_or_exit("CONFIRMATIONS"))
TARGET = int(getenv_or_exit("TARGET"))
TARGET_TIME = int(getenv_or_exit("TARGET_TIME"))
ADDRESS = getenv_or_exit("ADDRESS")
if web3.isAddress(ADDRESS) is False:
    if web3.isChecksumAddress(ADDRESS) is False:
        sys.exit("Invalid ADDRESS granted")
else:
    ADDRESS = web3.toChecksumAddress(ADDRESS)
PRIV_KEY = getenv_or_exit("PRIV_KEY")
ACCOUNT = Account.privateKeyToAccount(PRIV_KEY)


# Configuration warnings.
if TARGET * ((CONFIRMATIONS + 1) * 16.5) > TARGET_TIME:
    print(
        'Strongly advising you to reconsider the configuration!'
        '\nAccording to average mining and confirmation speed,'
        'this is nearly impossible. Performance is not guaranteed.'
        '\nAlso it can lead to excessive expenditures.'
    )
elif TARGET_TIME / (TARGET * 60) <= 1:
    print(
        'Current configuration targets are hard to reach'
        'due to possible network fluctuations.'
    )


BASE_PRICE = int(web3.eth.gasPrice / 10)


# Creates contract instance.
if os.path.exists("abi.json") is True and os.path.isfile("abi.json") is True:
    with open("abi.json") as file:
        abi = json.load(file)
    INSTANCE = web3.eth.contract(address=ADDRESS, abi=abi)
else:
    sys.exit("ABI should be present in file \'abi.json\'")
