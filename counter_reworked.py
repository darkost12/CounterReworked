#!/usr/bin/env python
import time
import datetime
from web3.exceptions import TransactionNotFound, BlockNotFound
from web3.middleware import construct_sign_and_send_raw_middleware
from config import (
    CONFIRMATIONS,
    TARGET,
    TARGET_TIME,
    ACCOUNT,
    BASE_PRICE,
    web3,
    INSTANCE,
)


def get_transaction(tx_hash):
    """ Function that tries to get the transaction receipt.
    Args:
        hash (hex string) - Hash of transaction to be checked.
    Return:
        Tuple - Transaction and receipt or (None, None) if it doesn't
            exist.
    """
    try:
        tx_receipt = web3.eth.getTransactionReceipt(tx_hash)
        tx = web3.eth.getTransaction(tx_hash)
        return tx, tx_receipt
    except TransactionNotFound:
        return None, None
    except TypeError as error:
        if "Exactly one of the passed values can be specified." in str(error):
            return None, None
        raise error


def await_confirmations(block_hash):
    """ Function that waits for enough confirmations of block and decides to
        start over again in case of fork.
    Args:
        block_hash (hex string) - Hash of block to be checked.
    Return:
        (Bool) - Returns 'True' in case of succeeding in getting enough
            confirmations. Returns 'False' in case of block outdating.
    """
    while True:
        try:
            block_number = web3.eth.getBlock(block_hash).number
        except BlockNotFound:
            # Fork occured.
            return False
        last_block = web3.eth.blockNumber
        if (last_block - block_number) >= CONFIRMATIONS:
            return True
        time.sleep(3)


def increase_price(current_price, current_nonce, start, pending):
    """ Function that increases the gas price. Is called periodically
        according to time spent in this iteration.
    Args:
        current_price (int) - Current gas price in Wei;
        current_nonce (int) - Current nonce;
        start (float/Unix format) - Time of iteration's start;
        pending[] - Array of transactions sent with this nonce (in case if
            transaction with lower price would be mined before).
    Return:
        current_price (int) - New gas price;
        pending[] - Array of transactions with same nonce with added one.
    """
    try:
        current_price += int(current_price / 10)
        tx_hash = process_transaction(current_price, current_nonce)
        if tx_hash is not None:
            pending.append(tx_hash)
    except ValueError as error:
        # One of the txs in pending was mined during increasing process.
        if "nonce too low" in str(error):
            return current_price, pending
        if "known transaction" in str(error):
            current_price += int(current_price / 10)
            return current_price, pending
        raise error

    return current_price, pending


def adjust_price(iteration, current_price, global_start, last_tx_time):
    """ Function that decides to lower or increase the price, according to the
        time of previous transaction and the progress in reaching TARGET in
        TARGET_TIME.
    Args:
        iteration (int) - Number of previous successful transactions. Iterator
            which changes with the changing of nonce;
        current_price (int) - Current gas price in Wei;
        global_start (float/Unix format) - The start of the whole process;
        last_tx_time (float/Unix format) - Time spent in previous iteration.
    Return:
        current_price (int) - New gas price after adjustments.
    """
    if iteration > 0:
        target_ratio = TARGET_TIME / TARGET
        actual_ratio = (time.time() - global_start) / iteration
        # If we check only the duration of the latest tx, it will increase
        # the price very rapidly, ignoring the global progress.
        # So it is necessary to control the price according to plan.
        if actual_ratio < target_ratio:
            current_price -= int(current_price / 10)
        elif last_tx_time >= target_ratio:
            current_price += int(current_price / 10)
    return current_price


def process_transaction(gas_price, nonce):
    """ Function that tries to form, sign and send the transaction with given
        parameters.
    Args:
        gas_price (int) - Desired gas price;
        nonce (int) - Desired nonce.
    Return:
        (Hex string) or None - Transaction hash or None if error occured.
    """
    try:
        tx = INSTANCE.functions.increment().buildTransaction(
            {'gasPrice': gas_price, 'nonce': nonce}
        )
        return web3.eth.sendTransaction(tx)
    except ValueError as error:
        # Web3 hasn't updated the nonce yet.
        if "replacement transaction underpriced" in str(error):
            return None


def process_iteration(iteration, current_price, global_start, last_tx_time):
    """ Function that deals with the processing of transactions with same
        nonce till it's farmed and confirmed. Sub-main function of program.
    Args:
        iteration (int) - Number of previous successful transactions. Iterator
            which changes with the changing of nonce;
        current_price (int) - Current gas price in Wei;
        global_start (float/Unix format) - The start of the whole process;
        last_tx_time (float/Unix format) - Time spent in previous iteration.
    Return:
        current_price (int) - The price of successful transaction among the
            others with same nonce;
        time.time() - time_start (float/Unix format) - Time spent in this
            iteration.
    """
    in_pending = 1
    current_price = adjust_price(
        iteration, current_price, global_start, last_tx_time
    )
    while True:
        # Checking whether web3 updated the nonce after previous transaction.
        current_nonce = web3.eth.getTransactionCount(ACCOUNT.address)
        pending = [process_transaction(current_price, current_nonce)]
        if pending[0] is None:
            pending = []
        else:
            break
    time_start = time.time()
    if (((iteration + 1) % 10 == 0) and (iteration is not (TARGET - 1))) or (
        iteration == 0
    ):
        status = "Header"
    else:
        status = "Pending"
    print_log(
        iteration + 1,
        time.ctime(),
        current_nonce,
        current_price,
        status,
        pending[-1],
    )
    while True:
        for some_tx in pending:
            tx, tx_receipt = get_transaction(some_tx)
            if (tx_receipt is not None) and (tx is not None):
                current_price = tx.gasPrice
                print_log(
                    iteration + 1,
                    time.ctime(),
                    current_nonce,
                    current_price,
                    "Mined",
                    some_tx,
                )
                tx_block_hash = tx_receipt.blockHash
                if await_confirmations(tx_block_hash) is False:
                    # The fork occured. Rolling back to txs in pending
                    continue
                current_progress = str(iteration + 1)
                current_time = time.ctime()
                print_log(
                    current_progress,
                    current_time,
                    current_nonce,
                    current_price,
                    "Success",
                    some_tx,
                )
                return current_price, time.time() - time_start
        # Increasing of price is available once in 25 seconds.
        if (time.time() - time_start) >= 25 * in_pending:
            in_pending += 1
            current_price, pending = increase_price(
                current_price, current_nonce, time_start, pending
            )
            print_log(
                iteration + 1,
                time.ctime(),
                current_nonce,
                current_price,
                "Pending",
                pending[-1],
            )
        time.sleep(1)


def print_log(progress, time, nonce, price, status, tx_hash):
    """ Function that deals with printing the log in particular format.
    Args:
        progress (int) - The biased value representing the current iteration
            in format understandable to man (iteration + 1);
        time (float/Unix format) - The time of event;
        current_nonce (int) - Current nonce;
        current_price (int) - Current gas price in Wei;
        status (string) - String value representing the type of event;
        tx_hash (hex string) - The hash of event transaction.
    """
    # If "Header" status is present, it prints the string twice.
    # First time it print the header itself, second - the information itself.
    if status == "Header":
        print(
            ' {} | {} | {} | {} | {} | {} '.format(
                "#".ljust(len(str(progress))),
                "Date & Time".ljust(len(time)),
                "Nonce".ljust(7),
                "Gas Price".ljust(10),
                "Status".ljust(7),
                "Tx hash",
            )
        )
        status = "Pending"
    print(
        ' {} | {} | {} | {} | {} | {}'.format(
            progress,
            time,
            str(nonce).ljust(7),
            str(price).ljust(10),
            status.ljust(7),
            web3.toHex(tx_hash),
        )
    )


if __name__ == "__main__":
    web3.middleware_onion.add(construct_sign_and_send_raw_middleware(ACCOUNT))
    web3.eth.defaultAccount = ACCOUNT.address
    current_price = BASE_PRICE
    last_tx_time = 0
    global_start = time.time()
    print("Started at {}.".format(time.ctime()))
    for iteration in range(TARGET):
        current_price, last_tx_time = process_iteration(
            iteration, current_price, global_start, last_tx_time
        )
    print(
        "Finished {} transactions in {}.".format(
            TARGET,
            str(datetime.timedelta(seconds=(time.time() - global_start))),
        )
    )
