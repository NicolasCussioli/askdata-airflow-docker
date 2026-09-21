"""Exporta texto de documentacao oficial; nunca executa comandos dos documentos."""
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
import textwrap
from xml.sax.saxutils import escape

import requests
from bs4 import BeautifulSoup
from pypdf import PdfReader
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Preformatted

ROOT = Path(__file__).resolve().parents[1]
SOURCES = [
    ('01-airflow-docker', 'Running Airflow in Docker', 'Apache Airflow 3.3.2',
     'https://airflow.apache.org/docs/apache-airflow/3.3.2/howto/docker-compose/index.html'),
    ('02-airflow-dags', 'Dags', 'Apache Airflow 3.3.2',
     'https://airflow.apache.org/docs/apache-airflow/3.3.2/core-concepts/dags.html'),
    ('03-airflow-tasks', 'Tasks', 'Apache Airflow 3.3.2',
     'https://airflow.apache.org/docs/apache-airflow/3.3.2/core-concepts/tasks.html'),
    ('04-docker-compose', 'Docker Compose Quickstart', 'Docker Docs - snapshot',
     'https://docs.docker.com/compose/gettingstarted/'),
]


def fetch(url):
    response = requests.get(url, timeout=60)
    response.raise_for_status()
    return response.content


def footer(canvas, doc):
    canvas.setFont('Helvetica', 8)
    canvas.setFillColor(colors.HexColor('#526175'))
    canvas.drawString(44, 25, 'AskData | Copia de estudo de documentacao oficial | Paginacao local')
    canvas.drawRightString(A4[0]-44, 25, str(doc.page))


def main():
    data = ROOT / 'data'
    provenance = ROOT / 'sources'
    data.mkdir(parents=True, exist_ok=True)
    provenance.mkdir(parents=True, exist_ok=True)
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name='BodyDoc', fontName='Helvetica', fontSize=10,
                              leading=14, spaceAfter=7))
    styles.add(ParagraphStyle(name='CodeDoc', fontName='Courier', fontSize=7.5,
                              leading=10, spaceAfter=9))
    manifest = []
    for slug, title, version, url in SOURCES:
        raw = fetch(url)
        (provenance / f'{slug}.html').write_bytes(raw)
        soup = BeautifulSoup(raw, 'html.parser')
        article = soup.select_one('div.body') if 'airflow.apache.org' in url else soup.select_one('article')
        if article is None:
            raise ValueError('Estrutura de documentacao alterada: ' + url)
        for junk in article.select('script, style, nav, .headerlink, button'):
            junk.decompose()
        story = [Paragraph(escape(title), styles['Title']),
                 Paragraph(escape(version), styles['Heading2']),
                 Paragraph('Origem: '+escape(url), styles['BodyDoc']),
                 Paragraph('Copia de estudo exportada em 21/09/2026. Texto original em ingles; '
                           'formatacao e paginacao locais. Imagens e navegacao omitidas; consulte '
                           'a origem para diagramas. Apache License 2.0; creditos em sources/.', styles['BodyDoc']),
                 Spacer(1, 12)]
        for tag in article.find_all(['h1','h2','h3','h4','p','li','pre','tr']):
            # Nao repetir paragrafos/listas contidos em um bloco ja capturado.
            if tag.find_parent(['pre','tr']):
                continue
            if tag.name == 'li' and tag.find(['p','pre','h1','h2','h3','h4','li']):
                continue
            text = tag.get_text(' ', strip=True) if tag.name != 'pre' else tag.get_text()
            text = text.replace('\u00b6','').replace('\u2011','-')
            if not text:
                continue
            if tag.name == 'pre':
                lines = []
                for line in text.expandtabs(4).splitlines():
                    lines.extend(textwrap.wrap(line, width=105, replace_whitespace=False,
                                               drop_whitespace=False) or [''])
                # Linhas longas quebradas apenas para impressao; original HTML preservado.
                story.append(Preformatted('\n'.join(lines), styles['CodeDoc']))
            elif tag.name.startswith('h'):
                story.append(Paragraph(escape(text), styles['Heading2' if tag.name in ('h1','h2') else 'Heading3']))
            else:
                story.append(Paragraph(escape(text), styles['BodyDoc']))
        target = data / f'{slug}.pdf'
        SimpleDocTemplate(str(target), pagesize=A4, rightMargin=44, leftMargin=44,
                          topMargin=42, bottomMargin=44, title=title,
                          author=version).build(story, onFirstPage=footer, onLaterPages=footer)
        pages = len(PdfReader(target).pages)
        manifest.append({'file': target.name, 'title': title, 'version': version, 'url': url,
                         'retrieved_at': datetime.now(timezone.utc).isoformat(), 'pages': pages,
                         'sha256': hashlib.sha256(target.read_bytes()).hexdigest(),
                         'source_sha256': hashlib.sha256(raw).hexdigest(),
                         'license': 'Apache-2.0', 'local_export': True})
        print(f'{target.name}: {pages} paginas')
    for name, url in [
        ('airflow-LICENSE.txt', 'https://raw.githubusercontent.com/apache/airflow/3.3.2/LICENSE'),
        ('airflow-NOTICE.txt', 'https://raw.githubusercontent.com/apache/airflow/3.3.2/NOTICE'),
        ('docker-LICENSE.txt', 'https://raw.githubusercontent.com/docker/docs/main/LICENSE'),
    ]:
        (provenance / name).write_bytes(fetch(url))
    (provenance / 'manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding='utf-8')
    print('Total:', sum(item['pages'] for item in manifest))


if __name__ == '__main__':
    main()
