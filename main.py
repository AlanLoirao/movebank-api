from datetime import datetime, timezone
from typing import Any
import re

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field


app = FastAPI(
    title="MoveBank Recovery API",
    description="API simulada para integração com o agente MoveBank Recovery AI",
    version="1.2.0",
)


# =========================================================
# BASE SIMULADA DE CLIENTES
# =========================================================

clientes = {
    "12345678900": {
        "nome": "João Silva",
        "cpf": "12345678900",
        "valor_divida": 3250.90,
        "dias_atraso": 68,
        "parcelas_disponiveis": [3, 6, 12],
        "desconto_avista_percentual": 15,
    },
    "99999999999": {
        "nome": "Maria Oliveira",
        "cpf": "99999999999",
        "valor_divida": 980.50,
        "dias_atraso": 22,
        "parcelas_disponiveis": [2, 4, 8],
        "desconto_avista_percentual": 10,
    },
    "11122233344": {
        "nome": "Carlos Mendes",
        "cpf": "11122233344",
        "valor_divida": 5870.40,
        "dias_atraso": 145,
        "parcelas_disponiveis": [6, 12, 18],
        "desconto_avista_percentual": 20,
    },
    "55566677788": {
        "nome": "Ana Paula Souza",
        "cpf": "55566677788",
        "valor_divida": 1740.75,
        "dias_atraso": 41,
        "parcelas_disponiveis": [3, 6, 9],
        "desconto_avista_percentual": 12,
    },
    "22233344455": {
        "nome": "Roberto Lima",
        "cpf": "22233344455",
        "valor_divida": 12450.00,
        "dias_atraso": 210,
        "parcelas_disponiveis": [12, 18, 24],
        "desconto_avista_percentual": 25,
    },
}


# =========================================================
# MODELOS DO PAYLOAD DA MOVEO
# =========================================================

class MoveoUser(BaseModel):
    external_id: str | None = None


class MoveoContext(BaseModel):
    user: MoveoUser | None = None


class MoveoWebhookPayload(BaseModel):
    context: MoveoContext = Field(default_factory=MoveoContext)


# =========================================================
# FUNÇÕES AUXILIARES
# =========================================================

def limpar_cpf(valor: str) -> str:
    return "".join(caractere for caractere in valor if caractere.isdigit())


def localizar_cpf_em_texto(texto: str) -> str | None:
    padrao = r"\b\d{3}\.?\d{3}\.?\d{3}-?\d{2}\b"
    resultado = re.search(padrao, texto)

    if resultado is None:
        return None

    return limpar_cpf(resultado.group())


def localizar_cpf_no_payload(valor: Any) -> str | None:
    if isinstance(valor, str):
        return localizar_cpf_em_texto(valor)

    if isinstance(valor, dict):
        for chave in (
            "cpf",
            "external_id",
            "message",
            "mensagem",
            "text",
            "texto",
            "content",
        ):
            if chave in valor:
                cpf = localizar_cpf_no_payload(valor[chave])
                if cpf:
                    return cpf

        for conteudo in valor.values():
            cpf = localizar_cpf_no_payload(conteudo)
            if cpf:
                return cpf

    if isinstance(valor, list):
        for item in valor:
            cpf = localizar_cpf_no_payload(item)
            if cpf:
                return cpf

    return None


def formatar_moeda(valor: float) -> str:
    return (
        f"R$ {valor:,.2f}"
        .replace(",", "X")
        .replace(".", ",")
        .replace("X", ".")
    )


def calcular_oferta(cliente: dict[str, Any]) -> dict[str, Any]:
    valor_divida = cliente["valor_divida"]
    desconto = cliente["desconto_avista_percentual"]

    valor_avista = round(
        valor_divida * (1 - desconto / 100),
        2,
    )

    parcelamentos = []

    for quantidade in cliente["parcelas_disponiveis"]:
        parcelamentos.append(
            {
                "quantidade": quantidade,
                "valor_parcela": round(
                    valor_divida / quantidade,
                    2,
                ),
            }
        )

    return {
        "valor_original": valor_divida,
        "desconto_avista_percentual": desconto,
        "valor_avista": valor_avista,
        "parcelamentos": parcelamentos,
    }


# =========================================================
# ENDPOINTS
# =========================================================

@app.get("/")
def status_api():
    return {
        "status": "online",
        "servico": "MoveBank Recovery API",
        "versao": "1.2.0",
        "data_hora": datetime.now(timezone.utc).isoformat(),
    }


@app.get("/cliente/{cpf}")
def consultar_cliente(cpf: str):
    cpf_limpo = limpar_cpf(cpf)
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
        "oferta": calcular_oferta(cliente),
    }


@app.post("/webhook/moveo")
async def receber_webhook_moveo(
    payload_model: MoveoWebhookPayload,
    request: Request,
) -> dict[str, Any]:

    payload = payload_model.model_dump()

    print("\n========== WEBHOOK MOVEO ==========")
    print("Payload recebido:", payload)
    print("Headers recebidos:", dict(request.headers))
    print("===================================\n")

    contexto = payload.get("context", {})
    usuario = contexto.get("user") or {}

    cpf = limpar_cpf(
        str(usuario.get("external_id", ""))
    )

    if len(cpf) != 11:
        cpf_encontrado = localizar_cpf_no_payload(payload)
        cpf = cpf_encontrado or ""

    if len(cpf) != 11:
        return {
            "responses": [
                {
                    "type": "text",
                    "texts": [
                        (
                            "Não consegui identificar o CPF informado. "
                            "Digite apenas os 11 números do CPF."
                        )
                    ],
                }
            ],
            "context": {
                "consulta_status": "cpf_invalido",
            },
        }

    cliente = clientes.get(cpf)

    if cliente is None:
        return {
            "responses": [
                {
                    "type": "text",
                    "texts": [
                        (
                            "Não localizei uma negociação disponível "
                            "para o CPF informado. Posso encaminhar "
                            "você para um especialista."
                        )
                    ],
                }
            ],
            "context": {
                "consulta_status": "cliente_nao_encontrado",
                "cpf_consultado": cpf,
            },
        }

    oferta = calcular_oferta(cliente)

    parcelas_texto = ", ".join(
        (
            f"{opcao['quantidade']}x de "
            f"{formatar_moeda(opcao['valor_parcela'])}"
        )
        for opcao in oferta["parcelamentos"]
    )

    mensagem = (
        f"Olá, {cliente['nome']}. "
        f"Localizei um débito de "
        f"{formatar_moeda(cliente['valor_divida'])}, "
        f"com {cliente['dias_atraso']} dias de atraso. "
        f"Para pagamento à vista, o valor simulado é "
        f"{formatar_moeda(oferta['valor_avista'])}, "
        f"com {oferta['desconto_avista_percentual']}% de desconto. "
        f"Também temos as opções: {parcelas_texto}. "
        f"Qual opção você prefere?"
    )

    return {
        "responses": [
            {
                "type": "text",
                "texts": [mensagem],
            }
        ],
        "context": {
            "consulta_status": "cliente_localizado",
            "cliente_nome": cliente["nome"],
            "cpf_consultado": cpf,
            "valor_divida": cliente["valor_divida"],
            "valor_avista": oferta["valor_avista"],
            "dias_atraso": cliente["dias_atraso"],
        },
    }