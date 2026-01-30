import datetime
import os
import re
import subprocess
import tomllib
from collections import defaultdict
from functools import lru_cache
from pathlib import Path
from typing import Any

from lxml import etree
from rich import print as rich_print
from rich.panel import Panel

from erddap_docker.errors import DatasetNotInRepoError, RepoNotFoundError

ERDDAP_SERVICE = "erddap"
ERDDAP_REPO_ENV_VAR = "ERDDAP_REPO_DIR"
ERDDAP_CONTAINER_MANAGER_ENV_VAR = "ERDDAP_CONTAINER_MANAGER"
ERDDAP_CONTAINER_COMPOSER_ENV_VAR = "ERDDAP_CONTAINER_COMPOSER"


@lru_cache(maxsize=32)
def get_project_root(explicit_root: Path | None = None, env_var: str | None = None):
    if explicit_root:
        if not explicit_root.is_dir():
            raise RepoNotFoundError(
                f"Explicit repo path given ('{explicit_root}') "
                f"but is not an existing directory."
            )
        return explicit_root

    if root_from_env := _get_repo_root_from_env(env_var):
        return root_from_env

    if root_from_cwd := _locate_repo_root_from_cwd():
        return root_from_cwd

    root_from_default_location = Path("/srv/erddap")
    if root_from_default_location.is_dir():
        return root_from_default_location

    raise RepoNotFoundError("Could not locate project root.")


def _get_repo_root_from_env(env_var: str | None) -> Path | None:
    if env_value := os.environ.get(env_var or ERDDAP_REPO_ENV_VAR):
        root_from_env = Path(env_value)
        if not root_from_env.is_dir():
            raise RepoNotFoundError(
                f"Repo path specified in enviroment variables ('{root_from_env}') "
                f"but is not an existing directory."
            )
        return root_from_env
    return None


def _locate_repo_root_from_cwd() -> Path | None:
    cwd = Path.cwd().resolve()
    for directory in (cwd, *cwd.parents):
        potential_project_file = directory / "python" / "pyproject.toml"
        if potential_project_file.exists():
            with potential_project_file.open("rb") as project_file:
                project_metadata = tomllib.load(project_file)
            if project_metadata.get("project", {}).get("name", "") == "erddap-docker":
                return directory
    return None


def run_command(
    command: list[str], capture: bool = False
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        check=True,
        text=True,
        stdout=subprocess.PIPE if capture else None,
        stderr=subprocess.PIPE if capture else None,
    )


def run_command_in_service_container(
    service: str, command: list[str], capture: bool = False
) -> str:
    repo_root = get_project_root()
    compose_file = repo_root / "docker" / "docker-compose.yml"
    container_composer = os.environ.get(
        ERDDAP_CONTAINER_COMPOSER_ENV_VAR, "docker-compose"
    )
    process = run_command(
        [container_composer, "-f", str(compose_file), "exec", service, *command],
        capture=capture,
    )
    return process.stdout or ""


def test_dataset(dataset_id: str):
    podman_command = [
        "bash",
        "-c",
        f"cd webapps/erddap/WEB-INF/ && bash DasDds.sh {dataset_id}",
    ]

    message = (
        f"Running DasDds.sh on dataset '{dataset_id}' "
        f"inside containered service '{ERDDAP_SERVICE}'..."
    )

    print_banner(message)
    run_command_in_service_container(ERDDAP_SERVICE, podman_command)


def print_banner(message: str):
    rich_print(
        "\n",
        Panel(
            message,
            title="erddapcli",
            padding=(1, 2),
            width=100,
            border_style="bold cyan",
            style="on grey23",
        ),
        "\n",
    )


def generate_dataset_xml(
    target_directory: Path, file_pattern: str, dataset_type: str, verbose: bool = False
) -> str:
    repo_root = get_project_root()
    data_dir = repo_root / "data"
    if data_dir not in (target_directory, *target_directory.parents):
        raise DatasetNotInRepoError("Dataset not in ERDDAP data directory.")

    container_manager = os.environ.get(ERDDAP_CONTAINER_MANAGER_ENV_VAR, "docker")
    flag_key = f"{datetime.datetime.now().timestamp():.0f}"
    default_input = ['""'] * 18
    podman_command = [
        container_manager,
        "run",
        "--rm",
        "-v",
        f"{target_directory.absolute()}:/data/data_dir",
        "--workdir",
        "/usr/local/tomcat/webapps/erddap/WEB-INF",
        "-e",
        f"ERDDAP_flagKeyKey={flag_key}",
        "docker.io/axiom/docker-erddap:v2.28.1",
        "bash",
        "./GenerateDatasetsXml.sh",
        dataset_type,
        "/data/data_dir",
        file_pattern,
        *default_input,
    ]

    print_banner("Running GenerateDatasetsXml.sh inside separate container.")
    try:
        process = run_command(podman_command, capture=True)
    except subprocess.CalledProcessError as exc:
        if exc.stderr:
            print(exc.stderr)
        if exc.stdout:
            print(exc.stdout)
        raise
    if process.stderr:
        print(process.stderr)

    captured_output = process.stdout

    match = re.search(
        r"(?s)<dataset\b[^>]*>.*?</dataset>",
        captured_output,
    )

    if not match and verbose:
        print(captured_output)

    return match.group(0) if match else ""


def request_update_of_dataset(dataset_id: str):
    print(f"Requesting reload of dataset '{dataset_id}'.")
    run_command_in_service_container(
        ERDDAP_SERVICE, ["touch", f"/erddapData/hardFlag/{dataset_id}"]
    )


def build_xml_and_trigger_update():
    repo_root = get_project_root()
    datasets_d = repo_root / "docker" / "datasets.d"

    run_datasets_d_script()
    for dataset in datasets_d.glob("*.xml"):
        dataset_id = etree.parse(dataset).getroot().get("datasetID")
        request_update_of_dataset(dataset_id)


def run_datasets_d_script():
    run_command_in_service_container(ERDDAP_SERVICE, ["bash", "/init.d/50-datasets.d.sh"])


def get_dataset_info() -> defaultdict[Any, dict]:
    found_datasets = defaultdict(dict)
    repo_root = get_project_root()

    explicit_active_state = {"true": "active", "false": "deactivated"}

    datasets_d = repo_root / "docker" / "datasets.d"
    for datasets_d_path in datasets_d.glob("*.xml"):
        for dataset in etree.parse(datasets_d_path).xpath("/dataset"):
            found_datasets[dataset.get("datasetID")]["datasets.d"] = (
                explicit_active_state.get(dataset.get("active"), "-")
            )

    datasets_xml = repo_root / "docker" / "content" / "datasets.xml"
    for dataset in etree.parse(datasets_xml).xpath("//dataset"):
        found_datasets[dataset.get("datasetID")]["datasets.xml"] = (
            explicit_active_state.get(dataset.get("active"), "-")
        )
    return found_datasets


def activate_dataset(dataset_id: str):
    repo_root = get_project_root()
    datasets_d = repo_root / "docker" / "datasets.d"

    for datasets_d_path in datasets_d.glob("*.xml"):
        tree = etree.parse(datasets_d_path)
        dataset = tree.xpath(f"/dataset[@datasetID='{dataset_id}' and @active='false']")
        if dataset:
            elem = dataset[0]
            elem.set("active", "true")

            tree.write(
                datasets_d_path,
                encoding="utf-8",
                xml_declaration=True,
                pretty_print=True,
            )
            build_xml_and_trigger_update()
            break
    else:
        print(f"There is no deactivated dataset with datasetID '{dataset_id}'.")


def deactivate_dataset(dataset_id: str):
    repo_root = get_project_root()
    datasets_d = repo_root / "docker" / "datasets.d"

    for datasets_d_path in datasets_d.glob("*.xml"):
        tree = etree.parse(datasets_d_path)
        dataset = tree.xpath(f"/dataset[@datasetID='{dataset_id}' and @active='true']")
        if dataset:
            elem = dataset[0]
            elem.set("active", "false")

            tree.write(
                datasets_d_path,
                encoding="utf-8",
                xml_declaration=True,
                pretty_print=True,
            )
            build_xml_and_trigger_update()
            break
    else:
        print(f"There is no active dataset with datasetID '{dataset_id}'.")


def relative_data_path(dataset_directory: Path):
    repo_root = get_project_root()
    data_directory = repo_root / "data"
    return Path("/data") / dataset_directory.absolute().relative_to(data_directory)
