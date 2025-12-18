from __future__ import annotations

import os
import click
from local_document_search.config import load_environment
from local_document_search.config import Config
from local_document_search.services.provider_factory import build_conversion_service


@click.group()
def cli() -> None:
    """Local Document Search CLI."""


@cli.command("convert-file")
@click.argument("file_path", type=click.Path(exists=True, dir_okay=False, readable=True))
@click.option("--file-type", "file_type", "-t", help="File extension (without dot). Defaults to path suffix.")
@click.option("--output", "output", "-o", type=click.Path(dir_okay=False, writable=True), help="Optional output file to write markdown.")
def convert_file(file_path: str, file_type: str | None, output: str | None) -> None:
    """Convert a single file to Markdown using the conversion service."""
    load_environment()
    service = build_conversion_service()
    result = service.convert(file_path, file_type)

    if not result.success:
        click.secho(f"[error] {result.error}", fg="red", err=True)
        raise SystemExit(1)

    if output:
        with open(output, "w", encoding="utf-8") as f:
            f.write(result.content or "")
        click.secho(f"[ok] written -> {os.path.abspath(output)}", fg="green")
    else:
        click.echo(result.content or "")


@cli.command("convert-dir")
@click.argument("source_dir", type=click.Path(exists=True, file_okay=False, readable=True))
@click.option("--output-dir", "output_dir", "-o", required=True, type=click.Path(file_okay=False, writable=True), help="Directory to write converted Markdown files (structure is preserved).")
@click.option("--extensions", "exts", "-e", help="Comma-separated list of file extensions to include (default: Config.SUPPORTED_FILE_TYPES).")
@click.option("--recursive/--no-recursive", default=True, help="Recurse into subdirectories (default: true).")
def convert_dir(source_dir: str, output_dir: str, exts: str | None, recursive: bool) -> None:
    """Convert a directory of files to Markdown, writing .md files to OUTPUT_DIR."""
    load_environment()
    service = build_conversion_service()

    include_exts = None
    if exts:
        include_exts = [x.strip().lower().lstrip('.') for x in exts.split(',') if x.strip()]
    else:
        include_exts = [ext.lower() for ext in Config.SUPPORTED_FILE_TYPES]

    total = success = failed = 0
    for root, dirs, files in os.walk(source_dir):
        if not recursive:
            # clear dirs to prevent deeper traversal
            dirs[:] = []
        for fname in files:
            ext = os.path.splitext(fname)[1].lstrip('.').lower()
            if ext not in include_exts:
                continue
            total += 1
            src_path = os.path.join(root, fname)
            rel_path = os.path.relpath(src_path, source_dir)
            rel_no_ext = os.path.splitext(rel_path)[0]
            out_path = os.path.join(output_dir, rel_no_ext + ".md")
            os.makedirs(os.path.dirname(out_path), exist_ok=True)

            result = service.convert(src_path, ext)
            if not result.success:
                failed += 1
                click.secho(f"[fail] {src_path} :: {result.error}", fg="red", err=True)
                continue
            success += 1
            with open(out_path, "w", encoding="utf-8") as f:
                f.write(result.content or "")
            click.secho(f"[ok] {src_path} -> {out_path}", fg="green")

    click.echo(f"Done. total={total} success={success} failed={failed}")


if __name__ == "__main__":
    cli()
