-- Métricas governadas da Torre: a fórmula de cada KPI num lugar só.
--
-- gold.mv_projetos é uma METRIC VIEW (Unity Catalog): dimensões + medidas em YAML.
-- O dashboard, o Genie e quem escreve SQL leem a mesma fórmula com MEASURE():
--   SELECT cliente, MEASURE(spi) FROM farol_projeto.gold.mv_projetos GROUP BY cliente
-- Razões são sempre SUM/SUM (nunca média de razão): o SPI da carteira é
-- Σ EV ÷ Σ PV, não a média dos SPIs dos projetos.
--
-- Fonte: gold.projeto_situacao_atual (a fotografia de 16/10/2026), só em andamento.
--
-- ARMADILHAS:
--   * roda como sql_task (ou python scripts/run_sql.py): o aitools tira a indentação do YAML
--   * a sql_task corta o arquivo em todo ponto e vírgula, inclusive dentro do bloco $$:
--     NENHUM ponto e vírgula dentro do YAML, nem em comment
CREATE OR REPLACE VIEW farol_projeto.gold.mv_projetos
WITH METRICS
LANGUAGE YAML
COMMENT 'Métricas governadas dos projetos em andamento da Vértice (fotografia de 16/10/2026): SPI, CPI, EAC, estouro previsto, margem, projetos em risco, críticos e melancias. Consulte com MEASURE().'
AS $$
version: 1.1
comment: "Métricas governadas dos projetos em andamento (fotografia de 16/10/2026). Razões calculadas como soma sobre soma."
source: farol_projeto.gold.projeto_situacao_atual
filter: status = 'em_andamento'

dimensions:
  - name: projeto_id
    expr: projeto
    comment: "Código do projeto no PMO, no formato PRJ-000"
    synonyms: ["código do projeto", "id do projeto", "PRJ"]
  - name: projeto
    expr: nome
    comment: "Nome do projeto (sistema e cliente)"
    synonyms: ["nome do projeto", "iniciativa"]
  - name: cliente
    expr: cliente
    synonyms: ["conta", "empresa cliente"]
  - name: segmento
    expr: segmento
    comment: "Segmento do cliente: varejo, financeiro, saude, logistica ou industria"
    synonyms: ["setor", "vertical", "indústria do cliente"]
  - name: ferramenta
    expr: ferramenta
    comment: "Onde o gerente controla o cronograma: excel, clickup ou msproject"
    synonyms: ["ferramenta de gestão", "sistema de cronograma"]
  - name: situacao
    expr: situacao
    comment: "Situação calculada pelas regras de corte: crítico (SPI ou CPI abaixo de 0,8), atenção (abaixo de 0,9) ou ok"
    synonyms: ["status de risco", "classificação", "saúde do projeto"]
  - name: farol_do_gerente
    expr: farol_do_gerente
    comment: "Farol que o gerente reportou no último status semanal (verde, amarelo ou vermelho)"
    synonyms: ["farol reportado", "farol declarado"]
  - name: farol_calculado
    expr: farol_calculado
    comment: "Farol pela regra do manual da Vértice: verde com SPI a partir de 0,95, amarelo a partir de 0,90, vermelho abaixo"
    synonyms: ["farol real", "farol pelo SPI"]
  - name: gerente_projeto
    expr: gerente_projeto
    comment: "Gerente responsável pelo projeto"
    synonyms: ["gerente", "GP", "responsável"]

measures:
  - name: projetos
    expr: COUNT(1)
    comment: "Número de projetos em andamento"
    synonyms: ["quantidade de projetos", "número de projetos", "total de projetos"]
  - name: carteira
    expr: SUM(valor_contrato)
    comment: "Soma do valor de contrato em reais"
    synonyms: ["valor da carteira", "valor de contrato", "receita contratada"]
  - name: spi
    expr: SUM(ev) / SUM(pv)
    comment: "Índice de desempenho de prazo = valor agregado (EV) dividido pelo valor planejado (PV). Abaixo de 1 é atraso, abaixo de 0,9 atenção, abaixo de 0,8 crítico"
    synonyms: ["índice de prazo", "desempenho de prazo", "schedule performance index"]
  - name: cpi
    expr: SUM(ev) / SUM(ac)
    comment: "Índice de desempenho de custo = valor agregado (EV) dividido pelo custo real (AC). Abaixo de 1 é estouro de custo"
    synonyms: ["índice de custo", "desempenho de custo", "cost performance index"]
  - name: eac
    expr: SUM(eac)
    comment: "Estimativa no término em reais = orçamento dividido pelo CPI de cada projeto"
    synonyms: ["estimativa no término", "custo final previsto", "estimate at completion"]
  - name: estouro_previsto
    expr: SUM(estouro_previsto)
    comment: "Quanto os projetos devem custar acima do orçamento, em reais (EAC menos orçamento, só quando positivo)"
    synonyms: ["estouro", "custo do atraso", "prejuízo previsto", "overrun"]
  - name: margem_projetada
    expr: (SUM(valor_contrato) - SUM(eac)) / SUM(valor_contrato)
    comment: "Margem prevista no fim = (valor de contrato menos EAC) dividido pelo valor de contrato, em fração (0,15 = 15%)"
    synonyms: ["margem", "margem prevista", "rentabilidade"]
  - name: atraso_projetado_medio_dias
    expr: AVG(atraso_projetado_dias)
    comment: "Atraso médio previsto em dias corridos = duração baseline dividida pelo SPI menos a duração baseline"
    synonyms: ["atraso médio", "dias de atraso", "atraso previsto"]
  - name: projetos_em_risco
    expr: COUNT(1) FILTER (WHERE situacao IN ('atenção', 'crítico'))
    comment: "Projetos em atenção ou críticos (SPI ou CPI abaixo de 0,9)"
    synonyms: ["projetos atrasados", "em risco", "projetos problemáticos"]
  - name: projetos_criticos
    expr: COUNT(1) FILTER (WHERE situacao = 'crítico')
    comment: "Projetos críticos (SPI ou CPI abaixo de 0,8)"
    synonyms: ["críticos", "projetos em vermelho"]
  - name: projetos_melancia
    expr: COUNT(1) FILTER (WHERE melancia)
    comment: "Melancias = farol do gerente verde mas SPI abaixo de 0,9 (verde por fora, vermelho por dentro)"
    synonyms: ["melancias", "verde por fora vermelho por dentro", "farol maquiado"]
$$;
