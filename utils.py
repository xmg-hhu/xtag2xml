import xml.etree.ElementTree as ET
import xml.dom.minidom as minidom
import re
import os


def numberToString(number):
    """
    integer -> string
    Generate variable names (for cross-referenced node feature values).
    Variable 0 will be "A", Variable 1 will be "B", etc.
    Variable 26 will be "AA", Variable 27 will be "AB"
    """
    if number/26 < 1:
        correspondingString = chr(number+65)
        return correspondingString
    else:
        correspondingString = numberToString(int(number/26)-1) + \
                              numberToString(number%26)
        return correspondingString

def nodeNameToAttrDict(nodeName):
    """
    string -> (dictionary, string)
    Extract encoded node attribute information from the node name and save
    as separate dictionary entries.
    Currently encoded attributes are node type, connector, display-feature,
    constraints, constraint-type.
    Returns attribute dict and remaining node name.
    """
    attributes = {}
    # set type attribute to default value (will be changed below if type
    # information is given)
    attributes["type"] = "std"

    node_name_re = re.compile("^([^#\+!%\$]+)")
    type_re = re.compile("#([^\+!%\$]+)")
    connector_re = re.compile("\+([^#!%\$]+)")
    disp_feature_re = re.compile("!([^#!%\$]+)")
    const_re = re.compile("%([^#!%\$]+)")
    const_type_re = re.compile("\$([^#!%\$]+)$")

    node_name_match = re.search(node_name_re, nodeName)
    type_match = re.search(type_re, nodeName)
    connector_match = re.search(connector_re, nodeName)
    disp_feature_match = re.search(disp_feature_re, nodeName)
    const_match = re.search(const_re, nodeName)
    const_type_match = re.search(const_type_re, nodeName)

    if node_name_match:
        cleaned_up_node_name = node_name_match.group(1)
    if type_match:
        if type_match.group(1) == "footp":
            attributes["type"] = "foot"
        elif type_match.group(1) == "substp":
            attributes["type"] = "subst"
        elif type_match.group(1) == "headp":
            attributes["type"] = "anchor"
        elif type_match.group(1) == "NA":
            attributes["type"] = "nadj"
        else:
            attributes["type"] = "std"
    if connector_match:
        attributes["connector"] = connector_match.group(1)
    if disp_feature_match:
        attributes["display-feature"] = disp_feature_match.group(1)
    if const_match:
        attributes["constraints"] = const_match.group(1)
    if const_type_match:
        attributes["constraint-type"] = const_type_match.group(1)

    return attributes, cleaned_up_node_name

def bracketToDict(bracket_string, node_feature_dict):
    """
    string, dictionary -> dictionary
    Parse the bracket representation of the trees from the *.trees files.
    Return a dictionary that represents the tree.
    Each node has the attributes name (node name), features (as given in
    node_feature_dict) and children (list of nodes).
    """

    # in this case, bracket_strings are read as
    # "((bracket A) dominates (bracket B) and (bracket C))"

    result_dict = {}

    # remove surrounding brackets that have no value
    #surrounding_brackets = re.compile("^\s*\(([^()]*)\)\s*$")
    surrounding_brackets = re.compile("^\s*\((.*)\)\s*$")
    bracket_string = re.sub(surrounding_brackets, r"\1", bracket_string)

    # cleaning up node names in bracket_string
    simple_nodename = re.compile("\"([A-Za-z_0-9]+)\"\s*\.\s*\"\s*\"")
    compound_nodename = re.compile("\"([A-Za-z_0-9]+)\"\s*\.\s*\"([A-Za-z_0-9]+)\"")
    bracket_string = re.sub(simple_nodename, r"\1", bracket_string)
    bracket_string = re.sub(compound_nodename, r"\1_\2", bracket_string)

    # sticking type information to the relevant node, e.g. :substp T, :footp T
    type_info = re.compile("(\s*):([a-z]*)\s*T")
    bracket_string = re.sub(type_info, r"#\2", bracket_string) # to keep Type info

    # sticking connector information to the relevant node, e.g. :connector :LINE
    conn_info = re.compile("(\s*):connector\s*:(LINE)")
    bracket_string = re.sub(conn_info, r"+\2", bracket_string) # to keep connector info
    #bracket_string = re.sub(conn_info, r"", bracket_string) # to discard connector info

    # sticking display-feature information to the relevant node
    display_feature_info = re.compile("(\s*):(display)-feature\?\s*T")
    bracket_string = re.sub(display_feature_info, r"!\2", bracket_string)

    # sticking constraints info to relevant node, e.g. :constraints "NA"
    constraints_info = re.compile("(\s*):constraints\s+\"([^\"]*)\"\s*")
    bracket_string = re.sub(constraints_info, r"%\2", bracket_string)

    # sticking constraint-type info to the relevant node, e.g. :constraint-type :NA
    constraint_type_info = re.compile("(\s*):constraint-type\s+:([^\(\)]*)\s*")
    bracket_string = re.sub(constraint_type_info, r"$\2", bracket_string)

    # cleaning up bracket structure of bracket_string;
    # remove brackets that enclose a single node
    useless_brackets = re.compile("\(([A-Za-z_0-9#\+!%$\"]+\s*)\)")
    while re.search(useless_brackets, bracket_string):
        bracket_string = re.sub(useless_brackets, r"\1", bracket_string)

    # easy case: no brackets left in the string
    final_nodename = re.compile("[A-Za-z_0-9#\+!%$]+\s*")
    node_name_no_info = re.compile("^[^#\+!%$\s]+")
    if not "(" in bracket_string and not ")" in bracket_string:
        nodes = re.findall(final_nodename, bracket_string)
        node_name_only = re.findall(node_name_no_info, nodes[0])[0]
        if node_name_only in node_feature_dict.keys():
            node_features = node_feature_dict[node_name_only]
        else:
            node_features = {}

        result_dict = {"name": nodes[0].rstrip("#+!%$ "), "children": [], "features": node_features}
        for daughter in nodes[1:]:
            daughter_name_only = re.findall(node_name_no_info, daughter)[0]
            if daughter_name_only in node_feature_dict.keys():
                daughter_features = node_feature_dict[daughter_name_only]
            else:
                daughter_features = {}
            result_dict["children"].append({"name": daughter.rstrip("#+!%$ "), "children": [], "features": daughter_features})
        return result_dict

    # hard case: still brackets left - call this function again
    else:
        # first node definitely dominates everything that comes after
        root = re.findall(final_nodename, bracket_string)[0]
        rest = re.sub(root, "", bracket_string)

        # divide rest into list of siblings (daughters to root)
        children = identify_siblings(rest, final_nodename)

        first_level_children = []
        for child in children:
            first_level_children.append(bracketToDict(child, node_feature_dict))
        root_name_only = re.findall(node_name_no_info, root)[0]
        if root_name_only in node_feature_dict.keys():
            root_features = node_feature_dict[root_name_only]
        else:
            root_features = {}

        result_dict = {"name": root.rstrip("#+!%$ "), "children":first_level_children, "features": root_features}
        return result_dict


def identify_siblings(string, final_nodename):
    """
    string, string -> list
    Split up given string (part of a bracket structure from a *.trees file)
    into a list of sibling node brackets.
    Return a list of strings.
    Ex. input string:   "V#headp  (PP_1 (P_1 to )  NP_1#substp )"
    Ex. output list:    ['V#headp  ', '(PP_1 (P_1 to )  NP_1#substp )'].
    """
    complex_siblings = []
    bracket_levels = 0
    sibling_start_index = None
    siblings = []

    # find start and end index of each sibling
    for index, char in enumerate(string):
        if char == "(":
            if bracket_levels == 0:
                sibling_start_index = index
            bracket_levels += 1

        elif char == ")":
            bracket_levels -= 1
            if bracket_levels == 0:
                complex_siblings.append((sibling_start_index, index))

    # generate list of all siblings (simple or bracketed)
    prev_index = 0
    for start, end in complex_siblings:
        for atomar_sibling in re.findall(final_nodename, string[prev_index:start]):
            siblings.append(atomar_sibling)
        siblings.append(string[start:end+1])
        prev_index = end+1
    # add anything that is located to the right of the last bracketed sibling - this
    # will always be another sibling, never a daughter node
    for atomar_sibling in re.findall(final_nodename, string[complex_siblings[-1][1]+1:]):
        siblings.append(atomar_sibling)

    return siblings

def collect_vars(hierarchy):
    """
    dictionary -> set
    Walk through all features of all nodes in a tree and collect all used
    variable names. This is needed when we create new variables because we
    want to make sure they're really new.
    Return a set of used variables.
    """
    used_vars = set()
    if "b" in hierarchy["features"]:
        for val in hierarchy["features"]["b"].values():
            if val.startswith("@"):
                used_vars.add(val)
    if "t" in hierarchy["features"]:
        for val in hierarchy["features"]["t"].values():
            if val.startswith("@"):
                used_vars.add(val)
    if hierarchy["children"] != []:
        for child in hierarchy["children"]:
            used_vars = used_vars.union(collect_vars(child))
    return used_vars


def mergeDicts(absoluteValues, variableMappings):
    """
    dict, dict -> dict
    Generate a dictionary that contains the absolute feature values as well
    as feature values that are variable names.
    """
    mergedDict = absoluteValues.copy()
    for variable in variableMappings:
        for node in variableMappings[variable]:
            for position in variableMappings[variable][node]:
                feature = variableMappings[variable][node][position]
                if node in absoluteValues:
                    if position in absoluteValues[node]:
                        if feature in absoluteValues[node][position]:
                            mergedDict[node][position].update({feature: variable})
                        else:
                            mergedDict[node][position][feature] = variable
                    else:
                        mergedDict[node][position] = {feature: variable}
                else:
                    mergedDict[node]= {position: {feature: variable}}

    return mergedDict


def prettifyXMLDocument(xmlContent):
    """
    string -> string
    Format XML document content in a nicer, more readable way.
    """
    reparsed = minidom.parseString(xmlContent)
    reparsed = reparsed.toprettyxml(indent="    ")
    while "\n\n" in reparsed:
        reparsed = re.sub("\n\s*\n", "\n", reparsed)
    return reparsed

def collectXMLDocuments(xmlpath):
    """
    string -> None
    Read all XML documents from xml directory and aggregate into one giant document.
    """
    grammarfile = open(xmlpath+"/grammar.xml", "w", encoding="utf8")
    grammar = ET.Element("grammar")
    xmlpath = xmlpath.strip("/")
    for directory in os.listdir(xmlpath):
        # check if directory is a valid directory
        if os.path.isdir(xmlpath+"/"+directory):
            for xmlfile in os.listdir(xmlpath+"/"+directory):
                    tree = ET.parse(xmlpath+"/"+directory+"/"+xmlfile)
                    root = tree.getroot()
                    # each document contains exactly one entry
                    grammar.extend(root)

    print('<?xml version="1.0" encoding="utf-8" standalone="no" ?>\n<!DOCTYPE grammar SYSTEM "xmg-tag.dtd,xml">', file=grammarfile)
    output = ET.tostring(grammar)

    print(prettifyXMLDocument(output).split(">", 1)[1].strip(), file=grammarfile)
    grammarfile.close()



