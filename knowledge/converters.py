class UnicodeSlugConverter:
    """URL path converter that supports Unicode characters in slugs."""
    regex = r'[-\w]+' 

    def to_python(self, value):
        return value

    def to_url(self, value):
        return value
