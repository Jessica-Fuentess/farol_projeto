-- gold.projeto_situacao_atual e gold.utilizacao_pessoa_semana.


-- ============================================================
-- A fotografia de hoje (16/10/2026): uma linha por projeto, com o cadastro e os KPIs.
-- Aqui o avanço vem das TAREFAS das ferramentas (o % de hoje), não do status do gerente.
-- ============================================================
CREATE OR REFRESH MATERIALIZED VIEW farol_projeto.gold.projeto_situacao_atual
COMMENT 'Situação de cada um dos 60 projetos em 16/10/2026 (uma linha por projeto): cadastro (cliente, segmento, tipo, ferramenta, gerente, valor do contrato, orçamento, datas e duração baseline, status) e os KPIs calculados sobre as tarefas das ferramentas: PV, EV, AC, SPI, CPI, EAC, estouro previsto, margem projetada, atraso e término projetados. situacao: concluído, crítico (SPI ou CPI < 0,8), atenção (< 0,9) ou ok. farol_do_gerente é o do último status; farol_calculado segue o manual da Vértice (verde SPI >= 0,95, amarelo >= 0,90). melancia = em andamento, farol do gerente verde e SPI < 0,9.'
AS
WITH
-- 1 · o avanço de hoje pelas tarefas: horas totais, horas que já deviam estar feitas e horas feitas
avanco AS (
  SELECT
    projeto_id,
    sum(horas) AS horas_totais,
    sum(horas * CASE
                  WHEN DATE'2026-10-16' >= fim_baseline   THEN 1.0
                  WHEN DATE'2026-10-16' <  inicio_baseline THEN 0.0
                  ELSE greatest(0, least(1, datediff(DATE'2026-10-16', inicio_baseline)
                                            / datediff(fim_baseline, inicio_baseline)))
                END)                         AS horas_planejadas,
    sum(horas * pct_concluido / 100)         AS horas_agregadas
  FROM tarefas
  GROUP BY projeto_id
),

-- 2 · o custo real até hoje
custo_real AS (
  SELECT projeto_id, sum(valor) AS ac
  FROM custos
  WHERE data <= DATE'2026-10-16'
  GROUP BY projeto_id
),

-- 3 · o último status publicado até hoje (o farol que o gerente diz)
ultimo_status AS (
  SELECT projeto_id, farol, data_status,
         row_number() OVER (PARTITION BY projeto_id ORDER BY data_status DESC) AS ordem
  FROM status_semanal
  WHERE data_status <= DATE'2026-10-16'
),

-- 4 · PV, EV e AC em reais
kpis AS (
  SELECT
    p.*,
    datediff(p.data_fim_baseline, p.data_inicio)                             AS duracao_baseline_dias,
    CAST(p.orcamento_custo AS DOUBLE) * a.horas_planejadas / a.horas_totais  AS pv,
    CAST(p.orcamento_custo AS DOUBLE) * a.horas_agregadas  / a.horas_totais  AS ev,
    CAST(coalesce(c.ac, 0) AS DOUBLE)                                        AS ac,
    u.farol                                                                  AS farol_do_gerente
  FROM projetos p
  LEFT JOIN avanco        a ON a.projeto_id = p.projeto_id
  LEFT JOIN custo_real    c ON c.projeto_id = p.projeto_id
  LEFT JOIN ultimo_status u ON u.projeto_id = p.projeto_id AND u.ordem = 1
),

-- 5 · os índices
indices AS (
  SELECT
    *,
    round(try_divide(ev, pv), 4) AS spi,
    round(try_divide(ev, ac), 4) AS cpi
  FROM kpis
),

-- 6 · as projeções
projecoes AS (
  SELECT
    *,
    try_divide(CAST(orcamento_custo AS DOUBLE), cpi)           AS eac,
    try_divide(duracao_baseline_dias, spi)                     AS duracao_projetada_dias
  FROM indices
)
SELECT
  projeto_id                                                   AS projeto,
  nome_projeto                                                 AS nome,
  cliente,
  segmento,
  tipo_projeto,
  ferramenta,
  gerente_projeto,
  valor_contrato,
  orcamento_custo                                              AS orcamento,
  data_inicio,
  data_fim_baseline,
  duracao_baseline_dias,
  status,
  round(pv, 2)                                                 AS pv,
  round(ev, 2)                                                 AS ev,
  round(ac, 2)                                                 AS ac,
  spi,
  cpi,
  round(eac, 2)                                                AS eac,
  round(greatest(eac - CAST(orcamento_custo AS DOUBLE), 0), 2) AS estouro_previsto,
  round(try_divide(CAST(valor_contrato AS DOUBLE) - eac, CAST(valor_contrato AS DOUBLE)), 4) AS margem_projetada,
  round(duracao_projetada_dias - duracao_baseline_dias, 1)     AS atraso_projetado_dias,
  date_add(data_inicio, CAST(round(duracao_projetada_dias) AS INT)) AS termino_projetado,
  CASE
    WHEN status <> 'em_andamento'  THEN 'concluído'
    WHEN spi < 0.8 OR cpi < 0.8    THEN 'crítico'
    WHEN spi < 0.9 OR cpi < 0.9    THEN 'atenção'
    ELSE 'ok'
  END                                                          AS situacao,
  farol_do_gerente,
  CASE
    WHEN spi >= 0.95 THEN 'verde'
    WHEN spi >= 0.90 THEN 'amarelo'
    ELSE 'vermelho'
  END                                                          AS farol_calculado,
  coalesce(status = 'em_andamento' AND farol_do_gerente = 'verde' AND spi < 0.9, false) AS melancia
FROM projecoes;


-- ============================================================
-- A utilização de cada pessoa, em cada projeto, em cada semana.
-- Responde: tenho gente parada enquanto outro projeto pede gente?
-- ============================================================
CREATE OR REFRESH MATERIALIZED VIEW farol_projeto.gold.utilizacao_pessoa_semana
COMMENT 'Utilização semanal de cada pessoa em cada projeto (uma linha por pessoa, projeto e sexta-feira): nome, papel, senioridade, horas disponíveis, apontadas e ociosas, utilização (apontadas / disponíveis), custo ocioso (horas ociosas × custo/hora) e o SPI do projeto naquela semana. Mostra gente parada num projeto enquanto outro está atrasado.'
AS
SELECT
  a.colaborador_id,
  c.nome,
  c.papel,
  c.senioridade,
  a.projeto_id,
  a.semana,
  a.horas_disponiveis,
  a.horas_apontadas,
  greatest(a.horas_disponiveis - a.horas_apontadas, 0)                                AS horas_ociosas,
  round(try_divide(a.horas_apontadas, a.horas_disponiveis), 4)                        AS utilizacao,
  round(greatest(a.horas_disponiveis - a.horas_apontadas, 0) * CAST(c.custo_hora AS DOUBLE), 2) AS custo_ocioso,
  f.spi                                                                               AS spi_do_projeto
FROM apontamentos a
LEFT JOIN colaboradores c
  ON c.colaborador_id = a.colaborador_id
LEFT JOIN farol_projeto.gold.fato_projeto_semana f
  ON f.projeto_id = a.projeto_id AND f.semana = a.semana;
