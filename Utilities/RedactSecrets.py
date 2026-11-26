import re

# Query parameters that carry credentials in the URLs this app requests (TMDB's api_key and Discogs's
# token, for example). requests and urllib3 put the full URL, query string included, into their
# exception messages, so any of those messages can contain a key
_SECRET_QUERY_PARAMS = re.compile(r"\b(api_key|access_token|token|client_secret)=[^&\s'\"()]+", re.IGNORECASE)


def redact_secrets(text):
    # Replaces the value of any credential query parameter with REDACTED, leaving the rest of the text
    # (host, path, other parameters) intact so it is still useful for debugging. Accepts exceptions as
    # well as strings, and passes None through unchanged
    if text is None:
        return None
    return _SECRET_QUERY_PARAMS.sub(r"\1=REDACTED", str(text))
