import pytest

from mininode_api.web_inspector.models import LinkEvidence
from mininode_api.web_inspector.selector import select_pages


def links(*items):
    return [LinkEvidence(url, text, "https://example.com/") for url, text in items]


def test_home_privacy_contact_and_at_most_two_additional_pages_are_prioritized():
    discovered = links(
        ("https://example.com/blog", "Blog"),
        ("https://example.com/news", "Noticias"),
        ("https://example.com/contacto", "Contáctanos"),
        ("https://example.com/privacidad", "Política de privacidad"),
        ("https://example.com/registro", "Registrarse"),
        ("https://example.com/newsletter", "Newsletter"),
        ("https://example.com/reserva", "Reservar"),
    )

    assert select_pages("HTTPS://EXAMPLE.COM", discovered) == [
        "https://example.com/",
        "https://example.com/privacidad",
        "https://example.com/contacto",
        "https://example.com/newsletter",
        "https://example.com/registro",
    ]


@pytest.mark.parametrize(
    ("url", "text"),
    [
        ("https://example.com/registro", "Registro"),
        ("https://example.com/newsletter", "Suscripción newsletter"),
        ("https://example.com/cotizar", "Cotización"),
        ("https://example.com/reserva", "Reserva"),
        ("https://example.com/empleo", "Trabaja con nosotros / postulación"),
    ],
)
def test_recognizes_relevant_additional_pages(url, text):
    assert select_pages("https://example.com", links((url, text))) == ["https://example.com/", url]


def test_excludes_external_subdomain_binary_non_http_noise_and_duplicates():
    discovered = links(
        ("https://other.example/contacto", "Contacto"),
        ("https://blog.example.com/privacidad", "Privacidad"),
        ("https://example.com/file.pdf", "Privacidad PDF"),
        ("mailto:a@example.com", "Email"),
        ("tel:+56223456789", "Teléfono"),
        ("javascript:void(0)", "Registro"),
        ("https://example.com/noticias", "Noticias"),
        ("https://example.com/contacto#top", "Contacto"),
        ("https://example.com/contacto", "Contacto duplicado"),
    )

    assert select_pages("https://example.com", discovered) == [
        "https://example.com/",
        "https://example.com/contacto",
    ]


def test_selection_is_deterministic_regardless_of_input_order():
    discovered = links(
        ("https://example.com/z-reserva", "Reserva"),
        ("https://example.com/a-cotizar", "Cotizar"),
        ("https://example.com/privacy", "Privacy"),
        ("https://example.com/contact", "Contact"),
    )
    assert select_pages("https://example.com", discovered) == select_pages(
        "https://example.com", reversed(discovered)
    )
