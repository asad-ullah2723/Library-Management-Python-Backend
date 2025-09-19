from fastapi.testclient import TestClient
import main

client = TestClient(main.app)

resp = client.get('/health')
print('STATUS:', resp.status_code)
try:
    print('BODY:', resp.json())
except Exception as e:
    print('BODY (text):', resp.text)
