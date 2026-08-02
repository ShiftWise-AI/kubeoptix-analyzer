"""Locale helpers and report internationalization utilities."""

from __future__ import annotations

from dataclasses import dataclass

DEFAULT_LOCALE = "pt-BR"
SUPPORTED_LOCALES = (DEFAULT_LOCALE, "en-US", "es-ES", "it-IT")


@dataclass(frozen=True)
class LocaleSpec:
    code: str
    language_name: str
    markdown_language_name: str


LOCALE_SPECS: dict[str, LocaleSpec] = {
    "pt-BR": LocaleSpec("pt-BR", "Brazilian Portuguese", "português do Brasil"),
    "en-US": LocaleSpec("en-US", "English (United States)", "English (United States)"),
    "es-ES": LocaleSpec("es-ES", "Spanish (Spain)", "español (España)"),
    "it-IT": LocaleSpec("it-IT", "Italian (Italy)", "italiano (Italia)"),
}


REPORT_REPLACEMENTS: dict[str, list[tuple[str, str]]] = {
    "en-US": [
        ("## Referências utilizadas", "## References used"),
        ("# Relatório de assessment OpenShift", "# OpenShift assessment report"),
        ("## Sumário quantitativo", "## Quantitative summary"),
        ("## Sumário executivo", "## Executive summary"),
        ("### Achados de configuração", "### Configuration findings"),
        ("### Inventário", "### Inventory"),
        ("- Aplicações:", "- Applications:"),
        ("- ClusterServiceVersions (operadores):", "- ClusterServiceVersions (operators):"),
        ("- Arquivos de log:", "- Log files:"),
        ("Gerado em", "Generated at"),
        ("análise local, sem LLM", "local analysis, no LLM"),
        ("modo embedded: heurísticas +", "embedded mode: heuristics +"),
        ("Artefatos:", "Artifacts:"),
        ("Nenhum namespace encontrado nos artefatos.", "No namespaces found in the artifacts."),
        ("Nenhum achado pelas heurísticas locais.", "No findings detected by local heuristics."),
        ("achados", "findings"),
        ("ocorrências em logs", "log occurrences"),
        ("ocorrencias em logs", "log occurrences"),
        ("indícios sensíveis em ConfigMaps", "sensitive hints in ConfigMaps"),
        ("Memória req/lim", "Memory req/lim"),
        ("alto=", "high="),
        ("médio=", "medium="),
        ("medio=", "medium="),
        ("baixo=", "low="),
        ("Severidade:", "Severity:"),
        ("sem workloads para score", "no workloads available for scoring"),
        ("Aplicacao", "Application"),
        ("Aplicações", "Applications"),
        ("Metrica", "Metric"),
        ("Mediana do grupo", "Group median"),
        ("Achados priorizados por heuristica + reranking", "Findings prioritized by heuristics + reranking"),
        ("Nenhum achado para priorizar.", "No findings to prioritize."),
        ("Clustering de erros de log", "Log error clustering"),
        ("Agrupamento por assinatura normalizada para reduzir ruido e destacar padroes repetitivos.", "Grouping by normalized signature to reduce noise and highlight repeated patterns."),
        ("Categoria", "Category"),
        ("Repeticoes", "Repetitions"),
        ("Assinatura normalizada", "Normalized signature"),
        ("Exemplo", "Sample"),
        ("sem clusters", "no clusters"),
        ("Outliers de requests/limits", "Requests/limits outliers"),
        ("Score de risco por workload", "Risk score by workload"),
        ("Nivel", "Level"),
        ("Principais fatores", "Main factors"),
        ("sem workloads detectados", "no workloads detected"),
        ("sem agravantes relevantes", "no relevant aggravating factors"),
        ("conteiner(es) sem limits completos", "container(s) without complete limits"),
        ("conteiner(es) sem requests completos", "container(s) without complete requests"),
        ("QoS BestEffort detectado", "BestEffort QoS detected"),
        ("replica unica", "single replica"),
        ("sem podAntiAffinity apesar de replicas > 1", "no podAntiAffinity despite replicas > 1"),
        ("sem readinessProbe", "missing readinessProbe"),
        ("sem livenessProbe", "missing livenessProbe"),
        ("imagem mutable (:latest)", "mutable image (:latest)"),
    ],
    "es-ES": [
        ("## Referências utilizadas", "## Referencias utilizadas"),
        ("# Relatório de assessment OpenShift", "# Informe de assessment de OpenShift"),
        ("## Sumário quantitativo", "## Resumen cuantitativo"),
        ("## Sumário executivo", "## Resumen ejecutivo"),
        ("### Achados de configuração", "### Hallazgos de configuración"),
        ("### Inventário", "### Inventario"),
        ("- Aplicações:", "- Aplicaciones:"),
        ("- ClusterServiceVersions (operadores):", "- ClusterServiceVersions (operadores):"),
        ("- Arquivos de log:", "- Archivos de log:"),
        ("Gerado em", "Generado en"),
        ("análise local, sem LLM", "análisis local, sin LLM"),
        ("modo embedded: heurísticas +", "modo embedded: heurísticas +"),
        ("Artefatos:", "Artefactos:"),
        ("Nenhum namespace encontrado nos artefatos.", "No se encontraron namespaces en los artefactos."),
        ("Nenhum achado pelas heurísticas locais.", "No se detectaron hallazgos mediante heurísticas locales."),
        ("achados", "hallazgos"),
        ("ocorrências em logs", "ocurrencias en logs"),
        ("ocorrencias em logs", "ocurrencias en logs"),
        ("indícios sensíveis em ConfigMaps", "indicios sensibles en ConfigMaps"),
        ("Memória req/lim", "Memoria req/lim"),
        ("baixo=", "bajo="),
        ("Severidade:", "Severidad:"),
        ("sem workloads para score", "sin workloads para calcular score"),
        ("Aplicacao", "Aplicación"),
        ("Aplicações", "Aplicaciones"),
        ("Metrica", "Métrica"),
        ("Mediana do grupo", "Mediana del grupo"),
        ("Achados priorizados por heuristica + reranking", "Hallazgos priorizados por heurística + reranking"),
        ("Nenhum achado para priorizar.", "No hay hallazgos para priorizar."),
        ("Clustering de erros de log", "Agrupación de errores de log"),
        ("Agrupamento por assinatura normalizada para reduzir ruido e destacar padroes repetitivos.", "Agrupación por firma normalizada para reducir ruido y destacar patrones repetitivos."),
        ("Categoria", "Categoría"),
        ("Repeticoes", "Repeticiones"),
        ("Assinatura normalizada", "Firma normalizada"),
        ("Exemplo", "Ejemplo"),
        ("sem clusters", "sin clusters"),
        ("Outliers de requests/limits", "Valores atípicos de requests/limits"),
        ("Score de risco por workload", "Puntuación de riesgo por workload"),
        ("Nivel", "Nivel"),
        ("Principais fatores", "Factores principales"),
        ("sem workloads detectados", "sin workloads detectados"),
        ("sem agravantes relevantes", "sin agravantes relevantes"),
        ("conteiner(es) sem limits completos", "contenedor(es) sin limits completos"),
        ("conteiner(es) sem requests completos", "contenedor(es) sin requests completos"),
        ("QoS BestEffort detectado", "QoS BestEffort detectado"),
        ("replica unica", "réplica única"),
        ("sem podAntiAffinity apesar de replicas > 1", "sin podAntiAffinity pese a réplicas > 1"),
        ("sem readinessProbe", "sin readinessProbe"),
        ("sem livenessProbe", "sin livenessProbe"),
        ("imagem mutable (:latest)", "imagen mutable (:latest)"),
    ],
    "it-IT": [
        ("## Referências utilizadas", "## Riferimenti utilizzati"),
        ("# Relatório de assessment OpenShift", "# Report di assessment OpenShift"),
        ("## Sumário quantitativo", "## Sommario quantitativo"),
        ("## Sumário executivo", "## Sommario esecutivo"),
        ("### Achados de configuração", "### Rilevazioni di configurazione"),
        ("### Inventário", "### Inventario"),
        ("- Aplicações:", "- Applicazioni:"),
        ("- ClusterServiceVersions (operadores):", "- ClusterServiceVersions (operatori):"),
        ("- Arquivos de log:", "- File di log:"),
        ("Gerado em", "Generato il"),
        ("análise local, sem LLM", "analisi locale, senza LLM"),
        ("modo embedded: heurísticas +", "modalità embedded: euristiche +"),
        ("Artefatos:", "Artefatti:"),
        ("Nenhum namespace encontrado nos artefatos.", "Nessun namespace trovato negli artefatti."),
        ("Nenhum achado pelas heurísticas locais.", "Nessuna rilevazione individuata dalle euristiche locali."),
        ("achados", "rilevazioni"),
        ("ocorrências em logs", "occorrenze nei log"),
        ("ocorrencias em logs", "occorrenze nei log"),
        ("indícios sensíveis em ConfigMaps", "indizi sensibili nei ConfigMap"),
        ("Memória req/lim", "Memoria req/lim"),
        ("baixo=", "basso="),
        ("Severidade:", "Severità:"),
        ("sem workloads para score", "nessun workload disponibile per il punteggio"),
        ("Aplicacao", "Applicazione"),
        ("Aplicações", "Applicazioni"),
        ("Metrica", "Metrica"),
        ("Mediana do grupo", "Mediana del gruppo"),
        ("Achados priorizados por heuristica + reranking", "Rilevazioni prioritarie per euristica + reranking"),
        ("Nenhum achado para priorizar.", "Nessuna rilevazione da prioritizzare."),
        ("Clustering de erros de log", "Clustering degli errori di log"),
        ("Agrupamento por assinatura normalizada para reduzir ruido e destacar padroes repetitivos.", "Raggruppamento per firma normalizzata per ridurre il rumore ed evidenziare pattern ripetitivi."),
        ("Categoria", "Categoria"),
        ("Repeticoes", "Ripetizioni"),
        ("Assinatura normalizada", "Firma normalizzata"),
        ("Exemplo", "Esempio"),
        ("sem clusters", "nessun cluster"),
        ("Outliers de requests/limits", "Outlier di requests/limits"),
        ("Score de risco por workload", "Punteggio di rischio per workload"),
        ("Nivel", "Livello"),
        ("Principais fatores", "Fattori principali"),
        ("sem workloads detectados", "nessun workload rilevato"),
        ("sem agravantes relevantes", "nessun fattore aggravante rilevante"),
        ("conteiner(es) sem limits completos", "container senza limits completi"),
        ("conteiner(es) sem requests completos", "container senza requests completi"),
        ("QoS BestEffort detectado", "QoS BestEffort rilevato"),
        ("replica unica", "replica singola"),
        ("sem podAntiAffinity apesar de replicas > 1", "assenza di podAntiAffinity nonostante repliche > 1"),
        ("sem readinessProbe", "assenza di readinessProbe"),
        ("sem livenessProbe", "assenza di livenessProbe"),
        ("imagem mutable (:latest)", "immagine mutable (:latest)"),
    ],
}


def normalize_locale(locale: str | None) -> str:
    if not locale:
        return DEFAULT_LOCALE
    if locale not in LOCALE_SPECS:
        supported = ", ".join(SUPPORTED_LOCALES)
        raise ValueError(f"Unsupported locale '{locale}'. Supported values: {supported}")
    return locale


def get_locale_spec(locale: str | None) -> LocaleSpec:
    return LOCALE_SPECS[normalize_locale(locale)]


def translate_markdown(text: str, locale: str | None) -> str:
    resolved = normalize_locale(locale)
    if resolved == DEFAULT_LOCALE:
        return text

    translated = text
    for source, target in sorted(
        REPORT_REPLACEMENTS.get(resolved, []),
        key=lambda item: len(item[0]),
        reverse=True,
    ):
        translated = translated.replace(source, target)
    return translated