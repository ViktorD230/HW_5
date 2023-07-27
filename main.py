import sys
from datetime import datetime, timedelta
import aiohttp
import asyncio
import json
import websockets
import aiofile

url = f'https://api.privatbank.ua/p24api/exchange_rates?json'
curency_list = ['USD', 'EUR']
dates_list = []

def generate_dates(num_days):
    end_date = datetime.now()
    start_date = end_date - timedelta(days=num_days)

    date_range = [start_date + timedelta(days=i) for i in range(num_days + 1)]
    return date_range

async def fetch_currency(session, url):
    async with session.get(url) as response:
        return await response.json()

async def get_exchange(dates, currencies):
    async with aiohttp.ClientSession() as session:
        responses = await asyncio.gather(*[fetch_currency(session, f"{url}&date={date}")for date in dates])

    result = {}
    our_curr_dict = {}

    for response in responses:
        if response.get('date') in dates:
            exchange_rate = response.get('exchangeRate')
            for currency in exchange_rate:
                if currency.get('currency') in currencies:
                    our_curr_dict[currency.get('currency')] = {
                        "sale": float(currency.get('saleRate')),
                        "purchase": float(currency.get('purchaseRate'))
                    }
        result[response.get('date')] = our_curr_dict.copy()
    return result

async def handle_exchange_command(command):
    try:
        params = command.split()
        num_days = int(params[1])
    except ValueError as e:
        return f'Please give me a number! Error: {e}'

    currencies = params[2:] if len(params) > 2 else curency_list

    if num_days > 10:
        return "Too much days, max is 10 days"

    dates = generate_dates(num_days)
    for date in dates:
        dates_list.append(date.strftime("%d.%m.%Y"))

    res = await get_exchange(dates_list, currencies)
    return json.dumps(res, indent=2)

async def save_to_log(command):
    async with aiofile.async_open('chat_log.txt', 'a') as f:
        await f.write(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - {command}\n")

async def chat_handler(websocket, path):
    async for message in websocket:
        if message.startswith('exchange'):
            command_result = await handle_exchange_command(message)
            await save_to_log(message)
            await websocket.send(command_result)
        else:
            await websocket.send('Unknown command')

async def run_chat_server():
    start_server = websockets.serve(chat_handler, "localhost", 8765)
    await start_server
    asyncio.get_event_loop().run_forever()

async def run_exchange_command(date_delta):
    command = f"exchange {date_delta}"
    res = await handle_exchange_command(command)
    print(res)

def main():
    if len(sys.argv) > 1 and sys.argv[1] == 'exchange':
        asyncio.run(run_chat_server())
    else:
        date_delta = int(sys.argv[1]) if len(sys.argv) > 1 else 5
        asyncio.run(run_exchange_command(date_delta))

if __name__ == "__main__":
    main()
