import nh3

ALLOWED_TAGS = {
    "a", "b", "i", "em", "strong", "u", "s", "sub", "sup", "small", "br", "p", "div", "span",
    "ul", "ol", "li", "dl", "dt", "dd", "blockquote", "code", "pre", "hr",
    "h1", "h2", "h3", "h4", "h5", "h6", "table", "thead", "tbody", "tr", "th", "td", "img",
}
ALLOWED_ATTRIBUTES = {"a": {"href", "title"}, "img": {"src", "alt", "title"}, "th": {"align"}, "td": {"align"}}


def clean_html(html):
    """Санитизация HTML из внешних источников (словари, markdown пользователей)."""
    return nh3.clean(
        html,
        tags=ALLOWED_TAGS,
        attributes=ALLOWED_ATTRIBUTES,
        url_schemes={"http", "https", "mailto"},
        link_rel="noopener noreferrer nofollow",
    )
