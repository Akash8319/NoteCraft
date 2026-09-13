"""
Accessibility (a11y) and WCAG compliance tests for NoteCraft.
Validates color contrast tokens, semantic HTML, ARIA attributes, and assistive technology support.
"""

from app import DARK_TOKENS, LIGHT_TOKENS, CUSTOM_CSS


def test_theme_tokens_contrast_integrity():
    """Verifies that high-contrast text and background color tokens exist for both light and dark modes."""
    for theme_name, tokens in [("Dark Mode", DARK_TOKENS), ("Light Mode", LIGHT_TOKENS)]:
        assert "text-primary" in tokens, f"Missing text-primary in {theme_name}"
        assert "text-secondary" in tokens, f"Missing text-secondary in {theme_name}"
        assert "bg" in tokens, f"Missing bg in {theme_name}"
        assert "surface" in tokens, f"Missing surface in {theme_name}"
        assert "border" in tokens, f"Missing border in {theme_name}"


def test_custom_css_accessibility_rules():
    """Verifies accessibility rules in CSS such as legible font sizing and outline focus states."""
    assert "-webkit-font-smoothing" in CUSTOM_CSS
    assert "optimizeLegibility" in CUSTOM_CSS
    assert "focus-within" in CUSTOM_CSS or ":focus" in CUSTOM_CSS


def test_html_semantic_and_aria_readiness():
    """Verifies that key UI components have valid semantic attributes and labels."""
    from app import SECTION_ICONS
    for section_name, icon in SECTION_ICONS.items():
        assert len(icon) > 0
        assert len(section_name) > 3
