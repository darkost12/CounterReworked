#!/usr/bin/env python
import json
from web3 import Web3
import sys
import os
from eth_account import Account


def get_env_var(name):
    var = os.getenv(name)
    if var is None:
        sys.exit("Please set the environment variable {}".format(name))
    else:
        return var


# Establishes the web3 provider. Also gets the average gas price.
web3 = Web3(Web3.HTTPProvider(get_env_var("RPC")))
if web3.isConnected():
    print("Connected to the network!")
else:
    sys.exit("Could not connect to network. Check your RPC settings.")


CONFIRMATIONS = int(get_env_var("CONFIRMATIONS"))
TARGET = int(get_env_var("TARGET"))
TARGET_TIME = int(get_env_var("TARGET_TIME"))
ADDRESS = get_env_var("ADDRESS")
if web3.isAddress(ADDRESS) is False:
    if web3.isChecksumAddress(ADDRESS) is False:
        sys.exit("Invalid ADDRESS granted")
else:
    ADDRESS = web3.toChecksumAddress(ADDRESS)
PRIV_KEY = get_env_var("PRIV_KEY")
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
