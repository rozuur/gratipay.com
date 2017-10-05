from __future__ import absolute_import, division, print_function, unicode_literals

import os

from gratipay.testing import BrowserHarness, images


class Tests(BrowserHarness):

    def fetch(self):
        return self.db.one('SELECT pfos.*::payments_for_open_source '
                           'FROM payments_for_open_source pfos')


    def fill_cc(self, credit_card_number, expiration, cvv):
        if self.app.env.load_braintree_form_on_homepage:
            self.wait_for('.braintree-form-number')
            with self.get_iframe('braintree-hosted-field-number') as iframe:
                iframe.fill('credit-card-number', credit_card_number)
            with self.get_iframe('braintree-hosted-field-expirationDate') as iframe:
                iframe.fill('expiration', expiration)
            with self.get_iframe('braintree-hosted-field-cvv') as iframe:
                iframe.fill('cvv', cvv)
        else:
            # The field should already have "fake-valid-nonce" for a value.
            self.wait_for('#braintree-container input')


    def fill_form(self, amount, credit_card_number, expiration, cvv,
                  name='', email_address='', promotion_logo='',
                  promotion_name='', promotion_url='', promotion_twitter='', promotion_message=''):
        self.fill('amount', amount)
        self.fill_cc(credit_card_number, expiration, cvv)
        if name: self.fill('name', name)
        if email_address: self.fill('email_address', email_address)
        if promotion_logo: self.fill('promotion_logo', promotion_logo)
        if promotion_name: self.fill('promotion_name', promotion_name)
        if promotion_url: self.fill('promotion_url', promotion_url)
        if promotion_twitter: self.fill('promotion_twitter', promotion_twitter)
        if promotion_message: self.fill('promotion_message', promotion_message)


    def test_loads_for_anon(self):
        assert self.css('#banner h1').text == 'Invest in open source.'
        assert self.css('#header .sign-in button').html.strip()[:17] == 'Sign in / Sign up'

    def test_redirects_for_authed_exclamation_point(self):
        self.make_participant('alice', claimed_time='now')
        self.sign_in('alice')
        with self.page_reload_afterwards():
            self.visit('/')
        assert self.css('#banner h1').html == 'Browse'
        assert self.css('.you-are a').html.strip()[:6] == '~alice'

    def submit_succeeds(self):
        self.css('fieldset.submit button').click()
        self.wait_for('.payment-complete', 4)
        told_them = self.css('#banner h1').text == 'Payment complete!'
        return self.fetch().succeeded and told_them

    @images.fixture
    def test_anon_can_post(self, filepath):
        self.fill_form('537', '4242424242424242', '1020', '123',
                       'Alice Liddell', 'alice@example.com', filepath,
                       'Wonderland', 'http://www.example.com/', 'thebestbutter',
                       'Love me! Love me! Say that you love me!')
        assert self.submit_succeeds()
        self.wait_for('a.invoice').click()
        uuid = self.wait_for('.txnid').text.split()[1].lower()
        assert self.css('#items tbody tr').text == 'open source software $ 537.00'
        assert self.client.GET('/browse/payments/{}/logo'.format(uuid)).body == images.LARGE

    def test_options_are_optional(self):
        self.fill_form('537', '4242424242424242', '1020', '123')
        assert self.submit_succeeds()

    @images.fixture('.gif')
    def test_errors_are_handled(self, filepath):
        self.fill_form('1,000', '4242424242424242', '1020', '123',
                       'Alice Liddell', 'alice@example', filepath,
                       'Wonderland', 'htp://www.example.com/', 'thebestbutter', 'Love me!')
        self.css('fieldset.submit button').click()
        assert self.wait_for_error() == 'Eep! Mind looking over your info for us?'
        assert self.css('.field.email_address').has_class('error')
        assert self.css('.field.promotion_logo').has_class('error')
        assert self.css('.field.promotion_url').has_class('error')
        assert not self.css('.field.email_address').has_class('amount')
        assert self.fetch() is None

    @images.fixture()
    def test_file_chooser_works(self, filepath):
        val = lambda: self.css('.field.promotion_logo label.button').text
        assert val() == 'Choose file ...'
        self.attach_file('promotion_logo', filepath)
        assert val() == filepath.split(os.sep)[-1]
