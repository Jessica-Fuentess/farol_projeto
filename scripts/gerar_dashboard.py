#!/usr/bin/env python3
"""Gera resources/dashboard-portfolio.lvdash.json: o painel AI/BI (Lakeview, GRID_V1) da Torre.

Quatro páginas:
  Portfólio         · quais projetos estão atrasados, e quanto esse atraso vai me custar?
  Pessoas           · tenho gente parada enquanto outro projeto pede gente?
  Fornecedores      · o que vai dar errado no próximo mês?
  Sobre o projeto   · o problema, a arquitetura e os números do pipeline

Regras do formato AI/BI (skill databricks-aibi-dashboards):
  - O grid GRID_V1 tem 12 colunas.
  - As linhas de uma caixa de texto são concatenadas: título e texto de apoio são widgets separados.
  - A expressão de um widget só aceita agregação simples (SUM, COUNT, MAX...). Razões como
    SUM(ev) / SUM(pv) são MEDIDAS declaradas no dataset (columns) e lidas com MEASURE().
    Assim os filtros mudam os KPIs e a razão continua SUM/SUM, nunca AVG de razão.
  - Cor condicional existe na célula da tabela (style.rules), não no contador.
  - As queries da gold usam o nome PURO da tabela: catálogo e schema vêm do recurso do
    bundle (dataset_catalog / dataset_schema). A silver vai com o nome completo.
  - Valores em R$ nas TABELAS saem prontos do SQL em português (R$ 150.056,72): o formato
    numérico do AI/BI segue o idioma do navegador de quem abre o painel.

Uso:  python scripts/gerar_dashboard.py
"""
import json
from pathlib import Path

SAIDA = Path(__file__).resolve().parent.parent / "resources" / "dashboard-portfolio.lvdash.json"
REPOSITORIO = "https://github.com/Jessica-Fuentess/farol_projeto"
HOJE = "16/10/2026"
RODAPE = f"*Fonte: Excel, ClickUp e MS Project integrados no Databricks · dados de {HOJE}*"

# ---------------------------------------------------------------------------
# Paleta: as cores do projeto + as cores de situação
# ---------------------------------------------------------------------------
AZUL, CIANO, FUNDO_ESCURO = "#0059DB", "#22C2F4", "#14141A"
VERMELHO, AMBAR, CINZA = "#FF5F46", "#F6C344", "#9AA4B2"
ROXO, VERDE, LARANJA = "#7B61FF", "#2BB673", "#FF8A3D"

CORES_SITUACAO = {"Crítico": VERMELHO, "Atenção": AMBAR, "OK": CIANO, "Concluído": CINZA}
CORES_CAUSA = {
    "Mudança de escopo": AZUL,
    "Bug e retrabalho": VERMELHO,
    "Aprovação do cliente": AMBAR,
    "Dependência de fornecedor": ROXO,
    "Falta de SRE": CIANO,
    "Rotatividade": LARANJA,
    "Change freeze": VERDE,
}
CORES_INDICE = {"SPI · prazo": AZUL, "CPI · custo": AMBAR, "Meta (1,0)": CINZA}
CORES_DESTAQUE = {"CodeForge": VERMELHO, "Demais fornecedores": AZUL}


# ---------------------------------------------------------------------------
# Rótulos em português (nada de nome técnico na tela) e números no padrão brasileiro
# ---------------------------------------------------------------------------
def _case(coluna, de_para, senao=None):
    whens = " ".join(f"WHEN '{de}' THEN '{para}'" for de, para in de_para.items())
    return f"CASE {coluna} {whens} ELSE {senao or coluna} END"


SITUACAO = {"crítico": "Crítico", "atenção": "Atenção", "ok": "OK", "concluído": "Concluído"}
SITUACAO_ICONE = {"crítico": "🔴 Crítico", "atenção": "🟡 Atenção", "ok": "🟢 OK", "concluído": "⚪ Concluído"}
FAROL = {"verde": "🟢 Verde", "amarelo": "🟡 Amarelo", "vermelho": "🔴 Vermelho"}
SEGMENTO = {"financeiro": "Financeiro", "industria": "Indústria", "logistica": "Logística",
            "saude": "Saúde", "varejo": "Varejo"}
PAPEL = {"agilista": "Agilista", "arquiteto": "Arquitetura", "designer_ux": "Designer UX",
         "dev_backend": "Dev back-end", "dev_frontend": "Dev front-end", "dev_mobile": "Dev mobile",
         "engenheiro_dados": "Engenharia de dados", "gestor_engenharia": "Gestão de engenharia",
         "product_owner": "Product owner", "qa": "QA", "sre": "SRE", "tech_lead": "Tech lead"}
SENIORIDADE = {"junior": "Júnior", "pleno": "Pleno", "senior": "Sênior", "especialista": "Especialista"}
CAUSA = {"mudanca_escopo": "Mudança de escopo", "bug_retrabalho": "Bug e retrabalho",
         "aprovacao_cliente": "Aprovação do cliente", "dependencia_fornecedor": "Dependência de fornecedor",
         "falta_sre": "Falta de SRE", "rotatividade": "Rotatividade", "change_freeze": "Change freeze"}


def _br(numero_formatado):
    """format_number devolve 150,056.72: troca vírgula e ponto → 150.056,72."""
    return f"translate({numero_formatado}, ',.', '.,')"


def reais(expr):
    return f"concat('R$ ', {_br(f'format_number({expr}, 2)')})"


def reais_mi(expr):
    return f"concat('R$ ', {_br(f'format_number(({expr}) / 1e6, 2)')}, ' mi')"


def pct(expr):
    return f"concat({_br(f'format_number(({expr}) * 100, 1)')}, '%')"


# ---------------------------------------------------------------------------
# Datasets. "medidas" = columns do dataset, lidas pelos widgets com MEASURE().
# ---------------------------------------------------------------------------
DATASETS = {
    # ======================= Portfólio =======================
    "projetos_em_andamento": {
        "sql": f"""
SELECT
  projeto,
  concat(projeto, ' · ', cliente)                       AS projeto_cliente,
  cliente,
  {_case('segmento', SEGMENTO)}                         AS segmento,
  gerente_projeto,
  {_case('situacao', SITUACAO)}                         AS situacao,
  {_case('situacao', SITUACAO_ICONE)}                   AS situacao_icone,
  valor_contrato, pv, ev, ac, eac, estouro_previsto,
  spi,
  cpi,
  CASE WHEN situacao = 'crítico' THEN 1 ELSE 0 END                     AS critico,
  CASE WHEN situacao IN ('atenção', 'crítico') THEN 1 ELSE 0 END      AS em_risco,
  CASE WHEN melancia THEN 1 ELSE 0 END                                 AS melancia,
  0.95                                                                 AS meta_indice,
  {reais_mi('estouro_previsto')}                        AS estouro_texto,
  {pct('margem_projetada')}                             AS margem_texto,
  CAST(round(atraso_projetado_dias) AS INT)             AS atraso_dias,
  {_case('farol_do_gerente', FAROL)}                    AS farol_do_gerente,
  {_case('farol_calculado', FAROL)}                     AS farol_calculado,
  CASE WHEN melancia THEN '🍉' ELSE '' END               AS melancia_icone
FROM projeto_situacao_atual
WHERE status = 'em_andamento'
ORDER BY spi
""",
        "medidas": {
            "Carteira em mi": "SUM(`valor_contrato`) / 1000000",
            "Estouro em mi": "SUM(`estouro_previsto`) / 1000000",
            "Margem projetada": "(SUM(`valor_contrato`) - SUM(`eac`)) / SUM(`valor_contrato`)",
            "SPI": "SUM(`ev`) / SUM(`pv`)",
            "CPI": "SUM(`ev`) / SUM(`ac`)",
        },
    },
    # os 15 maiores estouros
    "estouro_top15": {
        "sql": f"""
SELECT
  concat(projeto, ' · ', cliente)        AS projeto_cliente,
  {_case('segmento', SEGMENTO)}          AS segmento,
  gerente_projeto,
  {_case('situacao', SITUACAO)}          AS situacao,
  estouro_previsto
FROM projeto_situacao_atual
WHERE status = 'em_andamento' AND estouro_previsto > 0
ORDER BY estouro_previsto DESC
LIMIT 15
""",
    },
    # formato longo: SUM(numerador) / SUM(denominador) por semana e índice
    "evolucao_indices": {
        "sql": f"""
WITH semana AS (
  SELECT f.semana, f.pv, f.ev, f.ac,
         {_case('p.segmento', SEGMENTO)} AS segmento,
         {_case('p.situacao', SITUACAO)} AS situacao,
         p.gerente_projeto
  FROM fato_projeto_semana f
  JOIN projeto_situacao_atual p ON p.projeto = f.projeto_id
  WHERE f.semana >= DATE'2025-03-07'
)
SELECT semana, segmento, situacao, gerente_projeto, 'SPI · prazo' AS indice, ev AS numerador, pv AS denominador FROM semana
UNION ALL
SELECT semana, segmento, situacao, gerente_projeto, 'CPI · custo', ev, ac FROM semana
UNION ALL
SELECT semana, segmento, situacao, gerente_projeto, 'Meta (1,0)', 1.0, 1.0 FROM semana
""",
        "medidas": {"Indice": "SUM(`numerador`) / SUM(`denominador`)"},
    },

    # ======================= Pessoas =======================
    # uma pessoa por linha, últimas 12 semanas
    "pessoas_12_semanas": {
        "sql": """
SELECT
  colaborador_id,
  SUM(custo_ocioso)                                                          AS custo_ocioso,
  CASE WHEN SUM(horas_apontadas) / SUM(horas_disponiveis) < 0.2 THEN 1 ELSE 0 END AS uso_abaixo_de_20
FROM utilizacao_pessoa_semana
WHERE semana > DATE'2026-07-24'
GROUP BY colaborador_id
""",
        "medidas": {"Custo ocioso em mi": "SUM(`custo_ocioso`) / 1000000"},
    },
    "utilizacao_12_semanas": {
        "sql": f"""
SELECT {_case('papel', PAPEL)} AS papel, horas_disponiveis, horas_apontadas
FROM utilizacao_pessoa_semana
WHERE semana > DATE'2026-07-24'
""",
        "medidas": {"Utilizacao": "SUM(`horas_apontadas`) / SUM(`horas_disponiveis`)"},
    },
    "custo_hora_parada": {
        "sql": f"""
SELECT
  concat(nome, ' · ', {_case('papel', PAPEL)}, ' · ', projeto_id) AS pessoa,
  round(SUM(custo_ocioso), 2)                                    AS custo_ocioso
FROM utilizacao_pessoa_semana
WHERE semana > DATE'2026-07-24'
GROUP BY colaborador_id, nome, papel, projeto_id
ORDER BY custo_ocioso DESC
LIMIT 15
""",
    },
    "utilizacao_pessoa_projeto": {
        "sql": f"""
SELECT
  colaborador_id, nome,
  {_case('papel', PAPEL)}                                      AS papel,
  {_case('senioridade', SENIORIDADE)}                          AS senioridade,
  projeto_id,
  CAST(round(SUM(horas_disponiveis)) AS INT)                   AS horas_disponiveis,
  CAST(round(SUM(horas_apontadas)) AS INT)                     AS horas_apontadas,
  SUM(horas_apontadas) / SUM(horas_disponiveis)                AS utilizacao,
  {reais('SUM(custo_ocioso)')}                                 AS custo_ocioso
FROM utilizacao_pessoa_semana
WHERE semana > DATE'2026-07-24'
GROUP BY colaborador_id, nome, papel, senioridade, projeto_id
ORDER BY utilizacao
""",
    },
    "causas_bloqueio": {
        "sql": f"""
SELECT
  concat(e.projeto_id, ' · ', {_case('p.situacao', SITUACAO)}) AS projeto,
  {_case('e.causa_bloqueio', CAUSA)}                          AS causa,
  count(*)                                                    AS status
FROM status_estruturado e
JOIN projeto_situacao_atual p ON p.projeto = e.projeto_id
WHERE e.data_status >= DATE'2026-07-18'
  AND e.causa_bloqueio NOT IN ('sem_bloqueio', 'nao_reportado')
  AND p.situacao IN ('atenção', 'crítico')
GROUP BY ALL
""",
    },

    # ======================= Fornecedores =======================
    "entregas": {
        "sql": """
SELECT
  fornecedor,
  CASE WHEN fornecedor = 'CodeForge Consultoria Ltda' THEN 'CodeForge'
       ELSE 'Demais fornecedores' END                                         AS destaque,
  CASE WHEN em_atraso THEN 1 ELSE 0 END                                        AS em_atraso,
  CASE WHEN em_atraso THEN valor ELSE 0 END                                    AS valor_em_atraso,
  CASE WHEN NOT em_aberto THEN 1 ELSE 0 END                                    AS entregue,
  CASE WHEN NOT em_aberto AND data_entrega <= data_prometida THEN 1 ELSE 0 END AS no_prazo,
  CASE WHEN NOT em_aberto THEN prazo_real_dias END                             AS prazo_real_entregue,
  CASE WHEN NOT em_aberto THEN prazo_prometido_dias END                        AS prazo_prometido_entregue
FROM farol_projeto.silver.entregas_fornecedor
""",
        "medidas": {
            "Prazo real sobre prometido": "SUM(`prazo_real_entregue`) / SUM(`prazo_prometido_entregue`)",
            "Pct no prazo": "SUM(`no_prazo`) / SUM(`entregue`)",
            "Valor em atraso em mil": "SUM(`valor_em_atraso`) / 1000",
        },
    },
    "fornecedores": {
        "sql": """
SELECT
  CASE WHEN fornecedor = 'CodeForge Consultoria Ltda' THEN concat('🔴 ', fornecedor)
       ELSE fornecedor END                                                          AS fornecedor,
  count(DISTINCT fornecedor_como_veio)                                              AS grafias_no_cadastro,
  count(*)                                                                          AS entregas,
  SUM(CASE WHEN NOT em_aberto THEN prazo_real_dias END)
    / SUM(CASE WHEN NOT em_aberto THEN prazo_prometido_dias END)                    AS prazo_real_sobre_prometido,
  count_if(NOT em_aberto AND data_entrega <= data_prometida) / count_if(NOT em_aberto) AS pct_no_prazo,
  count_if(em_atraso)                                                               AS em_atraso_hoje
FROM farol_projeto.silver.entregas_fornecedor
GROUP BY fornecedor
ORDER BY prazo_real_sobre_prometido DESC
""",
    },
    "entregas_em_atraso": {
        "sql": f"""
SELECT
  entrega_id, projeto_id, fornecedor, item,
  {reais('valor')}                              AS valor,
  date_format(data_pedido, 'dd/MM/yyyy')        AS data_pedido,
  date_format(data_prometida, 'dd/MM/yyyy')     AS data_prometida,
  datediff(DATE'2026-10-16', data_prometida)    AS dias_em_atraso
FROM farol_projeto.silver.entregas_fornecedor
WHERE em_atraso
ORDER BY dias_em_atraso DESC
""",
    },
}

# ---------------------------------------------------------------------------
# Formatos
# ---------------------------------------------------------------------------
def _casas(n, tipo="exact"):
    return {"type": tipo, "places": n}


FMT_MI = {"type": "number-plain", "decimalPlaces": _casas(1)}          # com formatTemplate "R$ … mi"
FMT_MI_2 = {"type": "number-plain", "decimalPlaces": _casas(2)}
FMT_REAIS = {"type": "number-currency", "currencyCode": "BRL", "decimalPlaces": _casas(2)}
FMT_REAIS_COMPACTO = {"type": "number-currency", "currencyCode": "BRL", "abbreviation": "compact",
                      "decimalPlaces": _casas(2, "max")}
FMT_PCT = {"type": "number-percent", "decimalPlaces": _casas(1, "max")}
FMT_INDICE = {"type": "number-plain", "decimalPlaces": _casas(2)}
FMT_INTEIRO = {"type": "number-plain", "decimalPlaces": _casas(0)}


# ---------------------------------------------------------------------------
# Construtores de widget
# ---------------------------------------------------------------------------
def _pos(x, y, w, h):
    return {"x": x, "y": y, "width": w, "height": h}


def _frame(titulo, descricao=None):
    frame = {"showTitle": True, "title": titulo}
    if descricao:
        frame.update({"showDescription": True, "description": descricao})
    return frame


def col(nome):
    """Coluna do dataset, sem agregação."""
    return (nome, f"`{nome}`")


def soma(nome):
    return (f"sum({nome})", f"SUM(`{nome}`)")


def maximo(nome):
    return (f"max({nome})", f"MAX(`{nome}`)")


def medida(nome):
    return (f"measure({nome})", f"MEASURE(`{nome}`)")


def _query(dataset, campos, desagregado):
    return [{"name": "main_query",
             "query": {"datasetName": dataset,
                       "fields": [{"name": n, "expression": e} for n, e in campos],
                       "disaggregated": desagregado}}]


def texto(nome, markdown, pos):
    linhas = markdown if isinstance(markdown, list) else [markdown]
    return {"widget": {"name": nome, "multilineTextboxSpec": {"lines": [l + "\n" for l in linhas]}},
            "position": _pos(*pos)}


def cabecalho(prefixo, pergunta, apoio, y=0):
    """Título (a pergunta) e texto de apoio em widgets separados: uma linha cada."""
    return [texto(f"{prefixo}_titulo", f"## {pergunta}", (0, y, 12, 1)),
            texto(f"{prefixo}_apoio", apoio, (0, y + 1, 12, 1))]


def rodape(prefixo, y):
    return texto(f"{prefixo}_rodape", RODAPE, (0, y, 12, 1))


def kpi(nome, dataset, campo, titulo, formato, pos, descricao=None, template=None, meta=None):
    """Contador. meta = (campo, texto): a meta aparece embaixo do número, com a distância até ela."""
    campos = [campo]
    valor = {"fieldName": campo[0], "displayName": titulo, "format": formato}
    if template:
        valor["formatTemplate"] = template
    encodings = {"value": valor}
    if meta:
        campos.append(meta[0])
        encodings["target"] = {"fieldName": meta[0][0], "displayName": meta[1]}
    return {
        "widget": {
            "name": nome,
            "queries": _query(dataset, campos, False),
            "spec": {"version": 2, "widgetType": "counter", "encodings": encodings,
                     "frame": _frame(titulo, descricao)},
        },
        "position": _pos(*pos),
    }


def grafico(nome, tipo, dataset, encodings, campos, titulo, pos, descricao=None, desagregado=False):
    return {
        "widget": {
            "name": nome,
            "queries": _query(dataset, campos, desagregado),
            "spec": {"version": 3, "widgetType": tipo, "encodings": encodings,
                     "frame": _frame(titulo, descricao)},
        },
        "position": _pos(*pos),
    }


def cor(campo, rotulo, cores):
    return {"fieldName": campo, "displayName": rotulo,
            "scale": {"type": "categorical",
                      "mappings": [{"value": v, "color": c} for v, c in cores.items()]}}


def regra(operador, valor, cor_hex):
    """Regra de cor da célula: a primeira que casar vale."""
    return {"condition": {"operand": {"type": "data-value", "value": str(valor)}, "operator": operador},
            "backgroundColor": {"hex": cor_hex}}


def tabela(nome, dataset, colunas, titulo, pos, descricao=None):
    """colunas: lista de dicts {campo, titulo, [format], [regras]}."""
    cols = []
    for c in colunas:
        coluna = {"fieldName": c["campo"], "displayName": c["titulo"]}
        if "format" in c:
            coluna["format"] = c["format"]
        if "regras" in c:
            coluna["style"] = {"type": "basic", "rules": c["regras"]}
        cols.append(coluna)
    return {
        "widget": {
            "name": nome,
            "queries": _query(dataset, [col(c["campo"]) for c in colunas], True),
            "spec": {"version": 2, "widgetType": "table", "encodings": {"columns": cols},
                     "frame": _frame(titulo, descricao)},
        },
        "position": _pos(*pos),
    }


def filtro(nome, campo, titulo, datasets, pos):
    """Filtro de seleção múltipla ligado a vários datasets: muda todos os widgets deles."""
    queries = [{"name": f"{nome}_{ds}",
                "query": {"datasetName": ds, "fields": [{"name": campo, "expression": f"`{campo}`"}],
                          "disaggregated": False}}
               for ds in datasets]
    return {
        "widget": {
            "name": nome,
            "queries": queries,
            "spec": {
                "version": 2,
                "widgetType": "filter-multi-select",
                "encodings": {"fields": [{"fieldName": campo, "displayName": titulo, "queryName": q["name"]}
                                         for q in queries]},
                "frame": {"showTitle": True, "title": titulo},
            },
        },
        "position": _pos(*pos),
    }


def c(campo, titulo, **extras):
    return {"campo": campo, "titulo": titulo, **extras}


META_INDICE = (maximo("meta_indice"), "meta 0,95")
REGRAS_INDICE = [regra("<", 0.8, VERMELHO), regra("<", 0.9, AMBAR)]

# ---------------------------------------------------------------------------
# Página 1 · Portfólio
# ---------------------------------------------------------------------------
DS_PORTFOLIO = ["projetos_em_andamento", "estouro_top15", "evolucao_indices"]
P = "projetos_em_andamento"

portfolio = [
    *cabecalho(
        "portfolio",
        "Quais projetos estão atrasados, e quanto esse atraso vai me custar?",
        "41 projetos em andamento, de três ferramentas de gestão, num número só. "
        "**17 em risco, R$ 6,47 mi de estouro previsto e 4 melancias** (farol verde com SPI abaixo de 0,9).",
    ),
    filtro("filtro_segmento", "segmento", "Segmento", DS_PORTFOLIO, (0, 2, 4, 2)),
    filtro("filtro_situacao", "situacao", "Situação", DS_PORTFOLIO, (4, 2, 4, 2)),
    filtro("filtro_gerente", "gerente_projeto", "Gerente", DS_PORTFOLIO, (8, 2, 4, 2)),
    # dinheiro
    kpi("kpi_carteira", P, medida("Carteira em mi"), "Carteira em andamento", FMT_MI, (0, 4, 3, 3),
        "Soma dos contratos", template="R$ {{@formatted}} mi"),
    kpi("kpi_estouro", P, medida("Estouro em mi"), "🔴 Estouro previsto", FMT_MI_2, (3, 4, 3, 3),
        "EAC − orçamento, quando positivo", template="R$ {{@formatted}} mi"),
    kpi("kpi_margem", P, medida("Margem projetada"), "Margem projetada", FMT_PCT, (6, 4, 3, 3),
        "(contrato − EAC) ÷ contrato"),
    kpi("kpi_em_risco", P, soma("em_risco"), "Projetos em risco", FMT_INTEIRO, (9, 4, 3, 3),
        "Atenção + crítico"),
    # prazo e custo
    kpi("kpi_spi", P, medida("SPI"), "SPI · prazo", FMT_INDICE, (0, 7, 3, 3),
        "Σ EV ÷ Σ PV", meta=META_INDICE),
    kpi("kpi_cpi", P, medida("CPI"), "CPI · custo", FMT_INDICE, (3, 7, 3, 3),
        "Σ EV ÷ Σ AC", meta=META_INDICE),
    kpi("kpi_criticos", P, soma("critico"), "🔴 Críticos", FMT_INTEIRO, (6, 7, 3, 3),
        "SPI ou CPI abaixo de 0,8"),
    kpi("kpi_melancias", P, soma("melancia"), "🍉 Melancias", FMT_INTEIRO, (9, 7, 3, 3),
        "Farol verde por fora, SPI < 0,9 por dentro"),
    grafico(
        "barra_estouro", "bar", "estouro_top15",
        {
            "x": {"fieldName": "sum(estouro_previsto)", "displayName": "Estouro previsto",
                  "scale": {"type": "quantitative"}, "format": FMT_REAIS_COMPACTO},
            "y": {"fieldName": "projeto_cliente", "displayName": "Projeto",
                  "scale": {"type": "categorical", "sort": {"by": "x-reversed"}}, "axis": {"hideTitle": True}},
            "color": cor("situacao", "Situação", CORES_SITUACAO),
            "label": {"show": True},
        },
        [col("projeto_cliente"), col("situacao"), soma("estouro_previsto")],
        "Os 15 maiores estouros previstos", (0, 10, 7, 9), "EAC − orçamento, por projeto",
    ),
    grafico(
        "dispersao_spi_cpi", "scatter", P,
        {
            "x": {"fieldName": "spi", "displayName": "SPI · prazo", "scale": {"type": "quantitative"},
                  "format": FMT_INDICE},
            "y": {"fieldName": "cpi", "displayName": "CPI · custo", "scale": {"type": "quantitative"},
                  "format": FMT_INDICE},
            "color": cor("situacao", "Situação", CORES_SITUACAO),
        },
        [col("projeto_cliente"), col("situacao"), col("spi"), col("cpi")],
        "Prazo × custo", (7, 10, 5, 9), "Um ponto por projeto · embaixo à esquerda: atrasado e estourado",
        desagregado=True,
    ),
    grafico(
        "linha_indices", "line", "evolucao_indices",
        {
            "x": {"fieldName": "semana", "displayName": "Semana", "scale": {"type": "temporal"}},
            "y": {"fieldName": "measure(Indice)", "displayName": "Índice", "scale": {"type": "quantitative"},
                  "format": FMT_INDICE},
            "color": cor("indice", "Índice", CORES_INDICE),
        },
        [col("semana"), col("indice"), medida("Indice")],
        "SPI e CPI da carteira, semana a semana", (0, 19, 8, 7),
        "Σ EV ÷ Σ PV e Σ EV ÷ Σ AC desde 07/03/2025 · a linha cinza é a meta (1,0)",
    ),
    grafico(
        "barra_carteira_segmento", "bar", P,
        {
            "x": {"fieldName": "sum(valor_contrato)", "displayName": "Valor dos contratos",
                  "scale": {"type": "quantitative"}, "format": FMT_REAIS_COMPACTO},
            "y": {"fieldName": "segmento", "displayName": "Segmento",
                  "scale": {"type": "categorical", "sort": {"by": "x-reversed"}}, "axis": {"hideTitle": True}},
            "color": cor("situacao", "Situação", CORES_SITUACAO),
        },
        [col("segmento"), col("situacao"), soma("valor_contrato")],
        "Carteira por segmento", (8, 19, 4, 7), "Quanto do contrato está em risco",
    ),
    tabela("tabela_projetos", P, [
        c("projeto", "Projeto"),
        c("cliente", "Cliente"),
        c("gerente_projeto", "Gerente"),
        c("situacao_icone", "Situação"),
        c("spi", "SPI", format=FMT_INDICE, regras=REGRAS_INDICE),
        c("cpi", "CPI", format=FMT_INDICE, regras=REGRAS_INDICE),
        c("estouro_texto", "Estouro previsto"),
        c("margem_texto", "Margem"),
        c("atraso_dias", "Atraso (dias)", format=FMT_INTEIRO),
        c("farol_do_gerente", "Farol do gerente"),
        c("farol_calculado", "Farol calculado"),
        c("melancia_icone", "Melancia"),
    ], "Projetos em andamento", (0, 26, 12, 11),
        "Farol calculado pela regra do manual: verde com SPI ≥ 0,95, amarelo ≥ 0,90 · "
        "SPI e CPI em vermelho abaixo de 0,8 e em âmbar abaixo de 0,9"),
    rodape("portfolio", 37),
]

# ---------------------------------------------------------------------------
# Página 2 · Pessoas
# ---------------------------------------------------------------------------
pessoas = [
    *cabecalho(
        "pessoas",
        "Tenho gente parada enquanto outro projeto pede gente?",
        "Timesheet das últimas 12 semanas. **Duas SREs do PRJ-007 usaram cerca de 5% das horas, "
        "enquanto o PRJ-011 (crítico) ficou 12 semanas bloqueado por falta de SRE.**",
    ),
    kpi("kpi_uso_baixo", "pessoas_12_semanas", soma("uso_abaixo_de_20"), "Pessoas com uso abaixo de 20%",
        FMT_INTEIRO, (0, 2, 6, 3), "Horas apontadas ÷ disponíveis, nas últimas 12 semanas"),
    kpi("kpi_custo_ocioso", "pessoas_12_semanas", medida("Custo ocioso em mi"), "Custo da hora parada",
        FMT_MI_2, (6, 2, 6, 3), "(horas disponíveis − apontadas) × custo/hora, em 12 semanas",
        template="R$ {{@formatted}} mi"),
    grafico(
        "barra_custo_parado", "bar", "custo_hora_parada",
        {
            "x": {"fieldName": "custo_ocioso", "displayName": "Custo ocioso (R$)",
                  "scale": {"type": "quantitative"}, "format": FMT_REAIS},
            "y": {"fieldName": "pessoa", "displayName": "Pessoa · papel · projeto",
                  "scale": {"type": "categorical", "sort": {"by": "x-reversed"}}, "axis": {"hideTitle": True}},
            "label": {"show": True},
        },
        [col("pessoa"), col("custo_ocioso")],
        "Top 15 · custo da hora parada", (0, 5, 7, 9), "12 semanas, por pessoa e projeto",
        desagregado=True,
    ),
    grafico(
        "barra_utilizacao_papel", "bar", "utilizacao_12_semanas",
        {
            "x": {"fieldName": "measure(Utilizacao)", "displayName": "Utilização",
                  "scale": {"type": "quantitative"}, "format": FMT_PCT},
            "y": {"fieldName": "papel", "displayName": "Papel",
                  "scale": {"type": "categorical", "sort": {"by": "x"}}, "axis": {"hideTitle": True}},
            "label": {"show": True},
        },
        [col("papel"), medida("Utilizacao")],
        "Utilização por papel", (7, 5, 5, 9), "Do papel mais parado ao mais ocupado",
    ),
    grafico(
        "barra_causas", "bar", "causas_bloqueio",
        {
            "x": {"fieldName": "sum(status)", "displayName": "Semanas com bloqueio", "scale": {"type": "quantitative"}},
            "y": {"fieldName": "projeto", "displayName": "Projeto",
                  "scale": {"type": "categorical", "sort": {"by": "x-reversed"}}, "axis": {"hideTitle": True}},
            "color": cor("causa", "Causa", CORES_CAUSA),
        },
        [col("projeto"), col("causa"), soma("status")],
        "O que está travando os projetos em risco", (0, 14, 12, 9),
        "Causa do bloqueio lida pela IA no texto do status semanal · projetos em atenção ou crítico · últimos 90 dias",
    ),
    tabela("tabela_utilizacao", "utilizacao_pessoa_projeto", [
        c("colaborador_id", "Colaborador"),
        c("nome", "Nome"),
        c("papel", "Papel"),
        c("senioridade", "Senioridade"),
        c("projeto_id", "Projeto"),
        c("horas_disponiveis", "Horas disponíveis", format=FMT_INTEIRO),
        c("horas_apontadas", "Horas apontadas", format=FMT_INTEIRO),
        c("utilizacao", "Utilização", format=FMT_PCT, regras=[regra("<", 0.2, VERMELHO), regra("<", 0.5, AMBAR)]),
        c("custo_ocioso", "Custo ocioso"),
    ], "Utilização por pessoa e projeto", (0, 23, 12, 10),
        "Da mais parada à mais ocupada · 12 semanas · vermelho abaixo de 20%, âmbar abaixo de 50%"),
    rodape("pessoas", 33),
]

# ---------------------------------------------------------------------------
# Página 3 · Fornecedores
# ---------------------------------------------------------------------------
E = "entregas"
fornecedores = [
    *cabecalho(
        "fornecedores",
        "O que vai dar errado no próximo mês?",
        "Prazo prometido × real das consultorias. **A CodeForge entrega 41% depois do prometido, "
        "nenhuma entrega no prazo, e tem as 5 entregas atrasadas hoje.**",
    ),
    kpi("kpi_atraso", E, soma("em_atraso"), "🔴 Entregas em atraso hoje", FMT_INTEIRO, (0, 2, 6, 3),
        "Em aberto, com a data prometida vencida"),
    kpi("kpi_valor_atraso", E, medida("Valor em atraso em mil"), "Valor em atraso", FMT_MI_2, (6, 2, 6, 3),
        "Soma das entregas atrasadas", template="R$ {{@formatted}} mil"),
    grafico(
        "barra_prazo_fornecedor", "bar", E,
        {
            "x": {"fieldName": "measure(Prazo real sobre prometido)", "displayName": "Prazo real ÷ prometido",
                  "scale": {"type": "quantitative"}, "format": FMT_INDICE},
            "y": {"fieldName": "fornecedor", "displayName": "Fornecedor",
                  "scale": {"type": "categorical", "sort": {"by": "x-reversed"}}, "axis": {"hideTitle": True}},
            "color": cor("destaque", "Fornecedor", CORES_DESTAQUE),
            "label": {"show": True},
        },
        [col("fornecedor"), col("destaque"), medida("Prazo real sobre prometido")],
        "Quanto o prazo real passa do prometido", (0, 5, 6, 7), "1,00 = entrega no prazo prometido",
    ),
    grafico(
        "barra_no_prazo_fornecedor", "bar", E,
        {
            "x": {"fieldName": "measure(Pct no prazo)", "displayName": "% no prazo",
                  "scale": {"type": "quantitative"}, "format": FMT_PCT},
            "y": {"fieldName": "fornecedor", "displayName": "Fornecedor",
                  "scale": {"type": "categorical", "sort": {"by": "x"}}, "axis": {"hideTitle": True}},
            "color": cor("destaque", "Fornecedor", CORES_DESTAQUE),
            "label": {"show": True},
        },
        [col("fornecedor"), col("destaque"), medida("Pct no prazo")],
        "Entregas feitas no prazo", (6, 5, 6, 7), "Das entregas já feitas",
    ),
    # a linha da CodeForge fica vermelha porque cada valor dela passa da regra da coluna
    tabela("tabela_fornecedores", "fornecedores", [
        c("fornecedor", "Fornecedor"),
        c("grafias_no_cadastro", "Grafias no cadastro", format=FMT_INTEIRO, regras=[regra(">", 1, VERMELHO)]),
        c("entregas", "Entregas", format=FMT_INTEIRO),
        c("prazo_real_sobre_prometido", "Prazo real ÷ prometido", format=FMT_INDICE,
          regras=[regra(">", 1.1, VERMELHO)]),
        c("pct_no_prazo", "No prazo", format=FMT_PCT, regras=[regra("<", 0.1, VERMELHO)]),
        c("em_atraso_hoje", "Em atraso hoje", format=FMT_INTEIRO, regras=[regra(">", 0, VERMELHO)]),
    ], "Resumo por fornecedor", (0, 12, 12, 5),
        "Em vermelho: mais de uma grafia no cadastro, prazo real 10% acima do prometido, menos de 10% no prazo, entrega atrasada"),
    tabela("tabela_entregas_atraso", "entregas_em_atraso", [
        c("entrega_id", "Entrega"),
        c("projeto_id", "Projeto"),
        c("fornecedor", "Fornecedor"),
        c("item", "Item"),
        c("valor", "Valor"),
        c("data_pedido", "Pedido em"),
        c("data_prometida", "Prometida para"),
        c("dias_em_atraso", "Dias em atraso", format=FMT_INTEIRO),
    ], "Entregas em atraso hoje", (0, 17, 12, 6), f"Em aberto, com a data prometida antes de {HOJE}"),
    rodape("fornecedores", 23),
]

# ---------------------------------------------------------------------------
# Página 4 · Sobre o projeto (para quem chega pelo portfólio)
# ---------------------------------------------------------------------------
sobre = [
    *cabecalho(
        "sobre",
        "Projeto Farol · uma Torre de Controle de projetos no Databricks",
        f"Da ingestão no data lake ao painel executivo, com qualidade de dados, IA generativa e tudo versionado "
        f"como código. Desenvolvido por **Jéssica Fuentes** · [{REPOSITORIO.removeprefix('https://')}]({REPOSITORIO})",
    ),
    texto("sobre_credito",
          "*Case baseado na imersão Jornada de Dados (Luciano Vasconcelos), refeito no meu workspace, "
          "com o meu data lake e os meus ajustes.*",
          (0, 2, 12, 1)),
    texto("sobre_problema", [
        "### O problema",
        "A **Vértice Tecnologia** tem 60 projetos, 520 pessoas e **R$ 305 mi** de carteira. "
        "Cada gerente controla o projeto numa ferramenta diferente: **20 em planilhas Excel, 25 no ClickUp e 15 no MS Project**.",
        "",
        "Ninguém conseguia responder ao dono:",
        "1. Quais projetos estão atrasados, e de quais clientes?",
        "2. Quanto esse atraso vai custar?",
        "3. Tenho gente parada enquanto outro projeto pede gente?",
        "4. O que vai dar errado no próximo mês?",
    ], (0, 3, 6, 6)),
    texto("sobre_solucao", [
        "### A solução",
        "- **Integração**: as três ferramentas viram **uma tabela só** de 4.917 tarefas, com o de-para do cadastro do PMO.",
        "- **Limpeza**: 18 tipos de sujeira tratados (datas em 3 formatos, % em texto, vírgula decimal, duplicados) "
        "sem perder um centavo: o custo total da bronze é igual ao da silver.",
        "- **Gestão por valor agregado**: SPI, CPI, EAC, estouro e margem projetada por projeto e por semana.",
        "- **IA generativa**: `ai_classify` e `ai_extract` transformam o texto livre do status semanal em causa do bloqueio, "
        "quem destrava e dias de impacto.",
        "- **Qualidade**: expectations no pipeline e 10 testes automáticos que param o job se algo não bater.",
    ], (6, 3, 6, 6)),
    texto("sobre_arquitetura", [
        "### Arquitetura",
        "```",
        "Supabase Storage (S3)          job farol_projeto_job · toda segunda às 6h",
        "        │",
        "        ▼",
        " ingestao_data_lake ──► conferencia_bronze ──► medalhao (Lakeflow Declarative Pipeline) ──┬──► testes_de_qualidade",
        "  notebook · boto3       contagem das 9          bronze ─► silver (7 tabelas)               └──► status_com_ia",
        "  9 tabelas bronze       tabelas                        ─► gold (fato semanal, situação,         ai_classify + ai_extract",
        "                                                              utilização)                         MERGE incremental",
        "                                                                    │",
        "                                                                    ▼",
        "                                                     este dashboard (AI/BI, como código)",
        "```",
    ], (0, 9, 12, 6)),
    texto("sobre_stack", [
        "### Stack",
        "**Databricks** (Unity Catalog · Lakeflow Spark Declarative Pipelines · Jobs · SQL Warehouse serverless · "
        "AI/BI Dashboards · AI Functions) · **Declarative Automation Bundles** (infraestrutura como código, deploy pela CLI) · "
        "**SQL** · **Python** (boto3) · arquitetura **medalhão** · **Git**",
    ], (0, 15, 6, 4)),
    texto("sobre_numeros", [
        "### Em números",
        "| | |",
        "|---|---|",
        "| Tarefas integradas de 3 ferramentas | **4.917** |",
        "| Lançamentos de custo conferidos | **23.640** (R$ 193,35 mi) |",
        "| Status semanais estruturados | **3.911** (163 pela IA) |",
        "| Testes de qualidade automáticos | **10** + expectations |",
    ], (6, 15, 6, 4)),
    rodape("sobre", 19),
]


def pagina(nome, titulo, layout):
    return {"name": nome, "displayName": titulo, "pageType": "PAGE_TYPE_CANVAS",
            "layoutVersion": "GRID_V1", "layout": layout}


def _dataset(nome, definicao):
    ds = {"name": nome, "displayName": nome,
          "queryLines": [linha + "\n" for linha in definicao["sql"].strip().splitlines()]}
    if definicao.get("medidas"):
        ds["columns"] = [{"displayName": n, "expression": e} for n, e in definicao["medidas"].items()]
    return ds


def dashboard():
    return {
        "datasets": [_dataset(n, d) for n, d in DATASETS.items()],
        "pages": [
            pagina("portfolio", "Portfólio", portfolio),
            pagina("pessoas", "Pessoas", pessoas),
            pagina("fornecedores", "Fornecedores", fornecedores),
            pagina("sobre", "Sobre o projeto", sobre),
        ],
        "uiSettings": {
            "theme": {
                "canvasBackgroundColor": {"light": "#F4F6FA", "dark": FUNDO_ESCURO},
                "widgetBackgroundColor": {"light": "#FFFFFF", "dark": "#1C1C24"},
                "widgetBorderColor": {"light": "#FFFFFF", "dark": "#1C1C24"},
                "fontColor": {"light": "#14141A", "dark": "#EDEFF3"},
                "selectionColor": {"light": AZUL, "dark": CIANO},
                "visualizationColors": [AZUL, CIANO, AMBAR, VERMELHO, ROXO, VERDE, LARANJA, CINZA],
                "widgetHeaderAlignment": "LEFT",
                "widgetCornerRadius": 12,
            },
            "applyModeEnabled": False,
        },
    }


if __name__ == "__main__":
    painel = dashboard()
    SAIDA.write_text(json.dumps(painel, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    widgets = sum(len(p["layout"]) for p in painel["pages"])
    print(f"{SAIDA.name}: {len(DATASETS)} datasets, {len(painel['pages'])} páginas, {widgets} widgets")
