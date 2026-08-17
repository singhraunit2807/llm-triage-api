from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_health():
    response = client.get('/health')
    assert response.status_code == 200

def test_triage_contract(monkeypatch):
    monkeypatch.setenv('LLM_STUB','1')
    monkeypatch.setenv('LLM_ENABLED','true')
    response = client.post('/triage', json={'text':'I was charged twice'})
    assert response.status_code == 200
    body = response.json()
    assert set(body) == {'category','urgency','confidence','reason'}

def test_bad_input():
    response = client.post('/triage', json={'text':''})
    assert response.status_code == 400
