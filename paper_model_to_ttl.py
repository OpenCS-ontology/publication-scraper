from rdflib import Graph, Literal, RDF, URIRef, Namespace, RDFS
from rdflib.namespace import XSD
from models.model import PaperModel
import hashlib
import random
import string

from rdflib import BNode


def add_to_graph(g, subject, predicate, object_, datatype=None, to_literal=True):
    """
    Add a triple to the RDF graph.

    Parameters
    ----------
    g : rdflib.Graph
        The RDF graph.
    subject : rdflib.URIRef or rdflib.BNode
        The subject of the triple.
    predicate : rdflib.URIRef
        The predicate of the triple.
    object_ : rdflib.URIRef or rdflib.BNode or rdflib.Literal or str or int
        The object of the triple.
    datatype : Optional[str]
        The datatype of the object if the object is to be added as a literal.
    to_literal : Optional[bool]
        Indicates if the object should be added as a literal or not. Default is True.
    Returns
    -------
    None
    """
    if object_ is not None:
        if to_literal:
            assert datatype is not None
            g.add((subject, predicate, Literal(object_, datatype=datatype)))
        else:
            g.add((subject, predicate, object_))


def gen_hash(input_string, length=9):
    if input_string is None or input_string == '':
        characters = string.ascii_letters + string.digits
        short_hash = "".join(random.choice(characters) for i in range(9))
    else:
        sha256_hash = hashlib.sha256()
        sha256_hash.update(input_string.encode("utf-8"))
        full_hash = sha256_hash.hexdigest()
        short_hash = full_hash[:length]

    return short_hash


def convert_paper_model_to_graph(article_data: PaperModel):
    """
    Convert a PaperModel instance containing information about an article to a RDF graph.

    Parameters
    ----------
    article_data : PaperModel
        A dictionary containing various information about an article, such as the title, author,
        and publication date.

    Returns
    -------
    rdflib.graph.Graph
        A RDF graph representing the information in the input dictionary.
    """
    g = Graph()
    bn = Namespace("https://w3id.org/ocs/kg/papers/")
    datacite = Namespace("http://purl.org/spar/datacite/")
    dc = Namespace("http://purl.org/dc/terms/")
    fabio = Namespace("http://purl.org/spar/fabio/")
    frapo = Namespace("http://purl.org/cerif/frapo/")
    frbr = Namespace("http://purl.org/vocab/frbr/core#")
    literal = Namespace("http://www.essepuntato.it/2010/06/literalreification/")
    prism = Namespace("http://prismstandard.org/namespaces/basic/2.0/")
    pro = Namespace("http://purl.org/spar/pro/")
    schema = Namespace("http://schema.org/")
    ocs_papers = Namespace("https://w3id.org/ocs/ont/papers/")
    owl = Namespace("http://www.w3.org/2002/07/owl#")

    g.bind("", bn)
    g.bind("datacite", datacite)
    g.bind("dc", dc)
    g.bind("fabio", fabio)
    g.bind("frapo", frapo)
    g.bind("frbr", frbr)
    g.bind("literal", literal)
    g.bind("prism", prism)
    g.bind("pro", pro)
    g.bind("schema", schema)
    g.bind("ocs_papers", ocs_papers)
    g.bind("owl", owl)

    paper = Literal(article_data.title)
    paper = URIRef(bn + f"paper_{gen_hash(article_data.abstract_text)}")

    authors_processed = []
    for i, author in enumerate(article_data.authors):
        if author.given_name == '' and author.family_name == '':
            continue
        author_ = URIRef(
            bn + f"author_{gen_hash(author.given_name + ' ' + author.family_name)}"
        )
        add_to_graph(g, author_, RDF.type, schema.Person, to_literal=False)
        add_to_graph(
            g,
            author_,
            schema.name,
            author.given_name + " " + author.family_name,
            datatype=XSD.string,
        )
        add_to_graph(
            g, author_, schema.givenName, author.given_name, datatype=XSD.string
        )
        add_to_graph(
            g, author_, schema.familyName, author.family_name, datatype=XSD.string
        )
        if author.affiliations:
            for j, affiliation in enumerate(author.affiliations):
                affiliation_name = '' if not affiliation.name else affiliation.name
                role = URIRef(bn + f"role_{gen_hash(author.name + affiliation_name)}")
                add_to_graph(g, author_, pro.holdsRoleInTime, role, to_literal=False)
                add_to_graph(g, role, RDF.type, pro.RoleInTime, to_literal=False)
                add_to_graph(g, role, pro.withRole, pro.author, to_literal=False)
                organization = URIRef(bn + f"org_{gen_hash(affiliation.name)}")
                add_to_graph(
                    g, role, pro.relatesToOrganization, organization, to_literal=False
                )
                add_to_graph(
                    g, organization, RDF.type, frapo.Organization, to_literal=False
                )
                add_to_graph(
                    g, organization, schema.name, affiliation.name, datatype=XSD.string
                )
        add_to_graph(g, paper, dc.creator, author_, to_literal=False)
        authors_processed.append(author_)

    add_to_graph(g, paper, RDF.type, fabio.ResearchPaper, to_literal=False)
    add_to_graph(g, paper, dc.title, article_data.title, datatype=XSD.string)

    doi = article_data.doi if article_data.doi else ''

    article_url = article_data.url if article_data.url else ''

    article_volume = article_data.volume if article_data.volume else ''

    add_to_graph(g, paper, dc.created, article_data.date_created, datatype=XSD.date)

    if article_data.keywords:
        for keyword in article_data.keywords:
            add_to_graph(g, paper, prism.keyword, keyword, datatype=XSD.string)

    desc = BNode()
    add_to_graph(g, paper, datacite.hasDescription, desc, to_literal=False)

    abstract_text = article_data.abstract_text if article_data.abstract_text else ''
    add_to_graph(
        g,
        desc,
        literal.hasLiteralValue,
        abstract_text,
        datatype=XSD.string,
    )
    add_to_graph(
        g, desc, datacite.hasDescriptionType, datacite.abstract, to_literal=False
    )

    if article_data.paper_type == "JournalArticle":
        article = URIRef(bn + f"Journal_Article_{gen_hash(doi)}")
        add_to_graph(g, article, RDF.type, fabio.JournalArticle, to_literal=False)

        issue = URIRef(bn + f"Journal_Issue_{gen_hash(doi+'issue')}")
        add_to_graph(g, issue, RDF.type, fabio.JournalIssue, to_literal=False)
        add_to_graph(g, article, frbr.partOf, issue, to_literal=False)

        volume = URIRef(
            bn + f"Journal_Volume_{gen_hash(article_url+article_volume)}"
        )
        add_to_graph(g, volume, RDF.type, fabio.JournalVolume, to_literal=False)
        add_to_graph(g, volume, prism.volume, article_data.volume, datatype=XSD.integer)
        add_to_graph(g, issue, frbr.partOf, volume, to_literal=False)
        add_to_graph(g, volume, frbr.part, issue, to_literal=False)

        journal = URIRef(bn + f"Journal_{gen_hash(article_url)}")
        add_to_graph(g, journal, RDF.type, fabio.Journal, to_literal=False)
        if article_data.journal:
            add_to_graph(
                g, journal, dc.title, article_data.journal.name, datatype=XSD.string
            )
        add_to_graph(g, journal, prism.issn, article_data.issn, datatype=XSD.string)
        add_to_graph(g, volume, frbr.partOf, journal, to_literal=False)
        add_to_graph(g, journal, frbr.part, volume, to_literal=False)

    elif article_data.paper_type == "ConferencePaper":
        article = URIRef(bn + f"Conference_Paper_{gen_hash(doi)}")
        add_to_graph(g, article, RDF.type, fabio.ConferencePaper, to_literal=False)
        proceedings = URIRef(
            bn + f"Conference_Proceedings_{gen_hash(article_data.conference.name)}"
        )
        add_to_graph(
            g, proceedings, RDF.type, fabio.ConferenceProceedings, to_literal=False
        )
        add_to_graph(
            g,
            proceedings,
            schema.name,
            article_data.conference.name,
            datatype=XSD.string,
        )
        add_to_graph(g, article, frbr.partOf, proceedings, to_literal=False)

    add_to_graph(g, paper, frbr.realization, article, to_literal=False)

    if article_data.language:
        if article_data.language == "english":
            language = "en-US"
        else:
            language = article_data.language
        add_to_graph(g, article, dc.language, language, datatype=XSD.string)

    add_to_graph(g, article, dc.license, article_data.license, datatype=XSD.anyURI)

    add_to_graph(g, article, fabio.hasURL, article_data.url, datatype=XSD.anyURI)

    add_to_graph(g, article, prism.doi, article_data.doi, datatype=XSD.anyURI)

    add_to_graph(
        g,
        article,
        prism.publicationDate,
        article_data.publication_date,
        datatype=XSD.date,
    )

    add_to_graph(
        g, article, prism.startingPage, article_data.startingPage, XSD.integer
    )

    add_to_graph(g, article, prism.endingPage, article_data.endingPage, XSD.integer)

    add_to_graph(
        g, article, prism.pageCount, article_data.page_count, datatype=XSD.integer
    )
    
    add_to_graph(g, article, owl.sameAs, URIRef(article_data.url), to_literal=False)

    if article_data.manifestation:
        manifestation = URIRef(
            bn + f"Manifestation_{gen_hash(article_data.manifestation.has_url)}"
        )
        add_to_graph(
            g, manifestation, RDF.type, fabio.DigitalManifestation, to_literal=False
        )
        add_to_graph(
            g,
            manifestation,
            dc.format,
            article_data.manifestation.format,
            to_literal=False,
        )
        add_to_graph(
            g,
            manifestation,
            fabio.hasURL,
            article_data.manifestation.has_url,
            to_literal=False,
        )
        add_to_graph(g, article, fabio.embodiment, manifestation, to_literal=False)

        publisher = URIRef(bn + f"Publisher_{gen_hash(article_data.publisher)}")
        add_to_graph(g, publisher, RDF.type, frapo.Organization, to_literal=False)
        add_to_graph(
            g, publisher, schema.name, article_data.publisher, datatype=XSD.string
        )
        add_to_graph(g, manifestation, dc.publisher, publisher, to_literal=False)

    return g.serialize(format="turtle")
