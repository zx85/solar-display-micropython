import re
import struct
import binascii


__all__ = [
    "b64encode",
]

bytes_types = (bytes, bytearray)  # Types acceptable as binary data

def _bytes_from_decode_data(s):
    if isinstance(s, str):
        try:
            return s.encode("ascii")
        #        except UnicodeEncodeError:
        except:
            raise ValueError("string argument should contain only ASCII characters")
    elif isinstance(s, bytes_types):
        return s
    else:
        raise TypeError("argument should be bytes or ASCII string, not %s" % s.__class__.__name__)


# Base64 encoding/decoding uses binascii


def b64encode(s, altchars=None):
    """Encode a byte string using Base64.

    s is the byte string to encode.  Optional altchars must be a byte
    string of length 2 which specifies an alternative alphabet for the
    '+' and '/' characters.  This allows an application to
    e.g. generate url or filesystem safe Base64 strings.

    The encoded byte string is returned.
    """
    if not isinstance(s, bytes_types):
        raise TypeError("expected bytes, not %s" % s.__class__.__name__)
    # Strip off the trailing newline
    encoded = binascii.b2a_base64(s)[:-1]
    if altchars is not None:
        if not isinstance(altchars, bytes_types):
            raise TypeError("expected bytes, not %s" % altchars.__class__.__name__)
        assert len(altchars) == 2, repr(altchars)
        return encoded.translate(bytes.maketrans(b"+/", altchars))
    return encoded
