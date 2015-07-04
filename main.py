################################################################################
# +++ XTAG to XML +++                                                          #
# A tool to convert XTAG grammar rules stored in the obsolete .trees format to #
# JSON and XML files. Developed as part of the CRC991 (Section A2) at Heinrich #
# Heine University Dusseldorf under supervision of Prof. Laura Kallmeyer.      #
# For more information, see http://www.sfb991.uni-duesseldorf.de/en/           #
#                                                                              #
# Author: Esther Seyffarth (esther.seyffarth@hhu.de)                           #
# Date: 04 July 2015                                                           #
#                                                                              #
# Written in Python 3.4.                                                       #
#                                                                              #
# How to use: python main.py (to use default settings from config.ini)         #
#             python main.py [xtag-directory] [json-directory] [xml-directory] #
#             [toggle-single-file]                                             #
################################################################################



import configparser
import sys

import GrammarToTree
import JSONtoXML
import utils



def getConfigSettings():
    settings = {}
    config = configparser.ConfigParser()
    config.read("config.ini")
    options = config.sections()[0]
    default_values = config.options(options)
    for attribute in default_values:
        try:
            settings[attribute] = config.get(options, attribute)
        except:
            print("Unable to read options.")

    return settings

if __name__ == "__main__":
    if len(sys.argv) == 1:
        settings = getConfigSettings()
    elif len(sys.argv) == 5:
        settings = {}
        settings["xtag_dir"] = sys.argv[1]
        settings["json_dir"] = sys.argv[2]
        settings["xml_dir"] = sys.argv[3]
        if sys.argv[4].lower() in ["true", "false"]:
            settings["make_single_xml_file"] = sys.argv[4]
        else:
            print("Last argument must be either true or false.")
            exit()
    else:
        print("""Please call this tool with the correct number of arguments.
First Argument:  XTAG directory (must be valid directory)
Second Argument: JSON directory (will be created if necessary)
Third Argument:  XML directory (will be created if necessary)
Fourth Argument: Toggle single-file XML output (must be either true or false)
If no arguments are given, default values from config.ini will be used.""")
        exit()

    print("Processing XTAG files...")
    GrammarToTree.convertXTAGtoJSON(settings["xtag_dir"], settings["json_dir"])
    print("Done!")
    print("Processing JSON files...")
    JSONtoXML.getJSONTrees(settings["json_dir"], settings["xml_dir"])
    print("Done!")
    if settings["make_single_xml_file"] == "true":
        print("Collecting all grammar entries into one file...")
        utils.collectXMLDocuments(settings["xml_dir"])
        print("Done!")
    print("""You can view your output files in the directories
{} (JSON files) and
{} (XML files).""".format(settings["json_dir"], settings["xml_dir"]))
    print("Press any key to exit.")
    input()
    exit()