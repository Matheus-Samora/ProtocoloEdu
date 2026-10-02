import io,datetime
from cryptography import x509
from cryptography.x509.oid import NameOID
from cryptography.hazmat.primitives import hashes,serialization
from cryptography.hazmat.primitives.asymmetric import rsa
def signed_pdf():
 from asn1crypto import keys,x509 as asn1x509
 from pyhanko.sign import signers
 from pyhanko.sign.fields import SigSeedSubFilter
 from pyhanko_certvalidator.registry import SimpleCertificateStore
 from pyhanko.pdf_utils.incremental_writer import IncrementalPdfFileWriter
 from pypdf import PdfWriter
 key=rsa.generate_private_key(public_exponent=65537,key_size=2048)
 name=x509.Name([x509.NameAttribute(NameOID.COMMON_NAME,'FICTITIOUS QA SIGNER')])
 now=datetime.datetime.now(datetime.timezone.utc)
 cert=x509.CertificateBuilder().subject_name(name).issuer_name(name).public_key(key.public_key()).serial_number(x509.random_serial_number()).not_valid_before(now-datetime.timedelta(days=1)).not_valid_after(now+datetime.timedelta(days=1)).add_extension(x509.BasicConstraints(ca=False,path_length=None),critical=True).add_extension(x509.KeyUsage(digital_signature=True,content_commitment=True,key_encipherment=False,data_encipherment=False,key_agreement=False,key_cert_sign=False,crl_sign=False,encipher_only=None,decipher_only=None),critical=True).sign(key,hashes.SHA256())
 signer=signers.SimpleSigner(signing_cert=asn1x509.Certificate.load(cert.public_bytes(serialization.Encoding.DER)),signing_key=keys.PrivateKeyInfo.load(key.private_bytes(serialization.Encoding.DER,serialization.PrivateFormat.PKCS8,serialization.NoEncryption())),cert_registry=SimpleCertificateStore())
 writer=PdfWriter();writer.add_blank_page(width=300,height=300);writer.add_metadata({'/QA':'QA_ORIGINAL'});buf=io.BytesIO();writer.write(buf)
 unsigned=buf.getvalue()
 output=io.BytesIO();signers.PdfSigner(signers.PdfSignatureMetadata(field_name='QA',subfilter=SigSeedSubFilter.PADES),signer=signer).sign_pdf(IncrementalPdfFileWriter(io.BytesIO(unsigned)),output=output)
 return output.getvalue()
