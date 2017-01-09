import glob
import os
from os import path
import random
import re
import shutil
import zipfile

import jinja2
from spectrum import logger

LOGGER = logger.logger(__name__)

def generate_article_id(template_id):
    # 2^31 = 2147483648 which is the maximum id
    maximum_prefix = 21474 # covers until template_id reaches 83648
    prefix = random.randrange(1, maximum_prefix + 1)
    return str(prefix * 100000 + int(template_id))

def article_zip(template_id):
    (template, kind) = _choose_template(template_id)
    id = generate_article_id(template_id)
    generated_article_directory = '/tmp/elife-%s-%s-r1' % (id, kind)
    os.mkdir(generated_article_directory)
    generated_files = []
    for file in glob.glob(template + "/*"):
        generated_file = _generate(file, id, generated_article_directory, template_id)
        generated_files.append(generated_file)
    zip_filename = generated_article_directory + '.zip'
    figure_names = []
    with zipfile.ZipFile(zip_filename, 'w') as zip_file:
        for generated_file in generated_files:
            zip_file.write(generated_file, path.basename(generated_file))
            match = re.match(r".*/elife-\d+-(.+).tif", generated_file)
            if match:
                figure_names.append(match.groups()[0])
    LOGGER.info("Generated %s with figures %s", zip_filename, figure_names, extra={'id': id})
    has_pdf = len(glob.glob(template + "/*.pdf")) >= 1
    return ArticleZip(id, zip_filename, generated_article_directory, revision=1, version=1, figure_names=figure_names, has_pdf=has_pdf)

def clean():
    for entry in glob.glob('/tmp/elife*'):
        if path.isdir(entry):
            shutil.rmtree(entry)
            LOGGER.info("Deleted directory %s", entry)
        else:
            os.remove(entry)
            LOGGER.info("Deleted file %s", entry)

def all_stored_articles():
    articles = []
    for template_directory in glob.glob('spectrum/templates/elife-*'):
        match = re.match(r".*/elife-(\d+)-.+", template_directory)
        assert match is not None
        assert len(match.groups()) == 1
        articles.append(match.groups()[0])
    return articles

def _choose_template(template_id):
    templates_pattern = './spectrum/templates/elife-%s-*-*' % template_id
    templates_found = glob.glob(templates_pattern)
    assert len(templates_found) == 1, "Found multiple candidate templates: %s" % templates_found
    chosen = templates_found[0]
    match = re.match(r'.*/elife-\d+-(vor|poa)-(r|v)\d+', chosen)
    assert match is not None, ("Bad name for template directory %s" % chosen)
    assert len(match.groups()) == 2
    kind = match.groups()[0] # vor or poa
    return (chosen, kind)


def _generate(filename, id, generated_article_directory, template_id):
    filename_components = path.splitext(filename)
    generated_filename = path.basename(filename).replace(template_id, id)
    target = generated_article_directory + '/' + generated_filename
    assert len(filename_components) == 2
    extension = filename_components[1]
    if extension == '.jinja':
        with open(filename, 'r') as template_file:
            data = template_file.read().decode('UTF-8')
        template = jinja2.Template(data)
        content = template.render(article={'id': id})
        target = target.replace('.jinja', '')
        with open(target, 'w') as target_file:
            target_file.write(content.encode('utf-8'))
    else:
        shutil.copy(filename, target)
    return target

class ArticleZip:
    def __init__(self, id, filename, directory, revision, version, figure_names=None, has_pdf=False):
        self._id = id
        self._filename = filename
        self._directory = directory
        self._revision = revision
        self._version = version
        self._figure_names = figure_names if figure_names else []
        self._has_pdf = has_pdf

    def id(self):
        return self._id

    def doi(self):
        return '10.7554/eLife.' + self._id

    def version(self):
        return self._version

    def filename(self):
        return self._filename

    def figure_names(self):
        return self._figure_names

    def has_figures(self):
        return len(self._figure_names) > 0

    def has_pdf(self):
        return self._has_pdf

    def new_revision(self, version=None):
        if version:
            new_version = version
        else:
            new_version = self._version
        new_revision = self._revision + 1
        new_filename = re.sub(r'-(r|v)\d+.zip$', ('-r%s.zip' % new_revision), self._filename)
        shutil.copy(self._filename, new_filename)
        new_directory = re.sub(r'-(r|v)\d+$', ('-r%s' % new_revision), self._directory)
        shutil.copytree(self._directory, new_directory)
        return ArticleZip(self._id, new_filename, new_directory, new_revision, new_version, self._figure_names, self._has_pdf)

    def new_version(self, version):
        # what is changed is actually the "run"
        new_revision = self._revision + 1
        new_filename = re.sub(r'-(r|v)\d+.zip$', ('-v%s.zip' % version), self._filename)
        shutil.copy(self._filename, new_filename)
        new_directory = re.sub(r'-(r|v)\d+$', ('-v%s' % version), self._directory)
        shutil.copytree(self._directory, new_directory)
        return ArticleZip(self._id, new_filename, new_directory, new_revision, version, self._figure_names, self._has_pdf)

    def replace_in_text(self, replacements):
        """Beware: violates immutability, as it modifies the file in place for performance reasons"""
        LOGGER.info("Replacing %s in article", replacements, extra={'id': self._id})
        with zipfile.ZipFile(self._filename, 'w') as zip_file:
            for file in glob.glob(self._directory + "/*"):
                if file.endswith('.xml'):
                    with open(file) as xml:
                        contents = xml.read()
                    for search, replace in replacements.iteritems():
                        contents = contents.replace(search, replace)
                    with open(file, 'w') as xml:
                        xml.write(contents)
                zip_file.write(file, path.basename(file))
        return self

    def clean(self):
        os.remove(self._filename)
        LOGGER.info("Deleted file %s", self._filename)
        shutil.rmtree(self._directory)
        LOGGER.info("Deleted directory %s", self._directory)

