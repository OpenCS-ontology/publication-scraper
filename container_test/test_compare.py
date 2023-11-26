from rdflib import Graph
import os
from rapidfuzz import fuzz
from rdflib.compare import isomorphic


def are_graphs_equal(graph1, graph2):
    isomorphic_result = isomorphic(graph1, graph2)

    return isomorphic_result


if __name__ == "__main__":
    archives = ["csis", "scpe"]
    input_path = "/scraper/output/ttls"
    output_path = "/scraper/container_test/true_ttl"
    for archive in archives:
        root_dir = os.path.join(input_path, archive)
        for dir in os.listdir(root_dir):
            dir_path = os.path.join(root_dir, dir)
            if os.path.isdir(dir_path):
                for ttl_file in os.listdir(dir_path):
                    final_in_path = os.path.join(dir_path, ttl_file)
                    found_file_flag = False
                    final_output_ttl = ttl_file
                    mod_ttl_file = "".join(
                        [char for char in ttl_file.lower() if char.isalpha()]
                    )
                    for out_ttl in os.listdir(output_path):
                        mod_out_ttl = "".join(
                            [char for char in out_ttl.lower() if char.isalpha()]
                        )
                        if fuzz.ratio(mod_ttl_file, mod_out_ttl) > 95:
                            final_out_path = os.path.join(output_path, out_ttl)
                            found_file_flag = True
                            break
                    if found_file_flag:
                        g1 = Graph()
                        g2 = Graph()

                        g1.parse(final_in_path, format="ttl")
                        g2.parse(final_out_path, format="ttl")
                        assert are_graphs_equal(g1, g2)
                    print(f"Test with {ttl_file} passed!")
