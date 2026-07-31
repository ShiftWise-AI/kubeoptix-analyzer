#!/usr/bin/env python3

import os
import re
import shutil
import argparse
from pathlib import Path

# Padrões de informações sensíveis
PATTERNS = {
    "CPF": re.compile(r"\b\d{3}\.\d{3}\.\d{3}-\d{2}\b|\b\d{11}\b"),
    
    "RG": re.compile(
        r"\b\d{1,2}\.?\d{3}\.?\d{3}-?[0-9Xx]\b"
    ),

    "CARTAO_CREDITO": re.compile(
        r"\b(?:\d[ -]*?){13,19}\b"
    ),

    "EMAIL": re.compile(
        r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"
    ),

    "TELEFONE": re.compile(
        r"\b(?:\+55\s?)?(?:\(?\d{2}\)?\s?)?(?:9?\d{4})[- ]?\d{4}\b"
    ),

    "CEP": re.compile(
        r"\b\d{5}-?\d{3}\b"
    ),

    "ENDERECO": re.compile(
        r"\b(?:Rua|R\.|Avenida|Av\.|Travessa|Tv\.|Alameda|Rodovia)\s+[A-Za-zÀ-ÿ0-9\s,.-]{5,100}",
        re.IGNORECASE
    ),

    "TOKEN": re.compile(
        r"\b(?:Bearer\s+)?[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{10,}\.?[A-Za-z0-9_-]*\b"
    ),

    # Headers e campos de token (Kubernetes/OpenShift, OAuth/JWT e variações)
    "TOKEN_EXPLICITO": re.compile(
        r"\b(?:authorization|x-auth-token|token|id_token|access_token|refresh_token|"
        r"bearerToken|serviceAccountToken)\s*[:=]\s*[\"']?(?:Bearer\s+)?[A-Za-z0-9._\-+/=]{8,}[\"']?",
        re.IGNORECASE
    ),

    "CHAVE_API": re.compile(
        r"(?:api[_-]?key|apikey|secret|token)\s*[:=]\s*[\"']?[A-Za-z0-9_\-]{8,}[\"']?",
        re.IGNORECASE
    ),

    # Certificados/segredos comuns em YAML de ConfigMap/OpenShift
    "CERTIFICADO_PEM": re.compile(
        r"-----BEGIN CERTIFICATE-----[\s\S]*?-----END CERTIFICATE-----",
        re.IGNORECASE
    ),

    "CHAVE_PRIVADA_PEM": re.compile(
        r"-----BEGIN (?:RSA |EC |OPENSSH |)?PRIVATE KEY-----[\s\S]*?-----END (?:RSA |EC |OPENSSH |)?PRIVATE KEY-----",
        re.IGNORECASE
    ),

    "CAMPO_CERTIFICADO": re.compile(
        r"\b(?:ca\.crt|tls\.crt|service-ca\.crt|caBundle|certificate|cert)\s*[:=]\s*[\"']?[A-Za-z0-9+/=._\-]{16,}[\"']?",
        re.IGNORECASE
    ),

    # Dados bancários: agência/conta, códigos bancários e identificadores internacionais
    "DADOS_BANCARIOS": re.compile(
        r"\b(?:agencia|ag\.?|conta|conta[_\s-]?corrente|conta[_\s-]?poupanca|"
        r"banco|codigo[_\s-]?banco|bank[_\s-]?code|iban|swift|bic|pix)"
        r"\s*[:=]\s*[\"']?[A-Za-z0-9.\-/]{3,}[\"']?",
        re.IGNORECASE
    ),

    # IBAN (identificador bancário internacional)
    "IBAN": re.compile(
        r"\b[A-Z]{2}\d{2}[A-Z0-9]{11,30}\b"
    ),

    # SWIFT/BIC (8 ou 11 caracteres)
    "SWIFT_BIC": re.compile(
        r"\b[A-Z]{6}[A-Z0-9]{2}(?:[A-Z0-9]{3})?\b"
    ),

    # Login corporativo iniciado por tbn (ex.: tbn12345, tbn.jose)
    "LOGIN_CORPORATIVO": re.compile(
        r"\btbn[a-z0-9._-]{2,}\b",
        re.IGNORECASE
    ),

    # Senha em texto claro no formato UUID
    "UUID": re.compile(
        r"\b[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[1-5][0-9a-fA-F]{3}-[89abAB][0-9a-fA-F]{3}-[0-9a-fA-F]{12}\b"
    ),

    # Segredos e tokens comumente presentes em YAML/Kubernetes/Infra
    "SEGREDO_INFRA": re.compile(
        r"\b(?:password|passwd|pwd|secret|token|clientSecret|accessKey|secretKey|"
        r"authorization|bearerToken|kubeconfig|privateKey|tls\.key|dockerconfigjson)"
        r"\s*[:=]\s*[\"']?[^\s\"']{4,}[\"']?",
        re.IGNORECASE
    ),

}


def mascarar_dados(conteudo):
    encontrou = False

    for tipo, pattern in PATTERNS.items():
        novo_conteudo, qtd = pattern.subn(f"[{tipo}_REMOVIDO]", conteudo)

        if qtd > 0:
            encontrou = True
            conteudo = novo_conteudo

    return conteudo, encontrou


def processar_arquivo(arquivo, backup=False):
    try:
        # Evita alterar arquivos binários ao processar diretórios inteiros
        with open(arquivo, "rb") as f:
            bruto = f.read()

        if b"\x00" in bruto:
            return

        conteudo = bruto.decode("utf-8", errors="ignore")

        novo_conteudo, encontrou = mascarar_dados(conteudo)

        if encontrou:
            if backup:
                shutil.copy2(arquivo, f"{arquivo}.bak")

            with open(arquivo, "w", encoding="utf-8") as f:
                f.write(novo_conteudo)

            print(f"[ALTERADO] {arquivo}")

    except Exception as e:
        print(f"[ERRO] {arquivo}: {e}")


def processar_diretorio(diretorio, backup=False):
    for raiz, _, arquivos in os.walk(diretorio):
        for nome_arquivo in arquivos:
            if nome_arquivo.endswith(".bak"):
                continue

            caminho = os.path.join(raiz, nome_arquivo)
            processar_arquivo(caminho, backup)


def main():
    parser = argparse.ArgumentParser(
        description="Remove informações sensíveis de arquivos do diretório informado."
    )

    parser.add_argument(
        "diretorio",
        help="Diretório contendo os arquivos"
    )

    parser.add_argument(
        "--backup",
        action="store_true",
        help="Cria arquivo .bak antes de alterar"
    )

    args = parser.parse_args()

    diretorio = Path(args.diretorio)

    if not diretorio.exists():
        print(f"Diretório não encontrado: {diretorio}")
        return

    processar_diretorio(diretorio, args.backup)


if __name__ == "__main__":
    main()