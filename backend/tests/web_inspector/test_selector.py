from mininode_api.web_inspector.models import LinkEvidence
from mininode_api.web_inspector.selector import (
    PageCandidate,
    candidate_identity,
    classify_page_candidates,
    select_pages,
)


def links(*values):
    return [LinkEvidence(url, text, "https://example.com/") for url, text in values]


def test_selection_order_filters_and_limit_are_deterministic():
    candidates = links(
        ("https://example.com/blog", "Blog"),
        ("https://example.com/news", "Noticias"),
        ("https://other.example/contact", "Contacto externo"),
        ("https://sub.example.com/contact", "Contacto subdominio"),
        ("https://example.com/file.pdf", "PDF"),
        ("https://example.com/contact", "Contáctanos"),
        ("https://example.com/privacy", "Política de privacidad"),
        ("https://example.com/register", "Registro"),
        ("https://example.com/newsletter", "Newsletter"),
        ("https://example.com/quote", "Cotización"),
        ("https://example.com/booking", "Reserva"),
        ("https://example.com/jobs", "Empleo y postulación"),
        ("https://example.com/register", "Duplicado"),
    )
    expected = [
        "https://example.com/", "https://example.com/privacy", "https://example.com/contact",
        "https://example.com/booking", "https://example.com/jobs",
    ]
    assert select_pages("https://example.com", candidates) == expected
    assert select_pages("https://example.com", reversed(candidates)) == expected
    assert len(select_pages("https://example.com", candidates)) == 5


def test_additional_signals_and_custom_limit():
    candidates = links(
        ("https://example.com/a", "Suscripción newsletter"),
        ("https://example.com/b", "Comprar checkout"),
    )
    assert select_pages("https://example.com", candidates, limit=2) == ["https://example.com/", "https://example.com/a"]


def test_classification_returns_all_relevant_candidates_without_final_limit():
    candidates = links(
        ("https://example.com/privacy", "Privacy"),
        ("https://example.com/contact", "Contacto"),
        ("https://example.com/register", "Registro"),
        ("https://example.com/quote", "Cotizar"),
        ("https://example.com/newsletter", "Newsletter"),
    )

    classified = classify_page_candidates("https://example.com", reversed(candidates))

    assert classified == [
        PageCandidate("https://example.com/contact", "contact", ("https://example.com/contact",)),
        PageCandidate("https://example.com/newsletter", "action", ("https://example.com/newsletter",)),
        PageCandidate("https://example.com/privacy", "privacy", ("https://example.com/privacy",)),
        PageCandidate("https://example.com/quote", "action", ("https://example.com/quote",)),
        PageCandidate("https://example.com/register", "action", ("https://example.com/register",)),
    ]


def test_candidate_identity_only_collapses_trailing_slash_and_keeps_query():
    assert candidate_identity("https://example.com/contact") == candidate_identity(
        "https://example.com/contact/"
    )
    assert candidate_identity("https://example.com/contact?id=1") != candidate_identity(
        "https://example.com/contact?id=2"
    )


def test_classification_deduplicates_slash_and_tracking_but_not_functional_query():
    candidates = links(
        ("https://example.com/contact/?utm_source=x", "Contacto slash"),
        ("https://example.com/contact", "Contacto"),
        ("https://example.com/contact?id=1#form", "Contacto"),
        ("https://example.com/contact?id=2", "Contacto"),
    )

    assert [
        item.url
        for item in classify_page_candidates("https://example.com/", candidates)
    ] == [
        "https://example.com/contact",
        "https://example.com/contact?id=1",
        "https://example.com/contact?id=2",
    ]


def test_classification_preserves_exact_hostname_and_existing_exclusions():
    candidates = links(
        ("https://www.example.com/contact", "Contacto www"),
        ("https://sub.example.com/privacy", "Privacy subdomain"),
        ("https://example.com/privacy.pdf", "Privacy PDF"),
        ("https://example.com/news/privacy", "Privacy news"),
        ("https://example.com/privacy", "Privacy"),
    )

    assert [item.url for item in classify_page_candidates("https://example.com", candidates)] == [
        "https://example.com/privacy"
    ]


def test_legacy_selection_remains_home_privacy_contact_and_two_actions():
    candidates = links(
        ("https://example.com/privacy", "Privacy"),
        ("https://example.com/contact", "Contact"),
        ("https://example.com/registro", "Registro"),
        ("https://example.com/cotizar", "Cotizar"),
        ("https://example.com/news", "News"),
    )

    assert select_pages("https://example.com", candidates) == [
        "https://example.com/",
        "https://example.com/privacy",
        "https://example.com/contact",
        "https://example.com/cotizar",
        "https://example.com/registro",
    ]
