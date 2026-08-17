import os
os.environ.setdefault('LLM_STUB', '1')
os.environ.setdefault('LLM_ENABLED', 'true')

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_health():
    response = client.get('/health')
    assert response.status_code == 200

def test_triage_contract():
    response = client.post('/triage', json={'text':'I was charged twice'})
    assert response.status_code == 200
    body = response.json()
    assert set(body) == {'category','urgency','confidence','reason'}

def test_bad_input():
    response = client.post('/triage', json={'text':''})
    assert response.status_code == 400
