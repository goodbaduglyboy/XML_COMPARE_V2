import glob
from pprint import pprint
from lxml import etree
import os
import xtdiff
import pandas as pd
import sys,datetime 
from os.path import basename,join,splitext,isdir,exists,isfile
import re

def check_validDirectory(string):
    if not isdir(string):
        msg = "%r is not a valid path" % string
        raise argparse.ArgumentTypeError(msg)
    return string

import argparse
parser = argparse.ArgumentParser()
parser.add_argument("source_path", help="Source directory where xmls are placed" ,type=check_validDirectory)
parser.add_argument("target_path", help="Target directory where xmls are placed" ,type=check_validDirectory)
parser.add_argument("log_file_path", help="Directory where log files are placed" ,type=check_validDirectory)
args = parser.parse_args()


#global variable declaration 
# src_path ='C:/Users/X118754/Desktop/python/testdata/src'
# tgt_path ='C:/Users/X118754/Desktop/python/testdata/tgt'
src_path = args.source_path
tgt_path = args.target_path

# xml_path = 'C:/Users/X118754/Desktop/python/testdata/data'
# xml_path = 'C:/Users/X118754/Desktop/python/testdata'

# log_file_path = 'C:/Users/X118754/Desktop/python/testdata/logs'
log_file_path = args.log_file_path



#----------------------------------------------------------------------------------

def sort_nodes(node) :
    links = node.xpath("./PublicID//text()")
    # for leaf_node in node :
    #     print(links[0] if len(links) != 0 else etree.tostring(leaf_node,pretty_print=False,method='xml'))
    node[:] = sorted(node,key = lambda leaf_node : links[0] if len(links) != 0 else etree.tostring(leaf_node,pretty_print=False,method='xml'))
    return

def sort_node_attributes(node) :

    #copy the attributes to a dictionary
    d = dict(node.attrib)

    # clear all the attributes
    node.attrib.clear()

    # reset attributes using sorted values
    for key,val in sorted(d) :
        node.set(key,val)


    
def sort(node):
    """ Sort children along tag and given attribute.
    if attr is None, sort along all attributes"""

    if not isinstance(node.tag, str):
        # PYTHON 2: use basestring instead
        # not a TAG, it is comment or DATA
        # no need to sort
        return

    if len(node) != 0 :
        for child in node:
            sort(child)
        #sort all child elments based on element converted to text
        sort_nodes(node)        
    else :
        sort_node_attributes(node)

old_out = sys.stdout
class append_datetime:

    """Stamped stdout."""
    nl = True
    def write(self, x):
        """Write function overloaded."""
        if x == '\n':
            old_out.write(x)
            self.nl = True
        elif self.nl:
            old_out.write('%s : %s' % (datetime.datetime.now().strftime("%d-%b-%Y %I:%M:%S %p"), x))
            self.nl = False
        else:
            old_out.write(x)
    def flush(self):
        self.flush

sys.stdout = append_datetime()



def dict_compare(d1, d2):
    d1_keys = set(d1.keys())
    d2_keys = set(d2.keys())
    intersect_keys = d1_keys.intersection(d2_keys)
    added = d1_keys - d2_keys
    removed = d2_keys - d1_keys
    modified = {o : (d1[o], d2[o]) for o in intersect_keys if d1[o] != d2[o]}
    same = set(o for o in intersect_keys if d1[o] == d2[o])
    return added, removed, modified, same

def getfilelist_bydirectory(src_path,tgt_path):
    # if files have the same name but in a different directory : 
    file_list = list()
    src_xml_files = glob.glob(src_path+'\\*.xml')
    for filename in src_xml_files:        
        tgt_file = join(tgt_path,basename(filename))
        if  isfile(tgt_file) :
            file_list.append([filename,tgt_file])
        else :
            print(filename+" file is missing")

    return file_list

def getfilelist_byprefix(path) :
    # if files have names with a different prefix:
    #find unique set of prefixes
    filePrefixes = set()
    for filename in glob.glob(join(path,'*.xml')) : # **/ , recursive=True --optional for the above command as it recursively finds in subdirectories         
        filePrefixes.add(splitext(filename)[0].rsplit('_',1)[0])

    #group set of prefix files and put them in list for easy comparison
    file_list = list()
    for prefix in filePrefixes :
        groupedfile_names = glob.glob(join(path,prefix+'*.xml')) 
        # , recursive=True
        if len(groupedfile_names) != 2 :
            print(groupedfile_names[0]+" file is missing")
        else :
            file_list.append(groupedfile_names)
    return file_list

def print_path_of_elems(elem, elem_path=""):
    for child in elem:
        if child.getchildren() and child.text:
            # node with child elements => recurse
            print_path_of_elems(child, "{}.{}".format(elem_path, child.tag))
        else:
            # leaf node => print
            print("{}.{}".format(elem_path, child.tag))


def compare_xmls(src_file,tgt_file,path_or_prefix,reverse_result) :
    differences_list = list()
    parser = etree.XMLParser(remove_blank_text=True)

    src_tree = etree.parse(src_file,parser=parser)
    tgt_tree = etree.parse(tgt_file,parser=parser)

    sort(src_tree.getroot())
    sort(tgt_tree.getroot())

    src_string = etree.tostring(src_tree.getroot(),pretty_print=True,method='xml')
    tgt_string= etree.tostring(tgt_tree.getroot(),pretty_print=True,method='xml')

    sorted_src_file = open(src_file+"_sorted","w")
    sorted_tgt_file = open(tgt_file+"_sorted","w")

    sorted_src_file.write(src_string)
    sorted_tgt_file.write(tgt_string)

        #if path then get the filename else if prefix then get prefix.
    if path_or_prefix == 'path' :
        filename= basename(src_file)
    else :
        filename= splitext(basename(src_file))[0].rsplit('_',1)[0]


    # walk the source tree and compare it against the target
    # for child in src_tree.getroot():
    for src_element in src_tree.iter() :

        xpath = src_tree.getpath(src_element)
        tgt_root = tgt_tree.getroot()
        # print(xpath)
        #first check if element is present

        humanized_xpath = re.sub(r'\[.*?\]','',xpath.replace('/','.')) 
        humanized_xpath = re.sub(r'^\.','',humanized_xpath)
        try :
            tgt_element = tgt_root.xpath(xpath)[0]

            # compare elements inner text only when the element is a leaf node 
            if not src_element.getchildren() :
                src_text = src_element.text
                tgt_text = tgt_element.text
                # print("text comparison")
                
                # to fix the duplciate issue when reports are generated
                if reverse_result :                    
                    if src_text == tgt_text :
                        differences_list.append( (filename,humanized_xpath,tgt_text,src_text,'No') )
                        # print((filename,humanized_xpath,src_text,tgt_text,'no'))
                    else :
                        differences_list.append( (filename,humanized_xpath,tgt_text,src_text,'yes') )
                        # print((filename,humanized_xpath,src_text,tgt_text,'yes'))
                else :
                    if src_text == tgt_text :
                        differences_list.append( (filename,humanized_xpath,src_text,tgt_text,'No') )
                        # print((filename,humanized_xpath,src_text,tgt_text,'no'))
                    else :
                        differences_list.append( (filename,humanized_xpath,src_text,tgt_text,'yes') )
                        # print((filename,humanized_xpath,src_text,tgt_text,'yes'))


            # compare attributes
            # To get an independent snapshot of the attributes that does not depend on the XML tree
            src_attribs = dict(src_element.attrib) 
            tgt_attribs = dict(tgt_element.attrib)
            # print("attribs comparison")
            added, removed, modified, same = dict_compare(src_attribs, tgt_attribs)

            if reverse_result :
                import copy

                temp = copy.deepcopy(tgt_attribs)
                tgt_attribs = copy.deepcopy(src_attribs)
                src_attribs = temp

            for attribs in added :

                differences_list.append( (filename,humanized_xpath+"."+attribs,src_attribs.get(attribs," ")," ",'Additional Attribute') )
                # print((filename,humanized_xpath+"."+attribs,src_element.get(attribs),'','Additional Attribute'))

            for attribs in removed :
                differences_list.append( (filename,humanized_xpath+"."+attribs,src_attribs.get(attribs," "),tgt_attribs.get(attribs," "),'Attribute missing') )
                # print((filename,humanized_xpath+"."+attribs,src_attribs.get(attribs,""),'','Attribute missing'))

            for attribs in modified :
                differences_list.append( (filename,humanized_xpath+"."+attribs,src_attribs.get(attribs," "),tgt_attribs.get(attribs," "),'Yes') )
                # print((filename,humanized_xpath+"."+attribs,src_element.get(attribs,""),tgt_attribs.get(attribs,""),'Yes'))

            for attribs in same :
                differences_list.append( (filename,humanized_xpath+"."+attribs,src_attribs.get(attribs," "),tgt_attribs.get(attribs," "),'No') )
                # print( (filename,humanized_xpath+"."+attribs,src_element.get(attribs),tgt_attribs.get(attribs),'No') )

        #element is not present
        except IndexError:
            src_attribs = dict(src_element.attrib) 
            # tgt_attribs = dict(tgt_element.attrib)
            # if reverse_result :
            #     import copy                
            #     temp = copy.deepcopy(tgt_attribs)
            #     tgt_attribs = copy.deepcopy(src_attribs)
            #     src_attribs = temp

            # print("element not found")
            differences_list.append( (filename,humanized_xpath,(" " if src_element.text =="" or src_element.text is None else src_element.text)," ",'Element missing') )
            # differences_list.append( (filename,humanized_xpath,str(src_attribs)," ",'Element missing') )
            # print((filename,humanized_xpath,src_element.attrib,'','Element missing'))
        except etree.XPathEvalError:
            src_attribs = dict(src_element.attrib) 
            # tgt_attribs = dict(tgt_element.attrib)
            # if reverse_result :
            #     import copy                
            #     temp = copy.deepcopy(tgt_attribs)
            #     tgt_attribs = copy.deepcopy(src_attribs)
            #     src_attribs = temp

            differences_list.append( (filename,humanized_xpath,src_element.text," "," ",'Namespace issue') )

    # print("")
    return differences_list

# pprint(getfilelist_byprefix(xml_path))
# pprint(getfilelist_bydirectory(src_path,tgt_path))
path_or_prefix='path'

variance_report_file =open(join(log_file_path,"variance_report.csv"),'w')
variance_report_file.write("File Name,Attribute Name,Attribute Value Refactored,Attribute Value Existing"+"\n")

# variance_report_file.close()
# for src_file,tgt_file in getfilelist_byprefix(xml_path) :
cols = ['File Name','SRC Attribute Count','TGT Attribute Count','Structure Mismatch']
df= pd.DataFrame(columns =cols)
dflist = []
for src_file,tgt_file in getfilelist_bydirectory(src_path,tgt_path) :   
    #do a source minus target first and then do the reverse 
    srcsize = os.path.getsize(src_file)
    print 'SRC FILE SIZE---',srcsize
    tgtsize = os.path.getsize(tgt_file)
    print 'TGT FILE SIZE---', tgtsize
    
    src_tree = etree.parse(src_file)
    srccount = sum(1 for _ in src_tree.iter("*"))
    print 'SRC XML ATTRIBUTE COUNT---',srccount
    sroot = src_tree.getroot()
    ditresult =[]
    for child in sroot:
        for child1 in child:         
            ditresult.append(child1.tag)
    # print ditresult

    # print 'SRC TREE LENGTH---',len(list(sroot))

    tgt_tree = etree.parse(tgt_file)    
    tgtcount = sum(1 for _ in tgt_tree.iter("*"))
    print 'TGT XML ATTRIBUTE COUNT---',tgtcount

    troot = tgt_tree.getroot()
    ditresult =[]
    for child in troot:
        for child1 in child:         
            ditresult.append(child1.tag)
    # print ditresult

    # print 'TGT TREE LENGTH---', len(list(troot))
    
    print(src_file+"\n---------------\n")

    if srccount == tgtcount:
        src_to_tgt_list = compare_xmls(src_file,tgt_file,path_or_prefix,False) 
        tgt_to_src_list = compare_xmls(tgt_file,src_file,path_or_prefix,True)
        # compare_xml_v2(src_file,tgt_file)
        src_to_tgt_list.extend(tgt_to_src_list)
        difference_set = set(src_to_tgt_list)    
        
        with open(join(log_file_path,splitext(basename(src_file))[0]+"_validation_results.csv"),'w') as logfile :
            logfile.write("File Name,Attribute Name,Attribute Value Refactored,Attribute Value Existing,Variance Found"+"\n")
            for diffs in difference_set :
                formatted_string = re.sub(r'[\r\n]','<<newline-char>>', '\"'+'","'.join(str(s) if s is not None else ' ' for s in diffs if s ))+'\"\n'
                logfile.write(formatted_string)
                if (diffs[4] != 'No') :
                    variance_report_file.write(formatted_string)
    else:
        
        
        # print df
        if path_or_prefix == 'path' :
            filename= basename(src_file)
        else :
            filename= splitext(basename(src_file))[0].rsplit('_',1)[0]
        cols = ['File Name','SRC Attribute Count','TGT Attribute Count','Structure Mismatch']
        
        
        strng = 'XML element count mismatch. Files are having mismatching structure. Further comparsion cannot be performed'
        
        listnew = [filename,srccount,tgtcount,strng]
        dflist.append(listnew)
        
        dfrow = pd.DataFrame(dflist,columns = cols)
        dfnew = pd.concat([df,dfrow])

# print dfnew        
writer = pd.ExcelWriter(log_file_path+'Structural_Mismatch_Report.xlsx')
dfrow.to_excel(writer,'Report',index=False)
worksheet = writer.sheets['Report']
worksheet.set_column('A:C',30)
worksheet.set_column('D:D',80)

writer.save()
        


print("Completed Comparison")