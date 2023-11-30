import uos


class Creds:
    CRED_FILE = "config/credentials.env"

    def __init__(
        self,
        ssid=None,
        password=None,
        soliskey=None,
        solissecret=None,
        solisid=None,
        solissn=None,
    ):
        self.ssid = ssid
        self.password = password
        self.soliskey = soliskey
        self.solissecret = solissecret
        self.solisid = solisid
        self.solissn = solissn

    def write(self):
        """Write credentials to CRED_FILE if valid input found."""
        if self.is_valid():
            print("writing credentials to {:s}".format(self.CRED_FILE))
            with open(self.CRED_FILE, "wb") as f:
                f.write(
                    b",".join(
                        [
                            self.ssid,
                            self.password,
                            self.soliskey,
                            self.solissecret,
                            self.solisid,
                            self.solissn,
                        ]
                    )
                )
            f.close()

    def load(self):
        try:
            with open(self.CRED_FILE, "rb") as f:
                contents = f.read().split(b",")
            print("Loaded WiFi credentials from {:s}".format(self.CRED_FILE))
            if len(contents) == 6:
                (
                    self.ssid,
                    self.password,
                    self.soliskey,
                    self.solissecret,
                    self.solisid,
                    self.solissn,
                ) = contents
            if not self.is_valid():
                self.remove()
        except OSError:
            pass

        return self

    def remove(self):
        """
        1. Delete credentials file from disk.
        2. Set ssid and password to None
        """
        print("Attempting to remove {}".format(self.CRED_FILE))
        try:
            uos.remove(self.CRED_FILE)
        except OSError:
            pass

        self.ssid = self.password = None
        self.soliskey = self.solissecret = None
        self.solisid = self.solissn = None

    def is_valid(self):
        # Ensure the credentials are entered as bytes
        if not isinstance(self.ssid, bytes):
            return False
        if not isinstance(self.password, bytes):
            return False
        if not isinstance(self.soliskey, bytes):
            return False
        if not isinstance(self.solissecret, bytes):
            return False
        if not isinstance(self.solisid, bytes):
            return False
        if not isinstance(self.solissn, bytes):
            return False

        print("validity OK")
        # Ensure credentials are not None or empty
        return all(
            (
                self.ssid,
                self.password,
                self.soliskey,
                self.solissecret,
                self.solisid,
                self.solissn,
            )
        )
