"""Validate user who logged in using a 3rd party authentication mechanism

Authenticating with Google, Faceboook, etc. is known as "federated" login.
Users that choose this option have been authenticated by the selected platform
so all we need to to to complete login is validate that the email address exists
on our database and build JWTs for access and refresh.
"""
from http import HTTPStatus

from selene.api import SeleneEndpoint
from selene.data.account import AccountRepository, RefreshTokenRepository
from selene.util.auth import AuthenticationError
from selene.util.db import get_db_connection


class ValidateFederatedEndpoint(SeleneEndpoint):
    def post(self):
        """Process a HTTP POST request."""
        try:
            self._get_account()
        except AuthenticationError as ae:
            self.response = str(ae), HTTPStatus.UNAUTHORIZED
        else:
            access_token, refresh_token = self._generate_tokens()
            self._set_token_cookies(access_token, refresh_token)
            self._add_refresh_token_to_db(refresh_token)
            self.response = 'account validated', HTTPStatus.OK

        return self.response

    def _get_account(self):
        """Use email returned by the authentication platform for validation"""
        email_address = self.request.form['email']
        with get_db_connection(self.config['DB_CONNECTION_POOL']) as db:
            acct_repository = AccountRepository(db)
            self.account = acct_repository.get_account_by_email(email_address)

        if self.account is None:
            raise AuthenticationError('account not found')

    def _add_refresh_token_to_db(self, refresh_token):
        """Track refresh tokens in the database.

        We need to store the value of the refresh token in the database so
        that we can validate it when it is used to request new tokens.

        :param refresh_token: the token to install into the database.
        """
        with get_db_connection(self.config['DB_CONNECTION_POOL']) as db:
            token_repo = RefreshTokenRepository(db, self.account)
            token_repo.add_refresh_token(refresh_token)
