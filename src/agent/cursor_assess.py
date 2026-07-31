"""Assessment via Cursor SDK (CURSOR_API_KEY da assinatura)."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

_ROOT = Path(__file__).resolve().parent.parent.parent
load_dotenv(_ROOT / ".env")


ASSESSMENT_PROMPT = """\
Você é um especialista em OpenShift/Kubernetes. Analise os artefatos neste diretório
de trabalho (YAML de deployments, services, routes, configmaps, resources e logs)
e gere UM ÚNICO arquivo Markdown em português do Brasil (com acentuação correta).

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
     Upgrade disponível = Subscription.status.state (`AtLatestKnown`, `UpgradeAvailable`, `UpgradePending`, `UpgradeFailed`) ou inferido via PackageManifest; `—` se sem evidência
     Fonte: `<ns>/resources/clusterserviceversions.operators.coreos.com/`, `subscriptions.operators.coreos.com/`, `packagemanifests.packages.operators.coreos.com/`
3. Arquitetura reversa
   - Baseada em Deployments, Services, Routes e ConfigMaps
   - Inclua um diagrama mermaid flowchart TB simples (Usuário → apps e apps → apps)
   - Sem sintaxe inválida no mermaid (não use parênteses em rótulos de aresta)
4. Recursos de CPU e memória
   - Lista por aplicação (requests = mínimo, limits = máximo)
   - Sumário do namespace
   - Tabela de capacidade dos worker nodes (`worknodes/`)
   - 3 comparativos: disponível×request, disponível×limit, disponível×otimizações
   - Economia de recursos simplificada (CPU/memória liberadas)
   - Sugestão conservadora otimizada de CPU/memória por contêiner (Burstable, limit ≈ 2× request)
   - Sugestões de HPA (min/max, target CPU/memória) e exemplos YAML aplicáveis
   - Gráficos pizza mermaid (`pie showData`) quando houver dados
5. Observabilidade (métricas, logs, monitoramento)
   - Oportunidades de rastreabilidade e correção de erros
   - Gráficos pizza de erros por sistema/aplicação e por categoria
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
            "Pacote cursor-sdk não instalado. Execute:\n"
            "  pip install cursor-sdk\n"
        ) from exc

    from agent.local_analyze import resolve_report_path

    artifacts_dir = artifacts_dir.resolve()
    if not artifacts_dir.is_dir():
        raise SystemExit(f"Diretório de artefatos inválido: {artifacts_dir}")

    api_key = os.getenv("CURSOR_API_KEY", "").strip()
    if not api_key:
        raise SystemExit(
            "CURSOR_API_KEY não definida. Configure no .env "
            "(https://cursor.com/dashboard/api)."
        )

    out = resolve_report_path(artifacts_dir, report_path)
    out.parent.mkdir(parents=True, exist_ok=True)

    model = os.getenv("CURSOR_MODEL", "composer-2.5").strip() or "composer-2.5"
    prompt = ASSESSMENT_PROMPT.format(report_path=str(out))

    print(f"[agent] Modo LLM via Cursor SDK")
    print(f"[agent] Artefatos (cwd): {artifacts_dir}")
    print(f"[agent] Modelo: {model}")
    print(f"[agent] Relatório alvo: {out}")

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
    print(f"[agent] Status Cursor: {status}")
    if text:
        preview = str(text).strip()
        if len(preview) > 400:
            preview = preview[:400] + "..."
        print(f"[agent] Resumo: {preview}")

    if not out.is_file():
        # Fallback: se o agente só devolveu texto, gravamos nós mesmos
        if text and str(text).strip():
            out.write_text(str(text).strip() + "\n", encoding="utf-8")
            print(f"[agent] Relatório gravado a partir da resposta do modelo: {out}")
        else:
            raise SystemExit(
                f"O agente Cursor terminou sem criar o arquivo: {out}\n"
                f"Status: {status}"
            )
    else:
        print(f"[agent] Relatório gerado em: {out}")

    return out
