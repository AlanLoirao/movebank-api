from datetime import datetime, timezone
from typing import Any

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

app = FastAPI(
    title="MoveBank Recovery API",
    description="API simulada para integração com o agente MoveBank Recovery AI",
    version="1.0.0",
)

clientes = {
    "12345678900": {
        "nome": "João Silva",
        "cpf": "12345678900",
        "valor_divida": 3250.90,
        "dias_atraso": 68,
        "parcelas_disponiveis": [3, 6, 12],
    },
    "99999999999": {
        "nome": "Maria Oliveira",
        "cpf": "99999999999",
        "valor_divida": 980.50,
        "dias_atraso": 22,
        "parcelas_disponiveis": [2, 4, 8],
    },
}


@app.get("/")
def status_api():
    return {
        "status": "online",
        "servico": "MoveBank Recovery API",
    }


@app.get("/cliente/{cpf}")
def consultar_cliente(cpf: str):
    cpf_limpo = "".join(caractere for caractere in cpf if caractere.isdigit())
    cliente = clientes.get(cpf_limpo)

    if cliente is None:
        return JSONResponse(
            status_code=404,
            content={
                "status": "erro",
                "mensagem": "Cliente não encontrado",
            },
        )

    return {
        "status": "sucesso",
        "cliente": cliente,
    }


@app.post("/webhook/moveo")
async def receber_webhook_moveo(request: Request) -> dict[str, Any]:
    """
    Recebe eventos enviados pela Moveo.

    Nesta primeira versão, registramos o conteúdo recebido e
    devolvemos HTTP 200 para validar a integração.
    """
    try:
        payload = await request.json()
    except Exception:
        payload = {"conteudo": "Corpo recebido sem JSON válido"}

    headers_recebidos = dict(request.headers)

    print("\n========== WEBHOOK MOVEO ==========")
    print("Payload recebido:", payload)
    print("Headers recebidos:", headers_recebidos)
    print("===================================\n")

    return {
        "status": "sucesso",
        "mensagem": "Evento recebido pela MoveBank Recovery API",
        "recebido_em": datetime.now(timezone.utc).isoformat(),
        "payload_recebido": payload,
    }