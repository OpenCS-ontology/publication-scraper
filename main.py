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


def main():
    processing_CSIS = True
    processing_SCPE = True
    if processing_SCPE:
        print("Processing SCPE archives...")
        logging.basicConfig(
            level=logging.INFO,
            format="[%(asctime)s] %(levelname)s: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        scraped_article_info = []
        scpe_article_data_models = []
        scrape_all_doi(scraped_article_info)
        for paper in scraped_article_info:
            doi_api_response = call_doi_api(paper.doi)
            if doi_api_response.status_code == HTTPStatus.OK:
                logging.info(f"Decoding response from DOI API for '{paper.doi}'")
                doi_response_paper_model = doi_api_decoder(doi_api_response.content)
            else:
                logging.warning(
                    f"Response from DOI API not OK: {doi_api_response.status_code}"
                )
                doi_response_paper_model = None

            paper_model = create_paper_model(paper, doi_response_paper_model)
            scpe_article_data_models.append(paper_model)

        print("Converting to Turtle")
        for article in scpe_article_data_models:
            g = convert_paper_model_to_graph(article)
            ttl_dir = f"./output/ttls/scpe/volume_{article.volume}"
            if not os.path.exists(ttl_dir):
                os.makedirs(ttl_dir)

            ttl_filename = os.path.join(ttl_dir, os.path.basename(article.title + ".ttl"))
            ttl_filename = ttl_filename.replace(" ", "_")
            
            with open(ttl_filename, "w") as file:
                file.write(g)
        print("Process succeded")

    if processing_CSIS:
        print("Processing CSIS archives...")

        parser = argparse.ArgumentParser(
            description="Program scraping https://annals-csis.org/"
        )
        parser.add_argument(
            "--volumes",
            type=tuple_type,
            default=tuple(range(1, 33)),
            help="Indices of volumes to scrape. A list of integers or a range of integers represented by a tuple of 2 integers. \
                        If the input is a list of integers, any duplicates will be removed. If the input is a tuple of 2 integers, \
                        it will be interpreted as an inclusive range of integers, and all integers within that range will be included in the final list.",
        )
        parser.add_argument(
            "--config",
            type=str,
            default="scrape_config.yaml",
            help="Path to config file, default `scrape_config.yaml`",
        )
        args = parser.parse_args()

        config = return_config(args.config)

        for volume in args.volumes:
            output_path = config["output_path"]

            #if os.path.exists(output_path):
            #    shutil.rmtree(output_path)

            #os.mkdir(output_path)
            if volume == 1:
                print("Voulme 1 currenly unavailable")
            else:
                scraper = DriverWrapper(output_path=output_path, volume=volume)

            page_to_scrape = config["base_webpage"] + f"Volume_{volume}"
            print(page_to_scrape)
            print(f"Scraping Volume {volume}, {page_to_scrape}")
            csis_article_data_models = scraper.traverse_papers(
                page_to_scrape, str(volume)
            )
            print("Converting to Turtle")
            for article in csis_article_data_models:
                g = convert_paper_model_to_graph(article)
                ttl_dir = f"./output/ttls/csis/volume_{article.volume}"
                if not os.path.exists(ttl_dir):
                    os.mkdir(ttl_dir)

                ttl_filename = os.path.join(ttl_dir, os.path.basename(article.title + ".ttl"))
                ttl_filename = ttl_filename.replace(" ", "_")

                with open(ttl_filename, "w") as file:
                    file.write(g)
        print("Process succeded")


if __name__ == "__main__":
    main()
