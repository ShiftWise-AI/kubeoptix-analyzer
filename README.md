# AI OCP App Assessment

Ferramenta para **assessment de aplicações OpenShift**: coleta artefatos do cluster, **anonimiza e remove secrets por scripts** (sem participação do agente de IA) e gera um relatório Markdown em português do Brasil.

---

## Índice

1. [Visão geral](#visão-geral)
2. [Pré-requisitos](#pré-requisitos)
3. [Instalação](#instalação)
4. [Fluxo de trabalho](#fluxo-de-trabalho)
5. [Pipeline — ordem de execução](#pipeline--ordem-de-execução)
6. [Scripts](#scripts)
7. [Anonimização e remoção de secrets](#anonimização-e-remoção-de-secrets)
8. [Executar sem LLM](#executar-sem-llm)
9. [Executar com LLM](#executar-com-llm)
10. [Conteúdo do relatório](#conteúdo-do-relatório)
11. [Estrutura do repositório](#estrutura-do-repositório)

---



## Visão geral

O processo tem **duas fases bem separadas**:


| Fase                          | Quem executa        | O quê                                                                              |
| ----------------------------- | ------------------- | ---------------------------------------------------------------------------------- |
| **1. Extração e sanitização** | Scripts bash/Python | Coleta YAML/logs do OpenShift, remove Secrets e anonimiza dados sensíveis nos logs |
| **2. Assessment**             | Agente local ou LLM | Lê apenas artefatos já sanitizados e gera o relatório Markdown                     |


**Importante:**

- Os dados **precisam ser extraídos pelos scripts de coleta** (`oc_collect_`*).
- A **anonimização e a remoção de secrets são feitas só pelos scripts**, **sem interação do agente de IA**.
- O agente (local ou LLM) **não** deve coletar do cluster nem manipular secrets; ele analisa a pasta de artefatos já preparada.

---



## Pré-requisitos

- `oc` instalado e sessão autenticada no cluster (`oc login` / `oc whoami`)
- Python 3.10+
- Acesso de leitura aos namespaces a avaliar

Para modo LLM com Cursor:

- Assinatura Cursor e API key em [cursor.com/dashboard/api](https://cursor.com/dashboard/api)

---



## Instalação

```bash
git clone <url-deste-repositorio>
cd ai-ocp-app-assessment

python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env
# Edite .env apenas se for usar --mode llm (CURSOR_API_KEY)
```

---



## Fluxo de trabalho

```text
┌─────────────────┐     ┌──────────────────────┐     ┌─────────────────────┐
│ 1. Coleta (oc)  │────▶│ 2. Sanitização       │────▶│ 3. Assessment       │
│ scripts bash    │     │ (scripts, sem IA)    │     │ local ou LLM        │
└─────────────────┘     └──────────────────────┘     └─────────────────────┘
        │                         │                            │
        ▼                         ▼                            ▼
  YAML + logs               Secrets removidos           assessment-report.md
  por namespace             Logs anonimizados           (único arquivo pt-BR)
```

1. **Coleta** — scripts usam `oc` e gravam manifests e logs em disco.
2. **Sanitização** — scripts removem arquivos `kind: Secret` e mascaram PII/tokens/certificados nos logs.
3. **Assessment** — agente lê a pasta sanitizada e gera o relatório.

Você pode rodar o pipeline completo de uma vez (`run_assessment.sh`) ou cada etapa manualmente.

---



## Pipeline — ordem de execução



### Ordem obrigatória (quando feita passo a passo)


| #   | Etapa           | Comando                                                     | Observação              |
| --- | --------------- | ----------------------------------------------------------- | ----------------------- |
| 1   | Coleta          | `oc_collect_all_namespaces.sh` ou `oc_collect_namespace.sh` | Extrai dados do cluster |
| 2   | Remover Secrets | `oc_remove_secret_manifests.sh -d <pasta>`                  | **Script**, sem agente  |
| 3   | Anonimizar logs | `python python_valida_logs.py <pasta>`                      | **Script**, sem agente  |
| 4   | Assessment      | `python -m agent --artifacts <pasta> ...`                   | Local ou LLM            |




### Pipeline único (recomendado)

O `run_assessment.sh` executa as etapas na ordem correta:

```bash
./scripts/run_assessment.sh --namespaces "ns1 ns2" -o ./pasta-saida
```

Fluxo interno:

1. Coleta (`oc_collect_all_namespaces.sh`)
2. Remoção de Secrets (`oc_remove_secret_manifests.sh`)
3. Anonimização de logs (`python_valida_logs.py`)
4. Assessment (`python -m agent`, padrão: `--mode local`)

Com artefatos **já coletados e já sanitizados**:

```bash
./scripts/run_assessment.sh --artifacts ./pasta-saida --skip-sanitize
```

---



## Scripts



### Coleta


| Script                                                                         | Função                                                                                       |
| ------------------------------------------------------------------------------ | -------------------------------------------------------------------------------------------- |
| `[scripts/oc_collect_namespace.sh](scripts/oc_collect_namespace.sh)`           | Coleta artefatos de **um** namespace (deployments, services, routes, configmaps, logs, etc.) |
| `[scripts/oc_collect_all_namespaces.sh](scripts/oc_collect_all_namespaces.sh)` | Orquestra a coleta para **vários** namespaces                                                |


Exemplos:

```bash
# Um namespace
./scripts/oc_collect_namespace.sh -n meu-namespace -o ./pasta-saida

# Vários namespaces
./scripts/oc_collect_all_namespaces.sh \
  --namespaces "app-a app-b" \
  -o ./pasta-saida \
  --tail-lines 300
```

Requisitos: `oc` no PATH e sessão autenticada.

### Sanitização (sem agente de IA)


| Script                                                                           | Função                                                                                 |
| -------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------- |
| `[scripts/oc_remove_secret_manifests.sh](scripts/oc_remove_secret_manifests.sh)` | Apaga manifests YAML com `kind: Secret`                                                |
| `[python_valida_logs.py](python_valida_logs.py)`                                 | Anonimiza dados sensíveis em arquivos de log (CPF, e-mail, tokens, certificados, etc.) |


```bash
./scripts/oc_remove_secret_manifests.sh -d ./pasta-saida
# Preview sem apagar:
./scripts/oc_remove_secret_manifests.sh -d ./pasta-saida --dry-run

python python_valida_logs.py ./pasta-saida
```



### Orquestração e assessment


| Script / comando                                         | Função                                                   |
| -------------------------------------------------------- | -------------------------------------------------------- |
| `[scripts/run_assessment.sh](scripts/run_assessment.sh)` | Pipeline completo: coleta (opcional) → sanitize → agente |
| `python -m agent`                                        | Gera o relatório a partir de uma pasta de artefatos      |




### Utilitários de conversão (opcional)


| Script                              | Função                                                               |
| ----------------------------------- | -------------------------------------------------------------------- |
| `scripts/convert.sh` / `md_to_*.py` | Conversão do relatório Markdown para outros formatos (se necessário) |


---



## Anonimização e remoção de secrets



### Princípio

> **Extração, remoção de Secrets e anonimização de logs são responsabilidade exclusiva dos scripts.**  
> O agente de assessment (local ou LLM) **não** participa dessas etapas e **não** deve receber artefatos ainda com secrets ou PII em claro.



### O que cada script faz

1. `oc_remove_secret_manifests.sh`
  - Percorre a árvore de artefatos
  - Identifica YAML com `kind: Secret`
  - Remove esses arquivos do disco
2. `python_valida_logs.py`
  - Percorre logs (e demais arquivos na pasta informada)
  - Detecta padrões sensíveis (documentos, contatos, tokens, certificados, credenciais, etc.)
  - Substitui/mascara os valores encontrados



### Por que isso importa

- Reduz risco de vazamento ao compartilhar a pasta de artefatos ou o relatório
- Permite que o LLM/agente trabalhe só sobre dados já tratados
- Mantém auditoria clara: sanitização determinística por script, análise depois

---



## Executar sem LLM

Usa heurísticas locais (sem `CURSOR_API_KEY` / sem API externa).

### Opção A — só assessment (artefatos já prontos)

```bash
source .venv/bin/activate

python -m agent \
  --artifacts ./pasta-saida \
  --mode local \
  --report ./assessment-report.md
```



### Opção B — pipeline completo sem LLM

```bash
source .venv/bin/activate

./scripts/run_assessment.sh \
  --namespaces "app-a app-b" \
  -o ./pasta-saida \
  --report ./pasta-saida/assessment-report.md
```



### Opção C — artefatos já coletados; ainda sanitizar + assessment

```bash
./scripts/run_assessment.sh \
  --artifacts ./pasta-saida \
  --report ./assessment-report.md
```

(`--artifacts` pula a coleta; sanitize roda a menos que use `--skip-sanitize`.)

---



## Executar com LLM

O `--mode llm` usa a **assinatura Cursor** via Cursor SDK (`CURSOR_API_KEY` no `.env`).

### Configuração

```bash
cp .env.example .env
# Preencha:
# CURSOR_API_KEY=crsr_...
# CURSOR_MODEL=composer-2.5   # opcional
```

Obter a key: [https://cursor.com/dashboard/api](https://cursor.com/dashboard/api)

### Assessment com LLM (artefatos já coletados e sanitizados)

```bash
source .venv/bin/activate

python -m agent \
  --artifacts ./pasta-saida \
  --mode llm \
  --report ./assessment-report.md
```



### Pipeline completo com LLM

```bash
./scripts/run_assessment.sh \
  --namespaces "app-a app-b" \
  -o ./pasta-saida \
  --use-llm \
  --report ./pasta-saida/assessment-report.md
```



### Alternativa OpenAI-compatible

Se não usar Cursor SDK, configure no `.env`:

```bash
LLM_API_KEY=...
LLM_BASE_URL=https://api.openai.com/v1
LLM_MODEL=gpt-4o-mini
```

(Sem `CURSOR_API_KEY`, o `--mode llm` tenta essa API.)

> A key do Cursor (`CURSOR_API_KEY`) **não** é uma chave OpenAI. Não use-a como `LLM_API_KEY`.

---



## Conteúdo do relatório

O assessment gera **um único** arquivo Markdown em **pt-BR**, em geral `assessment-report.md`, com:

1. Sumário executivo e inventário
2. Achados de configuração
3. Arquitetura reversa (Deployments, Services, Routes, ConfigMaps) + diagrama
4. CPU/memória por aplicação e sumário do namespace
5. Sugestões **conservadoras** de resources e **HPA**, com exemplos YAML
6. Observabilidade (logs, métricas, monitoramento) e oportunidades de melhoria
7. Análise de ConfigMaps (indícios de dados sensíveis)
8. Plano de ação separado:
   - Infraestrutura do cluster / plataforma
   - Melhorias da aplicação
9. Referências utilizadas (Kubernetes, OpenShift, HPA, QoS)

---



## Estrutura do repositório

```text
ai-ocp-app-assessment/
├── AGENTS.md                 # Instruções para o Cursor Agent no IDE
├── .cursor/rules/            # Rules do projeto
├── .env.example              # Modelo de variáveis (sem secrets)
├── README.md                 # Esta documentação
├── requirements.txt          # Dependências Python do agente
├── python_valida_logs.py     # Anonimização de logs (script, sem IA)
├── agent/                    # Pacote Python (local + LLM Cursor/OpenAI)
│   ├── __main__.py           # CLI: python -m agent
│   ├── local_analyze.py      # Assessment sem LLM
│   ├── cursor_assess.py      # Assessment com Cursor SDK
│   └── analysis/             # Módulos de análise (topo, recursos, logs, etc.)
└── scripts/
    ├── oc_collect_namespace.sh
    ├── oc_collect_all_namespaces.sh
    ├── oc_remove_secret_manifests.sh
    └── run_assessment.sh     # Pipeline coleta → sanitize → assessment
```

---



## Resumo rápido


| Objetivo                                    | Comando                                                           |
| ------------------------------------------- | ----------------------------------------------------------------- |
| Coletar + sanitizar + relatório **sem** LLM | `./scripts/run_assessment.sh --namespaces "ns1 ns2" -o ./out`     |
| Só relatório **sem** LLM                    | `python -m agent -a ./out --mode local -r ./assessment-report.md` |
| Só relatório **com** LLM (Cursor)           | `python -m agent -a ./out --mode llm -r ./assessment-report.md`   |
| Remover Secrets                             | `./scripts/oc_remove_secret_manifests.sh -d ./out`                |
| Anonimizar logs                             | `python python_valida_logs.py ./out`                              |


**Lembrete:** extraia com os scripts de coleta; anonimize e remova secrets **antes** do agente; o agente só analisa a pasta já sanitizada.