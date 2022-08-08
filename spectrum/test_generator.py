from unittest import mock
from . import generator

def test_generate_article_id():
    cases = [
        (9560, '9009560'),
        ('09560', '9009560'),
        ('00625', '9000625'),
        (1234567890, '91234567890'),
        ('1234567890', '91234567890'),
    ]
    for given, expected in cases:
        with mock.patch('spectrum.generator.random.randrange', return_value=9):
            assert generator.generate_article_id(given) == expected
