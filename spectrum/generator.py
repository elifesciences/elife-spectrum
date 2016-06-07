import re
from datetime import datetime
from jinja2 import Template
from os import path, mkdir, getpid, remove
from zipfile import ZipFile
from glob import glob
from shutil import copy, rmtree

def article_zip(template_id):
    template = _choose_template(template_id)
    id = "%s%05d" % (datetime.now().strftime("%Y%m%d%H%M%S"), getpid())
    generated_article_directory = '/tmp/' + path.basename(template).replace(template_id, id)
    mkdir(generated_article_directory)
    generated_files = []
    for file in glob(template + "/*"):
        generated_file = _generate(file, id, generated_article_directory, template_id)
        generated_files.append(generated_file)
    zip_filename = '/tmp/' + path.basename(template).replace(template_id, id) + '.zip'
    figure_names = []
    with ZipFile(zip_filename, 'w') as zip_file:
        for generated_file in generated_files:
            zip_file.write(generated_file, path.basename(generated_file))
            match = re.match(r".*/elife-.+-(.+)\.tif", generated_file)
            if match:
                figure_names.append(match.groups()[0])
    print("Generated %s with figures %s" % (zip_filename, figure_names))
    return ArticleZip(id, zip_filename, figure_names)

def clean():
    for entry in glob('/tmp/elife*'):
        if path.isdir(entry):
            rmtree(entry)
            print("Deleted directory %s" % entry)
        else:
            remove(entry)
            print("Deleted file %s" % entry)

def all_stored_articles():
    articles = []
    for template_directory in glob('spectrum/templates/elife-*-*-*'):
        match = re.match(r".*/elife-(.+)-.+-.+", template_directory)
        assert match is not None
        assert len(match.groups()) == 1
        articles.append(match.groups()[0])
    return articles

def _choose_template(template_id):
    templates_pattern = './spectrum/templates/elife-%s-*-*' % template_id
    templates_found = glob(templates_pattern)
    assert len(templates_found) == 1, "Found multiple candidate templates: %s" % templates_found
    return templates_found[0]

def _generate(filename, id, generated_article_directory, template_id):
    filename_components = path.splitext(filename)
    target = generated_article_directory + '/' + path.basename(filename).replace(template_id, id)
    assert len(filename_components) == 2
    extension = filename_components[1]
    if extension == '.jinja':
        with open(filename, 'r') as template_file:
            data = template_file.read().decode('UTF-8')
        template = Template(data)
        content = template.render(article = { 'id': id })
        target = target.replace('.jinja', '')
        with open(target, 'w') as target_file:
            target_file.write(content.encode('utf-8'))
    else:
        copy(filename, target)
    return target

class ArticleZip:
    def __init__(self, id, filename, figure_names = []):
        self._id = id
        self._filename = filename
        self._figure_names = figure_names

    def id(self):
        return self._id

    def doi(self):
        return '10.7554/eLife.' + self._id

    def filename(self):
        return self._filename

    def figure_names(self):
        return self._figure_names
