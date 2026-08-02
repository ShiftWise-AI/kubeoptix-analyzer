# kubeoptix-analyzer

Analisador offline de artefatos de aplicacoes OpenShift e Kubernetes. Ele le manifests, logs e inventario de worker nodes ja coletados e gera um unico relatorio Markdown.

Versoes do documento: [English](README.md) | [Italiano](README.it.md)

## Visao geral

Este projeto e a etapa de analise do fluxo KubeOptix.

- `kubeoptix-harvester` conecta em um cluster OpenShift em execucao, coleta os artefatos, remove manifests `Secret` e anonimiza valores sensiveis.
- `kubeoptix-analyzer` consome esses artefatos preparados e produz um relatorio de assessment.

O processo upstream de extracao e tratamento de dados esta documentado no README do harvester:

- https://github.com/ShiftWise-AI/kubeoptix-harvester/blob/main/README.md

De acordo com esse documento, o pipeline dos artefatos e:

1. Coletar os manifests dos worker nodes.
2. Coletar recursos dos namespaces e logs dos pods.
3. Remover os arquivos YAML cujo `kind` seja `Secret`.
4. Anonimizar in-place padroes sensiveis, como emails, tokens, certificados, chaves e outros segredos.

Este analyzer assume que essas etapas ja aconteceram antes do inicio da analise.

## Requisitos

- Python 3.9+
- Bash
- Um diretorio de artefatos gerado pelo `kubeoptix-harvester` ou por outro coletor compativel

## Instalacao

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

## Layout de entrada suportado

O analyzer aceita os dois layouts abaixo.

1. Layout orientado a recursos:

```text
<artifacts>/
  worknodes/
  <namespace>/
    resources/
      deployments.apps/
      services/
      routes.route.openshift.io/
      configmaps/
      pods/
      horizontalpodautoscalers.autoscaling/
      servicemonitors.monitoring.coreos.com/
      podmonitors.monitoring.coreos.com/
      prometheusrules.monitoring.coreos.com/
      clusterserviceversions.operators.coreos.com/
      subscriptions.operators.coreos.com/
      packagemanifests.packages.operators.coreos.com/
    pods-logs/
```

2. Layout legado orientado a aplicacao:

```text
<artifacts>/
  <namespace>/
    apps/
      <app>/
        deployments/
        services/
        routes/
        configmaps/
        hpa/
        pod-logs/
```

## Configuracao

O CLI carrega variaveis do arquivo `.env` na raiz do projeto.

Exemplo:

```dotenv
CURSOR_API_KEY=
CURSOR_MODEL=composer-2.5

# Alternativa OpenAI-compatible
# LLM_API_KEY=
# LLM_BASE_URL=https://api.openai.com/v1
# LLM_MODEL=gpt-4o-mini
```

O modo LLM agora valida o `.env` antes de executar:

- se o `.env` nao existir, a execucao para com erro amigavel
- se `CURSOR_API_KEY` e `LLM_API_KEY` estiverem vazias, a execucao para com erro amigavel

O modo embedded usa um endpoint local OpenAI-compatible. Exemplo com Ollama e uma variante quantizada de Mistral 7B Instruct:

```dotenv
EMBEDDED_BASE_URL=http://127.0.0.1:11434/v1
EMBEDDED_API_KEY=ollama
EMBEDDED_MODEL=mistral
EMBEDDED_TIMEOUT_S=120
```

## Fluxo de execucao

### 1. Preparar ou coletar os artefatos

Use o `kubeoptix-harvester` primeiro para exportar os dados do cluster, remover manifests `Secret` e anonimizar o conteudo sensivel.

### 2. Instalar dependencias

```bash
./run.sh --help
```

Na primeira execucao do script wrapper, ele vai:

1. Resolver a raiz do projeto.
2. Criar `.venv/` se ela nao existir.
3. Ativar o ambiente virtual.
4. Atualizar o `pip`.
5. Instalar as dependencias de `requirements.txt`.
6. Iniciar `python -m agent` com os mesmos argumentos de CLI.

### 3. Executar o analyzer

Modo local:

```bash
./run.sh --artifacts ./artifacts
```

Modo LLM:

```bash
./run.sh --artifacts ./artifacts --mode llm
```

Modo embedded:

```bash
./run.sh --artifacts ./artifacts --mode embedded
```

Caminho customizado do relatorio:

```bash
./run.sh --artifacts ./artifacts --report ./out/assessment-report.md
```

### 4. Escolher o modo de analise

`local`

- analise deterministica sem chamadas externas para LLM
- varre manifests, routes, services, ConfigMaps, logs, operadores, HPAs e capacidade dos worker nodes
- grava um relatorio Markdown diretamente a partir de heuristicas locais

`llm`

- valida que existe `.env` com credenciais
- se `CURSOR_API_KEY` estiver definida, usa Cursor SDK
- caso contrario, se `LLM_API_KEY` estiver definida, usa uma API OpenAI-compatible e um loop ReAct dirigido por tools
- grava um unico relatorio Markdown no diretorio de artefatos ou no caminho informado em `--report`

`embedded`

- executa primeiro a analise local deterministica
- calcula classificacao heuristica + reranking dos achados
- agrupa erros de log repetidos por assinatura normalizada
- calcula score de risco por workload com base em achados, logs, QoS, ausencia de limits/requests e postura de replicas
- detecta outliers de requests/limits com analise baseada em IQR
- envia apenas um resumo compacto das evidencias para um modelo local OpenAI-compatible, como Ollama + Mistral

### 5. Revisar a saida

Por padrao, o arquivo gerado e:

```text
<artifacts>/assessment-report.md
```

O relatorio cobre inventario, topologia, recursos, observabilidade, verificacoes de seguranca em ConfigMaps, achados, plano de acao e referencias.

## Fluxo interno do analyzer

```mermaid
flowchart TD
    A[Diretorio de artefatos preparados] --> B[run.sh]
    B --> C[Cria ou reutiliza .venv]
    C --> D[Instala dependencias]
    D --> E[python -m agent]
    E --> F{Modo}

    F -->|local| G[Descobre namespaces e worknodes]
    G --> H[Parse de manifests YAML e logs]
    H --> I[Executa modulos de analise local]
    I --> J[Grava assessment-report.md]

    F -->|llm| K[Valida .env e credenciais]
    K --> L{Provider}
    L -->|Cursor| M[Prompt via Cursor SDK sobre o diretorio]
    L -->|OpenAI-compatible| N[Inventaria artefatos e expoe tools locais]
    N --> O[Loop ReAct dirigido por tools]
    F -->|embedded| Q[Executa a analise local deterministica]
    Q --> R[Aplica reranking heuristico e score de risco]
    R --> S[Agrupa erros de log e detecta outliers]
    S --> T[Envia resumo compacto para modelo local OpenAI-compatible]
    M --> P[Grava relatorio Markdown]
    O --> P
    T --> P
```

## O que o modo local analisa

- descoberta de namespaces
- inventario de aplicacoes
- topologia inferida de Deployments, Services, Routes e ConfigMaps
- requests e limits de CPU e memoria
- totais allocatable e capacity dos worker nodes
- recursos relacionados a HPA e observabilidade
- padroes de erro em logs, como crash, OOM, timeout e falha de conexao
- padroes arriscados de configuracao em manifests e ConfigMaps
- inventario de operadores a partir de CSVs, Subscriptions e PackageManifests

## Comandos principais

Exibir ajuda do CLI:

```bash
python -m agent --help
```

Executar analise local diretamente:

```bash
python -m agent --artifacts ./artifacts --mode local
```

Executar analise LLM diretamente:

```bash
python -m agent --artifacts ./artifacts --mode llm
```

Executar analise embedded diretamente:

```bash
python -m agent --artifacts ./artifacts --mode embedded
```

## Observacoes

- O analyzer e offline em relacao ao cluster. Ele apenas le artefatos locais.
- A qualidade do relatorio depende da completude dos artefatos coletados.
- O modo LLM nao substitui a sanitizacao dos artefatos. A remocao de dados sensiveis deve acontecer antes, no pipeline do harvester.

## Versoes do documento

- [English](README.md)
- [PT-BR](README.pt-BR.md)
- [Italiano](README.it.md)