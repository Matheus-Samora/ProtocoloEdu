"""Honor forwarding headers only from explicitly configured proxy IPs."""
import ipaddress,os
class TrustedProxy:
    def __init__(self,app):
        self.app=app
        self.trusted={str(ipaddress.ip_address(value.strip())) for value in os.environ.get('TRUSTED_PROXY_IPS','').split(',') if value.strip()}
    def __call__(self,environ,start_response):
        peer=environ.get('REMOTE_ADDR','')
        if peer in self.trusted:
            proto=environ.get('HTTP_X_FORWARDED_PROTO','')
            if proto in {'https','http'}:environ['wsgi.url_scheme']=proto
            forwarded=environ.get('HTTP_X_FORWARDED_FOR','').split(',')[-1].strip()
            try:environ['REMOTE_ADDR']=str(ipaddress.ip_address(forwarded))
            except ValueError:pass
        return self.app(environ,start_response)
