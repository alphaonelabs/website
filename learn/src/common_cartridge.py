"""Secure parsing and validation for Common Cartridge manifest packages.

This module intentionally stops at manifest inspection.  It does not import
activities, materials, files, or QTI content into Learn.
"""

from __future__ import annotations

import io
import posixpath
import re
import stat
import zipfile
from typing import Any, BinaryIO, TypedDict
from urllib.parse import unquote, urlsplit
from xml.etree import ElementTree
from xml.parsers import expat


DEFAULT_MAX_ARCHIVE_BYTES = 50 * 1024 * 1024
DEFAULT_MAX_ENTRIES = 10_000
DEFAULT_MAX_UNCOMPRESSED_BYTES = 250 * 1024 * 1024
DEFAULT_MAX_ENTRY_BYTES = 100 * 1024 * 1024

_MANIFEST_NAME = "imsmanifest.xml"
_SUPPORTED_RESOURCE_TYPES = {
    "webcontent",
    "imswl_xmlv1p0",
    "imswl_xmlv1p1",
    "imswl_xmlv1p2",
    "imswl_xmlv1p3",
    "imswl_xmlv1p4",
    "imsqti_xmlv1p1",
    "imsqti_xmlv1p2",
    "imsqti_xmlv1p2/imscc_xmlv1p1",
    "imsqti_xmlv2p0",
}
_UNSAFE_SCHEMES = {"data", "file", "javascript", "vbscript"}
_DRIVE_PATH = re.compile(r"^[A-Za-z]:($|/)")
_SUPPORTED_MANIFEST_NAMESPACE = re.compile(
    r"^https?://www\.imsglobal\.org/xsd/"
    r"(?:imsccv1p[0-4]/)?imscp_v1p[0-4]$"
)


class CartridgeError(ValueError):
    """Base class for all parser validation failures."""

    category = "invalid_cartridge"

    def __init__(self, message: str):
        super().__init__(message)
        self.message = message

    def __str__(self) -> str:
        return self.message


class InvalidArchiveError(CartridgeError):
    category = "invalid_archive"


class ArchiveLimitError(CartridgeError):
    category = "archive_limit_exceeded"


class UnsafePathError(CartridgeError):
    category = "unsafe_path"


class MissingManifestError(CartridgeError):
    category = "missing_manifest"


class DuplicateManifestError(CartridgeError):
    category = "duplicate_manifest"


class InvalidXmlError(CartridgeError):
    category = "invalid_xml"


class InvalidManifestError(CartridgeError):
    category = "invalid_manifest"


class MissingLocalResourceError(CartridgeError):
    category = "missing_local_resource"


class UnresolvedDependencyError(CartridgeError):
    category = "unresolved_dependency"


class UnsupportedExternalReferenceError(CartridgeError):
    category = "unsupported_external_reference"


class ItemDict(TypedDict):
    identifier: str
    title: str
    identifierref: str | None
    items: list["ItemDict"]


class OrganizationDict(TypedDict):
    identifier: str
    title: str
    items: list[ItemDict]


class ResourceDict(TypedDict):
    identifier: str
    type: str
    href: str | None
    href_kind: str | None
    local_path: str | None
    dependencies: list[str]


class CartridgeManifestDict(TypedDict):
    identifier: str
    namespace: str
    organizations: list[OrganizationDict]
    resources: list[ResourceDict]
    unsupported_resource_types: list[str]


def parse_common_cartridge(
    archive: bytes | bytearray | memoryview | BinaryIO,
    *,
    max_archive_bytes: int = DEFAULT_MAX_ARCHIVE_BYTES,
    max_entries: int = DEFAULT_MAX_ENTRIES,
    max_uncompressed_bytes: int = DEFAULT_MAX_UNCOMPRESSED_BYTES,
    max_entry_bytes: int = DEFAULT_MAX_ENTRY_BYTES,
) -> CartridgeManifestDict:
    """Parse and validate a Common Cartridge archive without extracting it.

    Local references are normalized and checked against the archive.  HTTP(S)
    references are preserved as external metadata and are never fetched.
    Supported resource types are returned unchanged; unsupported types are
    reported in ``unsupported_resource_types``.
    """
    _validate_limits(
        max_archive_bytes,
        max_entries,
        max_uncompressed_bytes,
        max_entry_bytes,
    )
    data = _read_archive(archive, max_archive_bytes)

    try:
        package = zipfile.ZipFile(io.BytesIO(data))
    except (OSError, ValueError, zipfile.BadZipFile) as exc:
        raise InvalidArchiveError("The package is not a valid ZIP archive") from exc

    with package:
        infos = package.infolist()
        if len(infos) > max_entries:
            raise ArchiveLimitError("The archive contains too many entries")

        paths: dict[str, zipfile.ZipInfo] = {}
        total_size = 0
        for info in infos:
            normalized = _normalize_archive_path(info.filename)
            if normalized in paths:
                if normalized == _MANIFEST_NAME:
                    raise DuplicateManifestError(
                        "The archive contains duplicate root-level imsmanifest.xml entries"
                    )
                raise UnsafePathError(
                    f"Duplicate normalized archive path: {normalized}"
                )
            paths[normalized] = info

            if info.flag_bits & 0x1:
                raise InvalidArchiveError("Encrypted ZIP entries are not supported")
            if _is_symlink(info):
                raise UnsafePathError("Symbolic-link ZIP entries are not supported")
            if info.file_size < 0 or info.compress_size < 0:
                raise InvalidArchiveError("ZIP entry sizes are invalid")
            if info.file_size > max_entry_bytes:
                raise ArchiveLimitError("A ZIP entry exceeds the size limit")
            total_size += info.file_size
            if total_size > max_uncompressed_bytes:
                raise ArchiveLimitError(
                    "The archive exceeds the uncompressed size limit"
                )

        manifest_info = paths.get(_MANIFEST_NAME)
        if manifest_info is None:
            raise MissingManifestError(
                "The archive must contain root-level imsmanifest.xml"
            )
        try:
            manifest_bytes = package.read(manifest_info)
        except (OSError, RuntimeError, NotImplementedError, zipfile.BadZipFile) as exc:
            raise InvalidArchiveError("The manifest entry could not be read") from exc

    root = _parse_manifest_xml(manifest_bytes)
    manifest_namespace = _namespace(root.tag)
    if _local_name(root.tag) != "manifest" or not _is_supported_namespace(
        manifest_namespace
    ):
        raise InvalidManifestError("The manifest root element or namespace is invalid")

    manifest_id = _required_attribute(root, "identifier", "manifest")
    organizations_node = _required_child(root, "organizations", manifest_namespace)
    resources_node = _required_child(root, "resources", manifest_namespace)

    resources, resource_ids, unsupported_types = _parse_resources(
        resources_node, paths, manifest_namespace
    )
    organizations, organization_ids, item_ids, item_refs = _parse_organizations(
        organizations_node, manifest_namespace
    )

    duplicate_ids = (
        organization_ids & item_ids
        | organization_ids & resource_ids
        | item_ids & resource_ids
    )
    if duplicate_ids:
        raise InvalidManifestError(
            "Duplicate manifest identifier: " + sorted(duplicate_ids)[0]
        )

    unresolved_items = sorted(item_refs - resource_ids)
    if unresolved_items:
        raise InvalidManifestError(
            "Item references an unknown resource: " + unresolved_items[0]
        )

    declared_dependencies = {
        dependency
        for resource in resources
        for dependency in resource["dependencies"]
    }
    unresolved_dependencies = sorted(declared_dependencies - resource_ids)
    if unresolved_dependencies:
        raise UnresolvedDependencyError(
            "Resource dependency is unresolved: " + unresolved_dependencies[0]
        )

    return {
        "identifier": manifest_id,
        "namespace": manifest_namespace,
        "organizations": organizations,
        "resources": resources,
        "unsupported_resource_types": sorted(set(unsupported_types)),
    }


def _validate_limits(*limits: int) -> None:
    if any(isinstance(value, bool) or not isinstance(value, int) or value <= 0 for value in limits):
        raise ValueError("Archive limits must be positive integers")


def _read_archive(
    archive: bytes | bytearray | memoryview | BinaryIO, max_bytes: int
) -> bytes:
    if isinstance(archive, (bytes, bytearray, memoryview)):
        data = bytes(archive)
        if len(data) > max_bytes:
            raise ArchiveLimitError("The compressed archive exceeds the size limit")
        return data
    if not hasattr(archive, "read"):
        raise TypeError("archive must be bytes or a binary file-like object")

    chunks: list[bytes] = []
    size = 0
    while True:
        chunk = archive.read(min(1024 * 1024, max_bytes - size + 1))
        if not isinstance(chunk, (bytes, bytearray, memoryview)):
            raise TypeError("The archive stream must return bytes")
        if not chunk:
            break
        chunk_bytes = bytes(chunk)
        size += len(chunk_bytes)
        if size > max_bytes:
            raise ArchiveLimitError("The compressed archive exceeds the size limit")
        chunks.append(chunk_bytes)
    return b"".join(chunks)


def _is_symlink(info: zipfile.ZipInfo) -> bool:
    mode = (info.external_attr >> 16) & 0xFFFF
    return stat.S_ISLNK(mode)


def _normalize_archive_path(name: str) -> str:
    if "\x00" in name:
        raise UnsafePathError("ZIP entry names must not contain NUL bytes")
    normalized = name.replace("\\", "/")
    if normalized.startswith("/") or normalized.startswith("//") or _DRIVE_PATH.match(normalized):
        raise UnsafePathError("ZIP entry paths must be relative")
    parts = []
    for part in normalized.split("/"):
        if part in ("", "."):
            continue
        if part == "..":
            raise UnsafePathError("ZIP entry paths must not contain '..'")
        parts.append(part)
    result = "/".join(parts)
    if not result and not name.endswith(("/", "\\")):
        raise UnsafePathError("ZIP entry path is empty")
    return result


def _parse_manifest_xml(data: bytes) -> ElementTree.Element:
    parser = expat.ParserCreate()
    parser.StartDoctypeDeclHandler = _reject_xml_feature
    parser.EntityDeclHandler = _reject_xml_feature
    parser.ExternalEntityRefHandler = _reject_xml_feature
    try:
        parser.Parse(data, True)
        return ElementTree.fromstring(data)
    except CartridgeError:
        raise
    except (ElementTree.ParseError, expat.ExpatError, ValueError, TypeError) as exc:
        raise InvalidXmlError("The manifest XML is invalid") from exc


def _reject_xml_feature(*_args: Any) -> None:
    raise InvalidXmlError("DTD and entity declarations are not supported")


def _local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1] if "}" in tag else tag


def _namespace(tag: str) -> str:
    return tag[1:].split("}", 1)[0] if tag.startswith("{") else ""


def _is_supported_namespace(namespace: str) -> bool:
    return bool(_SUPPORTED_MANIFEST_NAMESPACE.fullmatch(namespace))


def _children(
    parent: ElementTree.Element, name: str, namespace: str | None = None
) -> list[ElementTree.Element]:
    return [
        child
        for child in list(parent)
        if _local_name(child.tag) == name
        and (namespace is None or _namespace(child.tag) == namespace)
    ]


def _required_child(
    parent: ElementTree.Element, name: str, namespace: str
) -> ElementTree.Element:
    matches = _children(parent, name, namespace)
    if len(matches) != 1:
        raise InvalidManifestError(
            f"Manifest must contain exactly one {name} element"
        )
    return matches[0]


def _required_attribute(
    element: ElementTree.Element, name: str, context: str
) -> str:
    value = (element.attrib.get(name) or "").strip()
    if not value:
        raise InvalidManifestError(f"{context} requires an {name} attribute")
    return value


def _text(element: ElementTree.Element | None) -> str:
    return "".join(element.itertext()).strip() if element is not None else ""


def _parse_organizations(
    organizations_node: ElementTree.Element,
    namespace: str,
) -> tuple[list[OrganizationDict], set[str], set[str], set[str]]:
    organizations = []
    organization_ids: set[str] = set()
    item_ids: set[str] = set()
    item_refs: set[str] = set()
    organization_nodes = _children(organizations_node, "organization", namespace)
    if not organization_nodes:
        raise InvalidManifestError("Manifest must contain an organization")

    for node in organization_nodes:
        identifier = _required_attribute(node, "identifier", "organization")
        if identifier in organization_ids:
            raise InvalidManifestError(f"Duplicate manifest identifier: {identifier}")
        organization_ids.add(identifier)
        organizations.append(
            {
                "identifier": identifier,
                "title": _text(next(iter(_children(node, "title", namespace)), None)),
                "items": _parse_items(node, item_ids, item_refs, namespace),
            }
        )
    return organizations, organization_ids, item_ids, item_refs


def _parse_items(
    parent: ElementTree.Element,
    item_ids: set[str],
    item_refs: set[str],
    namespace: str,
) -> list[ItemDict]:
    result = []
    for node in _children(parent, "item", namespace):
        identifier = _required_attribute(node, "identifier", "item")
        if identifier in item_ids:
            raise InvalidManifestError(f"Duplicate manifest identifier: {identifier}")
        item_ids.add(identifier)
        identifierref = (node.attrib.get("identifierref") or "").strip() or None
        if identifierref:
            item_refs.add(identifierref)
        result.append(
            {
                "identifier": identifier,
                "title": _text(next(iter(_children(node, "title", namespace)), None)),
                "identifierref": identifierref,
                "items": _parse_items(node, item_ids, item_refs, namespace),
            }
        )
    return result


def _parse_resources(
    resources_node: ElementTree.Element,
    paths: dict[str, zipfile.ZipInfo],
    namespace: str,
) -> tuple[list[ResourceDict], set[str], list[str]]:
    resources = []
    resource_ids: set[str] = set()
    unsupported_types = []
    for node in _children(resources_node, "resource", namespace):
        identifier = _required_attribute(node, "identifier", "resource")
        if identifier in resource_ids:
            raise InvalidManifestError(f"Duplicate resource identifier: {identifier}")
        resource_ids.add(identifier)
        resource_type = _required_attribute(node, "type", "resource")
        normalized_type = resource_type.lower()
        if normalized_type not in _SUPPORTED_RESOURCE_TYPES:
            unsupported_types.append(resource_type)

        href = (node.attrib.get("href") or "").strip() or None
        href_kind = None
        local_path = None
        if href:
            href_kind, local_path = _classify_reference(href)
            if href_kind == "local" and local_path not in paths:
                raise MissingLocalResourceError(
                    f"Resource {identifier} references a missing local file"
                )

        dependencies = []
        for dependency in _children(node, "dependency", namespace):
            dependencies.append(
                _required_attribute(dependency, "identifierref", "dependency")
            )

        for file_node in _children(node, "file", namespace):
            file_href = (file_node.attrib.get("href") or "").strip()
            if not file_href:
                raise InvalidManifestError("file requires an href attribute")
            file_kind, file_path = _classify_reference(file_href)
            if file_kind == "local" and file_path not in paths:
                raise MissingLocalResourceError(
                    f"Resource {identifier} references a missing local file"
                )

        resources.append(
            {
                "identifier": identifier,
                "type": resource_type,
                "href": href,
                "href_kind": href_kind,
                "local_path": local_path,
                "dependencies": dependencies,
            }
        )
    if not resources:
        raise InvalidManifestError("Manifest must contain a resource")
    return resources, resource_ids, unsupported_types


def _classify_reference(href: str) -> tuple[str, str | None]:
    if "\x00" in href:
        raise UnsafePathError("Resource references must not contain NUL bytes")
    parsed = urlsplit(href)
    if parsed.scheme or parsed.netloc:
        if parsed.scheme.lower() in _UNSAFE_SCHEMES:
            raise UnsupportedExternalReferenceError(
                "External resource scheme is not supported"
            )
        if parsed.scheme.lower() not in {"http", "https"} or not parsed.netloc:
            raise UnsupportedExternalReferenceError(
                "Only HTTP(S) external resource references are supported"
            )
        return "external", None

    decoded = parsed.path
    for _ in range(3):
        next_value = unquote(decoded)
        if next_value == decoded:
            break
        decoded = next_value
    return "local", _normalize_archive_path(decoded)
