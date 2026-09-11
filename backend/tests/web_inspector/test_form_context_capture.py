from mininode_api.web_inspector.extractor import extract_page
from mininode_api.web_inspector.models import LinkEvidence
from mininode_api.web_inspector.selector import classify_page_candidates


def test_form_captures_context_from_adjacent_copy_column():
    html = """
    <section>
      <div class="copy">
        <h1>See the product in action</h1>
        <p>We will answer your questions and walk you through a tailored demo.</p>
      </div>
      <div class="form-column">
        <div class="form-shell">
          <form>
            <input type="email" name="email">
            <button type="submit">Continue</button>
          </form>
        </div>
      </div>
    </section>
    """

    form = extract_page(html, "https://example.com/contact-sales").forms[0]

    assert form.heading == "See the product in action"
    assert form.introductory_text == (
        "We will answer your questions and walk you through a tailored demo."
    )


def test_form_context_does_not_cross_a_previous_form_wrapper():
    html = """
    <section>
      <div class="previous">
        <h2>Previous purpose</h2>
        <form><input type="email" name="first"></form>
      </div>
      <div class="current">
        <div><form><input type="email" name="second"></form></div>
      </div>
    </section>
    """

    second = extract_page(html, "https://example.com/").forms[1]

    assert second.heading is None
    assert second.introductory_text is None


def test_form_context_does_not_use_link_bearing_marketing_wrapper():
    html = """
    <section>
      <div class="copy">
        <h2>Learn more</h2>
        <p>Read the guide before continuing.</p>
        <a href="/guide">Open guide</a>
      </div>
      <div class="form-column"><form><input type="email"></form></div>
    </section>
    """

    form = extract_page(html, "https://example.com/").forms[0]

    assert form.heading is None
    assert form.introductory_text is None


def test_selector_recognizes_common_form_action_ctas():
    links = [
        LinkEvidence("https://example.com/free-trial/", "Start Free", "https://example.com/"),
        LinkEvidence("https://example.com/demo", "Get a demo", "https://example.com/"),
        LinkEvidence("https://example.com/meeting", "Request a meeting", "https://example.com/"),
    ]

    classified = classify_page_candidates("https://example.com/", links)

    assert [(item.url, item.category) for item in classified] == [
        ("https://example.com/demo", "action"),
        ("https://example.com/free-trial/", "action"),
        ("https://example.com/meeting", "action"),
    ]
