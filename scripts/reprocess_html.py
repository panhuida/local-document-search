import click
from flask import current_app
from run import create_app
from app.extensions import db
from app.models import Document, ConversionType
from app.services.converters import convert_to_markdown


@click.command()
@click.option('--only-missing', is_flag=True, help='只重新处理 conversion_type 不是 HTML_TO_MD 的 HTML/HTM 文档')
def reprocess_html(only_missing):
    app = create_app()
    with app.app_context():
        q = Document.query.filter(Document.file_type.in_(['html','htm']))
        if only_missing:
            q = q.filter(Document.conversion_type != ConversionType.HTML_TO_MD)
        docs = q.all()
        total = len(docs)
        print(f"Found {total} HTML docs to (re)process.")
        updated = 0
        for i, doc in enumerate(docs, start=1):
            result = convert_to_markdown(doc.file_path, doc.file_type)
            if not result.success:
                print(f"[{i}/{total}] FAIL {doc.file_path}: {result.error}")
                continue
            doc.markdown_content = result.content
            doc.conversion_type = result.conversion_type
            doc.status = 'completed'
            doc.error_message = None
            updated += 1
            if i % 20 == 0:
                db.session.commit()
                print(f"Committed batch up to {i}.")
        db.session.commit()
        print(f"Done. Updated {updated}/{total} docs.")


if __name__ == '__main__':
    reprocess_html()
