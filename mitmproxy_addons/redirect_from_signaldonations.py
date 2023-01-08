"""
Upon receiving a request to `https://signaldonations.org`, returns immediately
with a 302 redirect to `sgnl://`.

Based on a [mitmproxy example][0].

[0]: https://github.com/mitmproxy/mitmproxy/blob/main/examples/addons/http-reply-from-proxy.py
"""

import logging
from mitmproxy import http

class Redirect:
    def __init__(self, from_url: str, to_url: str):
        self.from_url = from_url
        self.to_url = to_url

    def request(self, flow: http.HTTPFlow):
        if flow.request.url.startswith(self.from_url):
            logging.info("Redirecting request to {} to {}".format(self.from_url, self.to_url))
            flow.response = self.__make_redirect_response(path=flow.request.path)

    def __make_redirect_response(self, path: str) -> http.Response:
        return http.Response.make(
            status_code=302,
            headers={
                "Location": "{}{}".format(self.to_url, path)
            }
        )


addons = [Redirect("https://signaldonations.org", "sgnl://paypal-payment")]
