import re
import simplejson as json
import os
import xml.etree.ElementTree as ET
import xml.dom.minidom as minidom
import pprint
import utils

def getJSONTrees(jsonpath, xmlpath):
    """
    string, string -> None
    Main entry point for this module. Reads JSON files from specified path,
    calls the other functions and writes the resulting XML files to the
    specified path.
    """
    jsonpath = jsonpath.strip("/")
    xmlpath = xmlpath.strip("/")
    if not os.path.exists(jsonpath):
        os.makedirs(jsonpath)
    if not os.path.exists(xmlpath):
        os.makedirs(xmlpath)
    for directory in os.listdir(jsonpath):
        for jsonfile in os.listdir(jsonpath+"/"+directory):
            with open(jsonpath+"/"+directory+"/"+jsonfile, "r", encoding="utf8") as infile:
                tree = json.load(infile)
            try:
                os.makedirs(xmlpath+"/"+directory)
            except FileExistsError:
                pass
                #print("Directory "+xmlpath+"/"+directory+" already exists")
            makeXMLFile(tree, xmlpath+"/"+directory+"/"+jsonfile.split(".", 1)[0]+".xml")
    return


def findDaughters(dict_tree_containing_node):
    """
    dict -> list
    Takes a (part of a) tree and returns the list of all daughters of the given
    mother node. Each daughter is itself a dictionary.
    """
    if "children" in dict_tree_containing_node.keys():
        daughters = dict_tree_containing_node["children"]
    else:
        daughters = []
    return daughters

def insert_feature_values(xmlnode, node_name, dict_tree_containing_node, used_vars):
    """
    ET.Subelement, string, dict, set -> ET.Subelement, set
    For the given node_name, insert the features that are given in the
    dict_tree into the XML Element structure. Returns the updated ET.SubElement
    as well as the set of used variables, in order to keep it up-to-date.
    """
    if "t" in dict_tree_containing_node["features"]:
        dtr_ftop = ET.SubElement(xmlnode, "f", {"name":"top"})
        # Generate a new variable for each "coref" tag
        coref_var = "@" + utils.numberToString(len(used_vars))
        used_vars.add(coref_var)
        dtr_topfs = ET.SubElement(dtr_ftop, "fs", {"coref": coref_var})

        # insert features in alphabetical order
        for feature in sorted(dict_tree_containing_node["features"]["t"].keys()):
            feature_tag = ET.SubElement(dtr_topfs, "f", {"name": feature.strip("<>")})
            value = dict_tree_containing_node["features"]["t"][feature]
            if value.startswith("@"):
                # add varname
                feature_tag_value = ET.SubElement(feature_tag, "sym", {"varname": value})
            else:
                # add value
                feature_tag_value = ET.SubElement(feature_tag, "sym", {"value": value})

    if "b" in dict_tree_containing_node["features"]:
        dtr_fbot = ET.SubElement(xmlnode, "f", {"name":"bot"})
        coref_var = "@" + utils.numberToString(len(used_vars))
        used_vars.add(coref_var)
        dtr_botfs = ET.SubElement(dtr_fbot, "fs", {"coref": coref_var})
        # insert features in alphabetical order
        for feature in sorted(dict_tree_containing_node["features"]["b"].keys()):
            feature_tag = ET.SubElement(dtr_botfs, "f", {"name": feature.strip("<>")})
            value = dict_tree_containing_node["features"]["b"][feature]
            if value.startswith("@"):
                # add varname
                feature_tag_value = ET.SubElement(feature_tag, "sym", {"varname": value})
            else:
                # add value
                feature_tag_value = ET.SubElement(feature_tag, "sym", {"value": value})

    if node_name.islower():
        dtr_fphon = ET.SubElement(xmlnode, "f", {"name":"phon"})
        dtr_sym = ET.SubElement(dtr_fphon, "sym", {"value":node_name.split("_")[0].lower()})

    else:
        dtr_fcat = ET.SubElement(xmlnode, "f", {"name":"cat"})
        dtr_sym = ET.SubElement(dtr_fcat, "sym", {"value":node_name.split("_")[0].lower()})
    return xmlnode, used_vars


def make_subtree(mother_node, dict_tree_containing_mother_node, used_vars):
    """
    ET.SubElement, dict, set -> ET.SubElement
    For the given mother node, insert all children into the XML structure.
    If the children also have children, call this function again.
    Return the updated ET.SubElement.
    """
    for daughter_dict in findDaughters(dict_tree_containing_mother_node):
        node_attribs, daughter_name = utils.nodeNameToAttrDict(daughter_dict["name"])

        node_attribs.update({"name":daughter_name})

        if daughter_name.islower():
            node_attribs.update({"type": "flex"})

        dtr = ET.SubElement(mother_node, "node", node_attribs)
        dtr_narg = ET.SubElement(dtr, "narg")
        fs_coref = "@" + utils.numberToString(len(used_vars))
        used_vars.add(fs_coref)
        dtr_fs = ET.SubElement(dtr_narg, "fs", {"coref": fs_coref})
        dtr_fs, used_vars = insert_feature_values(dtr_fs, daughter_name, daughter_dict, used_vars)
        if findDaughters(daughter_dict) != []:
            dtr = make_subtree(dtr, daughter_dict, used_vars)
    return mother_node


def makeXMLFile(currentTree, outpath):
    """
    dict, string -> None
    For a given tree structure, generates the XML structure. First generates
    the tags that are included in every XML file; then identifies the root
    of the given tree and generates the ET.SubElements that it requires.
    Finally, writes the XML content to the given output file.
    """
    xmlfile = open(outpath, "w", encoding="utf8")
    grammar = ET.Element("grammar")
    entry = ET.SubElement(grammar, "entry", attrib={"name": currentTree["NAME"]})
    family = ET.SubElement(entry, "family")
    family.text = outpath.split("/")[-2]
    trace = ET.SubElement(entry, "trace")
    traceClass = ET.SubElement(trace, "class")
    traceClass.text = outpath.split("/")[-2]
    tree = ET.SubElement(entry, "tree", attrib={"id": currentTree["NAME"]})
    root = currentTree["HIERARCHY"]["name"]

    if root is not None:
        # collecting all variables used in this tree in order to give new variable names
        # for occurences of "coref" in the XML tree
        used_vars = utils.collect_vars(currentTree["HIERARCHY"])

        root_attribs, root_name = utils.nodeNameToAttrDict(root)
        root_attribs.update({"name":root_name})
        root_node = ET.SubElement(tree, "node", root_attribs)
        root_narg = ET.SubElement(root_node, "narg")

        root_coref = "@" + utils.numberToString(len(used_vars))
        used_vars.add(root_coref)
        root_fs = ET.SubElement(root_narg, "fs", {"coref": root_coref})

        root_fs, used_vars = insert_feature_values(root_fs, root_name, currentTree["HIERARCHY"], used_vars)

        # take root XML node and add all daughters, and all their daughters, etc. to the XML structure
        tree = make_subtree(root_node, currentTree["HIERARCHY"], used_vars)

        # additional XML info
        frame = ET.SubElement(entry, "frame")
        semantics = ET.SubElement(entry, "semantics")
        interface = ET.SubElement(entry, "interface")
        fs = ET.SubElement(interface, "fs")
        print('<?xml version="1.0" encoding="utf-8" standalone="no" ?>\n<!DOCTYPE grammar SYSTEM "xmg-tag.dtd,xml">', file=xmlfile)
        output = ET.tostring(grammar)
        print(utils.prettifyXMLDocument(output).split(">", 1)[1].strip(), file=xmlfile)
        xmlfile.close()
    return