import argparse
import asyncio
from bleak import BleakScanner, BleakClient

mac = 'F0:5E:CD:25:A1:16'


async def main():
    print("scanning for 5 seconds, please wait...")

    dev = await BleakScanner.find_device_by_address(
        mac, cb={"use_bdaddr": True}
    )

    if not dev:
        print('not found')
        return

    async with BleakClient(dev) as client:
        print("Connected")
        await asyncio.sleep(5.0)



if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    asyncio.run(main())