from pyeodh.types import Link


def test_link_from_dict() -> None:
    data = {
        "rel": "self",
        "href": "https://example.com",
        "title": "Example",
        "type": "application/json",
    }

    link = Link.from_dict(data)

    assert link.rel == data["rel"]
    assert link.href == data["href"]
    assert link.title == data["title"]
    assert link.media_type == data["type"]


def test_get_link() -> None:
    links = [
        Link(rel="self", href="https://example.com"),
        Link(rel="next", href="https://example.com/next"),
        Link(rel="prev", href="https://example.com/prev"),
    ]

    assert Link.get_link(links, "self") == links[0]
    assert Link.get_link(links, "next") == links[1]
    assert Link.get_link(links, "prev") == links[2]
    assert Link.get_link(links, "nonexistent") is None
