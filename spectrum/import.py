import glob
import os
import re
import subprocess
import sys
import zipfile

def from_zip(filename):
    zip = zipfile.ZipFile(filename, "r")
    (article_full_name, _) = os.path.splitext(os.path.basename(filename))
    target_directory = os.path.realpath('./spectrum/templates/%s' % article_full_name)
    if not os.path.exists(target_directory):
        os.mkdir(target_directory)
    for each in zip.namelist():
        zip.extract(each, target_directory)
    xml_files = glob.glob('%s/elife-[0-9][0-9][0-9][0-9][0-9].xml' % target_directory)
    assert len(xml_files) > 0, 'No XML files correctly named found in the article package: %s' % target_directory
    assert len(xml_files) == 1, 'Too many XML files are named like an article in the package: %s' % xml_files
    xml_of_article_file = xml_files[0]
    xml_of_article_template_file = xml_of_article_file + '.jinja'
    with open(xml_of_article_template_file, 'w') as template:
        subprocess.call(['xmllint', '--format', xml_of_article_file], stdout=template)
    os.remove(xml_of_article_file)
    match = re.match(r"elife-([0-9]+)-.*-.*", article_full_name)
    assert match is not None, \
            "Could not match an id inside the article full name %s" % article_full_name
    assert len(match.groups()) == 1
    article_id = match.groups()[0]
    search_and_replace(xml_of_article_template_file, article_id, "{{ article['id'] }}")


def search_and_replace(filename, search, replace):
    contents = ''
    with open(filename, 'r') as file:
        contents = file.read()

    contents = contents.replace(search, replace)

    with open(filename, 'w') as file:
        file.write(contents)


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: %s ZIP_FILENAME\n" % sys.argv[0])
        exit(1)
    from_zip(sys.argv[1])
