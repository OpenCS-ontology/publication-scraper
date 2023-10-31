import requests
from requests.exceptions import ConnectionError, JSONDecodeError


class CrossRefClient(object):
    """
    A client for querying the CrossRef API for information about a given DOI.

    Parameters
    ----------
    accept : str, optional
        The content type to accept in the response, by default 'text/x-bibliography; style=apa'
    timeout : int, optional
        The number of seconds to wait for the server response, by default 3

    Attributes
    ----------
    headers : dict
        The headers to include in the request
    timeout : int
        The number of seconds to wait for the server response

    Methods
    -------
    query(doi)
        Performs a GET request to the CrossRef API for the given DOI
    doi2json(doi)
        Returns the response in JSON format for the given DOI
    """
    def __init__(self, accept='text/x-bibliography; style=apa', timeout=3):
        """
        Initialize the CrossRefClient class.

        Parameters:
        accept (str): The accept header to use in the request to the CrossRef API. Default is 'text/x-bibliography; style=apa'.
        timeout (int): The number of seconds to wait for a response from the CrossRef API before timing out. Default is 3.
        """
        self.headers = {'accept': accept}
        self.timeout = timeout

    def query(self, doi):
        """
        Perform a GET request to the CrossRef API for the given DOI

        Parameters
        ----------
        doi : str
            The DOI to query the API for

        Returns
        -------
        dict
            The JSON response from the API
        """
        if doi.startswith("http://"):
            url = doi
        else:
            url = "http://dx.doi.org/" + doi
        
        try:
            r = requests.get(url, headers=self.headers)
            return r.json()
        except (ConnectionError, JSONDecodeError) as e:
            print(f"No doi information for doi: {doi}")
            return {}

    def doi2json(self, doi):
        """
        Returns the response in JSON format for the given DOI

        Parameters
        ----------
        doi : str
            The DOI to query the API for

        Returns
        -------
        dict
            The JSON response from the API
        """
        self.headers['accept'] = 'application/vnd.citationstyles.csl+json'
        return self.query(doi)
