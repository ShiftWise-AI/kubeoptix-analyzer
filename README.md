# AI OCP App Assessment

Assessment de aplicações OpenShift a partir de artefatos coletados (YAML + logs).

## Análise direta (coleta opcional, sem LLM)

```bash
./scripts/run_assessment.sh --artifacts ./pasta-saida --report ./assessment-report.md
# ou
python -m agent --artifacts ./pasta-saida --mode local --report ./assessment-report.md
```

Gera **um único** Markdown em **pt-BR** contendo:

1. Sumário executivo e inventário
2. Achados de configuração
3. Arquitetura reversa simples (Deployments, Services, Routes, ConfigMaps)
4. CPU/memória por aplicação + sumário do namespace (gráficos pizza)
5. Observabilidade: logs, métricas, monitoramento (gráficos pizza de erros)
6. Análise de ConfigMaps (dados sensíveis)
7. Plano de ação: infraestrutura do cluster × melhorias da aplicação

## Pipeline com coleta

```bash
./scripts/run_assessment.sh --namespaces "app-a app-b" -o ./pasta-saida
```

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # preencha CURSOR_API_KEY
```

## Gerar com LLM (Cursor SDK)

Com `CURSOR_API_KEY` no `.env`:

```bash
python -m agent \
  --artifacts ./pasta-saida \
  --mode llm \
  --report ./assessment-report.md
```
