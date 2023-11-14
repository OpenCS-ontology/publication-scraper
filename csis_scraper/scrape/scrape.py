import urllib.request as rq
import requests

# from grobid_client.grobid_client import GrobidClient
from bs4 import BeautifulSoup
from tika import parser
import numpy as np
from selenium import webdriver
from webdriver_manager.chrome import ChromeDriverManager
import re
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
import pandas as pd
from pathlib import Path
from csis_scraper.scrape.doi import CrossRefClient
from abc import ABC, abstractmethod
import os
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
import tqdm
from urllib.error import HTTPError
import glob
import shutil
from paper_model_to_ttl import *
from dataclasses import dataclass, asdict
from typing import List, Optional, Tuple, Callable
from models.model import AuthorModel, PaperModel, Journal, Conference


@dataclass
class PaperScraperResponse:
    """
    Model representing the scraped data about the paper.
    """

    url: str

    # DC.Identifier.DOI
    DOI: Optional[str]

    author: Optional[str]
    # DC.Title

    title: str
    book_title: Optional[str]
    editor: Optional[str]
    publisher: Optional[str]
    abstract: Optional[str]
    pages: Optional[int]
    source: Optional[str]
    session: Optional[str]
    volume_no: Optional[str]
    type: Optional[str]
    source_doi: Optional[str]
    event: Optional[str]
    container_title: Optional[str]
    ISSN: Optional[str]
    date: Optional[str]
    language: Optional[str]
    licence: Optional[str]
    volume_url: Optional[str]
    journal_name: Optional[str]


class _DriverWrapper(ABC):
    """
    A class for wrapping a webdriver to handle page navigation.

    Parameters
    ----------
    output_path : str
        The path to the directory where pdf and ttl files will be saved.
    pdf_directory : str, optional
        The name of the directory within `output_path` where pdf files will be saved. Default is 'pdfs'.
    ttl_directory : str, optional
        The name of the directory within `output_path` where ttl files will be saved. Default is 'ttls'.

    Attributes
    ----------
    pdf_directory : str
        The full path to the directory where pdf files will be saved.
    ttl_directory : str
        The full path to the directory where ttl files will be saved.
    driver : webdriver.Chrome
        The chrome webdriver instance used for navigating pages.
    source : str
        The source of the journal.
    journal_name : str
        The name of the journal.
    doi_client : CrossRefClient
        The doi client used for retrieving doi information.
    grobid_client : GrobidClient
        The grobid client used for retrieving metadata from pdf files.
    language : str
        The language of the journal.
    licence : str
       The license of the journal.
    """

    def __init__(self, output_path, volume, pdf_directory="pdfs", ttl_directory="ttls"):
        """
        Initialize the class with the provided output path.
        Creates two directories: pdf_directory and ttl_directory in the output path, if they don't exist.
        Initializes chrome web driver with headless and no-sandbox options.
        Initializes class variables source, journal_name, doi_client, grobid_client, language and licence.

        Parameters
        ----------
        output_path : str
            The path where the pdf and turtle files will be saved.
        pdf_directory : str, optional
            The name of the directory where pdf files will be saved. Default is 'pdfs'.
        ttl_directory : str, optional
            The name of the directory where turtle files will be saved. Default is 'ttls'.

        Returns
        -------
        None
        """
        volume_dir = "csis/volume_" + str(volume)
        self.pdf_directory = os.path.join(output_path, pdf_directory, volume_dir)
        # self.ttl_directory = os.path.join(output_path, ttl_directory)

        if not os.path.exists(self.pdf_directory):
            os.mkdir(self.pdf_directory)
        # if not os.path.exists(self.ttl_directory):
        #    os.makedirs(self.ttl_directory)

        service = Service(executable_path="./csis_scraper/chromedriver")

        chrome_options = Options()
        chrome_options.add_experimental_option(
            "prefs", {"profile.managed_default_content_settings.images": 2}
        )
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("start-maximized")  # open Browser in maximized mode
        chrome_options.add_argument("--headless")

        self.driver = webdriver.Chrome(service=service, options=chrome_options)

        self.source = "FedCSIS"
        self.journal_name = "Annals of Computer Science and Information Systems"
        self.doi_client = CrossRefClient()
        # self.grobid_client = GrobidClient(config_path="config.json")
        self.language = "english"
        self.licence = "https://creativecommons.org/licenses/by/4.0/"

    def get_page(self, url):
        """
        Navigate to a specified URL using the webdriver.

        Parameters
        ----------
        url : str
            The url to navigate to.

        Returns
        -------
        None
        """
        self.driver.get(url)

    def process_author(self, author):
        """
        Processes the author's name and returns it in given-family format.
        The last word of the author string is considered as the family name and the rest is considered as the given name.

        Parameters
        ----------
        author : str
            The name of the author in string format.

        Returns
        -------
        dict
            A dictionary containing the given name and family name of the author.
        """
        words = author.split(" ")
        return {"given": " ".join(words[:-1]), "family": words[-1]}

    def get_bibtech(self, text_):
        """
        Extract bibliographic information from a string of text in bibtex format.

        Parameters
        ----------
        text_ : str
           The string of text in bibtex format.

        Returns
        -------
        tuple
           A tuple containing the author, title, book title, year, editor, publisher and page number.
        """
        try:
            author = re.findall(r"author=\{(.*?)\}", text_)[0]
        except IndexError:
            author = None

        try:
            title = re.findall(r"\n\ttitle=\{(.*?)\}", text_)[0]
        except IndexError:
            title = None

        try:
            book_title = re.findall(r"\n\tbooktitle=\{(.*?)\}", text_)[0]
        except IndexError:
            book_title = None

        try:
            year = re.findall(r"year=\{(.*?)\}", text_)[0]
        except IndexError:
            year = None

        try:
            editor = re.findall(r"editor=\{(.*?)\}", text_)[0]
        except IndexError:
            editor = None

        try:
            publisher = re.findall(r"publisher=\{(.*?)\}", text_)[0]
        except IndexError:
            publisher = None

        try:
            pages = re.findall(r"pages=\{(.*?)\}", text_)[0]
            pages_splitted = re.findall(r"\d+", pages)
            pages_no = int(pages_splitted[1]) - int(pages_splitted[0])
        except IndexError:
            pages_no = None

        return author, title, book_title, year, editor, publisher, pages_no

    def get_article_urls(self):
        """
        Extract article urls from the current page source of the webdriver.

        Returns
        -------
        list
            A list of article url extensions.
        """
        page_souce = BeautifulSoup(self.driver.page_source, "html.parser")
        ulr_hrefs = page_souce.find_all("a", class_="tytul", href=True)
        url_extensions = [ulr_href["href"] for ulr_href in ulr_hrefs]

        return url_extensions

    def download_papers(self, pdf_links):
        """
        Download papers to the pdf_directory.

        Parameters
        ----------
        pdf_links : dict
            A dictionary with keys as the names of the papers and values as the download links for the papers.

        Returns
        -------
        None
        """
        for key, value in tqdm.tqdm(pdf_links.items()):
            response = requests.get(value)
            with open(os.path.join(self.pdf_directory, f"{key}.pdf"), "wb") as f:
                f.write(response.content)

    def click_elements(self, strategy, locator, every_second=False, make_visible=False):
        """
        Click on elements that match the specified strategy and locator.

        Parameters
        ----------
        strategy : str
            The strategy for finding the elements.
        locator : str
            The locator for finding the elements.
        every_second : bool, optional
            If True, only every second element will be clicked. Default is False.
        make_visible : bool, optional
            If True, the element will be scrolled to and made visible before clicking. Default is False.

        Returns
        -------
        None
        """
        elements = self.driver.find_elements(strategy, locator)
        if every_second:
            elements = elements[::2]
        script = (
            "var viewPortHeight = Math.max(document.documentElement.clientHeight, window.innerHeight || 0);"
            + "var elementTop = arguments[0].getBoundingClientRect().top;"
            + "window.scrollBy(0, elementTop-(viewPortHeight/2));"
        )

        for element in elements:
            if make_visible:
                self.driver.execute_script(script, element)
                element = WebDriverWait(self.driver, 10).until(
                    EC.visibility_of(element)
                )
                element = WebDriverWait(self.driver, 10).until(
                    EC.element_to_be_clickable(element)
                )
                self.driver.execute_script("arguments[0].click();", element)
            else:
                element.click()

    def get_doi_and_abstract(self, url):
        """
        Extract the DOI and abstract from a webpage.

        Parameters
        ----------
        url : str
            The url of the webpage.

        Returns
        -------
        tuple
             A tuple containing the DOI and abstract of the webpage.
        """
        try:
            html_file = self.request(url)
            doi = [
                elem["href"]
                for elem in html_file.find_all("a", href=True)
                if "doi" in elem["href"]
            ][0]

            try:
                abstract = html_file.find_all("p", itemprop="description")[
                    0
                ].text.replace("Abstract. ", "")
            except IndexError:
                abstract = html_file.find_all("p")[3].text.replace("Abstract. ", "")
            return doi, abstract
        except HTTPError as e:
            print(f"HTTPError for url when looking for doi and abstract: {url}", e)
            return "", ""

    def return_title_from_xml(self, file):
        """
        Extracts the title from an XML file using the BeautifulSoup library.
        It opens the file, reads its content, parse it as an XML, and finds the first element with the tag 'title'.
        If an IndexError is raised, it returns the basename of the file without its extension as the title.

        Parameters
        ----------
        file : str
            The file path of the xml file from which title needs to be extracted

        Returns
        -------
        str
            The title of the article.
        """
        with open(file, "r") as f:
            data = f.read()
            data = BeautifulSoup(data, "xml")
            try:
                return data.find_all("title")[0].contents[0]
            except IndexError as e:
                return os.path.basename(file).replace(".tei.xml", "")

    def rename_pdfs_and_return_new_filenames(self, pdfs_dir):
        """
        Rename pdf files using the title from their corresponding xml files (generated with GROBID) and returns the new
        filenames.

        Parameters
        ----------
        pdfs_dir : str
            The path of the directory containing the pdf files.

        Returns
        -------
        dict
            A dictionary with the old filenames as keys and the new filenames as values.
        """
        parent_dir = os.path.dirname(pdfs_dir)
        xml_dir = os.path.join(parent_dir, "xmls")

        if os.path.exists(xml_dir):
            shutil.rmtree(xml_dir)
        os.mkdir(xml_dir)

        self.grobid_client.process(
            "processHeaderDocument", pdfs_dir, output=xml_dir, force=True, n=10
        )

        pdf_files = glob.glob(os.path.join(pdfs_dir, "*"))
        pdf_files = {
            os.path.basename(file).replace(".pdf", ""): file for file in pdf_files
        }

        new_filenames = {}
        for xml_file in glob.glob(os.path.join(xml_dir, "*")):
            title = self.return_title_from_xml(xml_file)[:150]
            id_ = os.path.basename(xml_file).replace(".tei.xml", "")
            new_filename = title.replace(" ", "_").replace("/", "_") + ".pdf"
            new_filenames[id_] = os.path.join(pdfs_dir, new_filename)
            os.rename(pdf_files[id_], new_filenames[id_])

        shutil.rmtree(xml_dir)
        return new_filenames

    def request(self, link):
        """
        Send a request to a specified link and return the response as a BeautifulSoup object

        Parameters
         ----------
        link : str
            The url of the webpage.

        Returns
        -------
        BeautifulSoup object
            A beautifulsoup object of the webpage.
        """
        req = rq.Request(link)
        req = rq.urlopen(req)
        html_file = BeautifulSoup(req, "html.parser")
        return html_file

    def find_conferences(self, link_base):
        """
        Extract the conference names from a webpage.

        Parameters
        ----------
        link_base : str
            The base url of the webpage.

        Returns
        -------
        list
            A list containing the names of the conferences.
        """
        page_source_ = self.request(link_base)
        numbers_lst = []
        for lst_ in str(page_source_).split("<ul id="):
            numbers_lst.append(lst_.count('<span class="ID"'))

        if numbers_lst[0] == 0:
            numbers_lst = numbers_lst[1:]

        volume_no = int("".join(filter(str.isdigit, link_base)))

        if volume_no < 9 or (volume_no > 10 and volume_no < 25):
            h4 = page_source_.find_all("h4", id=True, class_=False)
            namespace = [marker.text for marker in h4]
        elif volume_no == 9:
            h4 = page_source_.find_all("h4", id=True, class_=False)
            namespace = [marker.text for marker in h4]
            namespace.remove(
                "Information Technology for Management, Business & Society"
            )
        else:
            h4 = page_source_.find_all("h4", id=True)
            h4_empty = page_source_.find_all("h4", id=True, class_="empty")
            empty_h4 = [empty.text for empty in h4_empty]
            namespace = [marker.text for marker in h4]
            namespace = [name for name in namespace if name not in empty_h4]

        volume_conference = []
        if len(namespace) == len(numbers_lst):
            for index, name in enumerate(namespace):
                for repetitive in range(numbers_lst[index]):
                    volume_conference.append(name)

        return volume_conference

    @abstractmethod
    def traverse_papers(self):
        """
        Abstract method to traverse through the papers. To be implemented by subclasses.

        Returns
        -------
        None
        """
        pass


class DriverWrapper(_DriverWrapper):
    """
    General purpose wrapper class for majority of volumes
    it is a subclass of _DriverWrapper.
    """

    def traverse_papers(self, page_url, volume_no):
        """
        Traverses the papers on the provided url and extracts the necessary information.
        Finds the conference names, extracts the abstracts and bibtex information from the page source,
        downloads the pdfs and renames them, then creates turtle files for each paper.

        Parameters
        ----------
        url : str
            The url of the webpage containing the papers.
        volume_no : int
            The number of the volume.

        Returns
        -------
        None
        """
        print(page_url)
        self.get_page(page_url)

        print("Reading conference names...")
        conference_lst = self.find_conferences(page_url)

        # create list with urls to papers
        article_urls = self.get_article_urls()
        # find elements with BibTeX text
        self.click_elements(By.XPATH, "//span[text()='Cite']", make_visible=True)

        article_urls = [
            url
            for url in article_urls
            if ".pdf" not in url
            and "Volume_" not in url
            and "doi" not in url
            and url not in {"index.html", "communication.html", "position.html"}
        ]

        filenames = [os.path.basename(url) for url in article_urls]
        webpages_to_get_doi = {
            filename.replace(".html", ""): f"{page_url}/drp/{filename}"
            for filename in filenames
        }
        urls_to_get_pdf = {
            id_: webpage.replace("drp", "pliks").replace("html", "pdf")
            for id_, webpage in webpages_to_get_doi.items()
        }

        print("Downloading papers...")
        self.download_papers(urls_to_get_pdf)

        dois, abstracts = {}, {}
        if page_url not in article_urls:
            print("Scrapping doi and abstracts...")
            for id_, url in tqdm.tqdm(webpages_to_get_doi.items()):
                dois[id_], abstracts[id_] = self.get_doi_and_abstract(url)

        print("Getting doi informations...")
        doi_info = {
            id_: self.doi_client.doi2json(doi) for id_, doi in tqdm.tqdm(dois.items())
        }
        elements = self.driver.find_elements(
            By.XPATH, "//*[contains(text(), 'BibTeX')]"
        )
        assert len(elements) == len(article_urls)

        print("Saving turtle files...")
        scraped_docs_list = []
        for index, element in enumerate(tqdm.tqdm(elements)):
            # click elements
            element.click()
            page_souce = BeautifulSoup(self.driver.page_source, "html.parser")
            text = page_souce.find_all("textarea")
            if text:
                text_ = str(text)
                (
                    author,
                    title,
                    book_title,
                    year,
                    editor,
                    publisher,
                    pages_no,
                ) = self.get_bibtech(text_)
                wait_xpath = (
                    '//*[@id="box"]/div/input'
                    if int(volume_no.replace("Volume_", "")) < 25
                    else '//button[text()="Close"]'
                )
                elem = WebDriverWait(self.driver, 10).until(
                    EC.element_to_be_clickable((By.XPATH, wait_xpath))
                )
                elem.click()
            else:
                continue

            file_for_doi_id = (
                filenames[index].split(".")[0] if ".html" in filenames[index] else None
            )

            assert file_for_doi_id is not None
            if file_for_doi_id not in doi_info:
                print(f"No doi for file {filenames[index]}")

            DOI = doi_info[file_for_doi_id].get("URL", None)
            type_ = doi_info[file_for_doi_id].get("type", None)
            source = doi_info[file_for_doi_id].get("source", None)
            event = doi_info[file_for_doi_id].get("event", None)
            container_title = doi_info[file_for_doi_id].get("container_title", None)
            ISSN = doi_info[file_for_doi_id].get("ISSN", None)
            if ISSN is not None:
                ISSN = ISSN[0]
            date = doi_info[file_for_doi_id].get("deposited", {}).get("date-time", year)

            title = doi_info[file_for_doi_id].get("title", title)
            author = doi_info[file_for_doi_id].get(
                "author",
                [self.process_author(author_) for author_ in author.split(" and ")],
            )
            authors_classed = []
            for author in author:
                authors_classed.append(
                    AuthorModel(
                        given_name=author["given"],
                        family_name=author["family"],
                    )
                )

            scraped = PaperModel(
                authors=set(authors_classed),
                title=title,
                publisher=publisher,
                abstract_text=abstracts[file_for_doi_id],
                url=f"{page_url}/{article_urls[index]}",
                page_count=pages_no,
                source=self.source,
                conference=Conference(name=conference_lst[index]),
                volume=volume_no,
                doi=DOI,
                additional_type=type_,
                issn=ISSN,
                publication_date=date,
                language=self.language,
                license=self.licence,
                journal=Journal(name=self.journal_name, website=page_url),
                paper_type="ConferencePaper",
            )

            pdf_id = str(article_urls[index]).lstrip("drp/").rstrip(".html")
            new_title = str(title).replace(" ", "_")
            source_file = os.path.join(self.pdf_directory, pdf_id) + ".pdf"
            target_file = os.path.join(self.pdf_directory, new_title) + ".pdf"
            target_path_list = target_file.split("/")
            if not re.search(r"volume_\d+", target_path_list[-2]):
                target_path_list[-2] = target_path_list[-2] + "_" + target_path_list[-1]
                target_path_list = target_path_list[:-1]
            target_file = os.path.join(*target_path_list)
            os.rename(source_file, target_file)
            scraped_docs_list.append(scraped)
        return scraped_docs_list
