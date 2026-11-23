-- gold.status_estruturado: o texto livre do status semanal vira coluna.
-- Três métodos, do mais barato ao mais caro:
--   regra         status vazio ou que diz que não há bloqueio (não precisa de IA)
--   ia            status com bloqueio dos últimos 90 dias: ai_classify + ai_extract (~5 s por texto)
--   palavra_chave status com bloqueio mais antigo: RLIKE no texto
-- A tabela ACUMULA: o MERGE só insere o que ainda não foi classificado,
-- então a IA nunca é refeita para o mesmo status.
-- (Nada de ponto e vírgula dentro dos textos: a sql_task corta o arquivo em cada um.)


-- a · a tabela, criada uma vez só (NÃO é CREATE OR REPLACE)
CREATE TABLE IF NOT EXISTS farol_projeto.gold.status_estruturado (
  projeto_id       STRING    COMMENT 'Projeto do status (PRJ-xxx)',
  data_status      DATE      COMMENT 'Sexta-feira em que o gerente publicou o status',
  farol            STRING    COMMENT 'Farol declarado pelo gerente: verde, amarelo ou vermelho',
  causa_bloqueio   STRING    COMMENT 'Causa do bloqueio: change_freeze, falta_sre, dependencia_fornecedor, rotatividade, mudanca_escopo, bug_retrabalho, aprovacao_cliente, sem_bloqueio, nao_reportado (status vazio) ou nao_identificado (palavra-chave não achou)',
  bloqueio         STRING    COMMENT 'O bloqueio em poucas palavras (só nos status classificados pela IA)',
  quem_destrava    STRING    COMMENT 'Quem precisa agir para destravar: cliente, fornecedor, área interna... (só IA)',
  dias_impacto     DOUBLE    COMMENT 'Dias de impacto no cronograma declarados no texto (1 semana = 7). NULL quando o texto não declara',
  metodo           STRING    COMMENT 'Como foi classificado: regra, ia (últimos 90 dias, com bloqueio) ou palavra_chave (histórico)',
  texto_status     STRING    COMMENT 'O texto livre original do status semanal',
  _classificado_em TIMESTAMP COMMENT 'Quando a linha foi classificada (a tabela acumula, a IA não é refeita)'
)
COMMENT 'Status semanal estruturado: a causa do bloqueio, o que trava, quem destrava e os dias de impacto, extraídos do texto livre de cada status (uma linha por projeto e sexta). Os 90 dias mais recentes com bloqueio são classificados por IA (ai_classify e ai_extract), o histórico por palavra-chave e os status sem bloqueio por regra.';


-- b · só os status que ainda não estão na tabela
MERGE INTO farol_projeto.gold.status_estruturado AS alvo
USING (
  WITH
  novos AS (
    SELECT
      s.projeto_id,
      s.data_status,
      s.farol,
      s.texto_status,
      s.status_vazio,
      lower(coalesce(s.texto_status, '')) AS texto,
      CASE
        WHEN s.status_vazio
          OR lower(s.texto_status) LIKE '%bloqueios: nenhum%'
          OR lower(s.texto_status) LIKE '%sem bloqueios%'
          OR lower(s.texto_status) LIKE '%nada relevante%'  THEN 'regra'
        WHEN s.data_status >= DATE'2026-07-18'              THEN 'ia'
        ELSE 'palavra_chave'
      END AS metodo
    FROM farol_projeto.silver.status_semanal s
    LEFT ANTI JOIN farol_projeto.gold.status_estruturado e
      ON e.projeto_id = s.projeto_id AND e.data_status = s.data_status
  ),

  -- os dias de impacto declarados no texto, por regex
  com_dias AS (
    SELECT
      *,
      CASE
        WHEN texto LIKE '%impacto estimado: 1 semana%' THEN 7.0
        ELSE CAST(nullif(regexp_extract(texto, 'impacto estimado de ([0-9]+) dias', 1), '') AS DOUBLE)
      END AS dias_regex
    FROM novos
  ),

  -- 1 · regra: vazio ou sem bloqueio
  por_regra AS (
    SELECT
      projeto_id, data_status, farol,
      CASE WHEN status_vazio THEN 'nao_reportado' ELSE 'sem_bloqueio' END AS causa_bloqueio,
      CAST(NULL AS STRING) AS bloqueio,
      CAST(NULL AS STRING) AS quem_destrava,
      dias_regex           AS dias_impacto,
      metodo, texto_status
    FROM com_dias
    WHERE metodo = 'regra'
  ),

  -- 2 · palavra-chave: o histórico com bloqueio
  por_palavra_chave AS (
    SELECT
      projeto_id, data_status, farol,
      CASE
        WHEN texto RLIKE 'freeze|congelamento|janela de deploy'               THEN 'change_freeze'
        WHEN texto RLIKE 'sre|infraestrutura|ambiente de homologação'          THEN 'falta_sre'
        WHEN texto RLIKE 'forge|consultoria|fornecedor'                        THEN 'dependencia_fornecedor'
        WHEN texto RLIKE 'saída de|rotatividade|onboarding'                    THEN 'rotatividade'
        WHEN texto RLIKE 'escopo|change request|regra de negócio'              THEN 'mudanca_escopo'
        WHEN texto RLIKE 'bugs|regressão|refazendo'                            THEN 'bug_retrabalho'
        WHEN texto RLIKE 'aprovação do cliente|homologação do cliente'         THEN 'aprovacao_cliente'
        ELSE 'nao_identificado'
      END AS causa_bloqueio,
      CAST(NULL AS STRING) AS bloqueio,
      CAST(NULL AS STRING) AS quem_destrava,
      dias_regex           AS dias_impacto,
      metodo, texto_status
    FROM com_dias
    WHERE metodo = 'palavra_chave'
  ),

  -- 3 · IA: os últimos 90 dias com bloqueio. Cada função é chamada uma vez por texto.
  ia_bruta AS (
    SELECT
      *,
      ai_classify(
        texto_status,
        '["change_freeze","falta_sre","dependencia_fornecedor","rotatividade","mudanca_escopo","bug_retrabalho","aprovacao_cliente","sem_bloqueio"]',
        map('version', '2.0')
      ) AS classificado,
      ai_extract(
        texto_status,
        '{"bloqueio": {"type": "string", "description": "o bloqueio relatado, em poucas palavras"},
          "quem_destrava": {"type": "string", "description": "quem precisa agir para destravar (cliente, fornecedor, SRE, time interno...)"},
          "dias_impacto": {"type": "number", "description": "dias de impacto no cronograma declarados no texto. 1 semana = 7. Sem impacto declarado = null"}}',
        map('version', '2.0')
      ) AS extraido
    FROM com_dias
    WHERE metodo = 'ia'
  ),
  por_ia AS (
    SELECT
      projeto_id, data_status, farol,
      classificado:response[0]::STRING                                  AS causa_bloqueio,
      extraido:response:bloqueio::STRING                                AS bloqueio,
      extraido:response:quem_destrava::STRING                           AS quem_destrava,
      coalesce(extraido:response:dias_impacto::DOUBLE, dias_regex)      AS dias_impacto,
      metodo, texto_status
    FROM ia_bruta
  )

  SELECT *, current_timestamp() AS _classificado_em FROM por_regra
  UNION ALL
  SELECT *, current_timestamp() FROM por_palavra_chave
  UNION ALL
  SELECT *, current_timestamp() FROM por_ia
) AS novo
ON alvo.projeto_id = novo.projeto_id AND alvo.data_status = novo.data_status
WHEN NOT MATCHED THEN INSERT *;


-- c · leitura: quantos status por método e causa
SELECT metodo, causa_bloqueio, count(*) AS status, round(sum(dias_impacto), 0) AS dias_impacto
FROM farol_projeto.gold.status_estruturado
GROUP BY metodo, causa_bloqueio
ORDER BY metodo, status DESC;
