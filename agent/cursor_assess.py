"""Assessment via Cursor SDK (subscription CURSOR_API_KEY)."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(_ROOT / ".env")


ASSESSMENT_PROMPT = """\
Você é um especialista em OpenShift/Kubernetes. Analise os artefatos neste diretório
de trabalho (YAML de deployments, services, routes, configmaps, resources e logs)
e gere UM ÚNICO arquivo Markdown em português do Brasil.

Grave o relatório exatamente em:
{report_path}

O arquivo deve ser fácil de entender por humanos e conter estas seções:

1. Sumário executivo
2. Inventário do namespace / aplicações
   - 2.1 Workloads em execução (tabela)
   - 2.2 Services (tabela)
   - 2.3 Exposição externa / Routes (tabela)
   - 2.4 ConfigMaps de aplicação (tabela)
   - 2.5 Secrets referenciados (tabela; sem reproduzir conteúdo)
   - 2.6 Operadores presentes no namespace / ClusterServiceVersions (**obrigatoriamente em tabela Markdown**, nunca em prosa/lista inline)
     Colunas: Operador (displayName) | CSV | Versão | Phase | Upgrade disponível | Provider | Evidência (path do YAML)
     Upgrade disponível = valor de `status.state` (buscar no atributo `status` do CSV ou da Subscription correspondente: propriedade `state:`). Exemplos: `AtLatestKnown`, `UpgradeAvailable`, `UpgradePending`, `UpgradeFailed`. Sem `status.state`, inferir via PackageManifest; `—` se sem evidência
     Fonte: `<ns>/resources/clusterserviceversions.operators.coreos.com/`, `subscriptions.operators.coreos.com/`, `packagemanifests.packages.operators.coreos.com/`
3. Arquitetura reversa
   - Baseada em Deployments, Services, Routes e ConfigMaps
   - Não use Mermaid. Incorpore os blocos Markdown de `list_visualizations` com PNG
     já embutidos como `data:image/png;base64,...` (nunca use paths `./report_assets/`)
4. Recursos de CPU e memória
   - 4.1 Lista por aplicação (requests/limits) **com coluna QoS** e **legenda QoS abaixo da tabela** (Guaranteed / Burstable / BestEffort)
   - Sumário do namespace
   - 4.3 Tabela de capacidade dos worker nodes (`worknodes/`) com **legenda abaixo** das colunas de CPU/memória (allocatable vs capacity)
   - 3 comparativos: disponível×request, disponível×limit, disponível×otimizações
   - Economia de recursos simplificada (CPU/memória liberadas)
   - Sugestão conservadora otimizada de CPU/memória por contêiner (Burstable, limit ≈ 2× request)
   - Sugestões de HPA (min/max, target CPU/memória) e exemplos YAML aplicáveis
   - Item de **boas práticas de affinity / anti-affinity** (inventário nos workloads + recomendações podAntiAffinity, nodeAffinity, topologia)
   - Gráficos de composição em PNG (donut matplotlib) quando houver dados
5. Observabilidade (métricas, logs, monitoramento)
   - Oportunidades de rastreabilidade e correção de erros
   - Gráficos PNG de erros por sistema/aplicação e por categoria
6. ConfigMaps e dados sensíveis (secrets, chaves, certificados)
7. Plano de ação em seções separadas:
   - Ações de infraestrutura do cluster / plataforma
   - Melhorias da aplicação
8. Referências utilizadas (documentação Kubernetes/OpenShift/HPA/QoS) no final do arquivo
   - Priorização e critérios de aceite

Regras:
- Não invente dados que não estejam nos arquivos.
- Não reintroduza secrets sanitizados.
- Escreva o arquivo .md completo no caminho pedido (crie diretórios se necessário).
- Ao terminar, responda só com o caminho do arquivo gerado.
"""


def run_cursor_assessment(
    artifacts_dir: Path,
    report_path: Path | None = None,
) -> Path:
    try:
        from cursor_sdk import Agent, AgentOptions, LocalAgentOptions
    except ImportError as exc:
        raise SystemExit(
            "cursor-sdk package is not installed. Run:\n"
            "  pip install cursor-sdk\n"
        ) from exc

    from agent.local_analyze import resolve_report_path
    from agent.visualization.pregenerate import (
        finalize_report_markdown,
        format_visualization_catalog,
        generate_all_visualizations,
    )

    artifacts_dir = artifacts_dir.resolve()
    if not artifacts_dir.is_dir():
        raise SystemExit(f"Invalid artifacts directory: {artifacts_dir}")

    api_key = os.getenv("CURSOR_API_KEY", "").strip()
    if not api_key:
        raise SystemExit(
            "CURSOR_API_KEY is not set. Configure SYSTEM_SETTINGS_URL or .env "
            "(https://cursor.com/dashboard/api)."
        )

    out = resolve_report_path(artifacts_dir, report_path)
    out.parent.mkdir(parents=True, exist_ok=True)

    assets, visualizations = generate_all_visualizations(artifacts_dir)
    viz_catalog = format_visualization_catalog(visualizations)
    if visualizations:
        print(
            f"[agent] Pre-generated {len(visualizations)} namespace visualization set(s) "
            f"in {assets.assets_dir}"
        )

    model = os.getenv("CURSOR_MODEL", "composer-2.5").strip() or "composer-2.5"
    prompt = ASSESSMENT_PROMPT.format(report_path=str(out))
    if viz_catalog.strip():
        prompt = (
            f"{prompt}\n\n"
            "Visualizações PNG já geradas (incorpore os blocos Markdown abaixo nas seções "
            "correspondentes do relatório; não gere novamente se os arquivos já existem):\n\n"
            f"{viz_catalog}\n"
        )

    print(f"[agent] LLM mode via Cursor SDK")
    print(f"[agent] Artifacts (cwd): {artifacts_dir}")
    print(f"[agent] Model: {model}")
    print(f"[agent] Target report: {out}")

    result = Agent.prompt(
        prompt,
        AgentOptions(
            api_key=api_key,
            model=model,
            local=LocalAgentOptions(cwd=str(artifacts_dir)),
        ),
    )

    status = getattr(result, "status", None)
    text = getattr(result, "result", None) or ""
    print(f"[agent] Cursor status: {status}")
    if text:
        preview = str(text).strip()
        if len(preview) > 400:
            preview = preview[:400] + "..."
        print(f"[agent] Summary: {preview}")

    if not out.is_file():
        # Fallback: if the agent returned only text, write it ourselves.
        if text and str(text).strip():
            out.write_text(str(text).strip() + "\n", encoding="utf-8")
            print(f"[agent] Report written from model output: {out}")
        else:
            raise SystemExit(
                f"The Cursor agent finished without creating the file: {out}\n"
                f"Status: {status}"
            )
    else:
        print(f"[agent] Report generated at: {out}")

    content = out.read_text(encoding="utf-8")
    final = finalize_report_markdown(
        content,
        artifacts_dir=artifacts_dir,
        report_dir=out.parent,
        visualizations=visualizations,
    )
    if final != content:
        out.write_text(final, encoding="utf-8")
        embedded_count = final.count("data:image/png;base64,")
        print(f"[agent] Embedded {embedded_count} PNG image(s) into report body")

    return out
