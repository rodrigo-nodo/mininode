from mininode_api.web_inspector.models import LinkEvidence
from mininode_api.web_inspector.selector import select_pages


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
