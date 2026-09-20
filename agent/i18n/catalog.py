"""Short user-facing report strings, one entry per message id."""

from __future__ import annotations


def msg(pt: str, en: str, es: str, it: str) -> dict[str, str]:
    return {"pt-br": pt, "en-us": en, "es": es, "it": it}


MESSAGES: dict[str, dict[str, str]] = {
    "yes": msg("sim", "yes", "sí", "sì"),
    "no": msg("não", "no", "no", "no"),
    "severity.alto": msg("Alto", "High", "Alto", "Alto"),
    "severity.medio": msg("Médio", "Medium", "Medio", "Medio"),
    "severity.baixo": msg("Baixo", "Low", "Bajo", "Basso"),
    "kind.cpu": msg("CPU", "CPU", "CPU", "CPU"),
    "kind.memory": msg("Memória", "Memory", "Memoria", "Memoria"),
    "table.total": msg("Total", "Total", "Total", "Totale"),
    "chart.empty": msg(
        "Sem dados para exibir",
        "No data to display",
        "No hay datos para mostrar",
        "Nessun dato da visualizzare",
    ),
    "chart.other": msg("outros", "other", "otros", "altri"),
    "viz.no_data": msg(
        "_Visualização indisponível: sem dados._",
        "_Visualization unavailable: no data._",
        "_Visualización no disponible: sin datos._",
        "_Visualizzazione non disponibile: nessun dato._",
    ),
    "viz.missing_file": msg(
        "_Visualização indisponível: arquivo de imagem não encontrado._",
        "_Visualization unavailable: image file not found._",
        "_Visualización no disponible: no se encontró el archivo de imagen._",
        "_Visualizzazione non disponibile: file immagine non trovato._",
    ),
    "viz.unavailable": msg(
        "_Gráfico indisponível (assets não configurados)._",
        "_Chart unavailable (assets are not configured)._",
        "_Gráfico no disponible (recursos no configurados)._",
        "_Grafico non disponibile (asset non configurati)._",
    ),
    "diagram.user": msg(
        "Usuário / Internet",
        "User / Internet",
        "Usuario / Internet",
        "Utente / Internet",
    ),
    "diagram.calls": msg("chama", "calls", "llama", "chiama"),
    "diagram.kube": msg(
        "_Diagrama gerado a partir dos manifests YAML do namespace (KubeDiagrams)._",
        "_Diagram generated from the namespace YAML manifests (KubeDiagrams)._",
        "_Diagrama generado a partir de los manifiestos YAML del espacio de nombres (KubeDiagrams)._",
        "_Diagramma generato dai manifest YAML dello spazio dei nomi (KubeDiagrams)._",
    ),
    "diagram.matplotlib": msg(
        "_Diagrama simplificado gerado localmente (matplotlib). "
        "Para diagrama completo de arquitetura, instale `kube-diagrams` e Graphviz `dot`._",
        "_Simplified diagram generated locally (matplotlib). "
        "For a full architecture diagram, install `kube-diagrams` and Graphviz `dot`._",
        "_Diagrama simplificado generado en local (matplotlib). "
        "Para un diagrama de arquitectura completo, instale `kube-diagrams` y Graphviz `dot`._",
        "_Diagramma semplificato generato in locale (matplotlib). "
        "Per un diagramma di architettura completo, installare `kube-diagrams` e Graphviz `dot`._",
    ),
    "diagram.unavailable": msg(
        "_Diagrama indisponível (assets não configurados)._",
        "_Diagram unavailable (assets are not configured)._",
        "_Diagrama no disponible (recursos no configurados)._",
        "_Diagramma non disponibile (asset non configurati)._",
    ),
    "report.title": msg(
        "# Relatório de assessment OpenShift",
        "# OpenShift assessment report",
        "# Informe de evaluación de OpenShift",
        "# Report di valutazione OpenShift",
    ),
    "report.generated": msg(
        "_Gerado em {when}_",
        "_Generated at {when}_",
        "_Generado el {when}_",
        "_Generato il {when}_",
    ),
    "report.generated_local": msg(
        "_Gerado em {when} (análise local, sem LLM)_",
        "_Generated at {when} (local analysis, without LLM)_",
        "_Generado el {when} (análisis local, sin LLM)_",
        "_Generato il {when} (analisi locale, senza LLM)_",
    ),
    "report.artifacts": msg(
        "_Artefatos: `{path}`_",
        "_Artifacts: `{path}`_",
        "_Artefactos: `{path}`_",
        "_Artefatti: `{path}`_",
    ),
    "report.no_sections": msg(
        "## Sem seções",
        "## No sections",
        "## Sin secciones",
        "## Nessuna sezione",
    ),
    "report.no_sections_body": msg(
        "O agente não registrou seções via `write_report_section`.",
        "The agent did not record sections via `write_report_section`.",
        "El agente no registró secciones mediante `write_report_section`.",
        "L'agente non ha registrato sezioni tramite `write_report_section`.",
    ),
    "report.incomplete_title": msg(
        "Resumo incompleto",
        "Incomplete summary",
        "Resumen incompleto",
        "Riepilogo incompleto",
    ),
    "report.incomplete_body": msg(
        "O agente atingiu o limite de iterações antes de concluir a análise.",
        "The agent reached the iteration limit before finishing the analysis.",
        "El agente alcanzó el límite de iteraciones antes de concluir el análisis.",
        "L'agente ha raggiunto il limite di iterazioni prima di completare l'analisi.",
    ),
    "viz.none": msg(
        "Nenhuma visualização foi gerada (nenhum namespace encontrado).",
        "No visualization was generated (no namespace found).",
        "No se generó ninguna visualización (no se encontró ningún espacio de nombres).",
        "Nessuna visualizzazione generata (nessuno spazio dei nomi trovato).",
    ),
    "viz.intro": msg(
        "Gráficos e diagramas embutidos como PNG base64 no corpo do relatório.",
        "Charts and diagrams embedded as base64 PNG in the report body.",
        "Gráficos y diagramas incrustados como PNG base64 en el cuerpo del informe.",
        "Grafici e diagrammi incorporati come PNG base64 nel corpo del report.",
    ),
    "viz.heading": msg(
        "Visualizações",
        "Visualizations",
        "Visualizaciones",
        "Visualizzazioni",
    ),
    "viz.ns_architecture": msg(
        "### Namespace `{namespace}` — diagrama de arquitetura",
        "### Namespace `{namespace}` — architecture diagram",
        "### Espacio de nombres `{namespace}` — diagrama de arquitectura",
        "### Spazio dei nomi `{namespace}` — diagramma di architettura",
    ),
    "viz.ns_memory": msg(
        "### Namespace `{namespace}` — memória limits por aplicação",
        "### Namespace `{namespace}` — memory limits by application",
        "### Espacio de nombres `{namespace}` — límites de memoria por aplicación",
        "### Spazio dei nomi `{namespace}` — limiti di memoria per applicazione",
    ),
    "viz.ns_cpu": msg(
        "### Namespace `{namespace}` — CPU limits por aplicação",
        "### Namespace `{namespace}` — CPU limits by application",
        "### Espacio de nombres `{namespace}` — límites de CPU por aplicación",
        "### Spazio dei nomi `{namespace}` — limiti di CPU per applicazione",
    ),
    "viz.ns_errors_app": msg(
        "### Namespace `{namespace}` — erros por aplicação",
        "### Namespace `{namespace}` — errors by application",
        "### Espacio de nombres `{namespace}` — errores por aplicación",
        "### Spazio dei nomi `{namespace}` — errori per applicazione",
    ),
    "viz.ns_errors_cat": msg(
        "### Namespace `{namespace}` — erros por categoria",
        "### Namespace `{namespace}` — errors by category",
        "### Espacio de nombres `{namespace}` — errores por categoría",
        "### Spazio dei nomi `{namespace}` — errori per categoria",
    ),
    "viz.title_architecture": msg(
        "Arquitetura reversa — {namespace}",
        "Reverse architecture — {namespace}",
        "Arquitectura inversa — {namespace}",
        "Architettura inversa — {namespace}",
    ),
    "viz.title_memory": msg(
        "Memória limits (Mi) por aplicação",
        "Memory limits (Mi) by application",
        "Límites de memoria (Mi) por aplicación",
        "Limiti di memoria (Mi) per applicazione",
    ),
    "viz.title_cpu": msg(
        "CPU limits (m) por aplicação",
        "CPU limits (m) by application",
        "Límites de CPU (m) por aplicación",
        "Limiti di CPU (m) per applicazione",
    ),
    "viz.title_errors_app": msg(
        "Erros por aplicação",
        "Errors by application",
        "Errores por aplicación",
        "Errori per applicazione",
    ),
    "viz.title_errors_cat": msg(
        "Erros por categoria",
        "Errors by category",
        "Errores por categoría",
        "Errori per categoria",
    ),
    "viz.cursor_note": msg(
        "Visualizações PNG já geradas (incorpore os blocos Markdown abaixo nas seções "
        "correspondentes do relatório; não gere novamente se os arquivos já existem):",
        "PNG visualizations already generated (paste the Markdown blocks below into the "
        "matching report sections; do not generate them again if the files already exist):",
        "Visualizaciones PNG ya generadas (incorpore los bloques Markdown siguientes en las "
        "secciones correspondientes del informe; no las genere de nuevo si los archivos ya existen):",
        "Visualizzazioni PNG già generate (incorporare i blocchi Markdown seguenti nelle "
        "sezioni corrispondenti del report; non generarle di nuovo se i file esistono già):",
    ),
    "tool.no_data": msg(
        "Nenhum dado fornecido para o gráfico.",
        "No data was provided for the chart.",
        "No se proporcionaron datos para el gráfico.",
        "Nessun dato fornito per il grafico.",
    ),
    "tool.ns_missing": msg(
        "Namespace '{namespace}' não encontrado. Disponíveis: {available}",
        "Namespace '{namespace}' was not found. Available: {available}",
        "No se encontró el espacio de nombres '{namespace}'. Disponibles: {available}",
        "Spazio dei nomi '{namespace}' non trovato. Disponibili: {available}",
    ),
    "tool.none": msg("(nenhum)", "(none)", "(ninguno)", "(nessuno)"),
    "tool.regenerated": msg(
        "Visualizações regeneradas para {count} namespace(s).",
        "Visualizations regenerated for {count} namespace(s).",
        "Visualizaciones regeneradas para {count} espacio(s) de nombres.",
        "Visualizzazioni rigenerate per {count} spazio/i dei nomi.",
    ),
    "prompt.viz_preface": msg(
        "Visualizações pré-geradas (incorpore nas seções do relatório):",
        "Pre-generated visualizations (embed them in the report sections):",
        "Visualizaciones pregeneradas (incorpórelas en las secciones del informe):",
        "Visualizzazioni pregenerate (incorporarle nelle sezioni del report):",
    ),
    "prompt.user_artifacts": msg(
        "Diretório de artefatos: {path}",
        "Artifacts directory: {path}",
        "Directorio de artefactos: {path}",
        "Directory degli artefatti: {path}",
    ),
    "prompt.user_inventory": msg(
        "Inventário inicial:",
        "Initial inventory:",
        "Inventario inicial:",
        "Inventario iniziale:",
    ),
    "prompt.user_closing": msg(
        "Analise os artefatos, use as ferramentas conforme necessário e monte o relatório "
        "completo de assessment em português do Brasil. Inclua todos os gráficos e diagramas "
        "PNG pré-gerados no relatório. Todo título, texto, rótulo e cabeçalho de tabela "
        "visível ao usuário deve estar nesse idioma.",
        "Analyze the artifacts, use the tools as needed, and build the full assessment "
        "report in English (United States). Include all pre-generated PNG charts and "
        "diagrams in the report. Every user-visible title, sentence, label, and table "
        "header must be in that language.",
        "Analice los artefactos, use las herramientas que necesite y redacte el informe "
        "completo de evaluación en español de España. Incluya todos los gráficos y diagramas "
        "PNG pregenerados. Todo título, texto, etiqueta y encabezado de tabla visible para "
        "el usuario debe estar en ese idioma.",
        "Analizza gli artefatti, usa gli strumenti necessari e componi il report completo "
        "di valutazione in italiano. Includi tutti i grafici e i diagrammi PNG pregenerati. "
        "Ogni titolo, testo, etichetta e intestazione di tabella visibile all'utente deve "
        "essere in quella lingua.",
    ),
    "section.executive": msg(
        "## Sumário executivo",
        "## Executive summary",
        "## Resumen ejecutivo",
        "## Riepilogo esecutivo",
    ),
    "exec.namespace": msg(
        "- Namespace `{name}`: **{apps}** apps, **{findings}** achados "
        "(alto={high}, médio={medium}, baixo={low}), "
        "**{logs}** ocorrências em logs, **{hits}** indícios sensíveis em ConfigMaps",
        "- Namespace `{name}`: **{apps}** apps, **{findings}** findings "
        "(high={high}, medium={medium}, low={low}), "
        "**{logs}** log occurrences, **{hits}** sensitive hints in ConfigMaps",
        "- Espacio de nombres `{name}`: **{apps}** aplicaciones, **{findings}** hallazgos "
        "(alto={high}, medio={medium}, bajo={low}), "
        "**{logs}** ocurrencias en logs, **{hits}** indicios sensibles en ConfigMaps",
        "- Spazio dei nomi `{name}`: **{apps}** applicazioni, **{findings}** rilievi "
        "(alto={high}, medio={medium}, basso={low}), "
        "**{logs}** occorrenze nei log, **{hits}** indizi sensibili nei ConfigMap",
    ),
    "exec.resources": msg(
        "  - CPU req/lim: **{cpu_req}m** / **{cpu_lim}m** · "
        "Memória req/lim: **{mem_req}Mi** / **{mem_lim}Mi**",
        "  - CPU req/lim: **{cpu_req}m** / **{cpu_lim}m** · "
        "Memory req/lim: **{mem_req}Mi** / **{mem_lim}Mi**",
        "  - CPU req/lím: **{cpu_req}m** / **{cpu_lim}m** · "
        "Memoria req/lím: **{mem_req}Mi** / **{mem_lim}Mi**",
        "  - CPU rich/lim: **{cpu_req}m** / **{cpu_lim}m** · "
        "Memoria rich/lim: **{mem_req}Mi** / **{mem_lim}Mi**",
    ),
    "exec.workers": msg(
        "  - Workers: **{count}** nodes · "
        "CPU allocatable **{cpu}m** · Mem allocatable **{mem}Mi**",
        "  - Workers: **{count}** nodes · "
        "CPU allocatable **{cpu}m** · Memory allocatable **{mem}Mi**",
        "  - Workers: **{count}** nodos · "
        "CPU allocatable **{cpu}m** · Memoria allocatable **{mem}Mi**",
        "  - Worker: **{count}** nodi · "
        "CPU allocatable **{cpu}m** · Memoria allocatable **{mem}Mi**",
    ),
    "exec.none": msg(
        "- Nenhum namespace encontrado nos artefatos.",
        "- No namespace was found in the artifacts.",
        "- No se encontró ningún espacio de nombres en los artefactos.",
        "- Nessuno spazio dei nomi trovato negli artefatti.",
    ),
    "section.namespace": msg(
        "## Namespace `{name}`",
        "## Namespace `{name}`",
        "## Espacio de nombres `{name}`",
        "## Spazio dei nomi `{name}`",
    ),
    "section.inventory": msg(
        "### Inventário",
        "### Inventory",
        "### Inventario",
        "### Inventario",
    ),
    "inv.apps": msg(
        "- Aplicações: **{count}** (`{names}`)",
        "- Applications: **{count}** (`{names}`)",
        "- Aplicaciones: **{count}** (`{names}`)",
        "- Applicazioni: **{count}** (`{names}`)",
    ),
    "inv.apps_none": msg(
        "- Aplicações: **0**",
        "- Applications: **0**",
        "- Aplicaciones: **0**",
        "- Applicazioni: **0**",
    ),
    "inv.workloads": msg(
        "- Deployments/workloads: **{count}**",
        "- Deployments/workloads: **{count}**",
        "- Deployments/cargas de trabajo: **{count}**",
        "- Deployment/workload: **{count}**",
    ),
    "inv.services": msg("- Services: **{count}**", "- Services: **{count}**", "- Services: **{count}**", "- Service: **{count}**"),
    "inv.routes": msg("- Routes: **{count}**", "- Routes: **{count}**", "- Routes: **{count}**", "- Route: **{count}**"),
    "inv.configmaps": msg(
        "- ConfigMaps: **{count}**",
        "- ConfigMaps: **{count}**",
        "- ConfigMaps: **{count}**",
        "- ConfigMap: **{count}**",
    ),
    "inv.operators": msg(
        "- ClusterServiceVersions (operadores): **{count}**",
        "- ClusterServiceVersions (operators): **{count}**",
        "- ClusterServiceVersions (operadores): **{count}**",
        "- ClusterServiceVersion (operatori): **{count}**",
    ),
    "inv.logs": msg(
        "- Arquivos de log: **{count}**",
        "- Log files: **{count}**",
        "- Archivos de log: **{count}**",
        "- File di log: **{count}**",
    ),
    "findings.heading": msg(
        "### Achados de configuração — `{name}`",
        "### Configuration findings — `{name}`",
        "### Hallazgos de configuración — `{name}`",
        "### Rilievi di configurazione — `{name}`",
    ),
    "findings.none": msg(
        "Nenhum achado pelas heurísticas locais.",
        "No findings from the local heuristics.",
        "Ningún hallazgo según las heurísticas locales.",
        "Nessun rilievo dalle euristiche locali.",
    ),
    "finding.latest_title": msg(
        "{app}: imagem :latest",
        "{app}: :latest image",
        "{app}: imagen :latest",
        "{app}: immagine :latest",
    ),
    "finding.latest_detail": msg(
        "O contêiner `{container}` usa `{image}`.",
        "Container `{container}` uses `{image}`.",
        "El contenedor `{container}` usa `{image}`.",
        "Il container `{container}` usa `{image}`.",
    ),
    "finding.readiness_title": msg(
        "{app}: sem readinessProbe",
        "{app}: missing readinessProbe",
        "{app}: sin readinessProbe",
        "{app}: readinessProbe assente",
    ),
    "finding.readiness_detail": msg(
        "O contêiner `{container}` não tem sonda de readiness.",
        "Container `{container}` is missing a readiness probe.",
        "El contenedor `{container}` no tiene sonda de readiness.",
        "Il container `{container}` non ha una sonda di readiness.",
    ),
    "finding.liveness_title": msg(
        "{app}: sem livenessProbe",
        "{app}: missing livenessProbe",
        "{app}: sin livenessProbe",
        "{app}: livenessProbe assente",
    ),
    "finding.liveness_detail": msg(
        "O contêiner `{container}` não tem sonda de liveness.",
        "Container `{container}` is missing a liveness probe.",
        "El contenedor `{container}` no tiene sonda de liveness.",
        "Il container `{container}` non ha una sonda di liveness.",
    ),
    "finding.limits_title": msg(
        "{app}: sem limits de recursos",
        "{app}: missing resource limits",
        "{app}: sin límites de recursos",
        "{app}: limiti di risorse assenti",
    ),
    "finding.limits_detail": msg(
        "O contêiner `{container}` não tem limits de CPU/memória.",
        "Container `{container}` is missing CPU/memory limits.",
        "El contenedor `{container}` no tiene límites de CPU/memoria.",
        "Il container `{container}` non ha limiti di CPU/memoria.",
    ),
    "finding.requests_title": msg(
        "{app}: sem requests de recursos",
        "{app}: missing resource requests",
        "{app}: sin solicitudes de recursos",
        "{app}: richieste di risorse assenti",
    ),
    "finding.requests_detail": msg(
        "O contêiner `{container}` não tem requests de CPU/memória.",
        "Container `{container}` is missing CPU/memory requests.",
        "El contenedor `{container}` no tiene solicitudes de CPU/memoria.",
        "Il container `{container}` non ha richieste di CPU/memoria.",
    ),
    "finding.replica_title": msg(
        "{app}: réplica única",
        "{app}: single replica",
        "{app}: réplica única",
        "{app}: replica singola",
    ),
    "finding.replica_detail": msg(
        "{kind}/{name} tem replicas=1 — risco de disponibilidade.",
        "{kind}/{name} has replicas=1 — availability risk.",
        "{kind}/{name} tiene replicas=1 — riesgo de disponibilidad.",
        "{kind}/{name} ha replicas=1 — rischio per la disponibilità.",
    ),
    "route.no_host": msg("(sem host)", "(no host)", "(sin host)", "(senza host)"),
    "finding.tls_title": msg(
        "Route/{name}: sem TLS",
        "Route/{name}: missing TLS",
        "Route/{name}: sin TLS",
        "Route/{name}: TLS assente",
    ),
    "finding.tls_detail": msg(
        "O host `{host}` está exposto sem TLS.",
        "Host `{host}` is exposed without TLS.",
        "El host `{host}` está expuesto sin TLS.",
        "L'host `{host}` è esposto senza TLS.",
    ),
    "finding.insecure_title": msg(
        "Route/{name}: HTTP inseguro permitido",
        "Route/{name}: insecure HTTP allowed",
        "Route/{name}: HTTP no seguro permitido",
        "Route/{name}: HTTP non sicuro consentito",
    ),
    "finding.insecure_detail": msg(
        "O host `{host}` tem `insecureEdgeTerminationPolicy=Allow`.",
        "Host `{host}` has `insecureEdgeTerminationPolicy=Allow`.",
        "El host `{host}` tiene `insecureEdgeTerminationPolicy=Allow`.",
        "L'host `{host}` ha `insecureEdgeTerminationPolicy=Allow`.",
    ),
    "suggest.missing": msg(
        "{kind}: ausentes — baseline conservadora {req}/{lim}",
        "{kind}: missing — conservative baseline {req}/{lim}",
        "{kind}: ausentes — línea de base conservadora {req}/{lim}",
        "{kind}: assenti — baseline conservativa {req}/{lim}",
    ),
    "suggest.limit_only": msg(
        "{kind}: só limit definido — request sugerido ≈ 50% do limit",
        "{kind}: only limit is set — suggested request ≈ 50% of the limit",
        "{kind}: solo el límite está definido — solicitud sugerida ≈ 50% del límite",
        "{kind}: solo il limite è definito — richiesta suggerita ≈ 50% del limite",
    ),
    "suggest.request_only": msg(
        "{kind}: só request definido — limit sugerido ≈ 2× request",
        "{kind}: only request is set — suggested limit ≈ 2× request",
        "{kind}: solo la solicitud está definida — límite sugerido ≈ 2× solicitud",
        "{kind}: solo la richiesta è definita — limite suggerito ≈ 2× richiesta",
    ),
    "suggest.limit_lt_request": msg(
        "{kind}: limit < request — corrigido para limit ≈ 2× request",
        "{kind}: limit < request — corrected so limit ≈ 2× request",
        "{kind}: límite < solicitud — corregido para que el límite ≈ 2× solicitud",
        "{kind}: limite < richiesta — corretto in modo che il limite ≈ 2× richiesta",
    ),
    "suggest.burst": msg(
        "{kind}: burst alto (limit/request={ratio}) — sugerido apertar limit para ≈ {factor}× request",
        "{kind}: high burst (limit/request={ratio}) — suggested tightening the limit to ≈ {factor}× request",
        "{kind}: ráfaga alta (limit/request={ratio}) — se sugiere ajustar el límite a ≈ {factor}× solicitud",
        "{kind}: burst elevato (limit/request={ratio}) — si suggerisce di stringere il limite a ≈ {factor}× richiesta",
    ),
    "suggest.guaranteed": msg(
        "{kind}: Guaranteed (req=lim) — sugerido Burstable com request ≈ 70% do limit",
        "{kind}: Guaranteed (req=lim) — suggested Burstable with request ≈ 70% of the limit",
        "{kind}: Guaranteed (req=lim) — se sugiere Burstable con solicitud ≈ 70% del límite",
        "{kind}: Guaranteed (req=lim) — suggerito Burstable con richiesta ≈ 70% del limite",
    ),
    "suggest.keep": msg(
        "manter faixa atual (arredondada)",
        "keep the current range (rounded)",
        "mantener el rango actual (redondeado)",
        "mantenere l'intervallo attuale (arrotondato)",
    ),
    "hpa.reason_min": msg(
        "minReplicas={min_replicas} (HA: evitar réplica única)",
        "minReplicas={min_replicas} (HA: avoid a single replica)",
        "minReplicas={min_replicas} (HA: evitar una réplica única)",
        "minReplicas={min_replicas} (HA: evitare una replica singola)",
    ),
    "hpa.reason_max": msg(
        "maxReplicas={max_replicas} (escala moderada, teto conservador)",
        "maxReplicas={max_replicas} (moderate scale, conservative cap)",
        "maxReplicas={max_replicas} (escala moderada, techo conservador)",
        "maxReplicas={max_replicas} (scala moderata, tetto conservativo)",
    ),
    "hpa.reason_cpu": msg(
        "targetCPUUtilization=70% (margem antes do throttling)",
        "targetCPUUtilization=70% (headroom before throttling)",
        "targetCPUUtilization=70% (margen antes del throttling)",
        "targetCPUUtilization=70% (margine prima del throttling)",
    ),
    "hpa.reason_exists": msg(
        "Já existe HPA `{name}` (min={min_replicas}, max={max_replicas}) — revisar valores.",
        "HPA `{name}` already exists (min={min_replicas}, max={max_replicas}) — review the values.",
        "Ya existe el HPA `{name}` (min={min_replicas}, max={max_replicas}) — revisar los valores.",
        "Esiste già l'HPA `{name}` (min={min_replicas}, max={max_replicas}) — rivedere i valori.",
    ),
    "hpa.reason_none": msg(
        "Nenhum HPA encontrado para este workload.",
        "No HPA was found for this workload.",
        "No se encontró ningún HPA para esta carga de trabajo.",
        "Nessun HPA trovato per questo workload.",
    ),
    "hpa.exists": msg(
        "existe `{name}`",
        "exists `{name}`",
        "existe `{name}`",
        "esiste `{name}`",
    ),
    "hpa.create": msg("criar", "create", "crear", "creare"),
    "action.title": msg(
        "# Plano de ação — `{name}`",
        "# Action plan — `{name}`",
        "# Plan de acción — `{name}`",
        "# Piano d'azione — `{name}`",
    ),
    "action.intro": msg(
        "Derivado dos relatórios de assessment (achados, recursos, observabilidade e ConfigMaps). Dividido por responsabilidade.",
        "Derived from the assessment reports (findings, resources, observability, and ConfigMaps). Split by responsibility.",
        "Derivado de los informes de evaluación (hallazgos, recursos, observabilidad y ConfigMaps). Dividido por responsabilidad.",
        "Derivato dai report di valutazione (rilievi, risorse, osservabilità e ConfigMap). Diviso per responsabilità.",
    ),
    "action.infra": msg(
        "## 1. Ações de infraestrutura do cluster / plataforma",
        "## 1. Cluster / platform infrastructure actions",
        "## 1. Acciones de infraestructura del clúster / plataforma",
        "## 1. Azioni sull'infrastruttura del cluster / piattaforma",
    ),
    "action.infra_none": msg(
        "- Nenhuma ação prioritária de infraestrutura foi identificada automaticamente.",
        "- No priority infrastructure action was identified automatically.",
        "- No se identificó automáticamente ninguna acción prioritaria de infraestructura.",
        "- Nessuna azione prioritaria di infrastruttura identificata automaticamente.",
    ),
    "action.apps": msg(
        "## 2. Ações de melhoria da aplicação",
        "## 2. Application improvement actions",
        "## 2. Acciones de mejora de la aplicación",
        "## 2. Azioni di miglioramento dell'applicazione",
    ),
    "action.apps_none": msg(
        "- Nenhuma ação prioritária de aplicação foi identificada automaticamente.",
        "- No priority application action was identified automatically.",
        "- No se identificó automáticamente ninguna acción prioritaria de aplicación.",
        "- Nessuna azione prioritaria sull'applicazione identificata automaticamente.",
    ),
    "action.priority": msg(
        "## 3. Priorização sugerida",
        "## 3. Suggested prioritization",
        "## 3. Priorización sugerida",
        "## 3. Priorità suggerita",
    ),
    "action.p1": msg(
        "1. Itens de severidade **alta** (TLS, limits, sondas, segredos).",
        "1. **High** severity items (TLS, limits, probes, secrets).",
        "1. Elementos de severidad **alta** (TLS, límites, sondas, secretos).",
        "1. Elementi di gravità **alta** (TLS, limiti, sonde, segreti).",
    ),
    "action.p2": msg(
        "2. Observabilidade (monitores, alertas, logging estruturado).",
        "2. Observability (monitors, alerts, structured logging).",
        "2. Observabilidad (monitores, alertas, registro estructurado).",
        "2. Osservabilità (monitor, avvisi, logging strutturato).",
    ),
    "action.p3": msg(
        "3. Itens de severidade **média/baixa** (liveness, réplicas, tags de imagem).",
        "3. **Medium/low** severity items (liveness, replicas, image tags).",
        "3. Elementos de severidad **media/baja** (liveness, réplicas, etiquetas de imagen).",
        "3. Elementi di gravità **media/bassa** (liveness, repliche, tag immagine).",
    ),
    "action.accept": msg(
        "## 4. Critérios de aceite",
        "## 4. Acceptance criteria",
        "## 4. Criterios de aceptación",
        "## 4. Criteri di accettazione",
    ),
    "action.a1": msg(
        "- Routes críticas com TLS e sem HTTP inseguro quando aplicável.",
        "- Critical Routes with TLS and without insecure HTTP when applicable.",
        "- Routes críticas con TLS y sin HTTP no seguro cuando corresponda.",
        "- Route critiche con TLS e senza HTTP non sicuro quando applicabile.",
    ),
    "action.a2": msg(
        "- 100% dos workloads com requests e limits definidos.",
        "- 100% of workloads with defined requests and limits.",
        "- 100% de las cargas de trabajo con solicitudes y límites definidos.",
        "- 100% dei workload con richieste e limiti definiti.",
    ),
    "action.a3": msg(
        "- Aplicações críticas com sondas de readiness/liveness e ≥2 réplicas ou HPA.",
        "- Critical applications with readiness/liveness probes and ≥2 replicas or an HPA.",
        "- Aplicaciones críticas con sondas de readiness/liveness y ≥2 réplicas o un HPA.",
        "- Applicazioni critiche con sonde di readiness/liveness e ≥2 repliche oppure un HPA.",
    ),
    "action.a4": msg(
        "- Segredos removidos dos ConfigMaps; ConfigMaps usados só para configuração não sensível.",
        "- Secrets removed from ConfigMaps; ConfigMaps used only for non-sensitive configuration.",
        "- Secretos retirados de los ConfigMaps; ConfigMaps usados solo para configuración no sensible.",
        "- Segreti rimossi dai ConfigMap; ConfigMap usati solo per configurazione non sensibile.",
    ),
    "action.a5": msg(
        "- Métricas e alertas básicos cobrindo taxa de erro e reinícios.",
        "- Basic metrics and alerts covering error rate and restarts.",
        "- Métricas y alertas básicas que cubran la tasa de error y los reinicios.",
        "- Metriche e avvisi di base che coprano il tasso di errore e i riavvii.",
    ),
    "action.review_quota": msg(
        "- Revisar a quota/LimitRange do namespace e padronizar requests/limits em todos os workloads.",
        "- Review the namespace quota/LimitRange and standardize requests/limits across all workloads.",
        "- Revisar la cuota/LimitRange del espacio de nombres y estandarizar solicitudes/límites en todas las cargas de trabajo.",
        "- Rivedere quota/LimitRange dello spazio dei nomi e standardizzare richieste/limiti in tutti i workload.",
    ),
    "action.complete_resources": msg(
        "- Completar requests/limits nas aplicações: {apps}.",
        "- Complete requests/limits in the applications: {apps}.",
        "- Completar solicitudes/límites en las aplicaciones: {apps}.",
        "- Completare richieste/limiti nelle applicazioni: {apps}.",
    ),
    "cm.title": msg(
        "# Análise de ConfigMaps — informações sensíveis — `{name}`",
        "# ConfigMap analysis — sensitive information — `{name}`",
        "# Análisis de ConfigMaps — información sensible — `{name}`",
        "# Analisi dei ConfigMap — informazioni sensibili — `{name}`",
    ),
    "cm.scanned": msg(
        "- ConfigMaps analisados: **{count}**",
        "- ConfigMaps analyzed: **{count}**",
        "- ConfigMaps analizados: **{count}**",
        "- ConfigMap analizzati: **{count}**",
    ),
    "cm.with_data": msg(
        "- Com dados (`data`/`binaryData`): **{count}**",
        "- With data (`data`/`binaryData`): **{count}**",
        "- Con datos (`data`/`binaryData`): **{count}**",
        "- Con dati (`data`/`binaryData`): **{count}**",
    ),
    "cm.hits": msg(
        "- Achados sensíveis: **{count}**",
        "- Sensitive findings: **{count}**",
        "- Hallazgos sensibles: **{count}**",
        "- Rilievi sensibili: **{count}**",
    ),
    "cm.findings": msg("## Achados", "## Findings", "## Hallazgos", "## Rilievi"),
    "cm.none": msg(
        "Não há evidência clara de segredos/certificados/tokens nos ConfigMaps analisados (ou os dados já estão sanitizados).",
        "No clear evidence of secrets/certificates/tokens in the analyzed ConfigMaps (or the data is already sanitized).",
        "No hay evidencia clara de secretos/certificados/tokens en los ConfigMaps analizados (o los datos ya están saneados).",
        "Nessuna evidenza chiara di segreti/certificati/token nei ConfigMap analizzati (oppure i dati sono già stati sanificati).",
    ),
    "cm.table": msg(
        "| ConfigMap | App | Chave | Categoria | Evidência (truncada) |\n|-----------|-----|-------|-----------|----------------------|",
        "| ConfigMap | App | Key | Category | Evidence (truncated) |\n|-----------|-----|-----|----------|----------------------|",
        "| ConfigMap | App | Clave | Categoría | Evidencia (truncada) |\n|-----------|-----|-------|-----------|----------------------|",
        "| ConfigMap | App | Chiave | Categoria | Evidenza (troncata) |\n|-----------|-----|--------|-----------|----------------------|",
    ),
    "cm.recommendations": msg(
        "## Recomendações",
        "## Recommendations",
        "## Recomendaciones",
        "## Raccomandazioni",
    ),
    "cm.suspicious_key": msg(
        "Nome da chave sugere segredo: `{key}`",
        "Key name suggests a secret: `{key}`",
        "El nombre de la clave sugiere un secreto: `{key}`",
        "Il nome della chiave suggerisce un segreto: `{key}`",
    ),
    "cm.cat.chave_suspeita": msg(
        "chave suspeita",
        "suspicious key",
        "clave sospechosa",
        "chiave sospetta",
    ),
    "cm.cat.certificado_pem": msg(
        "certificado PEM",
        "PEM certificate",
        "certificado PEM",
        "certificato PEM",
    ),
    "cm.cat.chave_privada_pem": msg(
        "chave privada PEM",
        "PEM private key",
        "clave privada PEM",
        "chiave privata PEM",
    ),
    "cm.cat.token_jwt": msg("token JWT", "JWT token", "token JWT", "token JWT"),
    "cm.cat.bearer": msg("bearer", "bearer", "bearer", "bearer"),
    "cm.cat.senha_explicita": msg(
        "senha explícita",
        "explicit password",
        "contraseña explícita",
        "password esplicita",
    ),
    "cm.cat.connection_string_credencial": msg(
        "credencial em connection string",
        "connection string credential",
        "credencial en cadena de conexión",
        "credenziale nella stringa di connessione",
    ),
    "cm.rec.move": msg(
        "Mover segredos (senhas, tokens, certificados privados) do ConfigMap para um Secret ou cofre externo (Vault/External Secrets), com rotação.",
        "Move secrets (passwords, tokens, private certificates) from ConfigMap to a Secret or external vault (Vault/External Secrets), with rotation.",
        "Mover los secretos (contraseñas, tokens, certificados privados) del ConfigMap a un Secret o a una bóveda externa (Vault/External Secrets), con rotación.",
        "Spostare i segreti (password, token, certificati privati) dal ConfigMap a un Secret o a un vault esterno (Vault/External Secrets), con rotazione.",
    ),
    "cm.rec.mask": msg(
        "Garantir que os pipelines de coleta continuem mascarando valores sensíveis antes de compartilhar artefatos.",
        "Ensure collection pipelines continue masking sensitive values before sharing artifacts.",
        "Asegurar que las canalizaciones de recolección sigan enmascarando los valores sensibles antes de compartir artefactos.",
        "Assicurarsi che le pipeline di raccolta continuino a mascherare i valori sensibili prima di condividere gli artefatti.",
    ),
    "cm.rec.rbac": msg(
        "Revisar o RBAC de leitura de ConfigMaps/Secrets no namespace.",
        "Review RBAC for reading ConfigMaps/Secrets in the namespace.",
        "Revisar el RBAC de lectura de ConfigMaps/Secrets en el espacio de nombres.",
        "Rivedere l'RBAC di lettura di ConfigMap/Secret nello spazio dei nomi.",
    ),
    "cm.rec.none": msg(
        "Não há evidência forte de segredos em ConfigMaps nos artefatos (os valores podem já estar sanitizados). Validar o processo de build/deploy para evitar regressão.",
        "No strong evidence of secrets in ConfigMaps in the artifacts (values may already be sanitized). Validate the build/deploy process to prevent regression.",
        "No hay evidencia sólida de secretos en ConfigMaps en los artefactos (los valores pueden estar ya saneados). Validar el proceso de build/deploy para evitar regresiones.",
        "Nessuna evidenza forte di segreti nei ConfigMap degli artefatti (i valori potrebbero essere già sanificati). Validare il processo di build/deploy per evitare regressioni.",
    ),
    "cm.rec.jdbc": msg(
        "Preferir referenciar credenciais de banco via Secret mesmo quando a URL JDBC permanece no ConfigMap.",
        "Prefer referencing database credentials via Secret even when the JDBC URL remains in the ConfigMap.",
        "Preferir referenciar las credenciales de base de datos mediante Secret aunque la URL JDBC permanezca en el ConfigMap.",
        "Preferire il riferimento alle credenziali del database tramite Secret anche se l'URL JDBC resta nel ConfigMap.",
    ),
    "obs.title": msg(
        "# Observabilidade — logs, métricas e monitoramento — `{name}`",
        "# Observability — logs, metrics, and monitoring — `{name}`",
        "# Observabilidad — logs, métricas y monitorización — `{name}`",
        "# Osservabilità — log, metriche e monitoraggio — `{name}`",
    ),
    "obs.inventory": msg(
        "## Inventário de monitoramento",
        "## Monitoring inventory",
        "## Inventario de monitorización",
        "## Inventario di monitoraggio",
    ),
    "obs.chart_app": msg(
        "## Gráfico — erros por aplicação/sistema",
        "## Chart — errors by application/system",
        "## Gráfico — errores por aplicación/sistema",
        "## Grafico — errori per applicazione/sistema",
    ),
    "obs.chart_cat": msg(
        "## Gráfico — erros por categoria",
        "## Chart — errors by category",
        "## Gráfico — errores por categoría",
        "## Grafico — errori per categoria",
    ),
    "obs.table_title": msg(
        "## Tabela quantitativa por aplicação",
        "## Quantitative table by application",
        "## Tabla cuantitativa por aplicación",
        "## Tabella quantitativa per applicazione",
    ),
    "obs.table": msg(
        "| Aplicação | Ocorrências | % do total |\n|-----------|-------------|------------|",
        "| Application | Occurrences | % of total |\n|-------------|-------------|------------|",
        "| Aplicación | Ocurrencias | % del total |\n|------------|-------------|-------------|",
        "| Applicazione | Occorrenze | % del totale |\n|--------------|-------------|--------------|",
    ),
    "obs.samples": msg(
        "## Amostra de evidências em logs",
        "## Sample log evidence",
        "## Muestra de evidencias en logs",
        "## Campione di evidenze nei log",
    ),
    "obs.no_patterns": msg(
        "Nenhum padrão de erro foi encontrado nos logs coletados.",
        "No error patterns were found in the collected logs.",
        "No se encontraron patrones de error en los logs recopilados.",
        "Nessun pattern di errore trovato nei log raccolti.",
    ),
    "obs.opportunities": msg(
        "## Oportunidades de melhoria (rastreabilidade e correção)",
        "## Improvement opportunities (traceability and remediation)",
        "## Oportunidades de mejora (trazabilidad y corrección)",
        "## Opportunità di miglioramento (tracciabilità e correzione)",
    ),
    "obs.no_monitors": msg(
        "Não há ServiceMonitor/PodMonitor no namespace — oportunidade de expor métricas pelo Prometheus Operator para SLIs/SLOs.",
        "There is no ServiceMonitor/PodMonitor in the namespace — an opportunity to expose metrics through the Prometheus Operator for SLIs/SLOs.",
        "No hay ServiceMonitor/PodMonitor en el espacio de nombres — oportunidad de exponer métricas mediante el Prometheus Operator para SLIs/SLOs.",
        "Non ci sono ServiceMonitor/PodMonitor nello spazio dei nomi — opportunità di esporre metriche tramite il Prometheus Operator per SLI/SLO.",
    ),
    "obs.apps_without": msg(
        "Aplicações sem monitor dedicado: {apps}{suffix}.",
        "Applications without a dedicated monitor: {apps}{suffix}.",
        "Aplicaciones sin monitor dedicado: {apps}{suffix}.",
        "Applicazioni senza monitor dedicato: {apps}{suffix}.",
    ),
    "obs.no_rules": msg(
        "Não há PrometheusRule — criar alertas para taxa de erro, latência e reinícios de pods.",
        "No PrometheusRule is present — create alerts for error rate, latency, and pod restarts.",
        "No hay PrometheusRule — crear alertas de tasa de error, latencia y reinicios de pods.",
        "Non è presente alcuna PrometheusRule — creare avvisi per tasso di errore, latenza e riavvii dei pod.",
    ),
    "obs.top_errors": msg(
        "Concentrar a correção de erros nas aplicações com mais ocorrências: {apps}.",
        "Concentrate error remediation on applications with the highest occurrence counts: {apps}.",
        "Concentrar la corrección de errores en las aplicaciones con más ocurrencias: {apps}.",
        "Concentrare la correzione degli errori sulle applicazioni con più occorrenze: {apps}.",
    ),
    "obs.structured": msg(
        "Padronizar logging estruturado (JSON) com `trace_id`/`correlation_id` para melhorar a rastreabilidade operacional entre serviços.",
        "Standardize structured logging (JSON) with `trace_id`/`correlation_id` to improve operational traceability across services.",
        "Estandarizar el registro estructurado (JSON) con `trace_id`/`correlation_id` para mejorar la trazabilidad operativa entre servicios.",
        "Standardizzare il logging strutturato (JSON) con `trace_id`/`correlation_id` per migliorare la tracciabilità operativa tra i servizi.",
    ),
    "obs.previous": msg(
        "Há logs `-previous` (pods reiniciados) — investigar causas de reinício (OOM, falhas de sonda, crashes) e correlacionar com eventos.",
        "There are `-previous` logs (restarted pods) — investigate restart causes (OOM, probe failures, crashes) and correlate with events.",
        "Hay logs `-previous` (pods reiniciados) — investigar las causas de reinicio (OOM, fallos de sonda, crashes) y correlacionarlas con eventos.",
        "Sono presenti log `-previous` (pod riavviati) — indagare le cause dei riavvii (OOM, sonde fallite, crash) e correlarle agli eventi.",
    ),
    "obs.few": msg(
        "Poucos sinais de lacunas de observabilidade nos artefatos; validar dashboards e runbooks no ambiente de operação.",
        "Few signs of observability gaps in the artifacts; validate dashboards and runbooks in the operating environment.",
        "Pocos indicios de carencias de observabilidad en los artefactos; validar paneles y runbooks en el entorno de operación.",
        "Pochi segnali di lacune di osservabilità negli artefatti; validare dashboard e runbook nell'ambiente operativo.",
    ),
    "topo.title": msg(
        "# Arquitetura reversa — `{name}`",
        "# Reverse architecture — `{name}`",
        "# Arquitectura inversa — `{name}`",
        "# Architettura inversa — `{name}`",
    ),
    "topo.intro": msg(
        "Visão simples reconstruída a partir de **Deployments**, **Services**, **Routes** e **ConfigMaps**.",
        "Simple view reconstructed from **Deployments**, **Services**, **Routes**, and **ConfigMaps**.",
        "Vista sencilla reconstruida a partir de **Deployments**, **Services**, **Routes** y **ConfigMaps**.",
        "Vista semplice ricostruita da **Deployment**, **Service**, **Route** e **ConfigMap**.",
    ),
    "topo.brief": msg("## Em resumo", "## In brief", "## En resumen", "## In sintesi"),
    "topo.fallback": msg(
        "Não foi possível montar um resumo.",
        "A summary could not be assembled.",
        "No se pudo componer un resumen.",
        "Non è stato possibile comporre un riepilogo.",
    ),
    "topo.diagram": msg("## Diagrama", "## Diagram", "## Diagrama", "## Diagramma"),
    "topo.routes": msg(
        "## Entrada pública (Routes)",
        "## Public entry (Routes)",
        "## Entrada pública (Routes)",
        "## Ingresso pubblico (Route)",
    ),
    "topo.routes_header": msg(
        "| Host | Aplicação | TLS |\n|------|-----------|-----|",
        "| Host | Application | TLS |\n|------|-------------|-----|",
        "| Host | Aplicación | TLS |\n|------|------------|-----|",
        "| Host | Applicazione | TLS |\n|------|--------------|-----|",
    ),
    "topo.apps": msg(
        "## Aplicações no namespace",
        "## Applications in the namespace",
        "## Aplicaciones en el espacio de nombres",
        "## Applicazioni nello spazio dei nomi",
    ),
    "topo.no_apps": msg(
        "- Nenhuma aplicação identificada.",
        "- No application was identified.",
        "- No se identificó ninguna aplicación.",
        "- Nessuna applicazione identificata.",
    ),
    "topo.app_line": msg(
        "- **{app}** (Service: `{service}`)",
        "- **{app}** (Service: `{service}`)",
        "- **{app}** (Service: `{service}`)",
        "- **{app}** (Service: `{service}`)",
    ),
    "topo.entry_title": msg(
        "**Entrada (usuário → aplicação)**",
        "**Entry (user → application)**",
        "**Entrada (usuario → aplicación)**",
        "**Ingresso (utente → applicazione)**",
    ),
    "topo.entry_line": msg(
        "- O usuário acessa `{host}` ({tls}) e chega à aplicação **{app}**.",
        "- The user accesses `{host}` ({tls}) and reaches application **{app}**.",
        "- El usuario accede a `{host}` ({tls}) y llega a la aplicación **{app}**.",
        "- L'utente accede a `{host}` ({tls}) e raggiunge l'applicazione **{app}**.",
    ),
    "topo.with_tls": msg("com TLS", "with TLS", "con TLS", "con TLS"),
    "topo.without_tls": msg("sem TLS", "without TLS", "sin TLS", "senza TLS"),
    "topo.no_route": msg(
        "**Entrada:** nenhuma Route encontrada (as aplicações são apenas internas ao cluster).",
        "**Entry:** no Route found (applications are internal to the cluster only).",
        "**Entrada:** no se encontró ninguna Route (las aplicaciones son solo internas al clúster).",
        "**Ingresso:** nessuna Route trovata (le applicazioni sono solo interne al cluster).",
    ),
    "topo.calls_title": msg(
        "**Chamadas entre aplicações** (descobertas nos ConfigMaps)",
        "**Calls between applications** (discovered in ConfigMaps)",
        "**Llamadas entre aplicaciones** (descubiertas en ConfigMaps)",
        "**Chiamate tra applicazioni** (scoperte nei ConfigMap)",
    ),
    "topo.call_line": msg(
        "- **{src}** chama **{dst}**.",
        "- **{src}** calls **{dst}**.",
        "- **{src}** llama a **{dst}**.",
        "- **{src}** chiama **{dst}**.",
    ),
    "topo.no_calls": msg(
        "**Chamadas entre aplicações:** nenhuma URL interna explícita nos ConfigMaps.",
        "**Calls between applications:** no explicit internal URL in ConfigMaps.",
        "**Llamadas entre aplicaciones:** ninguna URL interna explícita en los ConfigMaps.",
        "**Chiamate tra applicazioni:** nessun URL interno esplicito nei ConfigMap.",
    ),
    "topo.config_title": msg(
        "**Configuração injetada nos pods**",
        "**Configuration injected into pods**",
        "**Configuración inyectada en los pods**",
        "**Configurazione iniettata nei pod**",
    ),
    "topo.config_line": msg(
        "- **{app}** usa {refs}.",
        "- **{app}** uses {refs}.",
        "- **{app}** usa {refs}.",
        "- **{app}** usa {refs}.",
    ),
    "ops.title": msg(
        "### 2.6 Operadores presentes no namespace (ClusterServiceVersions) — `{name}`",
        "### 2.6 Operators present in the namespace (ClusterServiceVersions) — `{name}`",
        "### 2.6 Operadores presentes en el espacio de nombres (ClusterServiceVersions) — `{name}`",
        "### 2.6 Operatori presenti nello spazio dei nomi (ClusterServiceVersions) — `{name}`",
    ),
    "ops.counts": msg(
        "CSVs analisados: **{scanned}** · listados: **{listed}**",
        "CSVs analyzed: **{scanned}** · listed: **{listed}**",
        "CSV analizados: **{scanned}** · listados: **{listed}**",
        "CSV analizzati: **{scanned}** · elencati: **{listed}**",
    ),
    "ops.header": msg(
        "| Operador (displayName) | CSV | Versão | Phase | Upgrade disponível | Provider | Evidência |",
        "| Operator (displayName) | CSV | Version | Phase | Upgrade available | Provider | Evidence |",
        "| Operador (displayName) | CSV | Versión | Phase | Actualización disponible | Provider | Evidencia |",
        "| Operatore (displayName) | CSV | Versione | Phase | Aggiornamento disponibile | Provider | Evidenza |",
    ),
    "ops.separator": msg(
        "|------------------------|-----|---------|-------|-------------------|----------|----------|",
        "|------------------------|-----|---------|-------|-------------------|----------|----------|",
        "|------------------------|-----|---------|-------|---------------------------|----------|-----------|",
        "|-------------------------|-----|----------|-------|---------------------------|----------|-----------|",
    ),
    "ops.empty": msg(
        "Nenhum CSV em `resources/clusterserviceversions*`",
        "No CSVs in `resources/clusterserviceversions*`",
        "Ningún CSV en `resources/clusterserviceversions*`",
        "Nessun CSV in `resources/clusterserviceversions*`",
    ),
    "ops.upgrade_note": msg(
        "Coluna **Upgrade disponível**: valor da propriedade `status.state` (no CSV ou na Subscription OLM correspondente). Exemplos: `{at_latest}`, `{upgrade}`, `UpgradePending`, `UpgradeFailed`. Se `status.state` não estiver nos artefatos, o valor é inferido pelo `currentCSV` do PackageManifest (canal default); `{unknown}` significa que não houve evidência.",
        "Column **Upgrade available**: value of the `status.state` property (in the CSV or the corresponding OLM Subscription). Examples: `{at_latest}`, `{upgrade}`, `UpgradePending`, `UpgradeFailed`. If `status.state` is missing from the artifacts, the value is inferred from `currentCSV` in the PackageManifest (default channel); `{unknown}` means no evidence was found.",
        "Columna **Actualización disponible**: valor de la propiedad `status.state` (en el CSV o en la Subscription OLM correspondiente). Ejemplos: `{at_latest}`, `{upgrade}`, `UpgradePending`, `UpgradeFailed`. Si `status.state` no está en los artefactos, el valor se infiere del `currentCSV` del PackageManifest (canal predeterminado); `{unknown}` significa que no hubo evidencia.",
        "Colonna **Aggiornamento disponibile**: valore della proprietà `status.state` (nel CSV o nella Subscription OLM corrispondente). Esempi: `{at_latest}`, `{upgrade}`, `UpgradePending`, `UpgradeFailed`. Se `status.state` manca negli artefatti, il valore si deduce da `currentCSV` del PackageManifest (canale predefinito); `{unknown}` indica che non c'è evidenza.",
    ),
    "ops.footer": msg(
        "Os CSVs indicam operadores disponíveis via OLM no escopo coletado; por si só, não implicam que existam ServiceMonitor/PodMonitor/PrometheusRule configurados para as aplicações do namespace.",
        "The CSVs indicate operators available via OLM in the collected scope; they do not, by themselves, imply that ServiceMonitor/PodMonitor/PrometheusRule resources are configured for the namespace applications.",
        "Los CSV indican operadores disponibles vía OLM en el ámbito recopilado; por sí solos no implican que existan ServiceMonitor/PodMonitor/PrometheusRule configurados para las aplicaciones del espacio de nombres.",
        "I CSV indicano operatori disponibili via OLM nell'ambito raccolto; da soli non implicano che esistano ServiceMonitor/PodMonitor/PrometheusRule configurati per le applicazioni dello spazio dei nomi.",
    ),
    "res.title": msg(
        "# Recursos de CPU e memória — `{name}`",
        "# CPU and memory resources — `{name}`",
        "# Recursos de CPU y memoria — `{name}`",
        "# Risorse di CPU e memoria — `{name}`",
    ),
    "res.intro": msg(
        "Valores atuais extraídos de `resources.requests` (mínimo reservado) e `resources.limits` (teto). As sugestões abaixo são **conservadoras**: priorizam estabilidade (Burstable com limit ≈ 2× request), HA (≥2 réplicas) e escala moderada via HPA — sem assumir métricas reais de uso (VPA/Prometheus).",
        "Current values taken from `resources.requests` (reserved minimum) and `resources.limits` (ceiling). The suggestions below are **conservative**: they favor stability (Burstable with limit ≈ 2× request), HA (≥2 replicas), and moderate scale via HPA — without assuming real usage metrics (VPA/Prometheus).",
        "Valores actuales extraídos de `resources.requests` (mínimo reservado) y `resources.limits` (techo). Las sugerencias siguientes son **conservadoras**: priorizan la estabilidad (Burstable con límite ≈ 2× solicitud), la HA (≥2 réplicas) y una escala moderada vía HPA — sin asumir métricas reales de uso (VPA/Prometheus).",
        "Valori attuali estratti da `resources.requests` (minimo riservato) e `resources.limits` (tetto). I suggerimenti seguenti sono **conservativi**: privilegiano stabilità (Burstable con limite ≈ 2× richiesta), HA (≥2 repliche) e scala moderata via HPA — senza assumere metriche reali di utilizzo (VPA/Prometheus).",
    ),
    "res.current": msg(
        "## Sumário do namespace (atual)",
        "## Namespace summary (current)",
        "## Resumen del espacio de nombres (actual)",
        "## Riepilogo dello spazio dei nomi (attuale)",
    ),
    "res.cpu_req": msg(
        "- **CPU requests:** {value} ({raw}m)",
        "- **CPU requests:** {value} ({raw}m)",
        "- **Solicitudes de CPU:** {value} ({raw}m)",
        "- **Richieste di CPU:** {value} ({raw}m)",
    ),
    "res.cpu_lim": msg(
        "- **CPU limits:** {value} ({raw}m)",
        "- **CPU limits:** {value} ({raw}m)",
        "- **Límites de CPU:** {value} ({raw}m)",
        "- **Limiti di CPU:** {value} ({raw}m)",
    ),
    "res.mem_req": msg(
        "- **Memória requests:** {value}",
        "- **Memory requests:** {value}",
        "- **Solicitudes de memoria:** {value}",
        "- **Richieste di memoria:** {value}",
    ),
    "res.mem_lim": msg(
        "- **Memória limits:** {value}",
        "- **Memory limits:** {value}",
        "- **Límites de memoria:** {value}",
        "- **Limiti di memoria:** {value}",
    ),
    "res.suggested": msg(
        "## Sumário sugerido (conservador, namespace)",
        "## Suggested summary (conservative, namespace)",
        "## Resumen sugerido (conservador, espacio de nombres)",
        "## Riepilogo suggerito (conservativo, spazio dei nomi)",
    ),
    "res.cpu_req_sug": msg(
        "- **CPU requests sugeridos:** {value} ({raw}m)",
        "- **Suggested CPU requests:** {value} ({raw}m)",
        "- **Solicitudes de CPU sugeridas:** {value} ({raw}m)",
        "- **Richieste di CPU suggerite:** {value} ({raw}m)",
    ),
    "res.cpu_lim_sug": msg(
        "- **CPU limits sugeridos:** {value} ({raw}m)",
        "- **Suggested CPU limits:** {value} ({raw}m)",
        "- **Límites de CPU sugeridos:** {value} ({raw}m)",
        "- **Limiti di CPU suggeriti:** {value} ({raw}m)",
    ),
    "res.mem_req_sug": msg(
        "- **Memória requests sugerida:** {value}",
        "- **Suggested memory requests:** {value}",
        "- **Solicitud de memoria sugerida:** {value}",
        "- **Richiesta di memoria suggerita:** {value}",
    ),
    "res.mem_lim_sug": msg(
        "- **Memória limits sugerida:** {value}",
        "- **Suggested memory limits:** {value}",
        "- **Límite de memoria sugerido:** {value}",
        "- **Limite di memoria suggerito:** {value}",
    ),
    "res.estimate": msg(
        "_Estimativa com réplicas mínimas sugeridas (≥2 quando hoje há 1). Validar com métricas reais antes de aplicar em produção._",
        "_Estimate using the suggested minimum replicas (≥2 when there is currently 1). Validate with real metrics before applying in production._",
        "_Estimación con las réplicas mínimas sugeridas (≥2 cuando hoy hay 1). Validar con métricas reales antes de aplicar en producción._",
        "_Stima con le repliche minime suggerite (≥2 quando oggi ce n'è 1). Validare con metriche reali prima di applicare in produzione._",
    ),
    "wn.title": msg(
        "## Capacidade dos worker nodes",
        "## Worker node capacity",
        "## Capacidad de los nodos worker",
        "## Capacità dei nodi worker",
    ),
    "wn.missing": msg(
        "_Nenhum YAML em `worknodes/` encontrado. Execute `./scripts/oc_collect_worknodes.sh -o <pasta-saida>` antes do assessment._",
        "_No YAML was found in `worknodes/`. Run `./scripts/oc_collect_worknodes.sh -o <output-dir>` before the assessment._",
        "_No se encontró ningún YAML en `worknodes/`. Ejecute `./scripts/oc_collect_worknodes.sh -o <directorio-salida>` antes de la evaluación._",
        "_Nessun YAML trovato in `worknodes/`. Eseguire `./scripts/oc_collect_worknodes.sh -o <directory-output>` prima della valutazione._",
    ),
    "wn.source": msg(
        "Fonte: `{path}` — valores de **allocatable** (o que o scheduler pode usar).",
        "Source: `{path}` — **allocatable** values (what the scheduler can use).",
        "Fuente: `{path}` — valores de **allocatable** (lo que el scheduler puede usar).",
        "Fonte: `{path}` — valori di **allocatable** (ciò che lo scheduler può usare).",
    ),
    "wn.header": msg(
        "| Node | CPU allocatable | Memória allocatable | CPU capacity | Memória capacity |",
        "| Node | CPU allocatable | Memory allocatable | CPU capacity | Memory capacity |",
        "| Node | CPU allocatable | Memoria allocatable | CPU capacity | Memoria capacity |",
        "| Node | CPU allocatable | Memoria allocatable | CPU capacity | Memoria capacity |",
    ),
    "wn.legend_title": msg(
        "**Legenda — colunas de CPU e memória**",
        "**Legend — CPU and memory columns**",
        "**Leyenda — columnas de CPU y memoria**",
        "**Legenda — colonne di CPU e memoria**",
    ),
    "wn.legend_alloc": msg(
        "- **CPU allocatable / Memória allocatable**: capacidade efetiva que o scheduler pode usar para pods (`status.allocatable`). Já desconta reservas do sistema/kubelet.",
        "- **CPU allocatable / Memory allocatable**: effective capacity the scheduler can use for pods (`status.allocatable`). System/kubelet reservations are already deducted.",
        "- **CPU allocatable / Memoria allocatable**: capacidad efectiva que el scheduler puede usar para pods (`status.allocatable`). Ya descuenta las reservas del sistema/kubelet.",
        "- **CPU allocatable / Memoria allocatable**: capacità effettiva che lo scheduler può usare per i pod (`status.allocatable`). Le riserve di sistema/kubelet sono già sottratte.",
    ),
    "wn.legend_cap": msg(
        "- **CPU capacity / Memória capacity**: capacidade bruta do node (`status.capacity`), incluindo o que fica reservado à plataforma.",
        "- **CPU capacity / Memory capacity**: raw node capacity (`status.capacity`), including what is reserved for the platform.",
        "- **CPU capacity / Memoria capacity**: capacidad bruta del nodo (`status.capacity`), incluido lo reservado a la plataforma.",
        "- **CPU capacity / Memoria capacity**: capacità grezza del nodo (`status.capacity`), compreso quanto è riservato alla piattaforma.",
    ),
    "wn.legend_use": msg(
        "- Use **allocatable** nos comparativos de sizing do namespace; **capacity** serve apenas como referência do hardware.",
        "- Use **allocatable** in the namespace sizing comparisons; **capacity** is only a hardware reference.",
        "- Use **allocatable** en los comparativos de dimensionamiento del espacio de nombres; **capacity** sirve solo como referencia del hardware.",
        "- Usare **allocatable** nei confronti di dimensionamento dello spazio dei nomi; **capacity** serve solo come riferimento hardware.",
    ),
    "cmp.title": msg(
        "## Comparativos — workers × namespace `{name}`",
        "## Comparisons — workers × namespace `{name}`",
        "## Comparativas — workers × espacio de nombres `{name}`",
        "## Confronti — worker × spazio dei nomi `{name}`",
    ),
    "cmp.h1": msg(
        "### 1) Disponível × request do namespace",
        "### 1) Available × namespace request",
        "### 1) Disponible × solicitud del espacio de nombres",
        "### 1) Disponibile × richiesta dello spazio dei nomi",
    ),
    "cmp.t1": msg(
        "| Recurso | Disponível (workers) | Request namespace | Uso do disponível |\n|---------|----------------------|--------------------|-------------------|",
        "| Resource | Available (workers) | Namespace request | Share of available |\n|----------|---------------------|-------------------|--------------------|",
        "| Recurso | Disponible (workers) | Solicitud del espacio de nombres | Uso de lo disponible |\n|---------|----------------------|----------------------------------|----------------------|",
        "| Risorsa | Disponibile (worker) | Richiesta dello spazio dei nomi | Uso del disponibile |\n|---------|----------------------|----------------------------------|----------------------|",
    ),
    "cmp.h2": msg(
        "### 2) Disponível × limit do namespace",
        "### 2) Available × namespace limit",
        "### 2) Disponible × límite del espacio de nombres",
        "### 2) Disponibile × limite dello spazio dei nomi",
    ),
    "cmp.t2": msg(
        "| Recurso | Disponível (workers) | Limit namespace | Uso do disponível |\n|---------|----------------------|----------------|-------------------|",
        "| Resource | Available (workers) | Namespace limit | Share of available |\n|----------|---------------------|-----------------|--------------------|",
        "| Recurso | Disponible (workers) | Límite del espacio de nombres | Uso de lo disponible |\n|---------|----------------------|--------------------------------|----------------------|",
        "| Risorsa | Disponibile (worker) | Limite dello spazio dei nomi | Uso del disponibile |\n|---------|----------------------|-------------------------------|----------------------|",
    ),
    "cmp.h3": msg(
        "### 3) Disponível × otimizações sugeridas",
        "### 3) Available × suggested optimizations",
        "### 3) Disponible × optimizaciones sugeridas",
        "### 3) Disponibile × ottimizzazioni suggerite",
    ),
    "cmp.t3": msg(
        "| Recurso | Disponível | Sug. request | Sug. limit | % req | % lim |\n|---------|------------|--------------|------------|-------|-------|",
        "| Resource | Available | Sug. request | Sug. limit | % req | % lim |\n|----------|-----------|--------------|------------|-------|-------|",
        "| Recurso | Disponible | Sug. solicitud | Sug. límite | % sol | % lím |\n|---------|------------|----------------|-------------|-------|-------|",
        "| Risorsa | Disponibile | Sug. richiesta | Sug. limite | % rich | % lim |\n|---------|-------------|---------------|------------|--------|-------|",
    ),
    "eco.title": msg(
        "## Economia de recursos (simplificada)",
        "## Resource savings (simplified)",
        "## Ahorro de recursos (simplificado)",
        "## Risparmio di risorse (semplificato)",
    ),
    "eco.intro": msg(
        "Comparando **valores atuais do namespace** com as **sugestões conservadoras**:",
        "Comparing the **current namespace values** with the **conservative suggestions**:",
        "Comparando los **valores actuales del espacio de nombres** con las **sugerencias conservadoras**:",
        "Confrontando i **valori attuali dello spazio dei nomi** con i **suggerimenti conservativi**:",
    ),
    "eco.header": msg(
        "| Comparação | CPU | Memória |\n|------------|-----|---------|",
        "| Comparison | CPU | Memory |\n|------------|-----|--------|",
        "| Comparación | CPU | Memoria |\n|-------------|-----|---------|",
        "| Confronto | CPU | Memoria |\n|-----------|-----|---------|",
    ),
    "eco.req_row": msg(
        "Request atual → sugerido",
        "Current request → suggested",
        "Solicitud actual → sugerida",
        "Richiesta attuale → suggerita",
    ),
    "eco.lim_row": msg(
        "Limit atual → sugerido",
        "Current limit → suggested",
        "Límite actual → sugerido",
        "Limite attuale → suggerito",
    ),
    "eco.reading": msg("**Leitura direta:**", "**How to read this:**", "**Lectura directa:**", "**Lettura diretta:**"),
    "eco.down": msg(
        "- **↓** = economia (libera capacidade no scheduler).",
        "- **↓** = savings (frees scheduler capacity).",
        "- **↓** = ahorro (libera capacidad en el scheduler).",
        "- **↓** = risparmio (libera capacità nello scheduler).",
    ),
    "eco.up": msg(
        "- **↑** = aumento sugerido (ex.: subir de 1 para ≥2 réplicas por HA).",
        "- **↑** = suggested increase (for example, going from 1 to ≥2 replicas for HA).",
        "- **↑** = aumento sugerido (p. ej., pasar de 1 a ≥2 réplicas por HA).",
        "- **↑** = aumento suggerito (ad esempio, passare da 1 a ≥2 repliche per l'HA).",
    ),
    "eco.requests_line": msg(
        "- Requests: CPU {cpu}, memória {mem}.",
        "- Requests: CPU {cpu}, memory {mem}.",
        "- Solicitudes: CPU {cpu}, memoria {mem}.",
        "- Richieste: CPU {cpu}, memoria {mem}.",
    ),
    "eco.limits_line": msg(
        "- Limits: CPU {cpu}, memória {mem}.",
        "- Limits: CPU {cpu}, memory {mem}.",
        "- Límites: CPU {cpu}, memoria {mem}.",
        "- Limiti: CPU {cpu}, memoria {mem}.",
    ),
    "eco.today": msg(
        "- Uso do pool de workers hoje: requests **{cpu_req}** CPU / **{mem_req}** mem; limits **{cpu_lim}** CPU / **{mem_lim}** mem.",
        "- Worker pool usage today: requests **{cpu_req}** CPU / **{mem_req}** memory; limits **{cpu_lim}** CPU / **{mem_lim}** memory.",
        "- Uso actual del pool de workers: solicitudes **{cpu_req}** CPU / **{mem_req}** memoria; límites **{cpu_lim}** CPU / **{mem_lim}** memoria.",
        "- Uso attuale del pool di worker: richieste **{cpu_req}** CPU / **{mem_req}** memoria; limiti **{cpu_lim}** CPU / **{mem_lim}** memoria.",
    ),
    "eco.opt": msg(
        "- Com otimizações: requests **{cpu_req}** / **{mem_req}**; limits **{cpu_lim}** / **{mem_lim}**.",
        "- With optimizations: requests **{cpu_req}** / **{mem_req}**; limits **{cpu_lim}** / **{mem_lim}**.",
        "- Con optimizaciones: solicitudes **{cpu_req}** / **{mem_req}**; límites **{cpu_lim}** / **{mem_lim}**.",
        "- Con le ottimizzazioni: richieste **{cpu_req}** / **{mem_req}**; limiti **{cpu_lim}** / **{mem_lim}**.",
    ),
    "eco.note": msg(
        "> Estimativa a partir dos manifests (sem métricas reais de uso). Validar em homologação antes de alterar recursos em produção.",
        "> Estimate based on the manifests (no real usage metrics). Validate in a staging environment before changing resources in production.",
        "> Estimación a partir de los manifiestos (sin métricas reales de uso). Validar en un entorno de pruebas antes de cambiar recursos en producción.",
        "> Stima a partire dai manifest (senza metriche reali di utilizzo). Validare in un ambiente di collaudo prima di modificare le risorse in produzione.",
    ),
    "res.by_app": msg(
        "## Por aplicação (atual)",
        "## By application (current)",
        "## Por aplicación (actual)",
        "## Per applicazione (attuale)",
    ),
    "res.by_app_header": msg(
        "| Aplicação | Contêiner | Réplicas | CPU req | CPU lim | Mem req | Mem lim | QoS | HPA |\n|-----------|-----------|----------|---------|---------|---------|---------|-----|-----|",
        "| Application | Container | Replicas | CPU req | CPU lim | Mem req | Mem lim | QoS | HPA |\n|-------------|-----------|----------|---------|---------|---------|---------|-----|-----|",
        "| Aplicación | Contenedor | Réplicas | CPU sol | CPU lím | Mem sol | Mem lím | QoS | HPA |\n|------------|------------|----------|---------|---------|---------|---------|-----|-----|",
        "| Applicazione | Container | Repliche | CPU rich | CPU lim | Mem rich | Mem lim | QoS | HPA |\n|--------------|-----------|----------|----------|---------|----------|---------|-----|-----|",
    ),
    "qos.title": msg(
        "**Legenda — coluna QoS**",
        "**Legend — QoS column**",
        "**Leyenda — columna QoS**",
        "**Legenda — colonna QoS**",
    ),
    "qos.guaranteed": msg(
        "- **Guaranteed**: CPU e memória com `request = limit` — maior prioridade de scheduling/eviction; sem burst além do request.",
        "- **Guaranteed**: CPU and memory with `request = limit` — highest scheduling/eviction priority; no burst beyond the request.",
        "- **Guaranteed**: CPU y memoria con `request = limit` — mayor prioridad de scheduling/eviction; sin ráfaga más allá de la solicitud.",
        "- **Guaranteed**: CPU e memoria con `request = limit` — priorità massima di scheduling/eviction; nessun burst oltre la richiesta.",
    ),
    "qos.burstable": msg(
        "- **Burstable**: há request e/ou limit, porém `request < limit` (ou só um dos dois completo) — pode usar burst até o limit; prioridade intermediária.",
        "- **Burstable**: a request and/or limit exists, but `request < limit` (or only one of the two is complete) — can burst up to the limit; intermediate priority.",
        "- **Burstable**: hay solicitud y/o límite, pero `request < limit` (o solo uno de los dos está completo) — puede usar ráfaga hasta el límite; prioridad intermedia.",
        "- **Burstable**: sono presenti richiesta e/o limite, ma `request < limit` (oppure solo uno dei due è completo) — può usare burst fino al limite; priorità intermedia.",
    ),
    "qos.besteffort": msg(
        "- **BestEffort**: sem `requests` nem `limits` — menor prioridade; primeiro candidato a eviction sob pressão de memória no node.",
        "- **BestEffort**: no `requests` and no `limits` — lowest priority; first candidate for eviction under memory pressure on the node.",
        "- **BestEffort**: sin `requests` ni `limits` — menor prioridad; primer candidato a eviction bajo presión de memoria en el nodo.",
        "- **BestEffort**: senza `requests` né `limits` — priorità minima; primo candidato all'eviction sotto pressione di memoria sul nodo.",
    ),
    "qos.note": msg(
        "> **Requests** = mínimo reservado pelo scheduler. **Limits** = teto máximo do contêiner.",
        "> **Requests** = minimum reserved by the scheduler. **Limits** = container ceiling.",
        "> **Requests** = mínimo reservado por el scheduler. **Limits** = techo máximo del contenedor.",
        "> **Requests** = minimo riservato dallo scheduler. **Limits** = tetto massimo del container.",
    ),
    "res.suggest_title": msg(
        "## Sugestão conservadora por contêiner",
        "## Conservative suggestion per container",
        "## Sugerencia conservadora por contenedor",
        "## Suggerimento conservativo per container",
    ),
    "res.suggest_header": msg(
        "| App | Workload | Contêiner | CPU req→sug | CPU lim→sug | Mem req→sug | Mem lim→sug | Notas |\n|-----|----------|-----------|-------------|-------------|-------------|-------------|-------|",
        "| App | Workload | Container | CPU req→sug | CPU lim→sug | Mem req→sug | Mem lim→sug | Notes |\n|-----|----------|-----------|-------------|-------------|-------------|-------------|-------|",
        "| App | Workload | Contenedor | CPU sol→sug | CPU lím→sug | Mem sol→sug | Mem lím→sug | Notas |\n|-----|----------|------------|-------------|-------------|-------------|-------------|-------|",
        "| App | Workload | Container | CPU rich→sug | CPU lim→sug | Mem rich→sug | Mem lim→sug | Note |\n|-----|----------|-----------|--------------|-------------|--------------|-------------|------|",
    ),
    "res.yaml_title": msg(
        "## Exemplo YAML — resources sugeridos (`{workload}` / `{container}`)",
        "## YAML example — suggested resources (`{workload}` / `{container}`)",
        "## Ejemplo YAML — recursos sugeridos (`{workload}` / `{container}`)",
        "## Esempio YAML — risorse suggerite (`{workload}` / `{container}`)",
    ),
    "hpa.title": msg(
        "## Sugestões de HPA (conservadoras)",
        "## HPA suggestions (conservative)",
        "## Sugerencias de HPA (conservadoras)",
        "## Suggerimenti di HPA (conservativi)",
    ),
    "hpa.header": msg(
        "| App | Workload | min | max | CPU alvo | Mem alvo | Situação |\n|-----|----------|-----|-----|----------|----------|----------|",
        "| App | Workload | min | max | CPU target | Mem target | Status |\n|-----|----------|-----|-----|------------|------------|--------|",
        "| App | Workload | min | max | CPU objetivo | Mem objetivo | Situación |\n|-----|----------|-----|-----|--------------|--------------|-----------|",
        "| App | Workload | min | max | CPU obiettivo | Mem obiettivo | Situazione |\n|-----|----------|-----|-----|---------------|---------------|------------|",
    ),
    "hpa.rationale": msg(
        "### Racional ({app})",
        "### Rationale ({app})",
        "### Justificación ({app})",
        "### Motivazione ({app})",
    ),
    "hpa.yaml_title": msg(
        "## Exemplo YAML — HPA sugerido (`{name}`)",
        "## YAML example — suggested HPA (`{name}`)",
        "## Ejemplo YAML — HPA sugerido (`{name}`)",
        "## Esempio YAML — HPA suggerito (`{name}`)",
    ),
    "hpa.notes_title": msg(
        "Notas de aplicação:",
        "Application notes:",
        "Notas de aplicación:",
        "Note di applicazione:",
    ),
    "hpa.note1": msg(
        "- Aplicar HPA apenas em workloads stateless (Deployments); StatefulSets exigem cuidado.",
        "- Apply an HPA only to stateless workloads (Deployments); StatefulSets need extra care.",
        "- Aplicar el HPA solo a cargas de trabajo sin estado (Deployments); los StatefulSets exigen cuidado.",
        "- Applicare l'HPA solo a workload stateless (Deployment); gli StatefulSet richiedono attenzione.",
    ),
    "hpa.note2": msg(
        "- `behavior.scaleDown` com janela de 300s reduz flapping.",
        "- `behavior.scaleDown` with a 300s window reduces flapping.",
        "- `behavior.scaleDown` con una ventana de 300s reduce el flapping.",
        "- `behavior.scaleDown` con una finestra di 300s riduce il flapping.",
    ),
    "hpa.note3": msg(
        "- Confirmar que metrics-server (ou monitoramento equivalente) está saudável no cluster.",
        "- Confirm that metrics-server (or equivalent monitoring) is healthy in the cluster.",
        "- Confirmar que metrics-server (o una monitorización equivalente) está sano en el clúster.",
        "- Confermare che metrics-server (o un monitoraggio equivalente) sia integro nel cluster.",
    ),
    "hpa.note4": msg(
        "- Após aplicar, observar 1–2 ciclos de carga antes de reduzir `maxReplicas` ou apertar targets.",
        "- After applying, observe 1–2 load cycles before lowering `maxReplicas` or tightening targets.",
        "- Tras aplicarlo, observar 1–2 ciclos de carga antes de reducir `maxReplicas` o ajustar los objetivos.",
        "- Dopo l'applicazione, osservare 1–2 cicli di carico prima di ridurre `maxReplicas` o stringere i target.",
    ),
    "res.chart_mem": msg(
        "## Gráfico — memória limits atuais por aplicação (Mi)",
        "## Chart — current memory limits by application (Mi)",
        "## Gráfico — límites de memoria actuales por aplicación (Mi)",
        "## Grafico — limiti di memoria attuali per applicazione (Mi)",
    ),
    "res.chart_cpu": msg(
        "## Gráfico — CPU limits atuais por aplicação (millicores)",
        "## Chart — current CPU limits by application (millicores)",
        "## Gráfico — límites de CPU actuales por aplicación (millicores)",
        "## Grafico — limiti di CPU attuali per applicazione (millicores)",
    ),
    "aff.title": msg(
        "## Affinity e anti-affinity — boas práticas",
        "## Affinity and anti-affinity — good practices",
        "## Affinity y anti-affinity — buenas prácticas",
        "## Affinity e anti-affinity — buone pratiche",
    ),
    "aff.inventory": msg(
        "Inventário nos workloads analisados:",
        "Inventory of the analyzed workloads:",
        "Inventario de las cargas de trabajo analizadas:",
        "Inventario dei workload analizzati:",
    ),
    "aff.header": msg(
        "| Workload | App | nodeAffinity | podAffinity | podAntiAffinity |",
        "| Workload | App | nodeAffinity | podAffinity | podAntiAffinity |",
        "| Workload | App | nodeAffinity | podAffinity | podAntiAffinity |",
        "| Workload | App | nodeAffinity | podAffinity | podAntiAffinity |",
    ),
    "aff.practices": msg(
        "**Boas práticas sugeridas**",
        "**Suggested good practices**",
        "**Buenas prácticas sugeridas**",
        "**Buone pratiche suggerite**",
    ),
    "aff.p1": msg(
        "1. **podAntiAffinity (obrigatório para HA)** — para Deployments com ≥2 réplicas, preferir `requiredDuringSchedulingIgnoredDuringExecution` (ou `preferred…` em clusters pequenos) com `topologyKey: kubernetes.io/hostname`, para espalhar pods em nodes distintos.",
        "1. **podAntiAffinity (required for HA)** — for Deployments with ≥2 replicas, prefer `requiredDuringSchedulingIgnoredDuringExecution` (or `preferred…` on small clusters) with `topologyKey: kubernetes.io/hostname`, so pods spread across distinct nodes.",
        "1. **podAntiAffinity (obligatorio para HA)** — para Deployments con ≥2 réplicas, preferir `requiredDuringSchedulingIgnoredDuringExecution` (o `preferred…` en clústeres pequeños) con `topologyKey: kubernetes.io/hostname`, para repartir los pods en nodos distintos.",
        "1. **podAntiAffinity (obbligatorio per l'HA)** — per i Deployment con ≥2 repliche, preferire `requiredDuringSchedulingIgnoredDuringExecution` (o `preferred…` nei cluster piccoli) con `topologyKey: kubernetes.io/hostname`, per distribuire i pod su nodi distinti.",
    ),
    "aff.p2": msg(
        "2. **Evitar single point of failure** — réplica única + ausência de anti-affinity concentra risco; combine minReplicas≥2 (HPA/Deployment) com anti-affinity.",
        "2. **Avoid a single point of failure** — a single replica plus missing anti-affinity concentrates risk; combine minReplicas≥2 (HPA/Deployment) with anti-affinity.",
        "2. **Evitar un punto único de fallo** — una réplica única más la ausencia de anti-affinity concentra el riesgo; combine minReplicas≥2 (HPA/Deployment) con anti-affinity.",
        "2. **Evitare un singolo punto di errore** — una replica singola più l'assenza di anti-affinity concentra il rischio; combinare minReplicas≥2 (HPA/Deployment) con anti-affinity.",
    ),
    "aff.p3": msg(
        "3. **nodeAffinity / nodeSelector** — use para direcionar a pools (worker, infra, GPU) via labels; evite hard-coding de nomes de node.",
        "3. **nodeAffinity / nodeSelector** — use them to target pools (worker, infra, GPU) via labels; avoid hard-coding node names.",
        "3. **nodeAffinity / nodeSelector** — úselos para dirigir a pools (worker, infra, GPU) mediante labels; evite fijar nombres de nodo.",
        "3. **nodeAffinity / nodeSelector** — usarli per indirizzare i pool (worker, infra, GPU) tramite label; evitare di fissare i nomi dei nodi.",
    ),
    "aff.p4": msg(
        "4. **podAffinity** — reserve para componentes que realmente precisam de localidade (cache local, volumes, latência); uso excessivo gera hotspots.",
        "4. **podAffinity** — reserve it for components that truly need locality (local cache, volumes, latency); overuse creates hotspots.",
        "4. **podAffinity** — resérvelo para componentes que realmente necesitan localidad (caché local, volúmenes, latencia); un uso excesivo genera hotspots.",
        "4. **podAffinity** — riservarlo ai componenti che hanno davvero bisogno di località (cache locale, volumi, latenza); un uso eccessivo crea hotspot.",
    ),
    "aff.p5": msg(
        "5. **Zonas** — em clusters multi-AZ, considere `topology.kubernetes.io/zone` além de hostname para resiliência a falha de zona.",
        "5. **Zones** — on multi-AZ clusters, consider `topology.kubernetes.io/zone` in addition to hostname for zone-failure resilience.",
        "5. **Zonas** — en clústeres multi-AZ, considere `topology.kubernetes.io/zone` además del hostname para resistir el fallo de una zona.",
        "5. **Zone** — nei cluster multi-AZ, considerare `topology.kubernetes.io/zone` oltre all'hostname per resistere al guasto di una zona.",
    ),
    "aff.p6": msg(
        "6. **Não conflitar com taints/tolerations** — affinity deve ser coerente com taints dos pools (infra/ODF) para não deixar pods Pending.",
        "6. **Do not conflict with taints/tolerations** — affinity must be consistent with pool taints (infra/ODF) so pods do not stay Pending.",
        "6. **No entrar en conflicto con taints/tolerations** — la affinity debe ser coherente con los taints de los pools (infra/ODF) para no dejar pods en Pending.",
        "6. **Non entrare in conflitto con taint/toleration** — l'affinity deve essere coerente con i taint dei pool (infra/ODF) per non lasciare pod in Pending.",
    ),
    "aff.missing": msg(
        "_Nenhum `podAntiAffinity` encontrado em: {names}{extra}. Priorizar esta melhoria nos workloads críticos._",
        "_No `podAntiAffinity` found in: {names}{extra}. Prioritize this improvement on critical workloads._",
        "_No se encontró `podAntiAffinity` en: {names}{extra}. Priorizar esta mejora en las cargas de trabajo críticas._",
        "_Nessun `podAntiAffinity` trovato in: {names}{extra}. Dare priorità a questo miglioramento nei workload critici._",
    ),
    "aff.extra": msg(
        " (+{count} outros)",
        " (+{count} more)",
        " (+{count} más)",
        " (+{count} altri)",
    ),
    "references.body": msg(
        """## Referências utilizadas

1. Kubernetes — *Resource Management for Pods and Containers*  
   https://kubernetes.io/docs/concepts/configuration/manage-resources-containers/

2. Kubernetes — *Assign Memory Resources to Containers and Pods*  
   https://kubernetes.io/docs/tasks/configure-pod-container/assign-memory-resource/

3. Kubernetes — *Assign CPU Resources to Containers and Pods*  
   https://kubernetes.io/docs/tasks/configure-pod-container/assign-cpu-resource/

4. Kubernetes — *Horizontal Pod Autoscaling*  
   https://kubernetes.io/docs/tasks/run-application/horizontal-pod-autoscale/

5. Kubernetes — *HorizontalPodAutoscaler Walkthrough*  
   https://kubernetes.io/docs/tasks/run-application/horizontal-pod-autoscale-walkthrough/

6. OpenShift — *Quotas and Limit Ranges*  
   https://docs.openshift.com/container-platform/latest/nodes/clusters/nodes-cluster-limit-ranges.html

7. OpenShift — *Automatically scaling pods with the Horizontal Pod Autoscaler*  
   https://docs.openshift.com/container-platform/latest/nodes/pods/nodes-pods-autoscaling.html

8. CNCF / Kubernetes best practices — *Resource requests and limits* (orientação Burstable / evitar overcommit agressivo)  
   https://kubernetes.io/docs/concepts/workloads/pods/pod-qos/

9. Kubernetes — *Pod Quality of Service Classes*  
   https://kubernetes.io/docs/concepts/workloads/pods/pod-qos/

> As sugestões de resources/HPA deste relatório são **heurísticas conservadoras** baseadas nos manifests coletados, não em métricas de uso em tempo real (Prometheus/VPA). Validar em homologação antes de aplicar em produção.
""",
        """## References used

1. Kubernetes — *Resource Management for Pods and Containers*  
   https://kubernetes.io/docs/concepts/configuration/manage-resources-containers/

2. Kubernetes — *Assign Memory Resources to Containers and Pods*  
   https://kubernetes.io/docs/tasks/configure-pod-container/assign-memory-resource/

3. Kubernetes — *Assign CPU Resources to Containers and Pods*  
   https://kubernetes.io/docs/tasks/configure-pod-container/assign-cpu-resource/

4. Kubernetes — *Horizontal Pod Autoscaling*  
   https://kubernetes.io/docs/tasks/run-application/horizontal-pod-autoscale/

5. Kubernetes — *HorizontalPodAutoscaler Walkthrough*  
   https://kubernetes.io/docs/tasks/run-application/horizontal-pod-autoscale-walkthrough/

6. OpenShift — *Quotas and Limit Ranges*  
   https://docs.openshift.com/container-platform/latest/nodes/clusters/nodes-cluster-limit-ranges.html

7. OpenShift — *Automatically scaling pods with the Horizontal Pod Autoscaler*  
   https://docs.openshift.com/container-platform/latest/nodes/pods/nodes-pods-autoscaling.html

8. CNCF / Kubernetes best practices — *Resource requests and limits* (Burstable guidance / avoid aggressive overcommit)  
   https://kubernetes.io/docs/concepts/workloads/pods/pod-qos/

9. Kubernetes — *Pod Quality of Service Classes*  
   https://kubernetes.io/docs/concepts/workloads/pods/pod-qos/

> The resources/HPA suggestions in this report are **conservative heuristics** based on the collected manifests, not on real-time usage metrics (Prometheus/VPA). Validate in a staging environment before applying in production.
""",
        """## Referencias utilizadas

1. Kubernetes — *Resource Management for Pods and Containers*  
   https://kubernetes.io/docs/concepts/configuration/manage-resources-containers/

2. Kubernetes — *Assign Memory Resources to Containers and Pods*  
   https://kubernetes.io/docs/tasks/configure-pod-container/assign-memory-resource/

3. Kubernetes — *Assign CPU Resources to Containers and Pods*  
   https://kubernetes.io/docs/tasks/configure-pod-container/assign-cpu-resource/

4. Kubernetes — *Horizontal Pod Autoscaling*  
   https://kubernetes.io/docs/tasks/run-application/horizontal-pod-autoscale/

5. Kubernetes — *HorizontalPodAutoscaler Walkthrough*  
   https://kubernetes.io/docs/tasks/run-application/horizontal-pod-autoscale-walkthrough/

6. OpenShift — *Quotas and Limit Ranges*  
   https://docs.openshift.com/container-platform/latest/nodes/clusters/nodes-cluster-limit-ranges.html

7. OpenShift — *Automatically scaling pods with the Horizontal Pod Autoscaler*  
   https://docs.openshift.com/container-platform/latest/nodes/pods/nodes-pods-autoscaling.html

8. CNCF / Kubernetes best practices — *Resource requests and limits* (orientación Burstable / evitar overcommit agresivo)  
   https://kubernetes.io/docs/concepts/workloads/pods/pod-qos/

9. Kubernetes — *Pod Quality of Service Classes*  
   https://kubernetes.io/docs/concepts/workloads/pods/pod-qos/

> Las sugerencias de resources/HPA de este informe son **heurísticas conservadoras** basadas en los manifiestos recopilados, no en métricas de uso en tiempo real (Prometheus/VPA). Validar en un entorno de pruebas antes de aplicar en producción.
""",
        """## Riferimenti utilizzati

1. Kubernetes — *Resource Management for Pods and Containers*  
   https://kubernetes.io/docs/concepts/configuration/manage-resources-containers/

2. Kubernetes — *Assign Memory Resources to Containers and Pods*  
   https://kubernetes.io/docs/tasks/configure-pod-container/assign-memory-resource/

3. Kubernetes — *Assign CPU Resources to Containers and Pods*  
   https://kubernetes.io/docs/tasks/configure-pod-container/assign-cpu-resource/

4. Kubernetes — *Horizontal Pod Autoscaling*  
   https://kubernetes.io/docs/tasks/run-application/horizontal-pod-autoscale/

5. Kubernetes — *HorizontalPodAutoscaler Walkthrough*  
   https://kubernetes.io/docs/tasks/run-application/horizontal-pod-autoscale-walkthrough/

6. OpenShift — *Quotas and Limit Ranges*  
   https://docs.openshift.com/container-platform/latest/nodes/clusters/nodes-cluster-limit-ranges.html

7. OpenShift — *Automatically scaling pods with the Horizontal Pod Autoscaler*  
   https://docs.openshift.com/container-platform/latest/nodes/pods/nodes-pods-autoscaling.html

8. CNCF / Kubernetes best practices — *Resource requests and limits* (indicazione Burstable / evitare overcommit aggressivo)  
   https://kubernetes.io/docs/concepts/workloads/pods/pod-qos/

9. Kubernetes — *Pod Quality of Service Classes*  
   https://kubernetes.io/docs/concepts/workloads/pods/pod-qos/

> I suggerimenti di resources/HPA di questo report sono **euristiche conservative** basate sui manifest raccolti, non su metriche di utilizzo in tempo reale (Prometheus/VPA). Validare in un ambiente di collaudo prima di applicare in produzione.
""",
    ),
}
