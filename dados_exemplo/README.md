# Amostra dos dados brutos

Um arquivo de cada fonte, do jeito que chegam ao data lake, para mostrar o problema:
cada gerente controla o projeto numa ferramenta diferente, cada uma com seu formato.

| Pasta | Fonte | Formato | O que tem de "sujo" |
|---|---|---|---|
| `excel/` | Planilhas dos gerentes | `.xlsx` | datas em 3 formatos (texto, dd/mm/aaaa, número de série), % como texto ou fração, linha de TOTAL, nomes de arquivo sem padrão |
| `clickup/` | Export da API do ClickUp | `.json` | datas em milissegundos, % e baseline escondidos em `custom_fields`, status escrito de 12 jeitos |
| `msproject/` | Cronogramas do MS Project | `.xml` | tarefas-resumo misturadas às tarefas, horas em `PT40H0M0S` |
| `pmo/` | Cadastro do PMO (10 linhas) | `.csv` | ferramenta escrita de 8 jeitos, datas em 2 formatos, código vazio |

A lista completa das sujeiras e de como cada uma foi tratada está em [`docs/sujeiras.md`](../docs/sujeiras.md).

O dataset completo (60 projetos, 520 pessoas, ~30 mil apontamentos) é sintético e vem da
imersão Jornada de Dados; ele fica no data lake, fora do repositório.
