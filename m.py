"""Example of keys derivation using BIP84."""

from bip_utils import Bip39MnemonicGenerator, Bip39SeedGenerator, Bip39WordsNum, Bip44Changes, Bip84, Bip84Coins
from bip_utils import Bip39MnemonicGenerator, Bip39SeedGenerator, Bip39WordsNum, Bip44, Bip44Changes, Bip44Coins

from hdwallet.utils import generate_mnemonic



import asyncio

import aiohttp
import aiofiles

import time

# Create a lock to synchronize print statements
print_lock = asyncio.Lock()

# Counters
address_counter = 0
checked_addresses = 0
total_keys_checked = 0
found_addresses_counter = 0  # New counter for found addresses
error_count = 0  # New variable to track the number of errors

# Time tracking
start_time = time.time()

async def get_bal_async(session, addr, max_retries=3):
    url = f"https://bitcoin.atomicwallet.io/api/v2/address/{addr}"

    for attempt in range(max_retries):
        try:
            async with session.get(url) as response:
                if 'application/json' not in response.headers.get('Content-Type', ''):
                    raise ValueError(f"Unexpected response format: {response.content}")

                data = await response.json()
                if 'error' in data:
                    raise ValueError(f"API Error: {data['error']}")
                return int(data['balance']) 
        except Exception as e:
            print(f"Error fetching balance for {addr}. Retrying... (Attempt {attempt + 1}/{max_retries})")
            await asyncio.sleep(1)  # Introduce a short delay between retries

    raise ValueError(f"Failed to fetch balance for {addr} after {max_retries} attempts.")


async def generate_random_private_key_and_address():
    ADDR_NUM: int = 1
    STRENGTH: int = 128
    LANGUAGE: str = "english"
    MNEMONIC = generate_mnemonic(language=LANGUAGE, strength=STRENGTH)
    seed_bytes = Bip39SeedGenerator(MNEMONIC).Generate()

    bip84_mst_ctx = Bip84.FromSeed(seed_bytes, Bip84Coins.BITCOIN)
    bip84_acc_ctx = bip84_mst_ctx.Purpose().Coin().Account(0)
    bip84_chg_ctx = bip84_acc_ctx.Change(Bip44Changes.CHAIN_EXT)

    # bip44_mst_ctx = Bip44.FromSeed(seed_bytes, Bip44Coins.BITCOIN)
    # bip44_acc_ctx = bip44_mst_ctx.Purpose().Coin().Account(0)
    # bip44_chg_ctx = bip44_acc_ctx.Change(Bip44Changes.CHAIN_EXT)

    
    
    # bip44x=[]
    for i in range(ADDR_NUM):
        bip84_addr_ctx = bip84_chg_ctx.AddressIndex(i)
        bip84x = bip84_addr_ctx.PublicKey().ToAddress()
    # for i in range(ADDR_NUM):
    #     bip44_addr_ctx = bip44_chg_ctx.AddressIndex(i)

    #     bip44x.append(bip44_addr_ctx.PublicKey().ToAddress())
    
    return MNEMONIC,bip84x

async def save_to_file_async(private_key, btc_address, balance):
    
        global address_counter
        address_counter += 1
        file_name = f"{btc_address}.txt"
        async with aiofiles.open(file_name, 'w') as file:
            await file.write(f"Private Key: {private_key}\n")
            await file.write(f"Bitcoin Address: {btc_address}\n")
            await file.write(f"Balance: {balance} BTC\n")
        async with print_lock:
            print(f"Data saved to {file_name}")

async def generate_and_check_address():
    global checked_addresses, start_time, total_keys_checked, found_addresses_counter, error_count
    try:
        private_key, btc_address = await generate_random_private_key_and_address()

        async with aiohttp.ClientSession() as session:
            balance = await get_bal_async(session, btc_address)

        checked_addresses += 1
        total_keys_checked += 1  # Increment total keys checked
        elapsed_time = time.time() - start_time
        speed = checked_addresses / elapsed_time

        async with print_lock:
            line_to_print = (
                f"\rTime : {time.strftime('%Y-%m-%d %H:%M:%S')} | "
                f"Total Keys Checked: {total_keys_checked} | "
                f"Found Addresses: {found_addresses_counter} | "
                f"Errors: {error_count} | "
                f"Speed: {speed:.2f} key/s"
            )
            print(line_to_print, end='', flush=True)  # Overwrite the previous content

        if balance > 1:
            found_addresses_counter += 1  # Increment found addresses counter
            async with print_lock:
                line_to_print += f" | Address #{address_counter}: {btc_address} - Private Key: {private_key[:6]}...{private_key[-3:]} - Balance: {balance} BTC"
                line_to_print += f" | Found Addresses with Balance: {found_addresses_counter}"
                print(line_to_print)

            await save_to_file_async(private_key, btc_address, balance)

    except Exception as e:
        error_count += 1  # Increment error count
        async with print_lock:
            line_to_print = f"\rAn error occurred: {e} - Errors: {error_count}"
            print(line_to_print, end='', flush=True)

async def main():
    num_threads = 200

    while True:
        tasks = [generate_and_check_address() for _ in range(num_threads)]
        await asyncio.gather(*tasks)
        await asyncio.sleep(0)  # Update the time every 1 second

if __name__ == "__main__":
    asyncio.run(main())
