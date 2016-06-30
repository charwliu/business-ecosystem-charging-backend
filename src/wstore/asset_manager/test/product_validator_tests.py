# -*- coding: utf-8 -*-

# Copyright (c) 2015 - 2016 CoNWeT Lab., Universidad Politécnica de Madrid

# This file belongs to the business-charging-backend
# of the Business API Ecosystem.

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from __future__ import unicode_literals
from copy import deepcopy

from mock import MagicMock, call
from nose_parameterized import parameterized

from django.core.exceptions import PermissionDenied
from django.test.testcases import TestCase

from wstore.asset_manager import product_validator, offering_validator
from wstore.asset_manager.errors import ProductError
from wstore.asset_manager.test.product_validator_test_data import *


class ValidatorTestCase(TestCase):

    tags = ('product-validator', )

    def _mock_validator_imports(self, module):
        reload(module)

        module.ResourcePlugin = MagicMock()
        module.ResourcePlugin.objects.get.return_value = self._plugin_instance

        module.Resource = MagicMock()
        self._asset_instance = MagicMock()
        self._asset_instance.content_type = 'application/x-widget'
        self._asset_instance.provider = self._provider
        module.Resource.objects.get.return_value = self._asset_instance
        module.Resource.objects.create.return_value = self._asset_instance

        # Mock Site
        module.Context = MagicMock()
        self._context_inst = MagicMock()
        self._context_inst.site.domain = "http://testlocation.org/"
        module.Context.objects.all.return_value = [self._context_inst]

    def setUp(self):
        self._provider = MagicMock()

        self._plugin_instance = MagicMock()
        self._plugin_instance.media_types = ['application/x-widget']
        self._plugin_instance.formats = ["FILE"]
        self._plugin_instance.module = 'wstore.asset_manager.resource_plugins.plugin.Plugin'

        import wstore.asset_manager.resource_plugins.decorators
        wstore.asset_manager.resource_plugins.decorators.ResourcePlugin = MagicMock()
        wstore.asset_manager.resource_plugins.decorators.ResourcePlugin.objects.get.return_value = self._plugin_instance

    def _support_url(self):
        self._plugin_instance.formats = ["FILE", "URL"]

    def _only_url(self):
        self._plugin_instance.formats = ["URL"]

    def _support_file(self):
        self._plugin_instance.formats = ["FILE", "URL"]
        self._context_inst.site.domain = "http://mydomain.org/"

    def _not_supported(self):
        import wstore.asset_manager.resource_plugins.decorators
        wstore.asset_manager.resource_plugins.decorators.ResourcePlugin.objects.get.side_effect = Exception('Not found')
        self._mock_validator_imports(product_validator)

    def _inv_media(self):
        self._plugin_instance.media_types = ['text/plain']

    def _not_asset(self):
        product_validator.Resource.objects.get.side_effect = Exception('Not found')

    def _not_owner(self):
        self._asset_instance.provider = MagicMock()

    def _diff_media(self):
        self._asset_instance.content_type = 'text/plain'

    def _existing_asset(self):
        self._plugin_instance.formats = ["URL"]
        product_validator.Resource.objects.filter.return_value = [self._asset_instance]

    @parameterized.expand([
        ('basic', BASIC_PRODUCT, True),
        ('file_url_allowed', BASIC_PRODUCT, True, _support_url),
        ('url_asset', BASIC_PRODUCT, False, _only_url),
        ('url_file_allowed', BASIC_PRODUCT, False, _support_file),
        ('invalid_action', INVALID_ACTION, True, None, ValueError, 'The provided action (invalid) is not valid. Allowed values are create, attach, update, upgrade, and delete'),
        ('missing_media', MISSING_MEDIA, True, None, ProductError, 'ProductError: Digital product specifications must contain a media type characteristic'),
        ('missing_type', MISSING_TYPE, True, None, ProductError, 'ProductError: Digital product specifications must contain a asset type characteristic'),
        ('missing_location', MISSING_LOCATION, True, None, ProductError, 'ProductError: Digital product specifications must contain a location characteristic'),
        ('multiple_char', MULTIPLE_LOCATION, True, None, ProductError, 'ProductError: The product specification must not contain more than one location characteristic'),
        ('multiple_values', MULTIPLE_VALUES, True, None, ProductError, 'ProductError: The characteristic Location must not contain multiple values'),
        ('not_supported', BASIC_PRODUCT, True, _not_supported, ProductError, 'ProductError: The given product specification contains a not supported asset type: Widget'),
        ('inv_media', BASIC_PRODUCT, True, _inv_media, ProductError, 'ProductError: The media type characteristic included in the product specification is not valid for the given asset type'),
        ('inv_location', INVALID_LOCATION, True, None, ProductError, 'ProductError: The location characteristic included in the product specification is not a valid URL'),
        ('not_asset', BASIC_PRODUCT, True, _not_asset, ProductError, 'ProductError: The URL specified in the location characteristic does not point to a valid digital asset'),
        ('unauthorized', BASIC_PRODUCT, True, _not_owner, PermissionDenied, 'You are not authorized to use the digital asset specified in the location characteristic'),
        ('diff_media', BASIC_PRODUCT, True, _diff_media, ProductError, 'ProductError: The specified media type characteristic is different from the one of the provided digital asset'),
        ('existing_asset', BASIC_PRODUCT, False, _existing_asset, ProductError, 'ProductError: There is already an existing product specification defined for the given digital asset')
    ])
    def test_validate_creation(self, name, data, is_file, side_effect=None, err_type=None, err_msg=None):

        self._mock_validator_imports(product_validator)

        if side_effect is not None:
            side_effect(self)

        error = None
        try:
            validator = product_validator.ProductValidator()
            validator.validate(data['action'], self._provider, data['product'])
        except Exception as e:
            error = e

        if err_type is None:
            self.assertTrue(error is None)
            # Check calls
            product_validator.ResourcePlugin.objects.get.assert_called_once_with(name='Widget')

            if is_file:
                product_validator.Resource.objects.get.assert_called_once_with(download_link="http://testlocation.org/media/resources/test_user/widget.wgt")
            else:
                product_validator.Resource.objects.create.assert_called_once_with(
                    resource_path='',
                    download_link="http://testlocation.org/media/resources/test_user/widget.wgt",
                    provider=self._provider,
                    content_type='application/x-widget'
                )

        else:
            self.assertTrue(isinstance(error, err_type))
            self.assertEquals(err_msg, unicode(e))

    def _non_digital(self):
        return [[], []]

    def _mixed_assets(self):
        digital_asset = MagicMock()
        return [[], [digital_asset]]

    def _all_digital(self):
        digital_asset = MagicMock()
        digital_asset1 = MagicMock()
        return [[digital_asset], [digital_asset1]]

    @parameterized.expand([
        ('non_digital', _non_digital, False),
        ('mixed', _mixed_assets),
        ('all_digital', _all_digital)
    ])
    def test_bundle_creation(self, name, asset_mocker, created=True):
        self._mock_validator_imports(product_validator)

        assets = asset_mocker(self)
        expected_assets = [asset[0] for asset in assets if len(asset)]

        product_validator.Resource.objects.filter.side_effect = assets

        validator = product_validator.ProductValidator()
        validator.validate(BASIC_BUNDLE_CREATION['action'], self._provider, BASIC_BUNDLE_CREATION['product'])

        # Validate filter calls
        self.assertEquals([
            call(product_id=BASIC_BUNDLE_CREATION['product']['bundledProductSpecification'][0]['id']),
            call(product_id=BASIC_BUNDLE_CREATION['product']['bundledProductSpecification'][1]['id'])
        ], product_validator.Resource.objects.filter.call_args_list)

        # Check resource creation
        if created:
            product_validator.Resource.objects.create.assert_called_once_with(
                resource_path='',
                download_link='',
                provider=self._provider,
                content_type='bundle',
                bundled_assets=expected_assets
            )
        else:
            self.assertEquals(0, product_validator.Resource.objects.call_count)

    def _validate_bundle_creation_error(self, product_request, msg):
        self._mock_validator_imports(product_validator)

        try:
            validator = product_validator.ProductValidator()
            validator.validate(product_request['action'], self._provider, product_request['product'])
        except ProductError as e:
            error = e

        self.assertEquals(msg, unicode(error))

    def test_bundle_creation_missing_products(self):
        self._validate_bundle_creation_error({
            'action': 'create',
            'product': {
                'isBundle': True
            }
        }, 'ProductError: A product spec bundle must contain at least two bundled product specs')

    def test_bundle_assets_included(self):
        product_request = deepcopy(BASIC_PRODUCT)
        product_request['product']['isBundle'] = True

        self._validate_bundle_creation_error(
            product_request, 'ProductError: Product spec bundles cannot define digital assets')


    @parameterized.expand([
        ('no_chars', NO_CHARS_PRODUCT),
        ('no_digital_chars', EMPTY_CHARS_PRODUCT)
    ])
    def test_validate_physical(self, name, product):
        validator = product_validator.ProductValidator()
        validator.validate('create', self._provider, product)

        self.assertEquals(0, product_validator.ResourcePlugin.objects.get.call_count)
        self.assertEquals(0, product_validator.Resource.objects.get.call_count)
        self.assertEquals(0, product_validator.Resource.objects.create.call_count)


    @parameterized.expand([
        ('valid_pricing', BASIC_OFFERING),
        ('free_offering', FREE_OFFERING),
        ('missing_type', MISSING_PRICETYPE, 'Missing required field priceType in productOfferingPrice'),
        ('invalid_type', INVALID_PRICETYPE, 'Invalid priceType, it must be one time, recurring, or usage'),
        ('missing_charge_period', MISSING_PERIOD, 'Missing required field recurringChargePeriod for recurring priceType'),
        ('invalid_period', INVALID_PERIOD, 'Unrecognized recurringChargePeriod: invalid'),
        ('missing_price', MISSING_PRICE, 'Missing required field price in productOfferingPrice'),
        ('missing_currency', MISSING_CURRENCY, 'Missing required field currencyCode in price'),
        ('invalid_currency', INVALID_CURRENCY, 'Unrecognized currency: invalid')
    ])
    def test_create_offering_validation(self, name, offering, msg=None):
        self._mock_validator_imports(offering_validator)

        offering_validator.requests = MagicMock()
        product = deepcopy(BASIC_PRODUCT['product'])
        product['id'] = '20'
        resp = MagicMock()
        offering_validator.requests.get.return_value = resp
        resp.json.return_value = product

        error = None
        try:
            validator = offering_validator.OfferingValidator()
            validator.validate('create', self._provider, offering)
        except Exception as e:
            error = e

        if msg is not None:
            self.assertTrue(isinstance(error, ValueError))
            self.assertEquals(msg, unicode(error))
