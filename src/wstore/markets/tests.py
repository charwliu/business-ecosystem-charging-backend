
from urllib2 import HTTPError

from django.test import TestCase

from wstore.markets import markets_management
from wstore.models import Marketplace


class FakeMarketAdaptor():

    def __init__(self, url):
        pass

    def add_service(self, store, info):
        pass

    def delete_service(self, store, ser):
        pass

    def add_store(self, store_info):
        if store_info['store_uri'] == 'http://currentsiteerr.com':
            raise HTTPError('site', 500, 'Internal server error', None, None)

    def delete_store(self, store):
        pass


class RegisteringOnMarketplaceTestCase(TestCase):

    fixtures = ['reg_mark.json']

    @classmethod
    def setUpClass(cls):
        markets_management.MarketAdaptor = FakeMarketAdaptor
        super(RegisteringOnMarketplaceTestCase, cls).setUpClass()

    def test_basic_registering_on_market(self):

        markets_management.register_on_market('test_market', 'http://testmarket.com', 'http://currentsite.com')

        market = Marketplace.objects.get(name='test_market')

        self.assertEqual(market.name, 'test_market')
        self.assertEqual(market.host, 'http://testmarket.com/')

    def test_registering_already_registered(self):

        try:
            markets_management.register_on_market('test_market', 'http://testmarket.com', 'http://currentsiteerr.com')
        except Exception, e:
            error = True
            msg = e.message

        self.assertTrue(error)
        self.assertEquals(msg, 'Bad Gateway')

    def test_registering_existing_name(self):

        error = False
        try:
            markets_management.register_on_market('test_market1', 'http://testmarket.com', 'http://currentsite.com')
        except Exception, e:
            error = True
            msg = e.message

        self.assertTrue(error)
        self.assertEquals(msg, 'Marketplace name already in use')


class MarketPlacesRetievingTestCase(TestCase):

    fixtures = ['get_mark.json']

    def test_basic_retrieving_of_markets(self):

        markets = markets_management.get_marketplaces()

        self.assertEquals(len(markets), 3)
        self.assertEquals(markets[0]['name'], 'test_market1')
        self.assertEquals(markets[0]['host'], 'http://examplemarketplace1.com/')
        self.assertEquals(markets[1]['name'], 'test_market2')
        self.assertEquals(markets[1]['host'], 'http://examplemarketplace2.com/')
        self.assertEquals(markets[2]['name'], 'test_market3')
        self.assertEquals(markets[2]['host'], 'http://examplemarketplace3.com/')


class UnregisteringFromMarketplaceTestCase(TestCase):

    fixtures = ['del_mark.json']

    @classmethod
    def setUpClass(cls):
        markets_management.MarketAdaptor = FakeMarketAdaptor
        super(UnregisteringFromMarketplaceTestCase, cls).setUpClass()

    def test_basic_unregistering_from_market(self):

        markets_management.unregister_from_market('test_market')

        market = Marketplace.objects.all()
        self.assertEquals(len(market), 0)

    def test_unregistering_already_unregistered(self):

        error = False
        try:
            markets_management.unregister_from_market('test_market1')
        except:
            error = True

        self.assertTrue(error)