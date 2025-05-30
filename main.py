from telethon.sync import TelegramClient
from telethon.tl.functions.contacts import ImportContactsRequest, DeleteContactsRequest
from telethon.tl.types import InputPhoneContact
import os
import asyncio

# Environment Variables
API_ID = int(os.environ.get("API_ID"))
API_HASH = os.environ.get("API_HASH")
PHONE_NUMBER = os.environ.get("PHONE_NUMBER")

client = TelegramClient('checker_session', API_ID, API_HASH)

async def check_numbers(phone_numbers):
    await client.start(PHONE_NUMBER)

    # Add '+' to each number
    formatted_numbers = [f'+{num.strip()}' for num in phone_numbers]

    contacts = [
        InputPhoneContact(client_id=i, phone=number, first_name="Check", last_name="")
        for i, number in enumerate(formatted_numbers)
    ]

    result = await client(ImportContactsRequest(contacts))
    found_users = result.users
    valid_numbers = [user.phone for user in found_users]

    # Clean up added contacts
    if found_users:
        await client(DeleteContactsRequest(id=found_users))

    await client.disconnect()
    return valid_numbers

if __name__ == '__main__':
    # Example: user input without '+'
    raw_numbers = [
        '8801781234567',
        '919812345678',
        '8801976543210'
    ]

    # Run the checker
    valid = asyncio.run(check_numbers(raw_numbers))

    print("✅ Telegram account আছে এমন নাম্বার:")
    for number in valid:
        print(number)
