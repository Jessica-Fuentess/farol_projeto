# minha-torre · o app do Projeto Farol

App web (Databricks Apps + AppKit · React, TypeScript e Tailwind) em cima da gold do Projeto Farol.

| Tela | O que responde |
|---|---|
| **Projetos em risco** | Quais projetos estão atrasados ou estourando, o farol do gerente ao lado do farol calculado e as 🍉 melancias (verde por fora, vermelho por dentro) |
| **Simulador** | Vale a pena mover uma pessoa ociosa para um projeto travado? Horas, ociosidade que deixa de ser paga, dias recuperados, custo de onboarding e saldo do mês |
| **Perguntar** | Chat com o agente Genie "Farol · Diretoria", em português, com o SQL de cada resposta |

## Como funciona

- As consultas ficam em [`config/queries/`](config/queries) e rodam no SQL Warehouse.
- O Genie roda **em nome de quem pergunta** (user authorization, escopos `sql` e `genie`):
  cada pessoa vê só o que o Unity Catalog permite.
- [`scripts/conceder-acesso.sh`](../scripts/conceder-acesso.sh) (na raiz do repositório) dá ao service principal do app
  `USE CATALOG`, `USE SCHEMA` e `SELECT` na silver e na gold.

## Rodar e publicar

```bash
npm install
npm run typecheck && npm run lint
databricks bundle deploy --profile DEFAULT
cd .. && bash scripts/conceder-acesso.sh minha-torre && cd minha-torre
databricks apps deploy --profile DEFAULT
```

Para rodar local, copie `.env.example` para `.env` e preencha (o `.env` não vai para o Git).
