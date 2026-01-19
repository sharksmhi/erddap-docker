from pathlib import Path

from lxml import etree


def update_xml(
    dataset_xml: str, target_directory: Path, file_pattern: str, config: dict
) -> str:
    dataset = etree.fromstring(dataset_xml)
    _ensure_child(dataset, "fileDir").text = str(target_directory)
    _ensure_child(dataset, "fileNameRegex").text = file_pattern
    dataset.set("datasetID", target_directory.stem)
    _ensure_child(dataset, "recursive").text = "false"

    add_attrs = _ensure_child(dataset, "addAttributes")
    for tag in _ensure_children_with_attribute(add_attrs, "att", "name", "title"):
        tag.text = target_directory.name

    for tag in _ensure_children_with_attribute(add_attrs, "att", "name", "summary"):
        tag.text = f"Generated dataset for {target_directory.name}"

    if institution := config.get("dataset", {}).get("institution"):
        for tag in _ensure_children_with_attribute(
            add_attrs, "att", "name", "institution"
        ):
            tag.text = institution

    for tag in dataset.findall("dataVariable"):
        variable_name = tag.xpath("./sourceName[1]/text()")
        variable_name = variable_name[0] if variable_name else None

        add_attributes = tag.find("addAttributes")

        if variable_config := config.get("data_variables", {}).get(variable_name):
            for column in (
                "ioos_category",
                "long_name",
                "standard_name",
                "units",
                "flag_values",
                "flag_meanings",
            ):
                if value := variable_config.get(column):
                    _ensure_child(add_attributes, "att", column).text = value

    _reset_indentation(dataset)
    return etree.tostring(dataset, encoding="unicode", pretty_print=True)


def _reset_indentation(elem: etree._Element) -> None:
    if len(elem) and elem.text and not elem.text.strip():
        elem.text = None

    if elem.tail and not elem.tail.strip():
        elem.tail = None

    for child in elem:
        _reset_indentation(child)


def _ensure_child(
    parent: etree.Element, tag: str, attribute: str | None = None
) -> etree.Element:
    for child in parent.iterchildren(tag):
        if not attribute or child.get("name") == attribute:
            return child

    if not attribute:
        return etree.SubElement(parent, tag)
    else:
        return etree.SubElement(parent, tag, {"name": attribute})


def _ensure_children_with_attribute(
    parent: etree.Element, tag: str, attribute: str, value: str
) -> list[etree.Element]:
    if matches := [
        child for child in parent.findall(tag) if child.get(attribute) == value
    ]:
        return matches

    created = etree.SubElement(parent, tag)
    created.set(attribute, value)
    return [created]
