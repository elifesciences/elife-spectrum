import glob
import os
import re
import subprocess
import sys
import zipfile
import xml.etree.ElementTree

def from_zip(filename):
    zip = zipfile.ZipFile(filename, "r")
    (article_full_name, _) = os.path.splitext(os.path.basename(filename))
    target_directory = os.path.realpath('./spectrum/templates/%s' % article_full_name)
    if not os.path.exists(target_directory):
        os.mkdir(target_directory)
    for each in zip.namelist():
        zip.extract(each, target_directory)
    xml_files = glob.glob('%s/*.xml' % target_directory)
    assert len(xml_files) == 1, 'Too many XML files were found in the article package'
    xml_of_article_file = xml_files[0]
    xml_of_article_template_file = xml_of_article_file + '.jinja'
    duplicate(xml_of_article_file, xml_of_article_template_file)
    os.remove(xml_of_article_file)
    match = re.match(r"elife-([0-9]+)-.*-.*", article_full_name)
    assert match is not None, \
            "Could not match an id inside the article full name %s" % article_full_name
    assert len(match.groups()) == 1
    article_id = match.groups()[0]
    search_and_replace(xml_of_article_template_file, article_id, "{{ article['id'] }}")
    remove_related_articles(xml_of_article_template_file)
    format(xml_of_article_template_file)

def duplicate(source, target):
    with open(source) as s:
        with open(target, "w") as t:
            for line in s:
                t.write(line)

def search_and_replace(filename, search, replace):
    contents = ''
    with open(filename, 'r') as file:
        contents = file.read()

    contents = contents.replace(search, replace)

    with open(filename, 'w') as file:
        file.write(contents)

def remove_related_articles(filename):
    """Frickin XML parsers do not work
    
    LXML replaces my UTF-8 characters with HTML entities such as &#XA9
    BeautifulSoup inserts a goddamn HTML tag around the document"""

    contents = ''
    with open(filename, 'r') as file:
        contents = file.read()

    # non-greedy apparently
    contents = re.sub(r"(<related-article.*/>)", "<!--\\1-->", contents)

    with open(filename, 'w') as file:
        file.write(contents)
    

    #import lxml.etree as le
    #with open(filename, 'r') as f:
    #    doc = le.parse(f)
    #    for elem in doc.xpath('//related-article'):
    #        parent = elem.getparent()
    #        parent.remove(elem)
    #with open(filename, 'w') as f:
    #    f.write(
    #            le.tostring(doc, encoding='unicode').encode('UTF-8')
    #            )

    #from bs4 import BeautifulSoup, Comment
    #contents = ''
    #with open(filename, 'r') as file:
    #    contents = file.read()
    #article = BeautifulSoup(contents, 'lxml')
    #[t.extract() for t in article.findAll('related-article')]
    #with open(filename, 'w') as file:
    #    file.write(article.prettify().encode('UTF-8'))

def format(filename):
    result = subprocess.check_output(['xmllint', '--format', filename])
    with open(filename, 'w') as target:
        target.write(result)



if __name__ == '__main__':
    if len(sys.argv) < 2:
        print "Usage: %s ZIP_FILENAME\n" % sys.argv[0]
        exit(1)
    from_zip(sys.argv[1])
