# Credential Providers

Avoid hardcoding credentials:

```python
from fidelity_trader.credentials import (
    EnvProvider,             # FIDELITY_USERNAME, FIDELITY_PASSWORD env vars
    SecretsManagerProvider,  # AWS Secrets Manager
    SSMParameterProvider,    # AWS SSM Parameter Store
    FileProvider,            # JSON file
    DirectProvider,          # Direct (testing only)
)

creds = EnvProvider().get_credentials()
# or: SecretsManagerProvider(secret_name="fidelity/trader").get_credentials()
# or: SSMParameterProvider(prefix="/fidelity/trader").get_credentials()

with FidelityClient() as client:
    client.login(creds.username, creds.password, totp_secret=creds.totp_secret)
```
