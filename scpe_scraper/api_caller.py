import logging
from typing import Optional

from requests import Response
from requests.exceptions import ConnectionError

import scpe_scraper.requests_trials as requests


DOI_PREFIX = "https://doi.org/"


def call_doi_api(doi: Optional[str]) -> Response:
    """
    Call the https://doi.org api and get a turtle file with the Response.

    :param doi: Optional string with the requested DOI. If None, returns I AM A TEAPOT response.
    """
    if doi is not None:
        url_call = DOI_PREFIX + doi

        try:
            r_rdf = requests.get(url_call, headers={"Accept": "text/turtle"})
            return r_rdf
        except ConnectionError as e:
            logging.warning(f"DOI api call failure: {str(e)}")

    r = Response()
    r.status_code = 418  # I AM A TEAPOT
    return r
