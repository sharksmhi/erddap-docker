import json
import sys
from pathlib import Path

import rich_click as click
from rich.console import Console
from rich.table import Table
from rich.text import Text

from erddap_docker import erddap_container, erddap_xml
from erddap_docker.errors import DatasetNotInRepoError


@click.group()
def cli():
    """This application is used for:

    - Generating XML files from datasets
    - Compiling the main XML file from separate generated xml files
    - Activating and deactivating specific datasets"""
    pass


@cli.command(
    help="Generate dataset xml from data. "
         "Saved to datasets.d unless output dir given or if dry run."
)
@click.argument(
    "input_path",
    type=click.Path(exists=True, path_type=Path),
    help="File or directory path. If directory, you must also provide a file pattern.",
)
@click.option(
    "--file-pattern", type=str, help="File pattern when input_path is a directory."
)
@click.option("--datatype", type=str, default="EDDTableFromAsciiFiles")
@click.option(
    "-c",
    "--config",
    "config_path",
    type=click.Path(exists=True, path_type=Path),
    help="Config file for mapping the data.",
)
@click.option(
    "-o",
    "--output-dir",
    type=click.Path(exists=True, path_type=Path),
    help="Optional output directory if you want to save it outside of default location.",
)
@click.option("--dry-run", is_flag=True, help="Print the generated dataset.")
@click.option("-v", "--verbose", is_flag=True, help="More verbose output.")
def xml_from_data(
        input_path: Path,
        file_pattern: str,
        config_path: Path,
        output_dir: Path,
        dry_run: bool,
        datatype: str,
        verbose: bool,
):
    if input_path.is_dir() and not file_pattern:
        sys.exit("Input path is a directory. Please specify a file pattern.")
    elif input_path.is_file() and file_pattern:
        sys.exit("Input path is a file, a file pattern cannot be specified.")

    if input_path.is_file():
        target_directory = input_path.parent
        file_pattern = input_path.name
    else:
        target_directory = input_path

    try:
        dataset_xml = erddap_container.generate_dataset_xml(
            target_directory.absolute(), file_pattern, datatype, verbose=verbose
        )
    except DatasetNotInRepoError as e:
        sys.exit(str(e))

    if not dataset_xml:
        sys.exit("Dataset xml could not be generated.")

    if config_path:
        config = json.loads(config_path.read_text())
    else:
        config = {}

    dataset_xml = erddap_xml.update_xml(
        dataset_xml,
        erddap_container.relative_data_path(target_directory),
        file_pattern,
        config,
    )

    if dry_run:
        print(dataset_xml)
    else:
        if not output_dir:
            repo_root = erddap_container.get_project_root()
            output_dir = repo_root / "docker" / "datasets.d"
        output_path = output_dir / input_path.with_suffix(".xml").name
        output_path.write_text(dataset_xml)
        print(f"Wrote dataset xml to '{output_path}'.")


@cli.command(help="Generate datasets.xml from xml files in datasets.d.")
def build_datasets_xml():
    erddap_container.build_xml_and_trigger_update()


@cli.group(help="Actions on datasets.")
def datasets():
    pass


@datasets.command("list", help="List all datasets in datasets.d and datasets.xml.")
def list_datasets():
    datasets_table = Table(title="Datasets")

    datasets_table.add_column("datasetID", justify="left", style="white", no_wrap=True)
    datasets_table.add_column("datasets.d", justify="right", style="white", no_wrap=True)
    datasets_table.add_column(
        "datasets.xml", justify="right", style="white", no_wrap=True
    )

    dataset_info = erddap_container.get_dataset_info()

    active_state_to_color = {
        "active": "green",
        "deactivated": "red",
    }

    for dataset_id, info in dataset_info.items():
        if "datasets.d" in info:
            datasets_d_cell = Text(
                info["datasets.d"],
                style=active_state_to_color.get(info["datasets.d"], "white"),
            )
        else:
            datasets_d_cell = Text("-", style="white")

        if "datasets.xml" in info:
            datasets_xml_cell = Text(
                info["datasets.xml"],
                style=active_state_to_color.get(info["datasets.xml"], "white"),
            )
        else:
            datasets_xml_cell = Text("-", style="white")

        datasets_table.add_row(dataset_id, datasets_d_cell, datasets_xml_cell)

    console = Console()
    console.print(datasets_table)


@datasets.command("activate", help="Activate a dataset.")
@click.argument("dataset_id", help="Dataset do deactivate")
def activate(dataset_id: str):
    erddap_container.activate_dataset(dataset_id)


@datasets.command("deactivate", help="Deactivate a dataset.")
@click.argument("dataset_id", help="Dataset do deactivate")
def deactivate(dataset_id: str):
    erddap_container.deactivate_dataset(dataset_id)


@datasets.command("update", help="Trigger update of a dataset.")
@click.argument("dataset_id", help="Dataset do deactivate")
def update(dataset_id: str):
    erddap_container.request_update_of_dataset(dataset_id)


@datasets.command("test", help="Try to parse dataset metadata.")
@click.argument("dataset_id", help="Dataset do deactivate")
def test_dataset(dataset_id: str):
    erddap_container.test_dataset(dataset_id)


if __name__ == "__main__":
    cli()
