#!/usr/bin/env python3
"""Gera resources/farol.geniespace.json: o Genie "Farol · Diretoria" como código.

O arquivo é o `serialized_space` (versão 2) que o recurso genie_farol do bundle
(resources/genie.genie_space.yml) sobe no deploy. Quem pergunta é o dono da Vértice e a
diretoria, em português, sem escrever SQL.

O que entra:
  - 5 tabelas (gold.fato_projeto_semana, gold.projeto_situacao_atual,
    gold.status_estruturado, gold.utilizacao_pessoa_semana, silver.entregas_fornecedor)
  - a metric view gold.mv_projetos (as fórmulas governadas dos KPIs)
  - gold.score_estouro_30d (o modelo) SÓ se a tabela existir: o script pergunta ao
    workspace com `databricks tables exists`. Sem ela, nenhuma instrução nem exemplo
    fala de score (o Genie inventaria uma tabela que não existe)
  - as 4 perguntas do dono como perguntas de exemplo, uma instrução de texto e um SQL
    de exemplo para cada pergunta

Regras do formato: ids de 32 caracteres hex, únicos, e cada lista em ordem de id. As
tabelas vão em ordem de nome.

Uso:  python scripts/gerar_genie.py [--sem-checar-score]
Depois: databricks bundle deploy --profile DEFAULT
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

SAIDA = Path(__file__).resolve().parent.parent / "resources" / "farol.geniespace.json"
PROFILE = "DEFAULT"
C = "farol_projeto"
SCORE = f"{C}.gold.score_estouro_30d"

TABELAS = [
    f"{C}.gold.fato_projeto_semana",
    f"{C}.gold.projeto_situacao_atual",
    f"{C}.gold.status_estruturado",
    f"{C}.gold.utilizacao_pessoa_semana",
    f"{C}.silver.entregas_fornecedor",
]
METRIC_VIEW = f"{C}.gold.mv_projetos"

PERGUNTAS_DO_DONO = [
    "Quais projetos estão atrasados, e de quais clientes?",
    "Quanto esse atraso vai me custar?",
    "Tenho gente parada enquanto outro projeto pede gente?",
    "O que vai dar errado no próximo mês?",
]


def score_existe() -> bool:
    r = subprocess.run(
        ["databricks", "tables", "exists", SCORE, "--profile", PROFILE, "-o", "json"],
        capture_output=True, text=True,
    )
    if r.returncode != 0:
        sys.exit(f"não consegui checar {SCORE}: {r.stderr.strip()}")
    return bool(json.loads(r.stdout).get("table_exists"))


class Ids:
    """Ids de 32 hex, únicos e crescentes na ordem em que são pedidos."""

    def __init__(self) -> None:
        self.n = 0

    def __call__(self) -> str:
        self.n += 1
        return f"f4201000000000000000000000{self.n:06x}"


# ---------------------------------------------------------------------------
# Instrução de texto (uma só, em parágrafos)
# ---------------------------------------------------------------------------
def instrucao(com_score: bool) -> str:
    partes = [
        """QUEM PERGUNTA
Você responde ao dono da Vértice Tecnologia e à diretoria. Eles não escrevem SQL. A Vértice tem 60 projetos de sistemas para clientes de varejo, financeiro, saúde, logística e indústria (41 em andamento, 19 concluídos). Responda em português, com números em R$ (duas casas ou em mil/mi) e índices com 2 casas decimais. Comece pela resposta direta e depois o detalhe.""",

        """DATAS
HOJE é 2026-10-16 (sexta-feira). Nunca use current_date() nem now(): escreva DATE'2026-10-16'.
- "últimos 90 dias" = data_status >= DATE'2026-07-18' (na gold.status_estruturado).
- "últimas 12 semanas" = semana > DATE'2026-07-24' (12 sextas, de 31/07 a 16/10/2026).
- "próximo mês" = de 2026-10-17 a 2026-11-16.
- Semanas terminam na sexta: a semana de 25/09/2026 é semana = DATE'2026-09-25'.""",

        """FÓRMULAS E REGRAS DE CORTE
- SPI = EV / PV (prazo). CPI = EV / AC (custo). Abaixo de 1 é atraso / estouro.
- Regra de corte: SPI ou CPI < 0,9 = atenção, < 0,8 = crítico. A coluna situacao já traz isso: 'crítico', 'atenção', 'ok' ou 'concluído' (com acento, minúsculas).
- EAC = orçamento / CPI. Estouro previsto = EAC - orçamento, só quando positivo (já está na coluna estouro_previsto).
- Margem projetada = (valor do contrato - EAC) / valor do contrato.
- Atraso projetado (dias) = duração baseline / SPI - duração baseline.
- Razões da carteira são SOMA SOBRE SOMA (SUM(ev)/SUM(pv)), nunca média de SPIs.""",

        """QUAL TABELA USAR
- Totais e KPIs de hoje da carteira em andamento (SPI, CPI, estouro, carteira, margem, quantos críticos, quantos em risco, quantas melancias): use a metric view farol_projeto.gold.mv_projetos com MEASURE(), por exemplo SELECT MEASURE(spi) FROM farol_projeto.gold.mv_projetos. Ela já filtra status = 'em_andamento'.
- Listas, rankings e um projeto específico (qual projeto tem o maior estouro, o SPI do PRJ-011, os códigos dos críticos): use farol_projeto.gold.projeto_situacao_atual, sempre com status = 'em_andamento' quando falar de projetos atuais. O código do projeto é a coluna projeto (PRJ-000) e o nome é a coluna nome.
- Histórico semana a semana: farol_projeto.gold.fato_projeto_semana (projeto_id, semana). PV, EV e AC são ACUMULADOS até a semana: nunca some semanas. Para o valor de uma semana, filtre a semana. O spi e o cpi da semana já estão prontos.
- Ferramenta do gerente: coluna ferramenta = 'excel', 'clickup' ou 'msproject'.""",

        """FAROL E MELANCIA
- farol_do_gerente é o que o gerente reportou. farol_calculado é a regra do manual: verde com SPI >= 0,95, amarelo >= 0,90, vermelho abaixo.
- Melancia = farol do gerente verde e SPI < 0,9 (verde por fora, vermelho por dentro). Use a coluna booleana melancia (WHERE melancia). "Farol verde mas atrasado" é melancia.""",

        """POR QUE UM PROJETO ATRASOU
"Por que o projeto X atrasou" ou "qual a causa" responde com farol_projeto.gold.status_estruturado dos últimos 90 dias (data_status >= DATE'2026-07-18'), filtrando projeto_id e EXCLUINDO causa_bloqueio 'sem_bloqueio' e 'nao_reportado'. A causa principal é a que mais aparece (COUNT(*)), e dias_impacto somados mostram o tamanho. Mostre bloqueio e quem_destrava. Junte o SPI de hoje (projeto_situacao_atual). Se a causa for falta_sre, mostre também os SREs ociosos (papel = 'sre', utilização < 20% nas últimas 12 semanas) que poderiam ser realocados.
Causas: change_freeze, falta_sre, dependencia_fornecedor, rotatividade, mudanca_escopo, bug_retrabalho, aprovacao_cliente.""",

        """GENTE PARADA
"Gente parada", "ociosa" ou "subutilizada" = utilização < 20% nas últimas 12 semanas na farol_projeto.gold.utilizacao_pessoa_semana, calculada como SUM(horas_apontadas) / SUM(horas_disponiveis) agrupando por colaborador_id (semana > DATE'2026-07-24'). Papéis em minúsculas: 'sre', 'qa', 'dev_backend' etc. "Projeto pedindo gente" = causa falta_sre ou rotatividade no status dos últimos 90 dias.""",

        """FORNECEDORES
Use farol_projeto.silver.entregas_fornecedor. Quem mais atrasa = maior AVG(prazo_real_dias / prazo_prometido_dias) por fornecedor. "Entregas em atraso hoje" = WHERE em_atraso. O nome do fornecedor já está normalizado (CodeForge Consultoria Ltda).""",

        """O QUE VAI DAR ERRADO NO PRÓXIMO MÊS
Junte SEMPRE as duas fontes, como no SQL de exemplo dessa pergunta: (1) as entregas de consultoria em atraso (silver.entregas_fornecedor WHERE em_atraso) e os projetos delas, SEM filtro de data: elas já venceram e por isso pesam no próximo mês (são 5, todas da CodeForge), e (2) o change freeze de varejo da Black Friday, de 2026-11-01 a 2027-01-10, que trava deploy nos projetos de e-commerce em andamento. Projeto de e-commerce = status = 'em_andamento' e tipo_projeto contendo 'commerce', 'checkout' ou 'marketplace' (lower(tipo_projeto) LIKE '%commerce%' OR LIKE '%checkout%' OR LIKE '%marketplace%').
Se perguntarem "o que eu faço agora", depois da lista sugira ações concretas a partir dos dados: cobrar a CodeForge pelas entregas vencidas (ela entrega com prazo 1,41 vez o prometido), antecipar para antes de 01/11 o deploy dos projetos de e-commerce, e realocar gente ociosa para os projetos críticos que pedem gente (falta_sre ou rotatividade).""",

        """CLIENTES
"Quais clientes" devolve cada cliente UMA vez (SELECT DISTINCT cliente), nunca uma linha por projeto.""",
    ]
    if com_score:
        partes.append(
            """RISCO NOS PRÓXIMOS 30 DIAS (MODELO)
farol_projeto.gold.score_estouro_30d traz, por projeto, prob_estouro_30d (chance de o SPI ou CPI terminar o mês abaixo de 0,9), faixa_risco ('alto' >= 0,5, 'medio' >= 0,2, 'baixo') e principais_fatores. Use sempre a data_referencia mais recente (WHERE data_referencia = (SELECT MAX(data_referencia) FROM farol_projeto.gold.score_estouro_30d)). Em "o que vai dar errado no próximo mês", acrescente os projetos com situacao = 'ok' hoje e faixa_risco 'alto' ou 'medio', com principais_fatores: são os que ainda parecem bem e vão piorar. Mostre a probabilidade em %."""
        )
    return "\n\n".join(partes)


# ---------------------------------------------------------------------------
# SQL de exemplo das 4 perguntas do dono
# ---------------------------------------------------------------------------
SQL_ATRASADOS = """-- Projetos em andamento em atenção ou críticos, do pior para o melhor
SELECT projeto, nome, cliente, situacao,
       ROUND(spi, 2) AS spi, ROUND(cpi, 2) AS cpi,
       ROUND(atraso_projetado_dias, 0) AS atraso_projetado_dias,
       farol_do_gerente, melancia
FROM farol_projeto.gold.projeto_situacao_atual
WHERE status = 'em_andamento'
  AND situacao IN ('crítico', 'atenção')
ORDER BY CASE situacao WHEN 'crítico' THEN 1 ELSE 2 END, spi"""

SQL_CUSTO = """-- Estouro previsto da carteira em andamento, por situação, pela metric view
SELECT situacao,
       MEASURE(projetos) AS projetos,
       ROUND(MEASURE(estouro_previsto), 2) AS estouro_previsto,
       ROUND(MEASURE(eac), 2) AS eac,
       ROUND(MEASURE(carteira), 2) AS carteira,
       ROUND(MEASURE(margem_projetada), 4) AS margem_projetada
FROM farol_projeto.gold.mv_projetos
GROUP BY ALL
ORDER BY estouro_previsto DESC"""

SQL_GENTE = """-- Pessoas com utilização < 20% nas últimas 12 semanas e os projetos que pedem gente
WITH ociosos AS (
  SELECT colaborador_id, nome, papel, senioridade, projeto_id AS projeto_atual,
         ROUND(SUM(horas_apontadas) / SUM(horas_disponiveis), 3) AS utilizacao,
         ROUND(SUM(custo_ocioso), 2) AS custo_ocioso_12_semanas
  FROM farol_projeto.gold.utilizacao_pessoa_semana
  WHERE semana > DATE'2026-07-24'
  GROUP BY colaborador_id, nome, papel, senioridade, projeto_id
  HAVING SUM(horas_apontadas) / SUM(horas_disponiveis) < 0.2
),
pedindo_gente AS (
  SELECT projeto_id, causa_bloqueio, COUNT(*) AS semanas_com_bloqueio, SUM(dias_impacto) AS dias_impacto
  FROM farol_projeto.gold.status_estruturado
  WHERE data_status >= DATE'2026-07-18'
    AND causa_bloqueio IN ('falta_sre', 'rotatividade')
  GROUP BY projeto_id, causa_bloqueio
)
SELECT o.colaborador_id, o.nome, o.papel, o.projeto_atual, o.utilizacao, o.custo_ocioso_12_semanas,
       p.projeto_id AS projeto_que_pede_gente, p.causa_bloqueio, p.semanas_com_bloqueio, p.dias_impacto
FROM ociosos o
LEFT JOIN pedindo_gente p
  ON (o.papel = 'sre' AND p.causa_bloqueio = 'falta_sre')
  OR (o.papel <> 'sre' AND p.causa_bloqueio = 'rotatividade')
ORDER BY o.utilizacao, p.dias_impacto DESC"""

SQL_PROXIMO_MES = """-- Riscos do próximo mês: entregas de consultoria em atraso + change freeze da Black Friday
SELECT 'entrega de fornecedor em atraso' AS risco, e.projeto_id AS projeto, p.cliente,
       CONCAT(e.fornecedor, ': ', e.item, ' prometida para ', CAST(e.data_prometida AS STRING)) AS detalhe
FROM farol_projeto.silver.entregas_fornecedor e
JOIN farol_projeto.gold.projeto_situacao_atual p ON p.projeto = e.projeto_id
WHERE e.em_atraso
UNION ALL
SELECT 'change freeze de varejo (01/11/2026 a 10/01/2027)' AS risco, projeto, cliente,
       CONCAT(tipo_projeto, ', situação ', situacao, ', SPI ', CAST(ROUND(spi, 2) AS STRING)) AS detalhe
FROM farol_projeto.gold.projeto_situacao_atual
WHERE status = 'em_andamento'
  AND (lower(tipo_projeto) LIKE '%commerce%'
       OR lower(tipo_projeto) LIKE '%checkout%'
       OR lower(tipo_projeto) LIKE '%marketplace%')
ORDER BY risco, projeto"""

SQL_PROXIMO_MES_COM_SCORE = SQL_PROXIMO_MES.replace(
    "ORDER BY risco, projeto",
    """UNION ALL
SELECT 'modelo: pode estourar em 30 dias' AS risco, s.projeto_id AS projeto, p.cliente,
       CONCAT(CAST(ROUND(s.prob_estouro_30d * 100, 0) AS STRING), '% de chance (', s.faixa_risco, '): ',
              s.principais_fatores) AS detalhe
FROM farol_projeto.gold.score_estouro_30d s
JOIN farol_projeto.gold.projeto_situacao_atual p ON p.projeto = s.projeto_id
WHERE p.situacao = 'ok'
  AND s.faixa_risco IN ('alto', 'medio')
  AND s.data_referencia = (SELECT MAX(data_referencia) FROM farol_projeto.gold.score_estouro_30d)
ORDER BY risco, projeto""",
)

SQL_PRJ024 = """-- Chance de o PRJ-024 estourar nos próximos 30 dias (score mais recente)
SELECT s.projeto_id, p.situacao, ROUND(p.spi, 2) AS spi_hoje,
       ROUND(s.prob_estouro_30d, 2) AS prob_estouro_30d, s.faixa_risco, s.principais_fatores
FROM farol_projeto.gold.score_estouro_30d s
JOIN farol_projeto.gold.projeto_situacao_atual p ON p.projeto = s.projeto_id
WHERE s.projeto_id = 'PRJ-024'
  AND s.data_referencia = (SELECT MAX(data_referencia) FROM farol_projeto.gold.score_estouro_30d)"""


def linhas(texto: str) -> list[str]:
    """O serialized_space guarda texto como lista de linhas (cada uma com o \\n)."""
    partes = texto.split("\n")
    return [p + "\n" for p in partes[:-1]] + [partes[-1]]


def gerar(com_score: bool) -> dict:
    novo_id = Ids()
    tabelas = sorted(TABELAS + ([SCORE] if com_score else []))

    exemplos = [
        (PERGUNTAS_DO_DONO[0], SQL_ATRASADOS),
        (PERGUNTAS_DO_DONO[1], SQL_CUSTO),
        (PERGUNTAS_DO_DONO[2], SQL_GENTE),
        (PERGUNTAS_DO_DONO[3], SQL_PROXIMO_MES_COM_SCORE if com_score else SQL_PROXIMO_MES),
    ]
    if com_score:
        exemplos.append(("Qual a chance de o PRJ-024 estourar?", SQL_PRJ024))

    return {
        "version": 2,
        "config": {
            "sample_questions": [{"id": novo_id(), "question": [p]} for p in PERGUNTAS_DO_DONO],
        },
        "data_sources": {
            "tables": [{"identifier": t} for t in tabelas],
            "metric_views": [{"identifier": METRIC_VIEW}],
        },
        "instructions": {
            "text_instructions": [{"id": novo_id(), "content": linhas(instrucao(com_score))}],
            "example_question_sqls": [
                {"id": novo_id(), "question": [p], "sql": linhas(s)} for p, s in exemplos
            ],
        },
    }


def main() -> None:
    com_score = False if "--sem-checar-score" in sys.argv else score_existe()
    espaco = gerar(com_score)
    SAIDA.write_text(json.dumps(espaco, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"{SAIDA.relative_to(SAIDA.parent.parent)}: {len(espaco['data_sources']['tables'])} tabelas + mv_projetos, "
          f"{len(espaco['instructions']['example_question_sqls'])} exemplos de SQL, "
          f"score {'INCLUÍDO' if com_score else 'fora (a tabela não existe)'}")


if __name__ == "__main__":
    main()
