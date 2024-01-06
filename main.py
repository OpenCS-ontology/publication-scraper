import logging
from http import HTTPStatus

from csis_scraper.scrape.scrape import DriverWrapper
from scpe_scraper.api_caller import call_doi_api
from scpe_scraper.doi_api_model import doi_api_decoder
from scpe_scraper.paper_scraper import scrape_all_doi

from models.model_factory import create_paper_model
from paper_model_to_ttl import convert_paper_model_to_graph

import pandas as pd
import argparse
import os
import yaml
import shutil
import tqdm
import re


def tuple_type(strings):
    # https://stackoverflow.com/questions/33564246/passing-a-tuple-as-command-line-argument
    strings = strings.replace("(", "").replace(")", "")
    volumes = tuple(map(int, strings.split(",")))
    if len(volumes) == 2:
        volumes = tuple(range(volumes[0], volumes[1] + 1))
    else:
        volumes = tuple(set(volumes))

    return volumes


def return_config(path):
    with open(path, "r") as file:
        return yaml.safe_load(file)


def prepare_ttl_path(ttl_dir, article):
    ttl_path_split = os.path.join(ttl_dir, article.title).split("/")
    if not re.search(r"volume_\d+", ttl_path_split[-2]):
        ttl_path_split[-2] = ttl_path_split[-2] + "_" + ttl_path_split[-1]
        ttl_path_split = ttl_path_split[:-1]
    ttl_filename = os.path.join(*ttl_path_split) + ".ttl"
    ttl_filename = ttl_filename.replace(" ", "_")
    return ttl_filename


def scrape_scpe(scpe_issues_to_scrape):
    print("Processing SCPE archives...")
    logging.basicConfig(
        level=logging.INFO,
        format="[%(asctime)s] %(levelname)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    scraped_article_info = []
    scpe_article_data_models = []
    scrape_all_doi(scraped_article_info, scpe_issues_to_scrape)
    print("Gathering information from DOI API and creating graphs")
    for paper in tqdm.tqdm(scraped_article_info, total=len(scraped_article_info)):
        doi_api_response = call_doi_api(paper.doi)
        if doi_api_response.status_code == HTTPStatus.OK:
            doi_response_paper_model = doi_api_decoder(doi_api_response.content)
        else:
            doi_response_paper_model = None

        paper_model = create_paper_model(paper, doi_response_paper_model)
        scpe_article_data_models.append(paper_model)
    print("Saving turtle files...")
    for article in tqdm.tqdm(
        scpe_article_data_models, total=len(scpe_article_data_models)
    ):
        g = convert_paper_model_to_graph(article)
        if article.volume:
            ttl_dir = f"./output/ttls/scpe/volume_{article.volume}"
            if not os.path.exists(ttl_dir):
                os.makedirs(ttl_dir)

            ttl_filename = prepare_ttl_path(ttl_dir, article)
            try:
                with open(ttl_filename, "w") as file:
                    file.write(g)
            except:
                pass
    print("Process succeded")


def scrape_csis(csis_volumes_to_scrape, args):
    print("Processing CSIS archives...")

    config = return_config(args.config)

    for volume in csis_volumes_to_scrape:
        output_path = config["output_path"]

        # if os.path.exists(output_path):
        #    shutil.rmtree(output_path)

        # os.mkdir(output_path)
        if volume == 1:
            print("Voulme 1 currenly unavailable")
        else:
            scraper = DriverWrapper(output_path=output_path, volume=volume)

        page_to_scrape = config["base_webpage"] + f"Volume_{volume}"
        print(f"Scraping Volume {volume}, {page_to_scrape}")
        csis_article_data_models = scraper.traverse_papers(page_to_scrape, str(volume))
        print("Converting to Turtle")
        for article in csis_article_data_models:
            g = convert_paper_model_to_graph(article)
            ttl_dir = f"./output/ttls/csis/volume_{article.volume}"
            if not os.path.exists(ttl_dir):
                os.mkdir(ttl_dir)
            ttl_filename = prepare_ttl_path(ttl_dir, article)

            with open(ttl_filename, "w") as file:
                file.write(g)
    print("Process succeded")


def main():
    archives = ["scpe", "csis"]
    processing_CSIS = True
    processing_SCPE = True

    parser = argparse.ArgumentParser(description="Program scraping archives")

    parser.add_argument("--scpe_issues", type=str, help="Indices of volumes to scrape.")
    parser.add_argument(
        "--csis_volumes", type=str, help="Indices of volumes to scrape."
    )
    parser.add_argument(
        "--config",
        type=str,
        default="scrape_config.yaml",
        help="Path to config CSIS scraper file, default `scrape_config.yaml`",
    )
    args = parser.parse_args()
    if args.scpe_issues:
        scpe_issues_to_scrape = [int(issue) for issue in args.scpe_issues.split(",")]
    else:
        scpe_issues_to_scrape = [issue for issue in range(1, 201)]

    if args.csis_volumes:
        csis_volumes_to_scrape = [
            int(volume) for volume in args.csis_volumes.split(",")
        ]
    else:
        csis_volumes_to_scrape = [volume for volume in range(2, 39)]

    for archive in archives:
        pdf_path = f"/scraper/output/pdfs/{archive}"
        ttl_path = f"/scraper/output/ttls/{archive}"

        if os.path.exists(pdf_path):
            shutil.rmtree(pdf_path)
        if os.path.exists(ttl_path):
            shutil.rmtree(ttl_path)

        os.mkdir(pdf_path)
        os.mkdir(ttl_path)

    if processing_SCPE:
        scrape_scpe(scpe_issues_to_scrape)

    if processing_CSIS:
        scrape_csis(csis_volumes_to_scrape, args)


if __name__ == "__main__":
    main()
