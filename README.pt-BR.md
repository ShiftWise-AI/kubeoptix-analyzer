# kubeoptix-analyzer

Analisador offline de artefatos de aplicações OpenShift e Kubernetes. Ele lê manifests, logs e inventário de worker nodes já coletados e gera um único relatório Markdown.

Versões do documento: [English](README.md) | [Italiano](README.it.md)

## Visão geral

Este projeto é a etapa de análise do fluxo KubeOptix.

- `kubeoptix-analyzer` conecta em um cluster OpenShift em execução, coleta os artefatos, remove manifests `Secret` e anonimiza valores sensíveis.
- `kubeoptix-analyzer` consome esses artefatos preparados e produz um relatório de assessment.

O processo upstream de extração e tratamento de dados está documentado no README do harvester:

- https://github.com/ShiftWise-AI/kubeoptix-analyzer/blob/main/README.md

De acordo com esse documento, o pipeline dos artefatos é:

1. Coletar os manifests dos worker nodes.
2. Coletar recursos dos namespaces e logs dos pods.
3. Remover os arquivos YAML cujo `kind` seja `Secret`.
4. Anonimizar in-place padrões sensíveis, como emails, tokens, certificados, chaves e outros segredos.

Este analyzer assume que essas etapas já aconteceram antes do início da análise.

## Requisitos

- Python 3.9+
- Bash
- Um diretório de artefatos gerado pelo `kubeoptix-analyzer` ou por outro coletor compatível

## Instalação

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

## Instalação Helm no OpenShift

Este repositório agora inclui um chart Helm para deploy da API do analyzer no OpenShift:

```text
helm/kubeoptix-analyzer
```

Instalar ou atualizar:

```bash
helm upgrade --install kubeoptix-analyzer ./helm/kubeoptix-analyzer \
  --namespace shiftwise-ai \
  --create-namespace \
  --set env.MODE=local
```

Observações:

- Os relatórios são gravados em `/app/data/reports`.
- Os artefatos de entrada são lidos de `/app/data/assessment`.
- A API aceita `POST /run` com um body JSON contendo apenas `mode`.
- A API expõe `GET /status` com progresso em texto puro de `0` a `100`.
- A API expõe `DELETE /reports` para limpar o conteúdo de `/app/data/reports`.
- O chart força `replicaCount=1` e falha no render se configurado com qualquer outro valor.
- O chart pode selecionar `storageClassName` automaticamente (`persistence.storageClassName=auto`): prioriza a classe padrão e, se não houver, usa a primeira classe disponível.
- Se `persistence.existingClaim` for definido, o chart usa esse PVC diretamente e não cria um novo PVC.
- A Route do OpenShift fica habilitada por padrão.
- O chart cria `ImageStream` + `BuildConfig` do OpenShift por padrão.
- Source Git padrão do BuildConfig: `https://github.com/ShiftWise-AI/kubeoptix-analyzer.git`.
- A autenticação do source usa a secret existente `github-auth`.
- As credenciais de runtime do analyzer ficam em `secretEnv`. Por padrão o chart cria uma secret com `CURSOR_API_KEY`, `CURSOR_MODEL`, `LLM_API_KEY`, `LLM_BASE_URL` e `LLM_MODEL`.
- Para reutilizar uma secret existente nas credenciais do analyzer, configure `secretEnv.create=false` e `secretEnv.name=<nome-da-secret>`.

Formato esperado da secret (já existente no namespace):

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: github-auth
type: kubernetes.io/basic-auth
stringData:
  username: x-access-token
  password: <github-token>
```

Se precisar criar:

```bash
oc -n shiftwise-ai create secret generic github-auth \
  --type=kubernetes.io/basic-auth \
  --from-literal=username='x-access-token' \
  --from-literal=password='<github-token>'
```

## Uso da API

A API usa os diretórios fixos do runtime:

- `/app/data/assessment`
- `/app/data/reports`

Executar a análise:

```bash
curl -k -X POST https://analyzer-shiftwise-ai.apps-crc.testing/run \
  -H "Content-Type: application/json" \
  -d '{
    "mode": "local"
  }'
```

Limpar a pasta de relatórios:

```bash
curl -k -X DELETE https://analyzer-shiftwise-ai.apps-crc.testing/reports
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

## Configuração

O CLI carrega variáveis do arquivo `.env` na raiz do projeto.

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

- se o `.env` não existir, a execução para com erro amigável
- se `CURSOR_API_KEY` e `LLM_API_KEY` estiverem vazias, a execução para com erro amigável

O modo embedded usa um endpoint local OpenAI-compatible. Exemplo com Ollama e uma variante quantizada de Mistral 7B Instruct:

```dotenv
EMBEDDED_BASE_URL=http://127.0.0.1:11434/v1
EMBEDDED_API_KEY=ollama
EMBEDDED_MODEL=mistral
EMBEDDED_TIMEOUT_S=120
```

## Idioma do relatório

O CLI suporta internacionalização do relatório pelo parâmetro `--locale`.

Valores suportados:

- `pt-BR` (padrão)
- `en-US`
- `es-ES`
- `it-IT`

Se `--locale` não for informado, o relatório será gerado em `pt-BR`.

## Fluxo de execução

### 1. Preparar ou coletar os artefatos

Use o `kubeoptix-analyzer` primeiro para exportar os dados do cluster, remover manifests `Secret` e anonimizar o conteúdo sensível.

### 2. Instalar dependências

```bash
./run.sh --help
```

Na primeira execução do script wrapper, ele vai:

1. Resolver a raiz do projeto.
2. Criar `.venv/` se ela não existir.
3. Ativar o ambiente virtual.
4. Atualizar o `pip`.
5. Instalar as dependências de `requirements.txt`.
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

Observação: em execução dentro de container ou OpenShift (OCP), `--mode embedded` é bloqueado e retorna a mensagem em inglês:

```text
Embedded mode is not available in container or OpenShift environments yet.
```

Locale customizado:

```bash
./run.sh --artifacts ./artifacts --mode local --locale en-US
./run.sh --artifacts ./artifacts --mode embedded --locale es-ES
./run.sh --artifacts ./artifacts --mode llm --locale it-IT
```

Caminho customizado do relatório:

```bash
./run.sh --artifacts ./artifacts --report ./out/assessment-report.md
```

### 4. Escolher o modo de análise

`local`

- análise determinística sem chamadas externas para LLM
- varre manifests, routes, services, ConfigMaps, logs, operadores, HPAs e capacidade dos worker nodes
- grava um relatório Markdown diretamente a partir de heurísticas locais
- traduz o Markdown final para o locale selecionado em `--locale`

`llm`

- valida que existe `.env` com credenciais
- se `CURSOR_API_KEY` estiver definida, usa Cursor SDK
- caso contrário, se `LLM_API_KEY` estiver definida, usa uma API OpenAI-compatible e um loop ReAct dirigido por tools
- grava um único relatório Markdown no diretório de artefatos ou no caminho informado em `--report`
- instrui o modelo a responder no locale selecionado em `--locale`

`embedded`

- não disponível quando o analyzer está rodando em container ou em OpenShift (OCP)
- executa primeiro a análise local determinística
- calcula classificação heurística + reranking dos achados
- agrupa erros de log repetidos por assinatura normalizada
- calcula score de risco por workload com base em achados, logs, QoS, ausência de limits/requests e postura de réplicas
- detecta outliers de requests/limits com análise baseada em IQR
- envia apenas um resumo compacto das evidências para um modelo local OpenAI-compatible, como Ollama + Mistral
- traduz o Markdown final para o locale selecionado em `--locale`

### 5. Revisar a saída

Por padrão, o arquivo gerado é:

```text
<artifacts>/assessment-report.md
```

O relatório cobre inventário, topologia, recursos, observabilidade, verificações de segurança em ConfigMaps, achados, plano de ação e referências.

## Fluxo interno do analyzer

```mermaid
flowchart TD
    A[Diretório de artefatos preparados] --> B[run.sh]
    B --> C[Cria ou reutiliza .venv]
    C --> D[Instala dependências]
    D --> E[python -m agent]
    E --> F{Modo}

    F -->|local| G[Descobre namespaces e worknodes]
    G --> H[Parse de manifests YAML e logs]
    H --> I[Executa módulos de análise local]
    I --> J[Grava assessment-report.md]

    F -->|llm| K[Valida .env e credenciais]
    K --> L{Provider}
    L -->|Cursor| M[Prompt via Cursor SDK sobre o diretório]
    L -->|OpenAI-compatible| N[Inventaria artefatos e expõe tools locais]
    N --> O[Loop ReAct dirigido por tools]
    F -->|embedded| Q[Executa a análise local determinística]
    Q --> R[Aplica reranking heurístico e score de risco]
    R --> S[Agrupa erros de log e detecta outliers]
    S --> T[Envia resumo compacto para modelo local OpenAI-compatible]
    M --> P[Grava relatório Markdown]
    O --> P
    T --> P
```

  ## O que o modo local analisa

- descoberta de namespaces
  - inventário de aplicações
  - topologia inferida de Deployments, Services, Routes e ConfigMaps
  - requests e limits de CPU e memória
- totais allocatable e capacity dos worker nodes
  - recursos relacionados a HPA e observabilidade
  - padrões de erro em logs, como crash, OOM, timeout e falha de conexão
  - padrões arriscados de configuração em manifests e ConfigMaps
- inventario de operadores a partir de CSVs, Subscriptions e PackageManifests

## Comandos principais

  Exibir ajuda do CLI:

```bash
python -m agent --help
```

Executar análise local diretamente:

```bash
python -m agent --artifacts ./artifacts --mode local
```

Executar análise LLM diretamente:

```bash
python -m agent --artifacts ./artifacts --mode llm
```

Executar análise embedded diretamente:

```bash
python -m agent --artifacts ./artifacts --mode embedded
```

Executar com locale específico:

```bash
python -m agent --artifacts ./artifacts --mode local --locale en-US
```

## Observações

- O analyzer é offline em relação ao cluster. Ele apenas lê artefatos locais.
- A qualidade do relatório depende da completude dos artefatos coletados.
- O modo LLM não substitui a sanitização dos artefatos. A remoção de dados sensíveis deve acontecer antes, no pipeline do harvester.

## Versões do documento

- [English](README.md)
- [PT-BR](README.pt-BR.md)
- [Italiano](README.it.md)