-- silver.status_semanal e silver.custos: o que o gerente diz toda sexta e o que se gastou de verdade.


-- O status de toda sexta. É daqui que vem o histórico do avanço (as ferramentas só guardam o % de hoje).
CREATE OR REFRESH MATERIALIZED VIEW status_semanal (
  CONSTRAINT farol_conhecido EXPECT (farol IN ('verde', 'amarelo', 'vermelho')) ON VIOLATION FAIL UPDATE
)
COMMENT 'Status semanal que cada gerente entrega toda sexta (uma linha por projeto e sexta): farol declarado pelo gerente (verde, amarelo, vermelho), % concluído declarado e o texto livre com entregas e bloqueios. status_vazio marca o texto sem conteúdo (vazio, N/A, ver ata da reunião), que é mantido.'
AS
SELECT
  projeto_id,
  to_date(data_status)                         AS data_status,
  gerente,
  lower(trim(farol))                           AS farol,            -- sujeira 17: 'Verde', 'VERDE'
  CAST(pct_concluido AS INT)                   AS pct_concluido,
  texto_status,
  -- sujeira 18: status sem conteúdo NÃO é descartado, só sinalizado
  coalesce(trim(texto_status), '') IN ('', 'N/A', 'ver ata da reunião') AS status_vazio
FROM farol_projeto.bronze.status_semanal;


-- Os lançamentos de custo real.
CREATE OR REFRESH MATERIALIZED VIEW custos
COMMENT 'Lançamentos de custo real dos projetos (uma linha por lançamento): data, sexta da semana, categoria (pessoal, consultoria, cloud, licenças, despesas), descrição, valor em reais e centro de custo. Estornos ficam como valor negativo (o custo é líquido) e são marcados na coluna estorno. valor_veio_com_virgula marca os lançamentos que vieram com vírgula decimal na origem.'
AS
SELECT
  lancamento_id,
  projeto_id,
  to_date(data)                                AS data,
  date_add(date_trunc('WEEK', to_date(data)), 4) AS semana,         -- a sexta da semana
  categoria,
  descricao,
  -- sujeira 13: '12345,67' → troca a vírgula ANTES do CAST (try_cast jogaria R$ 5,4 mi fora em silêncio)
  CAST(replace(valor, ',', '.') AS DECIMAL(15, 2)) AS valor,
  valor LIKE '%,%'                                 AS valor_veio_com_virgula,   -- os 671 recuperados
  -- sujeira 14: estorno fica (custo é líquido), só sinalizado
  CAST(replace(valor, ',', '.') AS DECIMAL(15, 2)) < 0 AS estorno,
  centro_custo
FROM farol_projeto.bronze.custos;
