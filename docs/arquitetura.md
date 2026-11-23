# Arquitetura

```mermaid
flowchart LR
    subgraph Fontes["Fontes (cada gerente do seu jeito)"]
        XL["20 planilhas Excel"]
        CU["25 listas ClickUp (JSON)"]
        MP["15 cronogramas MS Project (XML)"]
        OUT["PMO · RH · timesheet · custos · fornecedores (CSV)"]
    end

    S3[("Data lake<br/>Supabase Storage · S3")]

    subgraph DBX["Databricks · Unity Catalog farol_projeto"]
        direction LR
        B["bronze<br/>9 tabelas, como vieram"]
        C{{"conferência<br/>9 contagens"}}
        S["silver<br/>7 tabelas limpas<br/>3 ferramentas → 1 modelo"]
        G["gold<br/>fato semanal · situação atual<br/>utilização por pessoa"]
        T{{"10 testes de qualidade"}}
        IA["status_estruturado<br/>ai_classify + ai_extract"]
        MV["metric view<br/>mv_projetos"]
    end

    subgraph Produtos["Produtos de dados"]
        D["Dashboard AI/BI<br/>4 páginas"]
        APP["App (React + AppKit)<br/>risco · simulador · perguntar"]
        GE["Agente Genie<br/>Farol · Diretoria"]
    end

    XL & CU & MP & OUT --> S3 -->|"boto3"| B --> C --> S --> G
    G --> T
    S --> IA
    G --> MV --> GE
    G --> D
    G --> APP
    IA --> D
    GE --> APP
```

## O job `farol_projeto_job` (toda segunda, 6h · ~4 min de ponta a ponta)

```mermaid
flowchart LR
    A[ingestao_data_lake] --> B[conferencia_bronze] --> C[medalhao<br/>pipeline Lakeflow]
    C --> D[testes_de_qualidade]
    C --> E[status_com_ia]
    D --> F[metricas_governadas<br/>metric view]
    E --> F
```

Tudo é código, publicado com `databricks bundle deploy` (Declarative Automation Bundles):
o job, o pipeline, o dashboard, o Genie e o app.
