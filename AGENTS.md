# AI OCP App Assessment — Cursor Agent

Este projeto avalia aplicações OpenShift a partir de artefatos já coletados (YAML + logs).

## Formas de assessment

1. **Cursor Agent (sem LLM externa)** — chat/Agent do Cursor. Não precisa de `.env` / `LLM_`*.
2. **Análise local (sem LLM)** — `PYTHONPATH=src python -m agent --artifacts <dir> --mode local` gera **um único** `assessment-report.md` em pt-BR.
3. **Agente Python LLM** (`--use-llm`) — requer API OpenAI-compatible.

## Análise local / script

```bash
./scripts/run_assessment.sh --namespaces "app-a app-b" -o ./pasta-saida
# ou
PYTHONPATH=src python -m agent --artifacts ./pasta-saida --mode local --report ./assessment-report.md
```

O Markdown único deve conter: sumário, inventário, achados, arquitetura reversa (mermaid), CPU/memória, observabilidade com gráficos, ConfigMaps sensíveis e plano de ação (infra × aplicação).

No inventário, a subseção **2.6 Operadores presentes (ClusterServiceVersions)** deve ser **sempre tabela Markdown** (colunas: Operador/displayName, CSV, Versão, Phase, Upgrade disponível, Provider, Evidência), a partir de `<ns>/resources/clusterserviceversions.operators.coreos.com/` — nunca lista em prosa. A coluna **Upgrade disponível** usa o `status.state` da Subscription OLM (ou inferência via PackageManifest).

## Prompt sugerido (Cursor Agent)

> Faça o assessment OCP dos artefatos em `./pasta-saida` e grave um único arquivo `./pasta-saida/assessment-report.md` em português do Brasil, com arquitetura reversa, recursos, logs/gráficos, ConfigMaps e plano de ação (infra vs aplicação). No inventário, a seção 2.6 (operadores/CSVs) deve ser uma tabela Markdown.

Não inventar dados que não estejam nos arquivos. Não reintroduzir secrets sanitizados.