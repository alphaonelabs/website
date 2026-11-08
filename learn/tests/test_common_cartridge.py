"""Adversarial tests for the Common Cartridge manifest parser."""

import io
import re
import zipfile

import pytest

from src.common_cartridge import (
    ArchiveLimitError,
    CartridgeError,
    InvalidArchiveError,
    InvalidManifestError,
    InvalidXmlError,
    MissingLocalResourceError,
    MissingManifestError,
    UnresolvedDependencyError,
    UnsafePathError,
    _normalize_archive_path,
    parse_common_cartridge,
)


NS = "http://www.imsglobal.org/xsd/imscp_v1p1"


def _manifest(
    *,
    prefix="",
    organizations="",
    resources="",
    identifier="manifest-1",
    namespace=NS,
):
    p = f"{prefix}:" if prefix else ""
    xmlns = f' xmlns:{prefix}="{namespace}"' if prefix else f' xmlns="{namespace}"'
    if prefix:
        def qualify(fragment):
            for name in (
                "organization",
                "title",
                "item",
                "resource",
                "dependency",
                "file",
            ):
                fragment = re.sub(
                    rf"(<\/?){name}(?=[\s>/])",
                    rf"\1{prefix}:{name}",
                    fragment,
                )
            return fragment

        organizations = qualify(organizations)
        resources = qualify(resources)
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<{p}manifest identifier="{identifier}"{xmlns}>
  <{p}organizations>{organizations}</{p}organizations>
  <{p}resources>{resources}</{p}resources>
</{p}manifest>""".encode()


def _organization(items="", identifier="org-1", title="Course"):
    return (
        f'<organization identifier="{identifier}"><title>{title}</title>'
        f"{items}</organization>"
    )


def _item(identifier="item-1", resource="resource-1", children=""):
    return (
        f'<item identifier="{identifier}" identifierref="{resource}">'
        f"<title>{identifier} title</title>{children}</item>"
    )


def _resource(
    identifier="resource-1",
    resource_type="webcontent",
    href="web/page.html",
    extra="",
):
    href_attr = f' href="{href}"' if href is not None else ""
    return f'<resource identifier="{identifier}" type="{resource_type}"{href_attr}>{extra}</resource>'


def _package(entries):
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as package:
        for name, content in entries.items():
            package.writestr(name, content)
    return buffer.getvalue()


def _valid_package(manifest=None, extra_entries=None):
    manifest = manifest or _manifest(
        organizations=_organization(_item()),
        resources=_resource(),
    )
    entries = {"imsmanifest.xml": manifest, "web/page.html": b"<h1>Course</h1>"}
    entries.update(extra_entries or {})
    return _package(entries)


def _error(category, archive, **kwargs):
    with pytest.raises(CartridgeError) as raised:
        parse_common_cartridge(archive, **kwargs)
    assert raised.value.category == category
    return raised.value


def test_parses_manifest_with_nested_items_and_stable_order():
    manifest = _manifest(
        organizations=_organization(
            _item(
                "item-1",
                children=_item("item-1-child", resource="resource-2"),
            )
        )
        + _organization(identifier="org-2", title="Second course"),
        resources=(
            _resource(extra='<dependency identifierref="resource-2"/>')
            + _resource("resource-2", href="web/second.html")
        ),
    )

    result = parse_common_cartridge(
        _valid_package(manifest, {"web/second.html": b"second"})
    )

    assert result["identifier"] == "manifest-1"
    assert result["namespace"] == NS
    assert [org["identifier"] for org in result["organizations"]] == ["org-1", "org-2"]
    assert result["organizations"][0]["items"][0]["items"][0]["identifier"] == (
        "item-1-child"
    )
    assert result["resources"][0]["dependencies"] == ["resource-2"]
    assert result["unsupported_resource_types"] == []


def test_namespace_prefix_does_not_change_parsed_result():
    prefixed = _manifest(
        prefix="cc",
        organizations=_organization(_item()),
        resources=_resource(),
    )

    result = parse_common_cartridge(_valid_package(prefixed))

    assert result["organizations"][0]["items"][0]["title"] == "item-1 title"
    assert result["resources"][0]["href_kind"] == "local"


def test_accepts_web_link_qti_and_external_uri_metadata():
    manifest = _manifest(
        organizations=_organization(_item("item-1", "link")),
        resources=(
            _resource(
                "link",
                "imswl_xmlv1p1",
                "https://example.test/course",
            )
            + _resource("qti", "imsqti_xmlv1p2", "quiz/assessment.xml")
        ),
    )

    result = parse_common_cartridge(
        _valid_package(manifest, {"quiz/assessment.xml": b"<assessment/>"})
    )

    assert result["resources"][0]["href_kind"] == "external"
    assert result["resources"][0]["local_path"] is None
    assert result["resources"][0]["href"] == "https://example.test/course"
    assert result["resources"][1]["type"] == "imsqti_xmlv1p2"


def test_percent_encoded_local_reference_is_normalized():
    manifest = _manifest(
        organizations=_organization(_item()),
        resources=_resource(href="web/course%20page.html"),
    )

    result = parse_common_cartridge(
        _valid_package(manifest, {"web/course page.html": b"page"})
    )

    assert result["resources"][0]["local_path"] == "web/course page.html"


def test_external_uri_is_preserved_and_not_fetched():
    manifest = _manifest(
        organizations=_organization(_item()),
        resources=_resource(href="https://example.test/resource.html"),
    )

    result = parse_common_cartridge(_valid_package(manifest))

    assert result["resources"][0]["href"] == "https://example.test/resource.html"
    assert result["resources"][0]["href_kind"] == "external"


def test_unsupported_resource_type_is_reported_without_reclassification():
    manifest = _manifest(
        organizations=_organization(_item()),
        resources=_resource("resource-1", "vendor_custom_type"),
    )

    result = parse_common_cartridge(_valid_package(manifest))

    assert result["resources"][0]["type"] == "vendor_custom_type"
    assert result["unsupported_resource_types"] == ["vendor_custom_type"]


def test_rejects_missing_manifest():
    _error("missing_manifest", _package({"web/page.html": b"page"}))


def test_rejects_nested_only_manifest():
    _error(
        "missing_manifest",
        _package({"course/imsmanifest.xml": _manifest(
            organizations=_organization(_item()), resources=_resource()
        )}),
    )


def test_rejects_duplicate_root_manifest():
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as package:
        package.writestr("imsmanifest.xml", b"first")
        package.writestr("imsmanifest.xml", b"second")
    _error("duplicate_manifest", buffer.getvalue())


def test_rejects_malformed_zip():
    _error("invalid_archive", b"not a zip")


def test_rejects_malformed_xml_and_invalid_root():
    _error(
        "invalid_xml",
        _package({"imsmanifest.xml": b"<manifest>", "web/page.html": b""}),
    )
    _error(
        "invalid_manifest",
        _package({"imsmanifest.xml": b"<root/>"}),
    )


@pytest.mark.parametrize(
    "xml",
    [
        b'<!DOCTYPE manifest [<!ENTITY xxe "blocked">]><manifest/>',
        b'<!DOCTYPE manifest SYSTEM "http://example.test/entity"><manifest/>',
    ],
)
def test_rejects_dtd_and_entity_declarations(xml):
    _error("invalid_xml", _package({"imsmanifest.xml": xml}))


def test_dtd_text_inside_comment_is_not_treated_as_a_declaration():
    _error(
        "invalid_manifest",
        _package({"imsmanifest.xml": b"<!-- <!DOCTYPE manifest> --><manifest/>"}),
    )


def test_rejects_missing_required_structure_and_attributes():
    _error(
        "invalid_manifest",
        _package({"imsmanifest.xml": _manifest(resources=_resource(href=None))}),
    )
    _error(
        "invalid_manifest",
        _package(
            {
                "imsmanifest.xml": _manifest(
                    organizations=_organization(_item()),
                    resources='<resource type="webcontent" href="web/page.html"/>',
                ),
                "web/page.html": b"",
            }
        ),
    )


def test_rejects_duplicate_identifiers_and_unresolved_references():
    duplicate = _manifest(
        organizations=_organization(_item("same")),
        resources=_resource("same"),
    )
    _error("invalid_manifest", _valid_package(duplicate))

    unresolved_item = _manifest(
        organizations=_organization(_item(resource="missing-resource")),
        resources=_resource(),
    )
    _error("invalid_manifest", _valid_package(unresolved_item))

    unresolved_dependency = _manifest(
        organizations=_organization(_item()),
        resources=_resource(extra='<dependency identifierref="missing"/>'),
    )
    _error("unresolved_dependency", _valid_package(unresolved_dependency))


def test_rejects_missing_local_resource():
    manifest = _manifest(
        organizations=_organization(_item()),
        resources=_resource(href="web/missing.html"),
    )
    error = _error("missing_local_resource", _valid_package(manifest))
    assert "resource-1" in str(error)


@pytest.mark.parametrize(
    "name",
    [
        "/absolute.txt",
        "../outside.txt",
        r"..\outside.txt",
        r"folder\..\outside.txt",
        r"C:\outside.txt",
        r"\\server\outside.txt",
    ],
)
def test_rejects_unsafe_archive_paths(name):
    _error("unsafe_path", _package({"imsmanifest.xml": _manifest(), name: b"x"}))


def test_rejects_nul_in_archive_path():
    with pytest.raises(UnsafePathError) as raised:
        _normalize_archive_path("bad\x00name.txt")
    assert raised.value.category == "unsafe_path"


@pytest.mark.parametrize(
    "href",
    [
        "../outside.html",
        r"..\outside.html",
        "%2e%2e/outside.html",
        "%252e%252e/outside.html",
        "data:text/html,blocked",
        "file:///etc/passwd",
        "javascript:alert(1)",
    ],
)
def test_rejects_unsafe_or_untrusted_references(href):
    manifest = _manifest(
        organizations=_organization(_item()),
        resources=_resource(href=href),
    )
    category = "unsupported_external_reference" if ":" in href and not href.startswith("..") else "unsafe_path"
    _error(category, _valid_package(manifest))


def test_rejects_duplicate_normalized_paths():
    _error(
        "unsafe_path",
        _package(
            {
                "imsmanifest.xml": _manifest(),
                "web//page.html": b"one",
                "web/page.html": b"two",
            }
        ),
    )


def test_rejects_archive_limits_before_manifest_processing():
    package = _valid_package()
    _error("archive_limit_exceeded", package, max_archive_bytes=len(package) - 1)
    _error("archive_limit_exceeded", package, max_entries=1)
    _error("archive_limit_exceeded", package, max_uncompressed_bytes=1)
    _error("archive_limit_exceeded", package, max_entry_bytes=1)


def test_accepts_binary_stream_and_never_extracts_to_filesystem(monkeypatch):
    package = _valid_package()
    called = False

    def fail_extractall(*_args, **_kwargs):
        nonlocal called
        called = True
        raise AssertionError("parser must not extract files")

    monkeypatch.setattr(zipfile.ZipFile, "extractall", fail_extractall)
    result = parse_common_cartridge(io.BytesIO(package))

    assert result["identifier"] == "manifest-1"
    assert called is False


def test_rejects_non_binary_input_and_invalid_limits():
    with pytest.raises(TypeError):
        parse_common_cartridge("not bytes")
    with pytest.raises(ValueError):
        parse_common_cartridge(_valid_package(), max_entries=0)
