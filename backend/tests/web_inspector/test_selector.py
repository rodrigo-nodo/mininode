from mininode_api.web_inspector.models import LinkEvidence
from mininode_api.web_inspector.selector import (
    PageCandidate,
    candidate_identity,
    policy_candidate_priority,
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
        PageCandidate("https://example.com/privacy", "privacy", ("2", "https://example.com/privacy")),
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


def test_privacy_policy_candidate_prioritizes_general_document_over_topic_specific_us_page():
    general = "https://example.com/es/proteccion-de-datos/"
    qualified = "https://example.com/es/politica-de-privacidad-y-consentimiento-de-exclusion-voluntaria-de-los-estados-unidos/"
    candidates = links(
        (qualified, "Política de privacidad y consentimiento de exclusión voluntaria de los Estados Unidos"),
        (general, "Protección de datos"),
    )
    assert policy_candidate_priority(general, "Protección de datos") == 3
    assert policy_candidate_priority(qualified, "Política de privacidad y consentimiento de exclusión voluntaria de los Estados Unidos") == 4
    assert policy_candidate_priority(qualified, "Política de privacidad") == 4
    assert select_pages("https://example.com/es/", candidates, limit=2) == [
        "https://example.com/es/", general,
    ]
    classified = classify_page_candidates("https://example.com/es/", candidates)
    assert min((p for p in classified if p.category == "privacy"), key=lambda p: p.rank).url == general


def test_explicit_legal_policy_beats_commercial_privacy_link():
    assert select_pages("https://example.com/", links(
        ("https://example.com/privacy/", "Privacy Web"),
        ("https://example.com/legal/privacy/", "Política de privacidad"),
    ), limit=2) == ["https://example.com/", "https://example.com/legal/privacy/"]


def test_general_policy_beats_commercial_data_protection_even_when_url_sorts_later():
    general = "https://example.com/privacy-policy"
    commercial = "https://example.com/en/data-protection"
    homepage = "https://example.com/"
    candidates = links(
        (commercial, "Privacy compliance services"),
        (general, "Privacy policy"),
    )
    assert policy_candidate_priority(general, "Privacy policy") == 0
    assert policy_candidate_priority(commercial, "Privacy compliance services") == 6
    assert select_pages(homepage, candidates, limit=2) == [homepage, general]
    assert select_pages(homepage, reversed(candidates), limit=2) == [homepage, general]


def test_general_privacy_beats_regional_us_privacy_with_generic_anchor():
    homepage = "https://example.com/"
    general = "https://example.com/privacy"
    regional = "https://example.com/us-privacy"
    candidates = links(
        (regional, "Privacy policy"),
        (general, "Privacy"),
    )
    assert policy_candidate_priority(regional, "Privacy policy") > policy_candidate_priority(
        general, "Privacy"
    )
    assert select_pages(homepage, candidates, limit=2) == [homepage, general]


def test_privacy_news_and_blog_are_ineligible_despite_policy_titles():
    homepage = "https://example.com/"
    general = "https://example.com/privacy"
    candidates = links(
        ("https://example.com/news/privacy-policy", "Privacy policy"),
        ("https://example.com/blog/privacy-policy", "Privacy policy"),
        (general, "Privacy"),
    )
    assert select_pages(homepage, candidates, limit=2) == [homepage, general]
    assert [
        item.url for item in classify_page_candidates(homepage, candidates)
        if item.category == "privacy"
    ] == [general]


def test_root_policy_beats_ambiguous_commercial_label_and_regional_policy():
    home = "https://example.com/"
    legal = "https://example.com/privacy-policy"
    commercial = "https://example.com/en/data-protection"
    regional = "https://example.com/california/privacy-policy"
    candidates = links(
        (commercial, "Data Protection"),
        (regional, "Privacy policy"),
        (legal, "Privacy policy"),
    )
    assert policy_candidate_priority(legal, "Privacy policy") == 0
    assert policy_candidate_priority(commercial, "Data Protection") == 3
    assert policy_candidate_priority(regional, "Privacy policy") == 4
    assert select_pages(home, candidates, limit=2) == [home, legal]
    assert select_pages(home, reversed(candidates), limit=2) == [home, legal]


def test_locale_policy_beats_long_region_specific_policy_but_not_root_policy():
    home = "https://example.com/es/"
    local = "https://example.com/es/proteccion-de-datos/"
    thematic = "https://example.com/es/politica-de-privacidad-y-consentimiento-estados-unidos/"
    assert select_pages(home, links(
        (thematic, "Política de privacidad"),
        (local, "Protección de datos"),
    ), limit=2) == [home, local]
    assert policy_candidate_priority(
        "https://example.com/california/privacy-policy", "Privacy policy"
    ) > policy_candidate_priority("https://example.com/privacy-policy", "Privacy policy")
