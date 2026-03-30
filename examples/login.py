"""Example: Login to Fidelity Trader+"""

from fidelity_trader import FidelityClient

with FidelityClient() as client:
    result = client.login(username="your_username", password="your_password")
    print(f"Logged in: {result}")
    print(f"Authenticated: {client.is_authenticated}")
