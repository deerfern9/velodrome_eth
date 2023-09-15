import random
import time

import requests
from web3 import Web3
from datetime import datetime
from colorama import Fore, init

from config import *
init()

colors = {
    'time': Fore.MAGENTA,
    'account_info': Fore.CYAN,
    'message': Fore.BLUE,
    'error_message': Fore.RED,
    'reset': Fore.RESET
}

web3 = Web3(Web3.HTTPProvider(op_rpc))
eth_web3 = Web3(Web3.HTTPProvider(ethereum_rpc))

velodrome_contract = web3.eth.contract(address=web3.to_checksum_address(velodrome_address), abi=velodrome_abi)
usdc_contract = web3.eth.contract(address=web3.to_checksum_address(usdc_address), abi=usdc_abi)


def read_file(filename):
    result = []
    with open(filename, 'r') as file:
        for tmp in file.readlines():
            result.append(tmp.strip())

    return result


def write_to_file(filename, text):
    with open(filename, 'a') as file:
        file.write(f'{text}\n')


def new_print(message_type, message, is_error=False):
    print(f'{colors["time"]}{datetime.now().strftime("%d %H:%M:%S")}{colors["account_info"]} | {message_type} |'
          f' {colors[(["message", "error_message"])[is_error]]}{message}{colors["reset"]}')


def wait_normal_gwei():
    while (eth_gwei := web3.from_wei(eth_web3.eth.gas_price, 'gwei')) > max_gwei:
        new_print('INFO', f"Current gas fee {eth_gwei} gwei > {max_gwei} gwei. Waiting for 17 seconds...")
        time.sleep(17)


def get_eth_price():
    usd_price = requests.get('https://min-api.cryptocompare.com/data/price?fsym=ETH&tsyms=USD')
    return usd_price.json()['USD']


def approve(private, token_contract):
    wait_normal_gwei()
    address = web3.eth.account.from_key(private).address
    tx = token_contract.functions.approve(web3.to_checksum_address(velodrome_address), 2**256-1).build_transaction({
        'from': address,
        'gasPrice': web3.eth.gas_price,
        'nonce': web3.eth.get_transaction_count(address),
        'chainId': web3.eth.chain_id,
    })
    tx_create = web3.eth.account.sign_transaction(tx, private)
    tx_hash = web3.eth.send_raw_transaction(tx_create.rawTransaction)

    new_print(address, f'Approving hash: {tx_hash.hex()}')
    write_to_file('approving hashes .txt', f'{private};{address};{tx_hash.hex()}')
    web3.eth.wait_for_transaction_receipt(tx_hash)


def add_eth_liquidity(private):
    address = web3.eth.account.from_key(private).address
    approve(private, usdc_contract)

    amount_desired = usdc_contract.functions.balanceOf(address).call()
    amount_min1 = int(amount_desired * 0.95)
    eth_price = get_eth_price()
    eth_amount = web3.to_wei((1 / eth_price) * (amount_desired / 1_000_000) * 0.995, 'ether')
    wait_normal_gwei()
    tx = velodrome_contract.functions.addLiquidityETH(
        usdc_address, False, amount_desired, amount_min1, eth_amount, address, int(time.time() + 1800)
    ).build_transaction({
        'from': address,
        'value': eth_amount,
        'gasPrice': web3.eth.gas_price,
        'nonce': web3.eth.get_transaction_count(address),
        'chainId': web3.eth.chain_id,
    })

    tx_create = web3.eth.account.sign_transaction(tx, private)
    tx_hash = web3.eth.send_raw_transaction(tx_create.rawTransaction)
    new_print(address, f'ETH liquidity added: {tx_hash.hex()}')
    write_to_file('adding liquidity hashes .txt', f'{private};{address};{tx_hash.hex()}')


def main():
    privates = read_file('privates.txt')
    for private in privates:
        try:
            try:
                add_eth_liquidity(private)
                time.sleep(random.randint(*delay))

            except Exception as e:
                print(web3.eth.account.from_key(private).address, e)
                write_to_file('errors.txt', f'{private};{e}')
        except Exception as e:
            new_print(web3.eth.account.from_key(private).address, f'Error: {e}', is_error=True)


if __name__ == '__main__':
    main()
