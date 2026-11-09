"""SD-JWT issue, present and verify, shared by every evidence profile here.

The first article's `sdjwt_evidence.py` keeps its published functions
verbatim; they are the special case of model-call evidence with every
claim disclosed. New profiles use these functions instead of repeating
that code. Every rejection is raised as ValueError.
"""
from hashlib import sha256
from time import time

from jsonschema import ValidationError, validate
from jwcrypto.common import JWException
from sd_jwt.common import SDObj
from sd_jwt.holder import SDJWTHolder
from sd_jwt.issuer import SDJWTIssuer
from sd_jwt.verifier import SDJWTVerifier

ALG = "ES256"
CLOCK_SKEW = 60  # Seconds of issuance time tolerated in the future.


def validated(claims, schema):
    try:
        validate(claims, schema)
    except ValidationError as error:
        raise ValueError(f"Claims do not match the schema: {error.message}") from error
    return claims


def selective(claims, names):
    """Mark the named top-level claims as selectively disclosable."""
    return {(SDObj(name) if name in names else name): value for name, value in claims.items()}


def issue(claims, key, typ):
    issued = SDJWTIssuer(claims, key, sign_alg=ALG, extra_header_parameters={"typ": typ})
    return issued.sd_jwt_issuance


def signed_payload(issuance):
    """The signed claims as the holder sees them: disclosable values replaced by digests."""
    return SDJWTHolder(issuance).sd_jwt_payload


def present(issuance, selection):
    """Disclose claims chosen in the holder's own structure.

    An object is a dict of claim name to True; an array is a list with one
    entry per element, each a dict (or None to disclose nothing).
    """
    holder = SDJWTHolder(issuance)
    holder.create_presentation(selection)
    return holder.sd_jwt_presentation


def verify(presentation, accepted_issuers, typ, schema=None):
    """Verify a presentation from an accepted issuer; return the disclosed claims.

    `accepted_issuers` maps issuer identifiers to public keys. Key binding
    is not used in this repository, so a presentation that carries it is
    rejected.
    """
    def issuer_key(issuer, header):
        if (issuer not in accepted_issuers or header.get("alg") != ALG
                or header.get("typ") != typ):
            raise ValueError("Unaccepted issuer, algorithm, or profile")
        return accepted_issuers[issuer]

    if not isinstance(presentation, str) or not presentation.endswith("~"):
        raise ValueError("Expected SD-JWT without key binding")
    try:
        claims = SDJWTVerifier(presentation, issuer_key).get_verified_payload()
    except (JWException, ValueError, KeyError, TypeError) as error:
        raise ValueError(f"Rejected presentation: {error}") from error
    if schema is not None:
        validated(claims, schema)
    if claims.get("iat", 0) > time() + CLOCK_SKEW:
        raise ValueError("Issuance time is in the future")
    return claims


def signed_jwt_sha256(sd_jwt):
    """Digest of the issuer-signed compact JWT, without disclosures or key binding."""
    return sha256(sd_jwt.split("~", 1)[0].encode("ascii")).hexdigest()
