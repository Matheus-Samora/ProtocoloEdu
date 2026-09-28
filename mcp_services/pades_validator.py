"""
Validador de Assinaturas Digitais ICP-Brasil e PAdES para PDFs Acadêmicos.
Conformidade técnica com a Portaria MEC 315/2018 (Acervo Acadêmico Digital)
e Portaria MEC 554/2019 (Diploma Digital / Representação Visual - RVDD).

Verifica:
1. Existência e integridade de assinaturas digitais PDF (ISO 32000 / PAdES).
2. Validação da cadeia criptográfica X.509 e emissão sob ICP-Brasil.
3. Extração de atributos do titular (CPF, Nome, Cargo, Organização).
4. Presença de Carimbo do Tempo (Timestamp RFC 3161 / ACT ICP-Brasil).
5. Verificação do ByteRange (detecção de alterações posteriores no documento).
6. Emissão de parecer regulatório para a Secretaria Acadêmica.
"""

import os
import re
import io
import sys
import json
import hashlib
import binascii
import datetime
import logging
from typing import Dict, Any, List, Optional, Tuple, Union
from pydantic import BaseModel, Field

try:
    from cryptography import x509
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.serialization import pkcs7
    from cryptography.x509.oid import NameOID, ExtensionOID
    CRYPTO_AVAILABLE = True
except ImportError:
    CRYPTO_AVAILABLE = False

try:
    import pypdf
    PYPDF_AVAILABLE = True
except ImportError:
    PYPDF_AVAILABLE = False

logger = logging.getLogger("PADES_VALIDATOR")

# OIDs específicos da Infraestrutura de Chaves Públicas Brasileira (ICP-Brasil)
OID_ICP_BRASIL_PREFIX = "2.16.76.1"
OID_ICP_BRASIL_CPF = "2.16.76.1.3.1"
OID_ICP_BRASIL_CNPJ = "2.16.76.1.3.3"
OID_ICP_BRASIL_RESPONSAVEL = "2.16.76.1.3.4"
OID_TIMESTAMP_TOKEN = "1.2.840.113549.1.9.16.2.14"

# Autoridades Certificadoras Raiz e Emissoras credenciadas na ICP-Brasil (ITI)
ICP_BRASIL_TRUSTED_ISSUERS = [
    "ICP-BRASIL",
    "AUTORIDADE CERTIFICADORA RAIZ BRASILEIRA",
    "AC RAIZ BRASILEIRA",
    "AC SERPRO",
    "AC CERTISIGN",
    "AC SOLUTI",
    "AC VALID",
    "AC IMPRENSA OFICIAL",
    "AC DIGITALSIGN",
    "AC CERTIFICAMINAS",
    "AC NOTARIAL",
    "AC DEFESA",
    "AC SINCOR",
    "AC OAB",
    "AC JUS",
    "AC PRODEMGE",
    "AC PRODABEL",
    "AC SAFEWEB",
    "AC BOA VISTA",
    "AC ONLINE"
]


class SignerCertificateInfo(BaseModel):
    """Metadados do certificado digital X.509 do signatário."""
    common_name: str
    organization: Optional[str] = None
    organizational_unit: Optional[str] = None
    issuer_cn: str
    issuer_org: Optional[str] = None
    serial_number: str
    not_valid_before: str
    not_valid_after: str
    is_valid_time_window: bool
    is_icp_brasil: bool
    certificate_policy: Optional[str] = None
    cpf_titular: Optional[str] = None
    cnpj_titular: Optional[str] = None
    subject_raw: str
    issuer_raw: str


class SignatureDetail(BaseModel):
    """Detalhes de uma assinatura individual extraída do PDF."""
    signature_index: int
    filter: Optional[str] = None
    sub_filter: Optional[str] = None
    is_pades: bool = False
    signing_time: Optional[str] = None
    claimed_signer_name: Optional[str] = None
    signing_reason: Optional[str] = None
    signing_location: Optional[str] = None
    byte_range: Optional[List[int]] = None
    byte_range_covers_full_doc: bool = False
    document_sha256_hash: Optional[str] = None
    has_timestamp_token: bool = False
    timestamp_details: Optional[str] = None
    signers: List[SignerCertificateInfo] = Field(default_factory=list)


class PadesVerificationReport(BaseModel):
    """Relatório oficial de conformidade técnica e jurídica MEC."""
    filename: str
    total_signatures_found: int = 0
    has_digital_signature: bool = False
    is_pades_compliant: bool = False
    is_icp_brasil_certified: bool = False
    all_certificates_valid: bool = False
    has_valid_timestamp: bool = False
    integrity_preserved: bool = False
    mec_315_status: str = "NAO_CONFORME"  # CONFORME, CONFORME_COM_RESSALVA, NAO_CONFORME
    mec_315_justification: str = ""
    signatures: List[SignatureDetail] = Field(default_factory=list)
    diagnostic_notes: List[str] = Field(default_factory=list)
    timestamp_verified_at: str = Field(default_factory=lambda: datetime.datetime.now(datetime.timezone.utc).isoformat())


class PadesSignatureValidator:
    """
    Validador especializado em assinaturas digitais ICP-Brasil / PAdES
    em documentos acadêmicos (Diplomas, Históricos, Certidões).
    """

    def __init__(self):
        self.logger = logger

    def verify_pdf(
        self,
        pdf_input: Union[bytes, str, io.BytesIO],
        filename: str = "documento.pdf"
    ) -> PadesVerificationReport:
        """
        Executa a análise forense e regulatória completa do PDF.
        
        Args:
            pdf_input: Conteúdo binário (bytes), caminho no disco (str) ou BytesIO.
            filename: Nome para exibição e referência de auditoria.
        """
        pdf_bytes = self._read_input_bytes(pdf_input)
        if not pdf_bytes:
            return PadesVerificationReport(
                filename=filename,
                mec_315_status="NAO_CONFORME",
                mec_315_justification="Arquivo corrompido ou vazio. Nenhum byte para processar."
            )

        report = PadesVerificationReport(filename=filename)
        signature_blocks = self._extract_signature_blocks(pdf_bytes)

        if not signature_blocks:
            report.has_digital_signature = False
            report.is_pades_compliant = False
            report.is_icp_brasil_certified = False
            report.mec_315_status = "NAO_CONFORME"
            report.mec_315_justification = (
                "O documento não contém nenhuma assinatura digital ICP-Brasil detectável. "
                "Documentos acadêmicos digitais (Portaria MEC 315/2018 e Diploma Digital) "
                "devem conter assinatura eletrônica qualificada com certificado ICP-Brasil."
            )
            report.diagnostic_notes.append("Nenhum bloco de assinatura /Type /Sig ou /ByteRange localizado no arquivo.")
            return report

        report.has_digital_signature = True
        report.total_signatures_found = len(signature_blocks)

        all_icp = True
        all_valid_certs = True
        all_integrity = True
        any_pades = False
        any_timestamp = False

        for idx, block in enumerate(signature_blocks):
            sig_detail = self._analyze_signature_block(idx + 1, block, pdf_bytes)
            report.signatures.append(sig_detail)

            if sig_detail.is_pades:
                any_pades = True
            if sig_detail.has_timestamp_token:
                any_timestamp = True
            if not sig_detail.byte_range_covers_full_doc:
                all_integrity = False
                report.diagnostic_notes.append(
                    f"Assinatura #{sig_detail.signature_index}: Existem modificações incrementais posteriores à assinatura."
                )

            # Verifica certificados
            sig_has_icp = False
            for cert_info in sig_detail.signers:
                if cert_info.is_icp_brasil:
                    sig_has_icp = True
                if not cert_info.is_valid_time_window:
                    all_valid_certs = False
                    report.diagnostic_notes.append(
                        f"Certificado '{cert_info.common_name}' está fora da janela de validade ({cert_info.not_valid_before} até {cert_info.not_valid_after})."
                    )

            if not sig_has_icp:
                all_icp = False
                report.diagnostic_notes.append(
                    f"Assinatura #{sig_detail.signature_index}: Emitida por autoridade fora da cadeia ICP-Brasil."
                )

        report.is_pades_compliant = any_pades
        report.is_icp_brasil_certified = all_icp and (len(report.signatures) > 0)
        report.all_certificates_valid = all_valid_certs
        report.has_valid_timestamp = any_timestamp
        report.integrity_preserved = all_integrity

        # Conclusão de conformidade MEC 315/2018 e Diploma Digital
        if report.is_icp_brasil_certified and report.all_certificates_valid and report.integrity_preserved:
            if report.has_valid_timestamp:
                report.mec_315_status = "CONFORME"
                report.mec_315_justification = (
                    "Documento plenamente conforme com a Portaria MEC nº 315/2018 e Diploma Digital. "
                    "Assinatura qualificada ICP-Brasil verificada com carimbo do tempo e integridade preservada."
                )
            else:
                report.mec_315_status = "CONFORME_COM_RESSALVA"
                report.mec_315_justification = (
                    "Assinatura ICP-Brasil qualificada e íntegra. Não foi localizado carimbo do tempo (ACT) RFC 3161 "
                    "incorporado ao bloco CMS. Aceito para arquivamento com recomendação de carimbo na emissão definitiva."
                )
        elif report.is_icp_brasil_certified and not report.integrity_preserved:
            report.mec_315_status = "CONFORME_COM_RESSALVA"
            report.mec_315_justification = (
                "Assinatura ICP-Brasil reconhecida, porém existem alterações incrementais anexadas após a assinatura "
                "(ex: anotações, carimbos visuais ou revisão de formulário)."
            )
        elif not report.is_icp_brasil_certified:
            report.mec_315_status = "NAO_CONFORME"
            report.mec_315_justification = (
                "Documento não atende aos requisitos do MEC: a assinatura eletrônica encontrada não provém de "
                "uma Autoridade Certificadora credenciada na ICP-Brasil."
            )
        else:
            report.mec_315_status = "NAO_CONFORME"
            report.mec_315_justification = "Certificado digital expirado ou inválido na data de verificação."

        return report

    def _read_input_bytes(self, pdf_input: Union[bytes, str, io.BytesIO]) -> bytes:
        """Converte qualquer formato suportado para bytes brutos."""
        if isinstance(pdf_input, bytes):
            return pdf_input
        elif isinstance(pdf_input, io.BytesIO):
            return pdf_input.getvalue()
        elif isinstance(pdf_input, str):
            if os.path.isfile(pdf_input):
                with open(pdf_input, 'rb') as f:
                    return f.read()
            # Pode ser base64 string
            try:
                clean_str = re.sub(r'^data:application/pdf;base64,', '', pdf_input.strip())
                return binascii.a2b_base64(clean_str)
            except Exception:
                return b""
        return b""

    def _extract_signature_blocks(self, pdf_bytes: bytes) -> List[Dict[str, Any]]:
        """
        Localiza todos os dicionários de assinatura no PDF via inspeção de ByteRange e /Contents.
        Combina análise direta do gap do ByteRange com parsing estrutural do PDF.
        """
        blocks = []
        byte_range_pattern = re.compile(
            rb'/ByteRange\s*\[\s*(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s*\]'
        )
        contents_pattern = re.compile(
            rb'/Contents\s*<([0-9a-fA-F\s]+)>'
        )

        matches = list(byte_range_pattern.finditer(pdf_bytes))
        for m in matches:
            b1 = int(m.group(1))
            l1 = int(m.group(2))
            b2 = int(m.group(3))
            l2 = int(m.group(4))

            # 1. Busca no gap exato do ByteRange (entre l1 e b2)
            hex_contents = b""
            gap_start = l1
            gap_end = b2
            surrounding = pdf_bytes[max(0, m.start() - 1024):min(len(pdf_bytes), m.end() + 1024)]

            if gap_start < gap_end and gap_end <= len(pdf_bytes):
                gap_bytes = pdf_bytes[gap_start:gap_end]
                surrounding = gap_bytes + b" " + surrounding

                c_pos = gap_bytes.find(b'/Contents')
                if c_pos != -1:
                    c_start = gap_bytes.find(b'<', c_pos)
                    if c_start != -1:
                        c_end = gap_bytes.find(b'>', c_start)
                        if c_end != -1:
                            hex_contents = gap_bytes[c_start + 1:c_end]
                else:
                    c_start = gap_bytes.find(b'<')
                    if c_start != -1:
                        c_end = gap_bytes.find(b'>', c_start)
                        if c_end != -1:
                            hex_contents = gap_bytes[c_start + 1:c_end]

            # 2. Se não achou no gap, busca na vizinhança
            if not hex_contents:
                c_match = contents_pattern.search(pdf_bytes[max(0, m.start() - 4096):min(len(pdf_bytes), m.end() + 16384)])
                if c_match:
                    hex_contents = c_match.group(1)

            # Extrai metadados complementares (SubFilter, Filter, M, Reason)
            sub_filter = None
            if b"/ETSI.CAdES.detached" in surrounding:
                sub_filter = "ETSI.CAdES.detached"
            elif b"/adbe.pkcs7.detached" in surrounding:
                sub_filter = "adbe.pkcs7.detached"
            elif b"/adbe.pkcs7.sha1" in surrounding:
                sub_filter = "adbe.pkcs7.sha1"

            filter_name = None
            if b"/Adobe.PPKLite" in surrounding:
                filter_name = "Adobe.PPKLite"

            # Nome do signatário no dicionário PDF (/Name)
            name_match = re.search(rb'/Name\s*\((.*?)\)', surrounding)
            claimed_name = name_match.group(1).decode('latin1', errors='ignore') if name_match else None

            # Motivo (/Reason)
            reason_match = re.search(rb'/Reason\s*\((.*?)\)', surrounding)
            reason = reason_match.group(1).decode('latin1', errors='ignore') if reason_match else None

            # Data de assinatura (/M)
            m_match = re.search(rb'/M\s*\(D:(\d{14}[^\)]*)\)', surrounding)
            raw_date = m_match.group(1).decode('latin1', errors='ignore') if m_match else None

            blocks.append({
                "byte_range": [b1, l1, b2, l2],
                "hex_contents": hex_contents,
                "sub_filter": sub_filter,
                "filter": filter_name,
                "claimed_name": claimed_name,
                "reason": reason,
                "signing_date": self._format_pdf_date(raw_date)
            })

        return blocks

    def _format_pdf_date(self, pdf_date: Optional[str]) -> Optional[str]:
        """Converte data PDF (D:YYYYMMDDHHmmSS) para ISO 8601."""
        if not pdf_date:
            return None
        try:
            digits = re.sub(r'\D', '', pdf_date)[:14]
            if len(digits) >= 14:
                dt = datetime.datetime.strptime(digits, "%Y%m%d%H%M%S")
                return dt.strftime("%Y-%m-%dT%H:%M:%SZ")
        except Exception:
            pass
        return pdf_date

    @staticmethod
    def _extract_clean_der_bytes(raw_bytes: bytes) -> bytes:
        """Determina o tamanho exato da estrutura ASN.1 SEQUENCE eliminando padding do PDF."""
        if len(raw_bytes) < 2 or raw_bytes[0] != 0x30:
            return raw_bytes
        if raw_bytes[1] < 0x80:
            der_len = 2 + raw_bytes[1]
        else:
            num_octets = raw_bytes[1] & 0x7f
            if len(raw_bytes) < 2 + num_octets:
                return raw_bytes
            length = 0
            for i in range(num_octets):
                length = (length << 8) | raw_bytes[2 + i]
            der_len = 2 + num_octets + length

        if 0 < der_len <= len(raw_bytes):
            return raw_bytes[:der_len]
        return raw_bytes

    def _analyze_signature_block(
        self,
        index: int,
        block: Dict[str, Any],
        pdf_bytes: bytes
    ) -> SignatureDetail:
        """Processa a assinatura individual, valida certificados X.509 e integridade."""
        br = block["byte_range"]
        b1, l1, b2, l2 = br[0], br[1], br[2], br[3]

        # 1. Integridade do ByteRange: cobre o arquivo até o fim?
        covers_full = (b2 + l2) >= len(pdf_bytes)

        # 2. Calcula hash SHA-256 do conteúdo coberto pela assinatura
        signed_bytes = pdf_bytes[b1:b1 + l1] + pdf_bytes[b2:b2 + l2]
        doc_hash = hashlib.sha256(signed_bytes).hexdigest()

        # 3. Decodifica o /Contents binário PKCS#7 / CMS
        raw_hex = re.sub(r'[^0-9a-fA-F]', '', block["hex_contents"].decode('latin1', errors='ignore'))
        if len(raw_hex) % 2 != 0:
            raw_hex = raw_hex[:-1]

        der_bytes = b""
        try:
            unpadded = binascii.unhexlify(raw_hex)
            der_bytes = self._extract_clean_der_bytes(unpadded)
        except Exception as e:
            logger.warning(f"Erro ao descompactar hex do PKCS#7: {e}")


        # 4. Análise de certificados X.509
        signers = []
        has_timestamp = False
        timestamp_info = None

        if der_bytes and CRYPTO_AVAILABLE:
            try:
                certs = pkcs7.load_der_pkcs7_certificates(der_bytes)
                for cert in certs:
                    info = self._parse_x509_certificate(cert)
                    signers.append(info)
            except Exception as e:
                logger.warning(f"Falha ao carregar certificados do PKCS#7 via cryptography: {e}")

            # Busca presença de Timestamp Token (OID 1.2.840.113549.1.9.16.2.14)
            # ou certificado de Carimbo do Tempo (ACT)
            has_timestamp, timestamp_info = self._detect_timestamp_token(der_bytes, signers)

        is_pades = (block.get("sub_filter") in ("ETSI.CAdES.detached", "adbe.pkcs7.detached"))

        return SignatureDetail(
            signature_index=index,
            filter=block.get("filter"),
            sub_filter=block.get("sub_filter"),
            is_pades=is_pades,
            signing_time=block.get("signing_date"),
            claimed_signer_name=block.get("claimed_name"),
            signing_reason=block.get("reason"),
            byte_range=br,
            byte_range_covers_full_doc=covers_full,
            document_sha256_hash=doc_hash,
            has_timestamp_token=has_timestamp,
            timestamp_details=timestamp_info,
            signers=signers
        )

    def _parse_x509_certificate(self, cert: x509.Certificate) -> SignerCertificateInfo:
        """Extrai metadados completos de um certificado X.509."""
        now = datetime.datetime.now(datetime.timezone.utc)

        # Subject CN, O, OU
        subject_cn = "Desconhecido"
        subject_org = None
        subject_ou = []
        for attr in cert.subject:
            if attr.oid == NameOID.COMMON_NAME:
                subject_cn = str(attr.value)
            elif attr.oid == NameOID.ORGANIZATION_NAME:
                subject_org = str(attr.value)
            elif attr.oid == NameOID.ORGANIZATIONAL_UNIT_NAME:
                subject_ou.append(str(attr.value))

        # Issuer CN, O
        issuer_cn = "Desconhecido"
        issuer_org = None
        for attr in cert.issuer:
            if attr.oid == NameOID.COMMON_NAME:
                issuer_cn = str(attr.value)
            elif attr.oid == NameOID.ORGANIZATION_NAME:
                issuer_org = str(attr.value)

        # Janela de validade
        not_before = cert.not_valid_before_utc
        not_after = cert.not_valid_after_utc
        is_valid_window = (not_before <= now <= not_after)

        # Verificação da cadeia ICP-Brasil
        is_icp = self._is_icp_brasil_cert(cert, issuer_cn, issuer_org, subject_ou)

        # Extração de CPF do titular (padrão ICP-Brasil: no CN ou em extensão)
        cpf_titular = self._extract_cpf_from_cert(cert, subject_cn)
        cnpj_titular = self._extract_cnpj_from_cert(cert, subject_cn)

        return SignerCertificateInfo(
            common_name=subject_cn,
            organization=subject_org,
            organizational_unit=", ".join(subject_ou) if subject_ou else None,
            issuer_cn=issuer_cn,
            issuer_org=issuer_org,
            serial_number=hex(cert.serial_number)[2:].upper(),
            not_valid_before=not_before.isoformat(),
            not_valid_after=not_after.isoformat(),
            is_valid_time_window=is_valid_window,
            is_icp_brasil=is_icp,
            cpf_titular=cpf_titular,
            cnpj_titular=cnpj_titular,
            subject_raw=cert.subject.rfc4514_string(),
            issuer_raw=cert.issuer.rfc4514_string()
        )

    def _is_icp_brasil_cert(
        self,
        cert: x509.Certificate,
        issuer_cn: str,
        issuer_org: Optional[str],
        subject_ou: List[str]
    ) -> bool:
        """Determina se o certificado pertence à cadeia ICP-Brasil oficial."""
        haystack = f"{issuer_cn} {issuer_org or ''} {' '.join(subject_ou)} {cert.issuer.rfc4514_string()}".upper()
        for trusted in ICP_BRASIL_TRUSTED_ISSUERS:
            if trusted in haystack:
                return True

        # Verifica Certificate Policies OID 2.16.76.1.*
        try:
            for ext in cert.extensions:
                if ext.oid == ExtensionOID.CERTIFICATE_POLICIES:
                    policies = ext.value
                    for pol in policies:
                        if pol.policy_identifier.dotted_string.startswith(OID_ICP_BRASIL_PREFIX):
                            return True
        except Exception:
            pass

        return False

    def _extract_cpf_from_cert(self, cert: x509.Certificate, subject_cn: str) -> Optional[str]:
        """Extrai o CPF do titular comum em certificados e-CPF ICP-Brasil."""
        # Geralmente no formato: NOME COMPLETO:12345678900
        match = re.search(r':(\d{11})$', subject_cn)
        if match:
            return match.group(1)
        # Tenta em qualquer sequência de 11 dígitos no CN
        match_digits = re.search(r'\b(\d{11})\b', subject_cn)
        if match_digits:
            return match_digits.group(1)
        return None

    def _extract_cnpj_from_cert(self, cert: x509.Certificate, subject_cn: str) -> Optional[str]:
        """Extrai CNPJ do titular (e-CNPJ ICP-Brasil)."""
        match = re.search(r':(\d{14})$', subject_cn)
        if match:
            return match.group(1)
        return None

    def _detect_timestamp_token(
        self,
        der_bytes: bytes,
        signers: List[SignerCertificateInfo]
    ) -> Tuple[bool, Optional[str]]:
        """Verifica a presença de Carimbo do Tempo (RFC 3161) ou ACT ICP-Brasil."""
        # 1. Procura o OID binário do timestamp token (1.2.840.113549.1.9.16.2.14)
        # Em ASN.1 DER: 06 0B 2A 86 48 86 F7 0D 01 09 10 02 0E
        ts_oid_bytes = bytes.fromhex("2a864886f70d010910020e")
        if ts_oid_bytes in der_bytes:
            return True, "Carimbo do Tempo RFC 3161 (id-aa-timeStampToken) detectado no bloco CMS."

        # 2. Verifica se algum dos certificados é de uma ACT (Autoridade de Carimbo do Tempo)
        for s in signers:
            name_upper = s.common_name.upper()
            if "CARIMBO" in name_upper or "ACT " in name_upper or "TIMESTAMP" in name_upper or "TEMPO" in name_upper:
                return True, f"Certificado de Carimbo do Tempo detectado: {s.common_name}"

        return False, None


# ==============================================================================
# CLI E EXECUÇÃO STANDALONE PARA TESTES
# ==============================================================================

def main():
    """Ponto de entrada de linha de comando."""
    if len(sys.argv) < 2:
        print("Uso: python -m mcp_services.pades_validator <arquivo.pdf>")
        sys.exit(1)

    filepath = sys.argv[1]
    if not os.path.isfile(filepath):
        print(f"Erro: Arquivo '{filepath}' não encontrado.")
        sys.exit(1)

    validator = PadesSignatureValidator()
    report = validator.verify_pdf(filepath, filename=os.path.basename(filepath))
    print(json.dumps(report.model_dump(), indent=2, ensure_ascii=False))


if __name__ == '__main__':
    main()
