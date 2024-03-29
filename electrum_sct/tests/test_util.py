from decimal import Decimal

from electrum_sct.util import (format_satoshis, format_fee_satoshis, parse_URI,
                               is_hash256_str)

from . import SequentialTestCase


class TestUtil(SequentialTestCase):

    def test_format_satoshis(self):
        self.assertEqual("0.00001234", format_satoshis(1234))

    def test_format_satoshis_negative(self):
        self.assertEqual("-0.00001234", format_satoshis(-1234))

    def test_format_fee_float(self):
        self.assertEqual("1.7", format_fee_satoshis(1700/1000))

    def test_format_fee_decimal(self):
        self.assertEqual("1.7", format_fee_satoshis(Decimal("1.7")))

    def test_format_fee_precision(self):
        self.assertEqual("1.666",
                         format_fee_satoshis(1666/1000, precision=6))
        self.assertEqual("1.7",
                         format_fee_satoshis(1666/1000, precision=1))

    def test_format_satoshis_whitespaces(self):
        self.assertEqual("     0.0001234 ",
                         format_satoshis(12340, whitespaces=True))
        self.assertEqual("     0.00001234",
                         format_satoshis(1234, whitespaces=True))

    def test_format_satoshis_whitespaces_negative(self):
        self.assertEqual("    -0.0001234 ",
                         format_satoshis(-12340, whitespaces=True))
        self.assertEqual("    -0.00001234",
                         format_satoshis(-1234, whitespaces=True))

    def test_format_satoshis_diff_positive(self):
        self.assertEqual("+0.00001234",
                         format_satoshis(1234, is_diff=True))

    def test_format_satoshis_diff_negative(self):
        self.assertEqual("-0.00001234", format_satoshis(-1234, is_diff=True))

    def _do_test_parse_URI(self, uri, expected):
        result = parse_URI(uri)
        self.assertEqual(expected, result)

    def test_parse_URI_address(self):
        #self._do_test_parse_URI('bitcoin:15mKKb2eos1hWa6tisdPwwDC1a5J1y9nma',
        # Converted to SmartCryptoTech using `contrib/convertAddress.py` from SmartCryptoTech Core.
        self._do_test_parse_URI('smartcryptotech:N1LgXEXdjF7G37MPzgwyATN6joULz6LfdQ',
                                #{'address': '15mKKb2eos1hWa6tisdPwwDC1a5J1y9nma'})
                                # Converted to SmartCryptoTech using `contrib/convertAddress.py` from SmartCryptoTech Core.
                                {'address': 'N1LgXEXdjF7G37MPzgwyATN6joULz6LfdQ'})

    def test_parse_URI_only_address(self):
        #self._do_test_parse_URI('15mKKb2eos1hWa6tisdPwwDC1a5J1y9nma',
        # Converted to SmartCryptoTech using `contrib/convertAddress.py` from SmartCryptoTech Core.
        self._do_test_parse_URI('N1LgXEXdjF7G37MPzgwyATN6joULz6LfdQ',
                                #{'address': '15mKKb2eos1hWa6tisdPwwDC1a5J1y9nma'})
                                # Converted to SmartCryptoTech using `contrib/convertAddress.py` from SmartCryptoTech Core.
                                {'address': 'N1LgXEXdjF7G37MPzgwyATN6joULz6LfdQ'})


    def test_parse_URI_address_label(self):
        #self._do_test_parse_URI('bitcoin:15mKKb2eos1hWa6tisdPwwDC1a5J1y9nma?label=electrum%20test',
        # Converted to SmartCryptoTech using `contrib/convertAddress.py` from SmartCryptoTech Core.
        self._do_test_parse_URI('smartcryptotech:N1LgXEXdjF7G37MPzgwyATN6joULz6LfdQ?label=electrum%20test',
                                #{'address': '15mKKb2eos1hWa6tisdPwwDC1a5J1y9nma', 'label': 'electrum test'})
                                # Converted to SmartCryptoTech using `contrib/convertAddress.py` from SmartCryptoTech Core.
                                {'address': 'N1LgXEXdjF7G37MPzgwyATN6joULz6LfdQ', 'label': 'electrum test'})

    def test_parse_URI_address_message(self):
        #self._do_test_parse_URI('bitcoin:15mKKb2eos1hWa6tisdPwwDC1a5J1y9nma?message=electrum%20test',
        # Converted to SmartCryptoTech using `contrib/convertAddress.py` from SmartCryptoTech Core.
        self._do_test_parse_URI('smartcryptotech:N1LgXEXdjF7G37MPzgwyATN6joULz6LfdQ?message=electrum%20test',
                                #{'address': '15mKKb2eos1hWa6tisdPwwDC1a5J1y9nma', 'message': 'electrum test', 'memo': 'electrum test'})
                                # Converted to SmartCryptoTech using `contrib/convertAddress.py` from SmartCryptoTech Core.
                                {'address': 'N1LgXEXdjF7G37MPzgwyATN6joULz6LfdQ', 'message': 'electrum test', 'memo': 'electrum test'})

    def test_parse_URI_address_amount(self):
        #self._do_test_parse_URI('bitcoin:15mKKb2eos1hWa6tisdPwwDC1a5J1y9nma?amount=0.0003',
        # Converted to SmartCryptoTech using `contrib/convertAddress.py` from SmartCryptoTech Core.
        self._do_test_parse_URI('smartcryptotech:N1LgXEXdjF7G37MPzgwyATN6joULz6LfdQ?amount=0.0003',
                                #{'address': '15mKKb2eos1hWa6tisdPwwDC1a5J1y9nma', 'amount': 30000})
                                # Converted to SmartCryptoTech using `contrib/convertAddress.py` from SmartCryptoTech Core.
                                {'address': 'N1LgXEXdjF7G37MPzgwyATN6joULz6LfdQ', 'amount': 30000})

    def test_parse_URI_address_request_url(self):
        #self._do_test_parse_URI('bitcoin:15mKKb2eos1hWa6tisdPwwDC1a5J1y9nma?r=http://domain.tld/page?h%3D2a8628fc2fbe',
        # Converted to SmartCryptoTech using `contrib/convertAddress.py` from SmartCryptoTech Core.
        self._do_test_parse_URI('smartcryptotech:N1LgXEXdjF7G37MPzgwyATN6joULz6LfdQ?r=http://domain.tld/page?h%3D2a8628fc2fbe',
                                #{'address': '15mKKb2eos1hWa6tisdPwwDC1a5J1y9nma', 'r': 'http://domain.tld/page?h=2a8628fc2fbe'})
                                # Converted to SmartCryptoTech using `contrib/convertAddress.py` from SmartCryptoTech Core.
                                {'address': 'N1LgXEXdjF7G37MPzgwyATN6joULz6LfdQ', 'r': 'http://domain.tld/page?h=2a8628fc2fbe'})

    def test_parse_URI_ignore_args(self):
        #self._do_test_parse_URI('bitcoin:15mKKb2eos1hWa6tisdPwwDC1a5J1y9nma?test=test',
        # Converted to SmartCryptoTech using `contrib/convertAddress.py` from SmartCryptoTech Core.
        self._do_test_parse_URI('smartcryptotech:N1LgXEXdjF7G37MPzgwyATN6joULz6LfdQ?test=test',
                                #{'address': '15mKKb2eos1hWa6tisdPwwDC1a5J1y9nma', 'test': 'test'})
                                # Converted to SmartCryptoTech using `contrib/convertAddress.py` from SmartCryptoTech Core.
                                {'address': 'N1LgXEXdjF7G37MPzgwyATN6joULz6LfdQ', 'test': 'test'})

    def test_parse_URI_multiple_args(self):
        #self._do_test_parse_URI('bitcoin:15mKKb2eos1hWa6tisdPwwDC1a5J1y9nma?amount=0.00004&label=electrum-test&message=electrum%20test&test=none&r=http://domain.tld/page',
        # Converted to SmartCryptoTech using `contrib/convertAddress.py` from SmartCryptoTech Core.
        self._do_test_parse_URI('smartcryptotech:N1LgXEXdjF7G37MPzgwyATN6joULz6LfdQ?amount=0.00004&label=electrum-test&message=electrum%20test&test=none&r=http://domain.tld/page',
                                #{'address': '15mKKb2eos1hWa6tisdPwwDC1a5J1y9nma', 'amount': 4000, 'label': 'electrum-test', 'message': u'electrum test', 'memo': u'electrum test', 'r': 'http://domain.tld/page', 'test': 'none'})
                                # Converted to SmartCryptoTech using `contrib/convertAddress.py` from SmartCryptoTech Core.
                                {'address': 'N1LgXEXdjF7G37MPzgwyATN6joULz6LfdQ', 'amount': 4000, 'label': 'electrum-test', 'message': u'electrum test', 'memo': u'electrum test', 'r': 'http://domain.tld/page', 'test': 'none'})

    def test_parse_URI_no_address_request_url(self):
        self._do_test_parse_URI('smartcryptotech:?r=http://domain.tld/page?h%3D2a8628fc2fbe',
                                {'r': 'http://domain.tld/page?h=2a8628fc2fbe'})

    def test_parse_URI_invalid_address(self):
        self.assertRaises(BaseException, parse_URI, 'smartcryptotechinvalidaddress')

    def test_parse_URI_invalid(self):
        #self.assertRaises(BaseException, parse_URI, 'notbitcoin:15mKKb2eos1hWa6tisdPwwDC1a5J1y9nma')
        # Converted to SmartCryptoTech using `contrib/convertAddress.py` from SmartCryptoTech Core.
        self.assertRaises(BaseException, parse_URI, 'notsmartcryptotech:N1LgXEXdjF7G37MPzgwyATN6joULz6LfdQ')

    def test_parse_URI_parameter_polution(self):
        #self.assertRaises(Exception, parse_URI, 'bitcoin:15mKKb2eos1hWa6tisdPwwDC1a5J1y9nma?amount=0.0003&label=test&amount=30.0')
        # Converted to SmartCryptoTech using `contrib/convertAddress.py` from SmartCryptoTech Core.
        self.assertRaises(Exception, parse_URI, 'smartcryptotech:N1LgXEXdjF7G37MPzgwyATN6joULz6LfdQ?amount=0.0003&label=test&amount=30.0')

    def test_is_hash256_str(self):
        self.assertTrue(is_hash256_str('09a4c03e3bdf83bbe3955f907ee52da4fc12f4813d459bc75228b64ad08617c7'))
        self.assertTrue(is_hash256_str('2A5C3F4062E4F2FCCE7A1C7B4310CB647B327409F580F4ED72CB8FC0B1804DFA'))
        self.assertTrue(is_hash256_str('00' * 32))

        self.assertFalse(is_hash256_str('00' * 33))
        self.assertFalse(is_hash256_str('qweqwe'))
        self.assertFalse(is_hash256_str(None))
        self.assertFalse(is_hash256_str(7))
