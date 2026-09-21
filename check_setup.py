"""Smoke test offline: dependencias, chave presente e corpus PDF legivel.

Nao imprime a chave e nao testa autenticacao nem consome a API.
"""
import argparse
import hashlib
import importlib
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent


def validar_documentos(folder):
    from pypdf import PdfReader
    files = sorted(folder.glob('*.pdf'))
    errors, records = [], []
    if not 3 <= len(files) <= 5:
        errors.append(f'Esperados 3 a 5 PDFs; encontrados {len(files)}.')
    for pdf in files:
        try:
            reader = PdfReader(pdf)
            lengths = [len((page.extract_text() or '').strip()) for page in reader.pages]
            if not lengths or any(length < 80 for length in lengths):
                errors.append(f'{pdf.name}: pagina sem texto suficiente; revisar PDF/OCR.')
            records.append({'arquivo': pdf.name, 'paginas': len(lengths),
                            'min_caracteres_pagina': min(lengths, default=0),
                            'sha256': hashlib.sha256(pdf.read_bytes()).hexdigest()})
        except Exception as exc:
            errors.append(f'{pdf.name}: falha de leitura ({type(exc).__name__}).')
    total = sum(row['paginas'] for row in records)
    if not 15 <= total <= 60:
        errors.append(f'Esperadas 15 a 60 paginas; encontradas {total}.')
    return records, errors


def main():
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--env-file', type=Path, default=ROOT / '.env')
    parser.add_argument('--data-dir', type=Path, default=ROOT / 'data')
    parser.add_argument('--report', type=Path)
    args = parser.parse_args()
    errors = []
    for module in ('google.genai', 'chromadb', 'pypdf', 'dotenv', 'fontTools'):
        try:
            importlib.import_module(module)
            print(f'OK dependencia: {module}')
        except ImportError:
            errors.append(f'Dependencia ausente: {module}')
    if errors:
        for error in errors:
            print('FALHA:', error)
        return 1
    from dotenv import load_dotenv
    load_dotenv(args.env_file, override=False)
    key_present = bool(os.getenv('GEMINI_API_KEY', '').strip())
    if not key_present:
        errors.append('GEMINI_API_KEY ausente; preencher .env local.')
    else:
        print('OK chave presente (autenticacao nao testada).')
    records, pdf_errors = validar_documentos(args.data_dir)
    errors.extend(pdf_errors)
    for row in records:
        print(f"{row['arquivo']}: {row['paginas']} paginas; texto extraivel.")
    report = {'modo': 'offline', 'api_autenticada': False, 'chave_presente': key_present,
              'documentos': records, 'total_paginas': sum(r['paginas'] for r in records),
              'erros': errors, 'aprovado': not errors}
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    for error in errors:
        print('FALHA:', error)
    print('APROVADO (offline)' if not errors else 'REPROVADO')
    return int(bool(errors))


if __name__ == '__main__':
    sys.exit(main())
