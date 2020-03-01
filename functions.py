import datetime
from math import ceil, floor

from lxml import etree

test_code = "OEDOISO"
test_name = "One Dimensional Consolidation ISO"
test_properties = [
    "Stage_StageReadings_StagePasteMins1",
    "Stage_StageReadings_StagePasteDive1",
]

def chunkstring(string, length):
    return (string[0+i:length+i] for i in range(0, len(string), length))

def parse_file(file):
    results = {"Stage_StageReadings_StagePasteDive1": [], "Stage_StageReadings_StagePasteMins1": []}
    with open(file, 'r') as input_file:
        data = input_file.read()
        for chunk in chunkstring(data, 17):
            if len(chunk) > 1:
                results["Stage_StageReadings_StagePasteDive1"].append(int(chunk[3:9]))
                hours = int(chunk[9:14])
                mins = int(chunk[14:16])
                tenth = int(chunk[16:])
                results["Stage_StageReadings_StagePasteMins1"].append(round((hours * 60) + mins + (tenth * 0.1),1))
    return results

def parse_results(files):
    results = []
    for file in files:
        results.append(parse_file(file))
    return results

def generate_xml(results):
    root = etree.Element(
        "keylab",
        content="schedule",
        timestamp=datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
        xmlns="http://www.keynetix.com/XSD/KeyLAB/Export"
    )

    test_defs = etree.SubElement(root, "test-definitions")
    test_def = etree.SubElement(test_defs, "test-definition", name=test_name, code=test_code)
    properties = etree.SubElement(test_def, "properties")

    for test in test_properties:
        etree.SubElement(properties, "property", name=test, unit="")

    project = etree.SubElement(root, "project", id="Unknown", name="Unknown")
    samples = etree.SubElement(project, "samples")
    sample = etree.SubElement(samples, "sample", id="Unknown")
    test = etree.SubElement(sample, "test", code=test_code, specimen="1")
    stages = etree.SubElement(test, "stages")

    for i, result in enumerate(results):
        #print(f"Processing - Stage {i+1}")
        stage = etree.SubElement(stages, "stage", number=str(i+1))
        parameters = etree.SubElement(stage, "parameters")
        
        for key, _ in result.items():
            for value in result[key]:
                etree.SubElement(parameters, "parameter", name=key, value=str(value))
    return etree.tostring(root, pretty_print=True, xml_declaration=True, encoding="utf-8")

def round_up(n, decimals=0):
    multiplier = 10 ** decimals
    return ceil(n * multiplier) / multiplier

def round_down(n, decimals=0):
    multiplier = 10 ** decimals
    return floor(n * multiplier) / multiplier